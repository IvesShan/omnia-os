"""
飞书 WebSocket 机器人 - 集成到 Omnia 主服务

作为后台线程运行，共享 Omnia 的 API Provider 配置。
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import requests
from datetime import datetime
from typing import Callable, Optional

# 飞书 SDK
try:
    import lark_oapi as lark
    from lark_oapi.ws import Client as WSClient
    from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
    FEISHU_SDK_AVAILABLE = True
except ImportError:
    FEISHU_SDK_AVAILABLE = False


class FeishuBot:
    """飞书机器人，集成到 Omnia 主服务"""
    
    def __init__(
        self,
        app_id: str,
        app_secret: str,
        omnia_api_url: str = "http://127.0.0.1:5001/api/chat",
        get_provider: Optional[Callable[[], str]] = None,
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self.omnia_api_url = omnia_api_url
        self.get_provider = get_provider  # 获取当前 API Provider 的回调
        
        self.access_token: Optional[str] = None
        self.token_expires: float = 0
        
        self.ws_client: Optional[WSClient] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        self._lock = threading.Lock()
    
    def refresh_token(self) -> bool:
        """获取 tenant_access_token"""
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        try:
            resp = requests.post(url, json={
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                self.access_token = data["tenant_access_token"]
                self.token_expires = time.time() + data.get("expire", 7200) - 300
                print(f"[Feishu] Token 刷新成功，有效期 {data.get('expire')}秒")
                return True
            else:
                print(f"[Feishu] Token 刷新失败: {data}")
                return False
        except Exception as e:
            print(f"[Feishu] Token 刷新异常: {e}")
            return False
    
    def send_message(self, chat_id: str, text: str) -> bool:
        """发送文本消息"""
        with self._lock:
            if not self.access_token or time.time() > self.token_expires:
                if not self.refresh_token():
                    return False
            
            url = "https://open.feishu.cn/open-apis/im/v1/messages"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            try:
                resp = requests.post(
                    url,
                    params={"receive_id_type": "chat_id"},
                    json={
                        "receive_id": chat_id,
                        "msg_type": "text",
                        "content": json.dumps({"text": text})
                    },
                    headers=headers,
                    timeout=10
                )
                
                data = resp.json()
                if data.get("code") == 0:
                    print(f"[Feishu] 消息发送成功")
                    return True
                else:
                    print(f"[Feishu] 消息发送失败: {data}")
                    return False
            except Exception as e:
                print(f"[Feishu] 消息发送异常: {e}")
                return False
    
    def call_omnia(self, message: str, user_id: str) -> str:
        """调用 Omnia API，使用当前 Provider"""
        # 获取当前 Provider（通过回调）
        provider = None
        if self.get_provider:
            provider = self.get_provider()
        
        try:
            payload = {
                "message": message,
                "user_id": user_id,
                "history": []
            }
            if provider:
                payload["provider"] = provider
            
            resp = requests.post(
                self.omnia_api_url,
                json=payload,
                timeout=120
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return data.get("reply", "抱歉，我暂时无法回复")
            else:
                return f"Omnia API 错误: {resp.status_code}"
        except Exception as e:
            return f"连接 Omnia 失败: {e}"
    
    def _on_message_receive(self, data):
        """处理消息事件"""
        try:
            event = data.event
            message = event.message
            sender = event.sender
            
            msg_type = message.message_type
            content_str = message.content
            chat_id = message.chat_id
            user_id = sender.sender_id.open_id
            
            print(f"\n{'='*50}", flush=True)
            print(f"📨 收到飞书消息 [{datetime.now().strftime('%H:%M:%S')}]", flush=True)
            print(f"   用户: {user_id}", flush=True)
            print(f"   类型: {msg_type}", flush=True)
            
            if msg_type == "text":
                try:
                    content = json.loads(content_str)
                    text = content.get("text", "")
                except:
                    text = content_str
                
                print(f"   内容: {text[:50]}...", flush=True)
                
                # 调用 Omnia
                reply = self.call_omnia(text, user_id)
                print(f"   回复: {reply[:50]}...", flush=True)
                
                # 发送回复
                self.send_message(chat_id, reply)
                
        except Exception as e:
            print(f"[Feishu] 处理消息失败: {e}", flush=True)
            import traceback
            traceback.print_exc()
    
    def start(self) -> bool:
        """启动飞书机器人（后台线程）"""
        if not FEISHU_SDK_AVAILABLE:
            print("[Feishu] SDK 未安装，跳过启动")
            return False
        
        if self.running:
            print("[Feishu] 机器人已在运行")
            return True
        
        # 刷新 Token
        if not self.refresh_token():
            print("[Feishu] Token 获取失败，无法启动")
            return False
        
        self.running = True
        self._stop_event.clear()
        
        def _run_ws():
            """在新线程中运行 WebSocket，使用独立的事件循环"""
            # 为这个线程创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 创建事件处理器
                event_handler = EventDispatcherHandler.builder("", "") \
                    .register_p2_im_message_receive_v1(self._on_message_receive) \
                    .build()
                
                # 创建 WebSocket 客户端
                self.ws_client = WSClient(
                    app_id=self.app_id,
                    app_secret=self.app_secret,
                    event_handler=event_handler,
                    log_level=lark.LogLevel.ERROR
                )
                
                print("[Feishu] ✅ WebSocket 客户端已启动")
                print("[Feishu] 📡 开始监听飞书消息...")
                
                # 阻塞运行 - 使用这个线程的事件循环
                loop.run_until_complete(self._run_ws_async())
                
            except Exception as e:
                print(f"[Feishu] WebSocket 运行异常: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.running = False
                try:
                    loop.close()
                except:
                    pass
        
        # 启动后台线程
        self.thread = threading.Thread(target=_run_ws, daemon=True, name="FeishuBot")
        self.thread.start()
        
        # 等待一下确认启动成功
        time.sleep(1)
        
        return self.running
    
    async def _run_ws_async(self):
        """异步运行 WebSocket"""
        try:
            # 使用 SDK 的内部方法运行
            await self.ws_client._connect()
            # 保持运行直到停止
            while self.running and not self._stop_event.is_set():
                await asyncio.sleep(1)
        except Exception as e:
            print(f"[Feishu] WebSocket 异步运行异常: {e}")
            import traceback
            traceback.print_exc()
    
    def stop(self):
        """停止飞书机器人"""
        self.running = False
        self._stop_event.set()
        print("[Feishu] 机器人已停止")


# 全局实例（在 web_server.py 中初始化）
_feishu_bot: Optional[FeishuBot] = None


def init_feishu_bot(
    app_id: str,
    app_secret: str,
    omnia_api_url: str = "http://127.0.0.1:5001/api/chat",
    get_provider: Optional[Callable[[], str]] = None,
) -> Optional[FeishuBot]:
    """初始化飞书机器人"""
    global _feishu_bot
    
    if not FEISHU_SDK_AVAILABLE:
        print("[Feishu] SDK 未安装，跳过初始化")
        return None
    
    if not app_id or not app_secret:
        print("[Feishu] 配置缺失，跳过初始化")
        return None
    
    _feishu_bot = FeishuBot(
        app_id=app_id,
        app_secret=app_secret,
        omnia_api_url=omnia_api_url,
        get_provider=get_provider,
    )
    
    return _feishu_bot


def get_feishu_bot() -> Optional[FeishuBot]:
    """获取飞书机器人实例"""
    return _feishu_bot


def start_feishu_bot() -> bool:
    """启动飞书机器人"""
    global _feishu_bot
    if _feishu_bot:
        return _feishu_bot.start()
    return False


def stop_feishu_bot():
    """停止飞书机器人"""
    global _feishu_bot
    if _feishu_bot:
        _feishu_bot.stop()
