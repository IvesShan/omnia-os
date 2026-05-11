"""WebSocket Adapter - Real-time bidirectional communication.

Provides WebSocket connectivity for real-time applications.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Callable, Awaitable, Optional, Dict, Set

from core.gateway.runner import ChannelAdapter, ChannelType, MessageEvent
from core.logging_config import get_logger

logger = get_logger(__name__)


class WebSocketAdapter(ChannelAdapter):
    """WebSocket 适配器 - 实时双向通信"""
    
    channel_type = ChannelType.WEBSOCKET
    
    def __init__(
        self,
        on_message: Callable[[MessageEvent], Awaitable[None]] | None = None,
    ):
        self._on_message = on_message
        self._running = False
        
        # 连接管理
        self._connections: Dict[str, Any] = {}  # connection_id -> websocket
        self._user_connections: Dict[str, Set[str]] = {}  # user_id -> set of connection_ids
        self._connection_users: Dict[str, str] = {}  # connection_id -> user_id
    
    async def start(self):
        """启动适配器"""
        self._running = True
        logger.info("[WebSocketAdapter] ✓ Started")
    
    async def stop(self):
        """停止适配器"""
        self._running = False
        
        # 关闭所有连接
        for conn_id, ws in self._connections.items():
            try:
                await ws.close()
            except Exception as e:
                logger.warning(f"[WebSocketAdapter] Error closing connection {conn_id}: {e}")
        
        self._connections.clear()
        self._user_connections.clear()
        self._connection_users.clear()
        
        logger.info("[WebSocketAdapter] ✓ Stopped")
    
    async def send(self, target: str, content: str, **kwargs) -> bool:
        """
        发送消息到 WebSocket 连接
        
        Args:
            target: connection_id 或 user_id
            content: 消息内容
            **kwargs: message_type, data 等
        """
        if not self._running:
            return False
        
        message_type = kwargs.get("message_type", "text")
        data = kwargs.get("data", {})
        
        message = json.dumps({
            "type": message_type,
            "content": content,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        })
        
        # 如果 target 是 connection_id
        if target in self._connections:
            try:
                ws = self._connections[target]
                await ws.send_text(message)
                return True
            except Exception as e:
                logger.error(f"[WebSocketAdapter] Error sending to {target}: {e}")
                # 移除失效连接
                await self._remove_connection(target)
                return False
        
        # 如果 target 是 user_id，发送到该用户的所有连接
        if target in self._user_connections:
            success = False
            for conn_id in self._user_connections[target].copy():
                if conn_id in self._connections:
                    try:
                        ws = self._connections[conn_id]
                        await ws.send_text(message)
                        success = True
                    except Exception as e:
                        logger.error(f"[WebSocketAdapter] Error sending to {conn_id}: {e}")
                        await self._remove_connection(conn_id)
            return success
        
        logger.warning(f"[WebSocketAdapter] Target not found: {target}")
        return False
    
    async def broadcast(self, content: str, **kwargs) -> int:
        """
        广播消息到所有连接
        
        Returns:
            成功发送的连接数
        """
        if not self._running:
            return 0
        
        message_type = kwargs.get("message_type", "broadcast")
        data = kwargs.get("data", {})
        
        message = json.dumps({
            "type": message_type,
            "content": content,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        })
        
        success_count = 0
        for conn_id in list(self._connections.keys()):
            try:
                ws = self._connections[conn_id]
                await ws.send_text(message)
                success_count += 1
            except Exception as e:
                logger.error(f"[WebSocketAdapter] Error broadcasting to {conn_id}: {e}")
                await self._remove_connection(conn_id)
        
        return success_count
    
    async def get_me(self) -> dict:
        """获取机器人信息"""
        return {
            "id": "omnia-websocket",
            "name": "Omnia WebSocket",
            "channel": "websocket",
            "connections": len(self._connections),
        }
    
    async def register_connection(
        self,
        connection_id: str,
        websocket: Any,
        user_id: Optional[str] = None,
    ):
        """
        注册新的 WebSocket 连接
        
        Args:
            connection_id: 连接 ID
            websocket: WebSocket 对象
            user_id: 用户 ID（可选）
        """
        self._connections[connection_id] = websocket
        
        if user_id:
            self._connection_users[connection_id] = user_id
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(connection_id)
        
        logger.info(f"[WebSocketAdapter] Connection registered: {connection_id} (user: {user_id})")
    
    async def _remove_connection(self, connection_id: str):
        """移除连接"""
        self._connections.pop(connection_id, None)
        
        # 移除用户映射
        user_id = self._connection_users.pop(connection_id, None)
        if user_id and user_id in self._user_connections:
            self._user_connections[user_id].discard(connection_id)
            if not self._user_connections[user_id]:
                del self._user_connections[user_id]
        
        logger.info(f"[WebSocketAdapter] Connection removed: {connection_id}")
    
    async def handle_message(
        self,
        connection_id: str,
        message: str,
    ):
        """
        处理来自 WebSocket 的消息
        
        Args:
            connection_id: 连接 ID
            message: 消息内容（JSON 字符串）
        """
        if not self._running or not self._on_message:
            return
        
        try:
            data = json.loads(message)
            content = data.get("content") or data.get("message") or message
            message_type = data.get("type", "text")
            
            user_id = self._connection_users.get(connection_id, connection_id)
            
            # 创建消息事件
            event = MessageEvent(
                channel=ChannelType.WEBSOCKET,
                user_id=user_id,
                chat_id=connection_id,
                message_id=f"ws_{datetime.now().timestamp()}",
                content=content,
                timestamp=datetime.now(),
                metadata={
                    "connection_id": connection_id,
                    "message_type": message_type,
                    "raw_data": data,
                }
            )
            
            await self._on_message(event)
            
        except json.JSONDecodeError:
            # 非 JSON 消息，当作纯文本处理
            user_id = self._connection_users.get(connection_id, connection_id)
            
            event = MessageEvent(
                channel=ChannelType.WEBSOCKET,
                user_id=user_id,
                chat_id=connection_id,
                message_id=f"ws_{datetime.now().timestamp()}",
                content=message,
                timestamp=datetime.now(),
                metadata={
                    "connection_id": connection_id,
                }
            )
            
            await self._on_message(event)
        
        except Exception as e:
            logger.error(f"[WebSocketAdapter] Error handling message: {e}")
    
    def get_connections(self) -> dict:
        """获取连接统计"""
        return {
            "total_connections": len(self._connections),
            "total_users": len(self._user_connections),
            "connections": list(self._connections.keys()),
            "users": list(self._user_connections.keys()),
        }


__all__ = ["WebSocketAdapter"]
