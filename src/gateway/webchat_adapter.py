"""
WebChat Adapter - Omnia Web 界面适配器

将 web_server.py 的消息转换为 Gateway 标准格式

Usage:
    from gateway.webchat_adapter import WebChatAdapter
    
    adapter = WebChatAdapter()
    await adapter.start()
    
    # 发送消息到 WebChat
    await adapter.send("user_123", "Hello!")
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Callable, Awaitable

from core.gateway.runner import ChannelAdapter, ChannelType, MessageEvent


class WebChatAdapter(ChannelAdapter):
    """WebChat 适配器"""
    
    channel_type = ChannelType.WEBCHAT
    
    def __init__(
        self,
        on_message: Callable[[MessageEvent], Awaitable[None]] | None = None,
    ):
        self._on_message = on_message
        self._running = False
        self._pending_responses: dict[str, asyncio.Queue] = {}
    
    async def start(self):
        """启动适配器"""
        self._running = True
        print("[WebChatAdapter] ✓ Started")
    
    async def stop(self):
        """停止适配器"""
        self._running = False
        print("[WebChatAdapter] ✓ Stopped")
    
    async def send(self, target: str, content: str, **kwargs) -> bool:
        """
        发送消息到 WebChat
        
        Args:
            target: chat_id 或 session_id
            content: 消息内容
        
        Returns:
            是否成功
        """
        # WebChat 的消息通过 SSE (Server-Sent Events) 推送
        # 这里将消息放入队列，由 web_server.py 的 SSE endpoint 取走
        
        if target in self._pending_responses:
            queue = self._pending_responses[target]
            await queue.put(content)
            return True
        
        print(f"[WebChatAdapter] No pending queue for target: {target}")
        return False
    
    async def get_me(self) -> dict:
        """获取机器人信息"""
        return {
            "id": "omnia",
            "name": "Omnia",
            "channel": "webchat",
        }
    
    def register_queue(self, chat_id: str, queue: asyncio.Queue):
        """注册响应队列（供 web_server.py 使用）"""
        self._pending_responses[chat_id] = queue
    
    def unregister_queue(self, chat_id: str):
        """注销响应队列"""
        self._pending_responses.pop(chat_id, None)
    
    async def receive_message(
        self,
        user_id: str,
        chat_id: str,
        content: str,
        metadata: dict | None = None,
    ) -> None:
        """
        接收来自 WebChat 的消息（供 web_server.py 调用）
        
        这个方法将 web_server.py 收到的消息转换为标准 MessageEvent，
        然后通过 Gateway Runner 分发给 Omnia 核心。
        """
        if not self._on_message:
            print("[WebChatAdapter] No message handler registered")
            return
        
        event = MessageEvent(
            channel=ChannelType.WEBCHAT,
            user_id=user_id,
            chat_id=chat_id,
            message_id=f"webchat_{datetime.now().timestamp()}",
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {},
        )
        
        await self._on_message(event)
