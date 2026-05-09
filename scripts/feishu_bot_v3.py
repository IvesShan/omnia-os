#!/usr/bin/env python3
"""
飞书 WebSocket 长连接机器人 v3
修复路径问题，简化依赖
"""

import os
import sys
import json
import asyncio
import requests
from datetime import datetime

# 强制禁用缓冲
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

# 加载 .env
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ[key.strip()] = value.strip()

APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")

# Omnia API 地址
OMNIA_API = "http://127.0.0.1:5001/api/chat"

print("=" * 60, flush=True)
print("🤖 飞书 WebSocket 机器人 v3", flush=True)
print("=" * 60, flush=True)
print(f"APP_ID: {APP_ID[:12]}...", flush=True)
print(f"Omnia API: {OMNIA_API}", flush=True)
print(flush=True)

class FeishuBot:
    def __init__(self, app_id, app_secret):
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token = None
        self.token_expires = 0
    
    def refresh_token(self):
        """获取 tenant_access_token"""
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        resp = requests.post(url, json={
            "app_id": self.app_id,
            "app_secret": self.app_secret
        })
        data = resp.json()
        if data.get("code") == 0:
            self.access_token = data["tenant_access_token"]
            self.token_expires = datetime.now().timestamp() + data.get("expire", 7200) - 300
            print(f"[Token] 刷新成功，有效期 {data.get('expire')}秒", flush=True)
            return True
        else:
            print(f"[Token] 刷新失败: {data}", flush=True)
            return False
    
    def send_message(self, chat_id, text):
        """发送文本消息"""
        if not self.access_token:
            self.refresh_token()
        
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        resp = requests.post(
            url,
            params={"receive_id_type": "chat_id"},
            json={
                "receive_id": chat_id,
                "msg_type": "text",
                "content": json.dumps({"text": text})
            },
            headers=headers
        )
        
        data = resp.json()
        if data.get("code") == 0:
            print(f"[Send] 消息发送成功", flush=True)
            return True
        else:
            print(f"[Send] 发送失败: {data}", flush=True)
            return False
    
    def call_omnia(self, message, user_id):
        """调用 Omnia API"""
        try:
            resp = requests.post(
                OMNIA_API,
                json={
                    "message": message,
                    "user_id": user_id,
                    "history": []
                },
                timeout=60
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("reply", "抱歉，我暂时无法回复")
            else:
                return f"Omnia API 错误: {resp.status_code}"
        except Exception as e:
            return f"连接 Omnia 失败: {e}"

def main():
    # 检查 Omnia API 是否可用
    try:
        resp = requests.get("http://127.0.0.1:5001/health", timeout=5)
        if resp.status_code == 200:
            print("✅ Omnia API 可用", flush=True)
        else:
            print("⚠️ Omnia API 状态异常", flush=True)
    except:
        print("⚠️ Omnia API 未启动，请先启动 Omnia 服务", flush=True)
    
    bot = FeishuBot(APP_ID, APP_SECRET)
    
    # 刷新 token
    if not bot.refresh_token():
        print("❌ 无法获取 access_token，请检查 APP_ID 和 APP_SECRET", flush=True)
        return
    
    # 使用 lark-oapi WebSocket
    try:
        import lark_oapi as lark
        from lark_oapi.ws import Client as WSClient
        from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
        
        print("✅ lark_oapi 导入成功", flush=True)
        
        def on_message_receive(data):
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
                print(f"📨 收到消息 [{datetime.now().strftime('%H:%M:%S')}]", flush=True)
                print(f"   用户: {user_id}", flush=True)
                print(f"   类型: {msg_type}", flush=True)
                
                if msg_type == "text":
                    content = json.loads(content_str)
                    text = content.get("text", "")
                    print(f"   内容: {text[:50]}...", flush=True)
                    
                    # 调用 Omnia
                    reply = bot.call_omnia(text, user_id)
                    print(f"   回复: {reply[:50]}...", flush=True)
                    
                    # 发送回复
                    bot.send_message(chat_id, reply)
                    
            except Exception as e:
                print(f"❌ 处理消息失败: {e}", flush=True)
                import traceback
                traceback.print_exc()
        
        # 创建事件处理器
        event_handler = EventDispatcherHandler.builder("", "") \
            .register_p2_im_message_receive_v1(on_message_receive) \
            .build()
        
        print("✅ 事件处理器创建成功", flush=True)
        print("\n📡 开始监听飞书消息...", flush=True)
        print("   在飞书中给机器人发消息试试！", flush=True)
        print("   按 Ctrl+C 停止\n", flush=True)
        
        # 创建 WebSocket 客户端
        ws_client = WSClient(
            app_id=APP_ID,
            app_secret=APP_SECRET,
            event_handler=event_handler,
            log_level=lark.LogLevel.ERROR  # 减少日志
        )
        
        # 启动监听
        ws_client.start()
        
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}", flush=True)
        print("   请运行: pip install lark-oapi", flush=True)
    except KeyboardInterrupt:
        print("\n\n👋 机器人已停止", flush=True)
    except Exception as e:
        print(f"❌ 启动失败: {e}", flush=True)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
