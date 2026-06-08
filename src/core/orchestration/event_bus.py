"""Event Bus — Omnia 的神经系统

模块间的解耦通信层。所有模块通过发布/订阅事件来交互，
不再直接 import 调用，彻底消除循环依赖。

支持：
- 同步/异步回调
- 优先级排序
- 通配符订阅 (* 匹配所有)
- 事件历史记录（可回放）
- 线程安全

用法：
    from core.orchestration.event_bus import EventBus, Event

    bus = EventBus.get()

    # 订阅
    @bus.on("chat.completed")
    def handle(context):
        print(f"收到消息: {context.data}")

    # 发布
    bus.emit("chat.completed", {"message": "你好"})

    # 通配符订阅（监控所有事件）
    @bus.on("*")
    def audit(context):
        log.write(context)
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, Deque, List, Optional, Set, Union

logger = logging.getLogger(__name__)

# ─── Event 定义 ────────────────────────────────────────────────────

@dataclass
class Event:
    """一个事件实例"""
    topic: str                          # 事件主题，如 "chat.completed"
    data: Dict[str, Any] = field(default_factory=dict)  # 事件数据
    source: str = ""                    # 来源模块
    timestamp: float = field(default_factory=time.time)
    cancelled: bool = False             # 可被回调取消

    def cancel(self):
        """阻止后续回调继续执行"""
        self.cancelled = True

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp,
        }


# ─── 回调包装 ─────────────────────────────────────────────────────

@dataclass
class Handler:
    """订阅回调的包装"""
    callback: Callable
    priority: int = 0           # 数字越小越先执行
    once: bool = False          # 只触发一次
    name: str = ""

    def __post_init__(self):
        if not self.name:
            self.name = getattr(self.callback, '__name__', repr(self.callback))


# ─── Event Bus ─────────────────────────────────────────────────────

CallbackFn = Union[
    Callable[[Event], Any],
    Callable[[Event], Coroutine],
]


class EventBus:
    """全局事件总线（单例模式）

    线程安全，支持同步/异步回调混合调用。
    """

    _instance: Optional['EventBus'] = None
    _lock_class = threading.Lock()

    def __init__(self, max_history: int = 500):
        # topic -> [Handler, ...]
        self._handlers: Dict[str, List[Handler]] = {}
        self._lock = threading.RLock()
        self._history: Deque[Event] = deque(maxlen=max_history)
        self._stats: Dict[str, int] = {}  # topic -> emit count

        # 默认内置事件主题（便于文档化和IDE提示）
        self.KNOWN_TOPICS: Set[str] = {
            # 对话生命周期
            "chat.started",
            "chat.completed",
            "chat.error",
            # 记忆系统
            "memory.added",
            "memory.consolidated",
            "memory.threshold",       # 记忆数量达到阈值
            # 知识图谱
            "graph.updated",
            "graph.new_entity",
            "graph.new_relation",
            # 工具执行
            "tool.before",
            "tool.after",
            "tool.error",
            # Agent
            "agent.started",
            "agent.completed",
            "agent.iteration",        # 每次循环
            # 工作流
            "workflow.step_complete",
            "workflow.complete",
            "workflow.error",
            # 系统
            "system.startup",
            "system.shutdown",
            "system.health_check",
            "system.idle",            # 空闲时
            # 用户
            "user.active",
            "user.idle",
    }

    @classmethod
    def get(cls) -> 'EventBus':
        """获取全局单例"""
        if cls._instance is None:
            with cls._lock_class:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """重置单例（测试用）"""
        with cls._lock_class:
            cls._instance = None

    # ─── 订阅 ──────────────────────────────────────────────────────

    def on(self, topic: str, priority: int = 0, once: bool = False) -> Callable:
        """装饰器：订阅事件

        @bus.on("chat.completed")
        def handle_chat(event: Event):
            ...

        @bus.on("*")  # 监听所有事件
        def audit(event: Event):
            ...
        """
        def decorator(func: CallbackFn) -> CallbackFn:
            handler = Handler(callback=func, priority=priority, once=once)
            self._subscribe(topic, handler)
            return func
        return decorator

    def subscribe(self, topic: str, callback: CallbackFn,
                  priority: int = 0, once: bool = False) -> Callable:
        """直接订阅（非装饰器用法）

        Returns: 取消订阅的函数
        """
        handler = Handler(callback=callback, priority=priority, once=once)
        self._subscribe(topic, handler)
        return lambda: self._unsubscribe(topic, handler)

    def _subscribe(self, topic: str, handler: Handler):
        with self._lock:
            if topic not in self._handlers:
                self._handlers[topic] = []
            self._handlers[topic].append(handler)
            self._handlers[topic].sort(key=lambda h: h.priority)
            logger.debug(f"[EventBus] Subscribed '{handler.name}' to '{topic}' (priority={handler.priority})")

    def _unsubscribe(self, topic: str, handler: Handler):
        with self._lock:
            if topic in self._handlers:
                self._handlers[topic] = [h for h in self._handlers[topic] if h is not handler]
                logger.debug(f"[EventBus] Unsubscribed '{handler.name}' from '{topic}'")

    # ─── 发布 ──────────────────────────────────────────────────────

    def emit(self, topic: str, data: Dict[str, Any] = None,
             source: str = "") -> Event:
        """发布事件（同步）

        Args:
            topic: 事件主题
            data: 事件数据
            source: 来源模块

        Returns:
            Event 对象（可检查是否被取消）
        """
        event = Event(topic=topic, data=data or {}, source=source)

        with self._lock:
            self._history.append(event)
            self._stats[topic] = self._stats.get(topic, 0) + 1

            # 收集匹配的回调（精确匹配 + 通配符）
            handlers = list(self._handlers.get(topic, []))
            wildcard_handlers = list(self._handlers.get("*", []))
            all_handlers = sorted(handlers + wildcard_handlers, key=lambda h: h.priority)

            # 记录需要移除的一次性回调
            to_remove: List[tuple[str, Handler]] = []

        # 在锁外执行回调（避免死锁）
        for handler in all_handlers:
            if event.cancelled:
                break

            try:
                result = handler.callback(event)

                # 如果是协程，调度到事件循环
                if asyncio.iscoroutine(result):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(result)
                    except RuntimeError:
                        # 没有运行中的事件循环，同步等待
                        asyncio.run(result)

                if handler.once:
                    to_remove.append((topic, handler))

            except Exception as e:
                logger.error(f"[EventBus] Handler '{handler.name}' for '{topic}' failed: {e}", exc_info=True)

        # 清理一次性回调
        for t, h in to_remove:
            self._unsubscribe(t, h)

        return event

    async def emit_async(self, topic: str, data: Dict[str, Any] = None,
                         source: str = "") -> Event:
        """发布事件（异步版本）"""
        event = Event(topic=topic, data=data or {}, source=source)

        with self._lock:
            self._history.append(event)
            self._stats[topic] = self._stats.get(topic, 0) + 1

            handlers = list(self._handlers.get(topic, []))
            wildcard_handlers = list(self._handlers.get("*", []))
            all_handlers = sorted(handlers + wildcard_handlers, key=lambda h: h.priority)
            to_remove: List[tuple[str, Handler]] = []

        for handler in all_handlers:
            if event.cancelled:
                break

            try:
                result = handler.callback(event)

                if asyncio.iscoroutine(result):
                    await result
                elif asyncio.isfuture(result):
                    await result

                if handler.once:
                    to_remove.append((topic, handler))

            except Exception as e:
                logger.error(f"[EventBus] Async handler '{handler.name}' for '{topic}' failed: {e}", exc_info=True)

        for t, h in to_remove:
            self._unsubscribe(t, h)

        return event

    # ─── 查询 ──────────────────────────────────────────────────────

    def history(self, topic: str = None, limit: int = 50) -> List[Event]:
        """查询事件历史"""
        with self._lock:
            events = list(self._history)

        if topic:
            events = [e for e in events if e.topic == topic or topic == "*"]

        return events[-limit:]

    def stats(self) -> Dict[str, int]:
        """各主题的发布次数"""
        with self._lock:
            return dict(self._stats)

    def subscribers(self, topic: str = None) -> Dict[str, int]:
        """各主题的订阅者数量"""
        with self._lock:
            if topic:
                return {topic: len(self._handlers.get(topic, []))}
            return {t: len(h) for t, h in self._handlers.items()}

    def known_topics(self) -> List[str]:
        """返回已知事件主题列表（用于文档/调试）"""
        return sorted(self.KNOWN_TOPICS)


# ─── 全局便捷函数 ─────────────────────────────────────────────────

def get_event_bus() -> EventBus:
    """获取全局事件总线"""
    return EventBus.get()
