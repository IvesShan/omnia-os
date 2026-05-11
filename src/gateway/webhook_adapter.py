"""Webhook Adapter - Generic webhook integration.

Allows external services to send messages to Omnia via HTTP webhooks.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
from datetime import datetime
from typing import Any, Callable, Awaitable, Optional

from core.gateway.runner import ChannelAdapter, ChannelType, MessageEvent
from core.logging_config import get_logger

logger = get_logger(__name__)


class WebhookAdapter(ChannelAdapter):
    """Webhook 适配器 - 接收外部服务的 HTTP 回调"""
    
    channel_type = ChannelType.WEBHOOK
    
    def __init__(
        self,
        on_message: Callable[[MessageEvent], Awaitable[None]] | None = None,
        secret: Optional[str] = None,
    ):
        self._on_message = on_message
        self._secret = secret
        self._running = False
        self._pending_responses: dict[str, asyncio.Queue] = {}
        self._message_handlers: dict[str, Callable] = {}  # webhook_id -> handler
    
    async def start(self):
        """启动适配器"""
        self._running = True
        logger.info("[WebhookAdapter] ✓ Started")
    
    async def stop(self):
        """停止适配器"""
        self._running = False
        logger.info("[WebhookAdapter] ✓ Stopped")
    
    async def send(self, target: str, content: str, **kwargs) -> bool:
        """
        发送消息（Webhook 通常是单向的，但可以支持回调 URL）
        
        Args:
            target: webhook_id 或 callback_url
            content: 消息内容
            **kwargs: callback_url, method, headers 等
        """
        callback_url = kwargs.get("callback_url") or target
        
        if callback_url.startswith("http"):
            # 发送 HTTP 回调
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    payload = {
                        "content": content,
                        "timestamp": datetime.now().isoformat(),
                        "source": "omnia"
                    }
                    headers = kwargs.get("headers", {})
                    
                    async with session.post(
                        callback_url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        if resp.status == 200:
                            logger.info(f"[WebhookAdapter] Callback sent to {callback_url}")
                            return True
                        else:
                            logger.warning(f"[WebhookAdapter] Callback failed: {resp.status}")
                            return False
            except Exception as e:
                logger.error(f"[WebhookAdapter] Callback error: {e}")
                return False
        
        # 如果有注册的队列，放入队列
        if target in self._pending_responses:
            queue = self._pending_responses[target]
            await queue.put(content)
            return True
        
        return False
    
    async def get_me(self) -> dict:
        """获取机器人信息"""
        return {
            "id": "omnia-webhook",
            "name": "Omnia Webhook",
            "channel": "webhook",
        }
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """验证 webhook 签名（可选）"""
        if not self._secret:
            return True  # 未配置密钥，跳过验证
        
        expected = hmac.new(
            self._secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected}", signature)
    
    async def receive_webhook(
        self,
        webhook_id: str,
        payload: dict,
        headers: Optional[dict] = None,
    ) -> dict:
        """
        接收来自外部服务的 webhook 调用
        
        这个方法由 FastAPI 路由调用
        
        Args:
            webhook_id: Webhook 标识符
            payload: Webhook 负载
            headers: HTTP 头
        
        Returns:
            响应数据
        """
        if not self._running:
            return {"error": "Adapter not running"}
        
        # 验证签名（如果有）
        if headers and "X-Webhook-Signature" in headers:
            import json
            payload_bytes = json.dumps(payload).encode()
            signature = headers["X-Webhook-Signature"]
            
            if not self.verify_signature(payload_bytes, signature):
                logger.warning(f"[WebhookAdapter] Invalid signature for webhook {webhook_id}")
                return {"error": "Invalid signature"}
        
        # 提取消息内容
        content = payload.get("content") or payload.get("message") or payload.get("text", "")
        user_id = payload.get("user_id") or payload.get("sender") or "webhook_user"
        chat_id = payload.get("chat_id") or payload.get("channel") or webhook_id
        
        # 创建消息事件
        if self._on_message and content:
            event = MessageEvent(
                channel=ChannelType.WEBHOOK,
                user_id=user_id,
                chat_id=chat_id,
                message_id=f"webhook_{datetime.now().timestamp()}",
                content=content,
                timestamp=datetime.now(),
                metadata={
                    "webhook_id": webhook_id,
                    "payload": payload,
                    "headers": headers,
                }
            )
            
            await self._on_message(event)
        
        # 检查是否有自定义处理器
        if webhook_id in self._message_handlers:
            handler = self._message_handlers[webhook_id]
            result = await handler(payload, headers)
            return result or {"status": "ok"}
        
        return {"status": "received"}
    
    def register_handler(self, webhook_id: str, handler: Callable):
        """注册特定 webhook 的处理器"""
        self._message_handlers[webhook_id] = handler
        logger.info(f"[WebhookAdapter] Registered handler for webhook: {webhook_id}")
    
    def unregister_handler(self, webhook_id: str):
        """注销 webhook 处理器"""
        self._message_handlers.pop(webhook_id, None)


__all__ = ["WebhookAdapter"]
