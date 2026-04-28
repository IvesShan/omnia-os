"""
from core.logging_config import get_logger

logger = get_logger(__name__)

Feishu Adapter - 飞书/Lark 通道适配器

支持：
- 接收飞书消息
- 发送消息到飞书
- Webhook 和 WebSocket 两种连接模式

Usage:
    from core.gateway.feishu_adapter import FeishuAdapter
    
    adapter = FeishuAdapter(
        app_id="cli_xxx",
        app_secret="xxx",
        connection_mode="websocket"  # or "webhook"
    )
    await adapter.start()
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from datetime import datetime
from typing import Any, Callable, Awaitable

from .runner import ChannelAdapter, ChannelType, MessageEvent


class FeishuAdapter(ChannelAdapter):
    """飞书适配器"""
    
    channel_type = ChannelType.FEISHU
    
    def __init__(
        self,
        app_id: str,
        app_secret: str,
        connection_mode: str = "websocket",
        on_message: Callable[[MessageEvent], Awaitable[None]] | None = None,
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self.connection_mode = connection_mode
        self._on_message = on_message
        self._running = False
        self._ws = None
        self._access_token = None
        self._token_expires = 0
    
    async def start(self):
        """启动适配器"""
        self._running = True
        
        # 获取 access_token
        await self._refresh_token()
        
        if self.connection_mode == "websocket":
            # WebSocket 长连接模式
            asyncio.create_task(self._ws_loop())
        else:
            # Webhook 模式由外部 HTTP 服务触发
            logger.info(f"[FeishuAdapter] Started in webhook mode")
    
    async def stop(self):
        """停止适配器"""
        self._running = False
        if self._ws:
            await self._ws.close()
    
    async def send(self, target: str, content: str, **kwargs) -> bool:
        """发送消息
        
        Args:
            target: open_id 或 chat_id
            content: 消息内容（文本或卡片）
        """
        import aiohttp
        
        if not self._access_token:
            await self._refresh_token()
        
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        
        # 判断是 open_id 还是 chat_id
        receive_id_type = "open_id" if target.startswith("ou_") else "chat_id"
        
        # 构建消息体
        if content.startswith("{"):
            # JSON 格式，可能是卡片
            msg_type = "interactive"
            content_body = content
        else:
            # 纯文本
            msg_type = "text"
            content_body = json.dumps({"text": content})
        
        params = {
            "receive_id_type": receive_id_type,
            "receive_id": target,
            "msg_type": msg_type,
            "content": content_body,
        }
        
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    params={"receive_id_type": receive_id_type},
                    json={
                        "receive_id": target,
                        "msg_type": msg_type,
                        "content": content_body,
                    },
                    headers=headers,
                ) as resp:
                    data = await resp.json()
                    if data.get("code") == 0:
                        print(f"[FeishuAdapter] Message sent to {target}")
                        return True
                    else:
                        print(f"[FeishuAdapter] Send failed: {data}")
                        return False
        except (ValueError) as e:
            print(f"[FeishuAdapter] Send error: {e}")
            return False
    
    async def get_me(self) -> dict:
        """获取机器人信息"""
        if not self._access_token:
            await self._refresh_token()
        
        import aiohttp
        
        url = "https://open.feishu.cn/open-apis/bot/v3/info"
        headers = {"Authorization": f"Bearer {self._access_token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                return data.get("bot", {})
    
    def on_message(self, handler: Callable[[MessageEvent], Awaitable[None]]):
        """注册消息处理器"""
        self._on_message = handler
    
    async def handle_webhook(self, event: dict) -> dict:
        """处理 Webhook 事件
        
        Args:
            event: 飞书推送的事件体
        
        Returns:
            响应体
        """
        # URL 验证
        if event.get("type") == "url_verification":
            return {"challenge": event.get("challenge")}
        
        # 消息事件
        if event.get("header", {}).get("event_type") == "im.message.receive_v1":
            await self._handle_message_event(event)
        
        return {"code": 0}
    
    async def _handle_message_event(self, event: dict):
        """处理消息事件"""
        body = event.get("event", {})
        message = body.get("message", {})
        sender = body.get("sender", {})
        
        msg_event = MessageEvent(
            channel=ChannelType.FEISHU,
            user_id=sender.get("sender_id", {}).get("open_id", "unknown"),
            chat_id=message.get("chat_id", "unknown"),
            message_id=message.get("message_id", "unknown"),
            content=self._extract_content(message),
            metadata={
                "message_type": message.get("message_type"),
                "create_time": message.get("create_time"),
            },
        )
        
        if self._on_message:
            await self._on_message(msg_event)
    
    def _extract_content(self, message: dict) -> str:
        """提取消息内容"""
        msg_type = message.get("message_type", "text")
        content = message.get("content", "{}")
        
        if msg_type == "text":
            try:
                data = json.loads(content)
                return data.get("text", "")
            except (json.JSONDecodeError) as e:
                return content
        
        # 其他类型暂不支持
        return f"[{msg_type}]"
    
    async def _refresh_token(self):
        """刷新 access_token"""
        import aiohttp
        
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={
                    "app_id": self.app_id,
                    "app_secret": self.app_secret,
                }
            ) as resp:
                data = await resp.json()
                self._access_token = data.get("tenant_access_token")
                self._token_expires = datetime.now().timestamp() + data.get("expire", 7200) - 300
                print(f"[FeishuAdapter] Token refreshed, expires in {data.get('expire')}s")
    
    async def _ws_loop(self):
        """WebSocket 长连接循环"""
        
        while self._running:
            try:
                await self._ws_connect()
            except Exception as e:
                print(f"[FeishuAdapter] WS error: {e}")
                await asyncio.sleep(5)
    
    async def _ws_connect(self):
        """建立 WebSocket 连接"""
        import aiohttp
        
        # 获取 WS 端点
        if not self._access_token:
            await self._refresh_token()
        
        url = "https://open.feishu.cn/open-apis/event/v4/websocket"
        headers = {"Authorization": f"Bearer {self._access_token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(url, headers=headers) as ws:
                self._ws = ws
                logger.info(f"[FeishuAdapter] WebSocket connected")
                
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        await self._handle_ws_message(data)
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print(f"[FeishuAdapter] WS error: {ws.exception()}")
                        break
    
    async def _handle_ws_message(self, data: dict):
        """处理 WebSocket 消息"""
        # 心跳响应
        if data.get("type") == "pong":
            return
        
        # 事件消息
        if data.get("type") == "event":
            await self._handle_message_event(data)


def verify_signature(timestamp: str, nonce: str, body: str, signature: str, app_secret: str) -> bool:
    """验证飞书签名
    
    Args:
        timestamp: 请求头中的 X-Lark-Request-Timestamp
        nonce: 请求头中的 X-Lark-Request-Nonce
        body: 请求体
        signature: 请求头中的 X-Lark-Signature
        app_secret: 飞书应用密钥
    """
    token = app_secret
    content = f"{timestamp}{nonce}{token}{body}"
    
    expected = hashlib.sha256(content.encode()).hexdigest()
    
    return hmac.compare(expected, signature)
