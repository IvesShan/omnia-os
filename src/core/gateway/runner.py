"""
Gateway Runner - Omnia 2.0

参考：OpenClaw Gateway + Hermes Gateway
目的：统一消息入口，支持多通道

支持通道：
- Telegram
- Discord
- Signal
- WhatsApp
- Slack
- Email
- WebChat
- CLI
- API

Usage:
    from core.gateway.runner import GatewayRunner
    
    runner = GatewayRunner()
    await runner.register_adapter("telegram", TelegramAdapter())
    await runner.start()
"""

from __future__ import annotations

from core.config import OMNIA_HOME
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Awaitable
import asyncio
import json


class ChannelType(Enum):
    """通道类型"""
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SIGNAL = "signal"
    WHATSAPP = "whatsapp"
    SLACK = "slack"
    EMAIL = "email"
    WEBCHAT = "webchat"
    CLI = "cli"
    API = "api"
    FEISHU = "feishu"
    LARK = "lark"


@dataclass
class MessageEvent:
    """消息事件"""
    channel: ChannelType
    user_id: str
    chat_id: str
    message_id: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    reply_to: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class DeliveryMessage:
    """投递消息"""
    target: str          # 目标用户/群组 ID
    content: str
    channel: ChannelType
    priority: int = 0    # 优先级
    scheduled_at: datetime | None = None
    metadata: dict = field(default_factory=dict)


class ChannelAdapter(ABC):
    """通道适配器基类"""
    
    channel_type: ChannelType
    
    @abstractmethod
    async def start(self):
        """启动适配器"""
        pass
    
    @abstractmethod
    async def stop(self):
        """停止适配器"""
        pass
    
    @abstractmethod
    async def send(self, target: str, content: str, **kwargs) -> bool:
        """发送消息"""
        pass
    
    @abstractmethod
    async def get_me(self) -> dict:
        """获取机器人信息"""
        pass
    
    def on_message(self, handler: Callable[[MessageEvent], Awaitable[None]]):
        """注册消息处理器"""
        self._message_handler = handler


class SessionStore:
    """会话存储"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(OMNIA_HOME / "sessions.json")
        self._sessions: dict[str, dict] = {}
        self._load()
    
    def _load(self):
        """加载会话"""
        try:
            import json
            from pathlib import Path
            if Path(self.db_path).exists():
                self._sessions = json.loads(Path(self.db_path).read_text())
        except:
            self._sessions = {}
    
    def _save(self):
        """保存会话"""
        from pathlib import Path
        Path(self.db_path).write_text(json.dumps(self._sessions, indent=2))
    
    def get_or_create(self, user_id: str, channel: ChannelType) -> dict:
        """获取或创建会话"""
        key = f"{channel.value}:{user_id}"
        if key not in self._sessions:
            self._sessions[key] = {
                "user_id": user_id,
                "channel": channel.value,
                "created_at": datetime.now().isoformat(),
                "message_count": 0,
                "context": {}
            }
            self._save()
        return self._sessions[key]
    
    def update(self, user_id: str, channel: ChannelType, updates: dict):
        """更新会话"""
        key = f"{channel.value}:{user_id}"
        if key in self._sessions:
            self._sessions[key].update(updates)
            self._sessions[key]["updated_at"] = datetime.now().isoformat()
            self._save()


class DeliveryQueue:
    """消息投递队列"""
    
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
    
    async def enqueue(self, msg: DeliveryMessage):
        """入队"""
        await self._queue.put(msg)
    
    async def dequeue(self) -> DeliveryMessage | None:
        """出队"""
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None
    
    async def start(self):
        """启动投递循环"""
        self._running = True
    
    async def stop(self):
        """停止投递循环"""
        self._running = False


class GatewayRunner:
    """
    网关运行器
    
    管理：
    - 通道适配器
    - 会话存储
    - 消息投递
    - Agent 调用
    """
    
    _instance: 'GatewayRunner' = None
    
    def __init__(self, agent_factory: Callable | None = None):
        self.adapters: dict[ChannelType, ChannelAdapter] = {}
        self.session_store = SessionStore()
        self.delivery_queue = DeliveryQueue()
        self.agent_factory = agent_factory
        self._running = False
    
    @classmethod
    def get_instance(cls) -> 'GatewayRunner':
        """获取全局单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def register_adapter(self, adapter: ChannelAdapter):
        """注册通道适配器"""
        self.adapters[adapter.channel_type] = adapter
        
        # 设置消息处理器
        async def handle_message(event: MessageEvent):
            await self._handle_inbound(event)
        
        adapter.on_message(handle_message)
    
    async def start(self):
        """启动网关"""
        self._running = True
        
        # 启动所有适配器
        for adapter in self.adapters.values():
            await adapter.start()
        
        # 启动投递循环
        asyncio.create_task(self._delivery_loop())
        
        print(f"[Gateway] Started with {len(self.adapters)} adapters")
    
    async def stop(self):
        """停止网关"""
        self._running = False
        
        for adapter in self.adapters.values():
            await adapter.stop()
    
    async def _handle_inbound(self, event: MessageEvent):
        """处理入站消息"""
        # 1. 获取/创建会话
        session = self.session_store.get_or_create(
            event.user_id, 
            event.channel
        )
        
        # 2. 创建 Agent
        if self.agent_factory:
            agent = self.agent_factory(session)
        else:
            # 默认：打印消息
            print(f"[Gateway] [{event.channel.value}] {event.user_id}: {event.content[:50]}...")
            return
        
        # 3. 运行 Agent
        response = await agent.run(event.content)
        
        # 4. 投递响应
        if response:
            await self.delivery_queue.enqueue(DeliveryMessage(
                target=event.chat_id,
                content=response,
                channel=event.channel
            ))
        
        # 5. 更新会话
        self.session_store.update(
            event.user_id,
            event.channel,
            {"message_count": session.get("message_count", 0) + 1}
        )
    
    async def _delivery_loop(self):
        """投递循环"""
        while self._running:
            msg = await self.delivery_queue.dequeue()
            if not msg:
                continue
            
            adapter = self.adapters.get(msg.channel)
            if not adapter:
                print(f"[Gateway] No adapter for {msg.channel}")
                continue
            
            try:
                await adapter.send(msg.target, msg.content, **msg.metadata)
            except Exception as e:
                print(f"[Gateway] Delivery failed: {e}")
    
    async def broadcast(self, content: str, channels: list[ChannelType] | None = None):
        """广播消息到所有/指定通道"""
        for channel_type, adapter in self.adapters.items():
            if channels and channel_type not in channels:
                continue
            
            # 获取该通道的所有活跃会话
            # TODO: 实现会话列表
            pass


# ============================================================================
# Simple WebChat Adapter (for testing)
# ============================================================================

class WebChatAdapter(ChannelAdapter):
    """WebChat 适配器（简化版）"""
    
    channel_type = ChannelType.WEBCHAT
    
    def __init__(self, port: int = 5001):
        self.port = port
        self._message_handler = None
    
    async def start(self):
        """启动（实际启动在 web_server.py）"""
        print(f"[WebChat] Adapter ready on port {self.port}")
    
    async def stop(self):
        """停止"""
        pass
    
    async def send(self, target: str, content: str, **kwargs) -> bool:
        """发送（WebChat 通过 WebSocket 推送）"""
        # 实际实现在 web_server.py
        return True
    
    async def get_me(self) -> dict:
        return {"id": "omnia", "name": "Omnia"}
