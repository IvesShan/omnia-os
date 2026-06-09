"""Evolution Bridge — 连接 EventBus 和 SelfEvolutionEngine

这是自进化闭环的核心桥梁：
  EventBus 事件 → 进化信号累积 → 触发进化周期 → 反馈到 EventBus

闭环流程：
  1. chat.completed → 累积进化信号
  2. signal_count >= threshold → 触发 evolution.check
  3. evolution.check → 运行 PatternDetector + SkillGenerator + SkillVetter
  4. evolution.completed → 记录结果，反馈到记忆系统
  5. system.idle → 空闲时触发进化检查
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from src.core.orchestration.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


@dataclass
class EvolutionFeedback:
    """进化反馈记录"""
    skill_id: str
    skill_name: str
    created_at: datetime
    usage_count: int = 0
    last_used: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0
    confidence: float = 0.5
    
    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "created_at": str(self.created_at),
            "usage_count": self.usage_count,
            "last_used": str(self.last_used) if self.last_used else None,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "confidence": self.confidence,
        }


class EvolutionBridge:
    """自进化闭环桥梁
    
    连接 EventBus 和 SelfEvolutionEngine，实现：
    1. 事件驱动的进化触发
    2. 进化结果反馈到记忆系统
    3. 技能使用效果跟踪
    4. 自动调整进化策略
    """
    
    def __init__(
        self,
        event_bus: EventBus = None,
        feedback_file: Optional[Path] = None,
        # 触发阈值
        chat_signal_threshold: int = 20,      # 每 20 次对话触发一次
        idle_trigger_seconds: float = 600.0,   # 空闲 10 分钟触发
        cooldown_seconds: float = 3600.0,      # 进化周期冷却 1 小时
        # 数据源
        memory_db: Optional[str] = None,
        memory_dir: Optional[str] = None,
    ):
        self.bus = event_bus or EventBus.get()
        self.feedback_file = feedback_file or Path.home() / ".omnia" / "evolution_feedback.json"
        
        # 触发配置
        self.chat_signal_threshold = chat_signal_threshold
        self.idle_trigger_seconds = idle_trigger_seconds
        self.cooldown_seconds = cooldown_seconds
        
        # 数据源
        self.memory_db = memory_db
        self.memory_dir = memory_dir
        
        # 状态
        self._signal_count = 0
        self._last_evolution_run = 0.0
        self._running = False
        self._evolution_lock = threading.Lock()
        
        # 反馈记录
        self._feedback: Dict[str, EvolutionFeedback] = {}
        self._load_feedback()
        
        # 统计
        self.stats = {
            "total_cycles": 0,
            "total_patterns_detected": 0,
            "total_skills_generated": 0,
            "total_skills_approved": 0,
            "total_signals_received": 0,
        }
    
    def start(self):
        """启动进化桥梁，注册事件监听"""
        if self._running:
            logger.warning("[EvolutionBridge] Already running")
            return
        
        self._running = True
        self._register_events()
        self.bus.emit("evolution.bridge_started", source="evolution_bridge")
        logger.info("[EvolutionBridge] Started — evolution loop active")
    
    def stop(self):
        """停止进化桥梁"""
        self._running = False
        self._save_feedback()
        logger.info("[EvolutionBridge] Stopped")
    
    def _register_events(self):
        """注册事件监听器"""
        
        # 1. 对话完成 → 累积进化信号
        @self.bus.on("chat.completed", priority=5)
        def on_chat_completed(event: Event):
            if not self._running:
                return
            
            self._signal_count += 1
            self.stats["total_signals_received"] += 1
            
            # 检查是否达到触发阈值
            if self._signal_count >= self.chat_signal_threshold:
                self._try_trigger_evolution("chat_threshold")
        
        # 2. 系统空闲 → 触发进化检查
        @self.bus.on("system.idle", priority=5)
        def on_system_idle(event: Event):
            if not self._running:
                return
            
            idle_seconds = event.data.get("idle_seconds", 0)
            if idle_seconds >= self.idle_trigger_seconds:
                self._try_trigger_evolution("idle")
        
        # 3. 记忆整合完成 → 触发进化检查（有新数据了）
        @self.bus.on("memory.consolidated", priority=5)
        def on_memory_consolidated(event: Event):
            if not self._running:
                return
            
            # 记忆整合后，有新数据，可以尝试进化
            self._try_trigger_evolution("memory_consolidated")
        
        # 4. 手动触发
        @self.bus.on("evolution.trigger", priority=0)
        def on_manual_trigger(event: Event):
            if not self._running:
                return
            
            force = event.data.get("force", False)
            if force:
                self._last_evolution_run = 0.0  # 重置冷却
            self._try_trigger_evolution("manual")
    
    def _try_trigger_evolution(self, trigger: str):
        """尝试触发进化周期"""
        now = time.time()
        
        # 检查冷却
        if now - self._last_evolution_run < self.cooldown_seconds:
            remaining = self.cooldown_seconds - (now - self._last_evolution_run)
            logger.debug(f"[EvolutionBridge] Cooldown active, {remaining/60:.0f}min remaining")
            return
        
        # 获取锁，避免并发
        if not self._evolution_lock.acquire(blocking=False):
            logger.debug("[EvolutionBridge] Evolution already in progress")
            return
        
        try:
            self._last_evolution_run = now
            self._signal_count = 0
            
            # 在后台线程运行进化
            thread = threading.Thread(
                target=self._run_evolution_cycle,
                args=(trigger,),
                daemon=True,
            )
            thread.start()
            
            logger.info(f"[EvolutionBridge] Evolution triggered by: {trigger}")
            
        finally:
            # 注意：不在这里释放锁，让进化线程自己释放
            pass
    
    def _run_evolution_cycle(self, trigger: str):
        """运行进化周期（在后台线程中执行）"""
        try:
            from .auto_evolution import SelfEvolutionEngine
            from .detector import PatternDetector
            
            # 创建引擎
            engine = SelfEvolutionEngine(
                memory_dir=Path(self.memory_dir) if self.memory_dir else None,
            )
            
            # 设置正确的数据库路径
            if self.memory_db:
                engine.detector.memory_db = self.memory_db
            
            # 运行进化周期
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(engine.run_evolution_cycle())
            finally:
                loop.close()
            
            # 更新统计
            self.stats["total_cycles"] += 1
            self.stats["total_patterns_detected"] += len(result.patterns_found)
            self.stats["total_skills_generated"] += len(result.skills_generated)
            self.stats["total_skills_approved"] += len(result.skills_approved)
            
            # 记录反馈
            for skill_id in result.skills_approved:
                self._feedback[skill_id] = EvolutionFeedback(
                    skill_id=skill_id,
                    skill_name=skill_id.replace("auto-forge-", ""),
                    created_at=datetime.now(),
                )
            
            # 发布进化完成事件
            self.bus.emit("evolution.completed", {
                "trigger": trigger,
                "cycle_id": result.cycle_id,
                "patterns_found": len(result.patterns_found),
                "skills_generated": len(result.skills_generated),
                "skills_approved": len(result.skills_approved),
                "skills_rejected": len(result.skills_rejected),
                "error": result.error,
            }, source="evolution_bridge")
            
            # 如果有新技能，发布技能激活事件
            for skill_id in result.skills_approved:
                self.bus.emit("evolution.skill_activated", {
                    "skill_id": skill_id,
                    "skill_name": skill_id.replace("auto-forge-", ""),
                }, source="evolution_bridge")
            
            logger.info(
                f"[EvolutionBridge] Cycle completed: "
                f"{len(result.patterns_found)} patterns, "
                f"{len(result.skills_approved)} skills approved"
            )
            
            # 保存反馈
            self._save_feedback()
            
        except Exception as e:
            logger.error(f"[EvolutionBridge] Evolution cycle failed: {e}", exc_info=True)
            
            self.bus.emit("evolution.error", {
                "trigger": trigger,
                "error": str(e),
            }, source="evolution_bridge")
            
        finally:
            self._evolution_lock.release()
    
    # ─── 技能使用反馈 ─────────────────────────────────────────────
    
    def record_skill_usage(self, skill_id: str, success: bool = True):
        """记录技能使用效果
        
        当 Omnia 使用自动生成的技能时，调用此方法记录效果。
        """
        if skill_id not in self._feedback:
            return
        
        feedback = self._feedback[skill_id]
        feedback.usage_count += 1
        feedback.last_used = datetime.now()
        
        if success:
            feedback.success_count += 1
            feedback.confidence = min(0.95, feedback.confidence + 0.05)
        else:
            feedback.failure_count += 1
            feedback.confidence = max(0.1, feedback.confidence - 0.1)
        
        # 如果置信度太低，标记为需要审查
        if feedback.confidence < 0.3:
            self.bus.emit("evolution.skill_low_confidence", {
                "skill_id": skill_id,
                "confidence": feedback.confidence,
                "usage_count": feedback.usage_count,
            }, source="evolution_bridge")
        
        self._save_feedback()
    
    def get_skill_confidence(self, skill_id: str) -> float:
        """获取技能置信度"""
        if skill_id in self._feedback:
            return self._feedback[skill_id].confidence
        return 0.5  # 默认置信度
    
    # ─── 反馈持久化 ───────────────────────────────────────────────
    
    def _load_feedback(self):
        """加载反馈记录"""
        if not self.feedback_file.exists():
            return
        
        try:
            data = json.loads(self.feedback_file.read_text(encoding="utf-8"))
            for skill_id, feedback_data in data.get("feedback", {}).items():
                self._feedback[skill_id] = EvolutionFeedback(
                    skill_id=feedback_data["skill_id"],
                    skill_name=feedback_data["skill_name"],
                    created_at=datetime.fromisoformat(feedback_data["created_at"]),
                    usage_count=feedback_data.get("usage_count", 0),
                    last_used=datetime.fromisoformat(feedback_data["last_used"]) if feedback_data.get("last_used") else None,
                    success_count=feedback_data.get("success_count", 0),
                    failure_count=feedback_data.get("failure_count", 0),
                    confidence=feedback_data.get("confidence", 0.5),
                )
            self.stats.update(data.get("stats", {}))
            logger.info(f"[EvolutionBridge] Loaded {len(self._feedback)} feedback records")
        except Exception as e:
            logger.warning(f"[EvolutionBridge] Failed to load feedback: {e}")
    
    def _save_feedback(self):
        """保存反馈记录"""
        try:
            self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "feedback": {k: v.to_dict() for k, v in self._feedback.items()},
                "stats": self.stats,
                "updated_at": datetime.now().isoformat(),
            }
            self.feedback_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"[EvolutionBridge] Failed to save feedback: {e}")
    
    # ─── 状态查询 ─────────────────────────────────────────────────
    
    def status(self) -> Dict[str, Any]:
        """获取进化桥梁状态"""
        now = time.time()
        cooldown_remaining = max(0, self.cooldown_seconds - (now - self._last_evolution_run))
        
        return {
            "running": self._running,
            "signal_count": self._signal_count,
            "chat_signal_threshold": self.chat_signal_threshold,
            "cooldown_remaining_seconds": cooldown_remaining,
            "stats": self.stats,
            "feedback_count": len(self._feedback),
            "skills_with_low_confidence": [
                k for k, v in self._feedback.items()
                if v.confidence < 0.3
            ],
        }


# ─── 模块级单例 ─────────────────────────────────────────────────

_evolution_bridge: Optional[EvolutionBridge] = None


def get_evolution_bridge() -> EvolutionBridge:
    """获取全局进化桥梁"""
    global _evolution_bridge
    if _evolution_bridge is None:
        _evolution_bridge = EvolutionBridge()
    return _evolution_bridge


def start_evolution_bridge(
    event_bus: EventBus = None,
    memory_db: Optional[str] = None,
) -> EvolutionBridge:
    """启动进化桥梁（入口函数）"""
    global _evolution_bridge
    _evolution_bridge = EvolutionBridge(
        event_bus=event_bus,
        memory_db=memory_db,
    )
    _evolution_bridge.start()
    return _evolution_bridge
