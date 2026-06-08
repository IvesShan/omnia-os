"""Nervous System — Omnia 的自主行为引擎

把事件总线和现有模块连接起来，实现：
  1. 感知（事件采集）
  2. 记忆（自动整理）
  3. 行动（事件驱动响应）
  4. 自省（周期反思）

设计原则：
- 所有行为都是 EventBus 回调，零侵入
- 每个行为独立注册，可单独开关
- 行为可以触发新的事件，形成链式反应
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import TYPE_CHECKING

from .event_bus import Event, EventBus

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class NervousSystem:
    """自主行为引擎

    启动后自动将各个传感器/效应器注册到 EventBus，
    让 Omnia 的各个模块能够自主联动。
    """

    def __init__(self, event_bus: EventBus = None):
        self.bus = event_bus or EventBus.get()
        self._started = False
        self._last_consolidation = 0.0
        self._conversation_count_since_consolidation = 0

    def start(self):
        """启动神经系统，注册所有内置反应"""
        if self._started:
            logger.warning("[NervousSystem] Already started")
            return

        self._register_chat_reactions()
        self._register_memory_reactions()
        self._register_graph_reactions()
        self._register_idle_watcher()

        self._started = True
        self.bus.emit("system.startup", source="nervous_system")
        logger.info("[NervousSystem] Started — all reflexes registered")

    def stop(self):
        """停止神经系统"""
        self._started = False
        self.bus.emit("system.shutdown", source="nervous_system")
        logger.info("[NervousSystem] Stopped")

    # ─── 1. 对话反应 ───────────────────────────────────────────────

    def _register_chat_reactions(self):
        """对话完成后自动提取记忆"""

        @self.bus.on("chat.completed", priority=50)
        def auto_extract_memory(event: Event):
            """对话完成 → 自动提取记忆到 Memory Palace"""
            message = event.data.get("message", "")
            response = event.data.get("response", "")
            session_id = event.data.get("session_id", "default")

            if not message:
                return

            # 调用 auto_memory 模块
            try:
                from src.services.auto_memory import AutoMemory
                memory = AutoMemory()
                memory.process_conversation(
                    user_message=message,
                    assistant_response=response,
                    session_id=session_id,
                )
                logger.debug(f"[NervousSystem] Memory extracted from conversation")
            except Exception as e:
                logger.debug(f"[NervousSystem] Auto memory skipped: {e}")

            # 计数，达到阈值时触发整合
            self._conversation_count_since_consolidation += 1
            if self._conversation_count_since_consolidation >= 10:
                self.bus.emit("memory.threshold", {
                    "count": self._conversation_count_since_consolidation,
                }, source="nervous_system")

        @self.bus.on("chat.completed", priority=80)
        def update_graph(event: Event):
            """对话完成 → 更新神经图谱"""
            message = event.data.get("message", "")
            response = event.data.get("response", "")

            try:
                from src.services.graph import get_graph
                graph = get_graph()
                if graph:
                    # 从对话中提取实体和关系
                    new_entities = graph.extract_from_conversation(message, response)
                    if new_entities:
                        self.bus.emit("graph.updated", {
                            "entities": new_entities,
                        }, source="nervous_system")
            except Exception as e:
                logger.debug(f"[NervousSystem] Graph update skipped: {e}")

    # ─── 2. 记忆反应 ───────────────────────────────────────────────

    def _register_memory_reactions(self):
        """记忆达到阈值时自动整合"""

        @self.bus.on("memory.threshold", priority=10)
        def consolidate_memories(event: Event):
            """记忆数量达到阈值 → 触发整合"""
            now = time.time()
            # 至少间隔 30 分钟
            if now - self._last_consolidation < 1800:
                logger.debug("[NervousSystem] Consolidation throttled (last run < 30min ago)")
                return

            self._last_consolidation = now
            self._conversation_count_since_consolidation = 0

            try:
                from src.services.context_compressor import ContextCompressor
                compressor = ContextCompressor()
                result = compressor.compress_recent()
                logger.info(f"[NervousSystem] Memory consolidated: {result}")
                self.bus.emit("memory.consolidated", {
                    "result": result,
                }, source="nervous_system")
            except Exception as e:
                logger.error(f"[NervousSystem] Memory consolidation failed: {e}")

    # ─── 3. 图谱反应 ───────────────────────────────────────────────

    def _register_graph_reactions(self):
        """图谱更新后尝试发现新关系"""

        @self.bus.on("graph.updated", priority=50)
        def discover_relations(event: Event):
            """图谱更新 → 自动发现隐含关系"""
            entities = event.data.get("entities", [])
            if len(entities) < 2:
                return

            try:
                from src.services.graph import get_graph
                graph = get_graph()
                if graph:
                    # 尝试在新实体之间建立连接
                    new_relations = graph.discover_relations(entities)
                    if new_relations:
                        self.bus.emit("graph.new_relation", {
                            "relations": new_relations,
                        }, source="nervous_system")
                        logger.info(f"[NervousSystem] Discovered {len(new_relations)} new relations")
            except Exception as e:
                logger.debug(f"[NervousSystem] Relation discovery skipped: {e}")

    # ─── 4. 空闲监控 ───────────────────────────────────────────────

    def _register_idle_watcher(self):
        """检测系统空闲，触发自省"""

        @self.bus.on("system.idle", priority=0)
        def self_reflect(event: Event):
            """系统空闲 → 自省"""
            try:
                from src.core.neuro_center.persona_daemon import PersonaDaemon
                daemon = PersonaDaemon()
                # daemon._run_heartbeat()  # 暂不自动调用，避免重复
                logger.debug("[NervousSystem] Idle self-reflection")
            except Exception as e:
                logger.debug(f"[NervousSystem] Self-reflection skipped: {e}")


# ─── 模块级单例 ─────────────────────────────────────────────────

_nervous_system: NervousSystem = None

def get_nervous_system() -> NervousSystem:
    """获取全局神经系统"""
    global _nervous_system
    if _nervous_system is None:
        _nervous_system = NervousSystem()
    return _nervous_system

def start_nervous_system():
    """启动神经系统（入口函数）"""
    ns = get_nervous_system()
    ns.start()
    return ns
