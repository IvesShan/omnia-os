"""Heartbeat Loop — Omnia 的自主心跳

让 Omnia 定期"醒过来"，检查：
1. 有没有待处理的任务
2. 有没有过期的记忆需要整理
3. 系统是否健康
4. 用户是否长时间没说话（空闲检测）

设计原则：
- 轻量级，每 60 秒检查一次
- 通过 EventBus 发布事件，不直接调用其他模块
- 可配置开关和间隔
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime, timedelta

from .event_bus import Event, EventBus

logger = logging.getLogger(__name__)


@dataclass
class HeartbeatConfig:
    """心跳配置"""
    # 基础间隔
    check_interval: float = 60.0  # 每 60 秒检查一次
    
    # 空闲检测
    idle_threshold: float = 300.0  # 5 分钟没活动认为空闲
    idle_reflect_interval: float = 1800.0  # 每 30 分钟触发一次自省
    
    # 健康检查
    health_check_interval: float = 300.0  # 每 5 分钟检查一次健康
    
    # 记忆整理
    memory_consolidation_interval: float = 3600.0  # 每小时整理一次记忆
    memory_threshold: int = 50  # 记忆数量阈值
    
    # 任务检查
    task_check_interval: float = 120.0  # 每 2 分钟检查一次任务
    
    # 开关
    enable_idle_detection: bool = True
    enable_health_check: bool = True
    enable_memory_consolidation: bool = True
    enable_task_check: bool = True


class HeartbeatLoop:
    """自主心跳循环
    
    启动后定期检查系统状态，通过 EventBus 发布事件。
    """
    
    def __init__(self, config: HeartbeatConfig = None, event_bus: EventBus = None):
        self.config = config or HeartbeatConfig()
        self.bus = event_bus or EventBus.get()
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_activity_time = time.time()
        self._last_health_check = 0.0
        self._last_memory_check = 0.0
        self._last_task_check = 0.0
        self._last_idle_reflect = 0.0
        
        # 统计
        self._heartbeat_count = 0
        self._events_emitted = 0
        
        # 注册活动监听
        self._register_activity_watchers()
    
    def _register_activity_watchers(self):
        """注册活动监听器，更新最后活动时间"""
        
        @self.bus.on("chat.started", priority=0)
        def on_chat_started(event: Event):
            self._last_activity_time = time.time()
            logger.debug("[Heartbeat] Activity detected: chat.started")
        
        @self.bus.on("chat.completed", priority=0)
        def on_chat_completed(event: Event):
            self._last_activity_time = time.time()
            logger.debug("[Heartbeat] Activity detected: chat.completed")
    
    def start(self):
        """启动心跳循环"""
        if self._running:
            logger.warning("[Heartbeat] Already running")
            return
        
        self._running = True
        self._last_activity_time = time.time()
        
        # 在事件循环中启动
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self._run_loop())
            logger.info("[Heartbeat] Started (async mode)")
        except RuntimeError:
            # 没有运行中的事件循环，用线程
            import threading
            thread = threading.Thread(target=self._run_sync_loop, daemon=True)
            thread.start()
            logger.info("[Heartbeat] Started (thread mode)")
    
    def stop(self):
        """停止心跳循环"""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("[Heartbeat] Stopped")
    
    def status(self) -> Dict[str, Any]:
        """获取心跳状态"""
        return {
            "running": self._running,
            "heartbeat_count": self._heartbeat_count,
            "events_emitted": self._events_emitted,
            "last_activity": self._last_activity_time,
            "idle_seconds": time.time() - self._last_activity_time,
            "config": {
                "check_interval": self.config.check_interval,
                "idle_threshold": self.config.idle_threshold,
            }
        }
    
    # ─── 主循环 ───────────────────────────────────────────────────
    
    async def _run_loop(self):
        """异步主循环"""
        logger.info("[Heartbeat] Loop started")
        
        while self._running:
            try:
                await self._heartbeat_tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Heartbeat] Tick error: {e}", exc_info=True)
            
            await asyncio.sleep(self.config.check_interval)
        
        logger.info("[Heartbeat] Loop ended")
    
    def _run_sync_loop(self):
        """同步主循环（用于没有事件循环的场景）"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self._run_loop())
        except Exception as e:
            logger.error(f"[Heartbeat] Sync loop error: {e}")
        finally:
            loop.close()
    
    async def _heartbeat_tick(self):
        """一次心跳检查"""
        self._heartbeat_count += 1
        now = time.time()
        
        logger.debug(f"[Heartbeat] Tick #{self._heartbeat_count}")
        
        # 1. 空闲检测
        if self.config.enable_idle_detection:
            await self._check_idle(now)
        
        # 2. 健康检查
        if self.config.enable_health_check:
            await self._check_health(now)
        
        # 3. 记忆整理
        if self.config.enable_memory_consolidation:
            await self._check_memory(now)
        
        # 4. 任务检查
        if self.config.enable_task_check:
            await self._check_tasks(now)
    
    # ─── 检查逻辑 ─────────────────────────────────────────────────
    
    async def _check_idle(self, now: float):
        """检查用户是否空闲"""
        idle_time = now - self._last_activity_time
        
        if idle_time >= self.config.idle_threshold:
            # 用户空闲
            if now - self._last_idle_reflect >= self.config.idle_reflect_interval:
                self._last_idle_reflect = now
                self.bus.emit("system.idle", {
                    "idle_seconds": idle_time,
                    "idle_minutes": idle_time / 60,
                }, source="heartbeat")
                self._events_emitted += 1
                logger.info(f"[Heartbeat] User idle for {idle_time/60:.1f} minutes, emitting system.idle")
    
    async def _check_health(self, now: float):
        """检查系统健康状态"""
        if now - self._last_health_check < self.config.health_check_interval:
            return
        
        self._last_health_check = now
        
        # 简单的健康检查
        health = {
            "timestamp": now,
            "heartbeat_count": self._heartbeat_count,
            "events_emitted": self._events_emitted,
            "memory": self._get_memory_stats(),
        }
        
        self.bus.emit("system.health_check", health, source="heartbeat")
        self._events_emitted += 1
        logger.debug(f"[Heartbeat] Health check: {health}")
    
    async def _check_memory(self, now: float):
        """检查记忆状态"""
        if now - self._last_memory_check < self.config.memory_consolidation_interval:
            return
        
        self._last_memory_check = now
        
        try:
            stats = self._get_memory_stats()
            total = stats.get("total", 0)
            
            if total >= self.config.memory_threshold:
                self.bus.emit("memory.threshold", {
                    "count": total,
                    "threshold": self.config.memory_threshold,
                }, source="heartbeat")
                self._events_emitted += 1
                logger.info(f"[Heartbeat] Memory threshold reached: {total} >= {self.config.memory_threshold}")
        except Exception as e:
            logger.debug(f"[Heartbeat] Memory check skipped: {e}")
    
    async def _check_tasks(self, now: float):
        """检查待处理任务"""
        if now - self._last_task_check < self.config.task_check_interval:
            return
        
        self._last_task_check = now
        
        try:
            from .scheduler import Scheduler
            scheduler = Scheduler()
            due_tasks = [
                task for task in scheduler.list_tasks()
                if task.should_run(datetime.now())
            ]
            
            if due_tasks:
                self.bus.emit("scheduler.tasks_due", {
                    "count": len(due_tasks),
                    "tasks": [t.name for t in due_tasks],
                }, source="heartbeat")
                self._events_emitted += 1
                logger.info(f"[Heartbeat] {len(due_tasks)} tasks due")
        except Exception as e:
            logger.debug(f"[Heartbeat] Task check skipped: {e}")
    
    # ─── 辅助方法 ─────────────────────────────────────────────────
    
    def _get_memory_stats(self) -> Dict[str, int]:
        """获取记忆统计"""
        try:
            from src.core.memory_palace import MemoryPalace
            palace = MemoryPalace()
            return palace.stats()
        except Exception:
            return {"total": 0, "error": "unavailable"}
    
    def notify_activity(self):
        """外部调用：通知有活动"""
        self._last_activity_time = time.time()


# ─── 模块级单例 ─────────────────────────────────────────────────

_heartbeat_loop: Optional[HeartbeatLoop] = None

def get_heartbeat_loop() -> HeartbeatLoop:
    """获取全局心跳循环"""
    global _heartbeat_loop
    if _heartbeat_loop is None:
        _heartbeat_loop = HeartbeatLoop()
    return _heartbeat_loop

def start_heartbeat_loop(config: HeartbeatConfig = None) -> HeartbeatLoop:
    """启动心跳循环（入口函数）"""
    global _heartbeat_loop
    _heartbeat_loop = HeartbeatLoop(config=config)
    _heartbeat_loop.start()
    return _heartbeat_loop
