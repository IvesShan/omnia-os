"""SmartPauser — 智能暂停与用户交互系统

功能：
- 检测关键决策点，主动询问用户
- 支持用户随时中断并给出反馈
- 动态调整执行计划
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path


class PauseReason(Enum):
    """暂停原因"""
    USER_REQUEST = "user_request"           # 用户主动请求
    RISKY_OPERATION = "risky_operation"     # 风险操作（删除、覆盖等）
    UNCERTAINTY = "uncertainty"             # 不确定如何继续
    MILESTONE = "milestone"                 # 完成重要阶段
    ERROR_RECOVERY = "error_recovery"       # 错误恢复需要用户确认
    PLAN_REVIEW = "plan_review"             # 计划审查


@dataclass
class PauseContext:
    """暂停上下文"""
    reason: PauseReason
    message: str
    current_step: int
    total_steps: int
    options: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "reason": self.reason.value,
            "message": self.message,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "options": self.options,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class UserFeedback:
    """用户反馈"""
    action: str  # continue, modify, cancel, pause
    modification: Optional[Dict] = None
    message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class SmartPauser:
    """智能暂停管理器"""
    
    # 风险操作关键词
    RISKY_KEYWORDS = [
        "删除", "移除", "清空", "覆盖", "重写",
        "drop", "delete", "remove", "clear", "overwrite",
        "rm ", "format", "truncate"
    ]
    
    # 不确定关键词
    UNCERTAINTY_KEYWORDS = [
        "不确定", "可能", "也许", "或者",
        "uncertain", "maybe", "might", "or",
        "???", "如何", "怎么办"
    ]
    
    # 里程碑关键词（完成重要阶段后暂停汇报）
    MILESTONE_KEYWORDS = [
        "完成", "成功", "已处理", "已生成",
        "completed", "success", "done", "finished"
    ]
    
    def __init__(self, auto_pause_enabled: bool = True):
        self.auto_pause_enabled = auto_pause_enabled
        self.pause_callback: Optional[Callable] = None
        self.feedback_callback: Optional[Callable] = None
        self.last_pause: Optional[PauseContext] = None
        self.pause_history: List[PauseContext] = []
        
        # 状态文件
        self.state_file = PAUSE_STATE_FILE
    
    def should_pause(self, step: Dict, step_index: int, total_steps: int) -> Optional[PauseContext]:
        """判断是否需要暂停"""
        if not self.auto_pause_enabled:
            return None
        
        tool_name = step.get("tool_name", "")
        tool_args = step.get("tool_args", {})
        description = step.get("description", "")
        
        # 1. 风险操作检测
        if self._is_risky_operation(tool_name, tool_args, description):
            return PauseContext(
                reason=PauseReason.RISKY_OPERATION,
                message=f"⚠️ 检测到风险操作：{description}",
                current_step=step_index,
                total_steps=total_steps,
                options=[
                    {"id": "proceed", "label": "继续执行", "style": "danger"},
                    {"id": "skip", "label": "跳过此步骤", "style": "warning"},
                    {"id": "cancel", "label": "取消任务", "style": "default"},
                ],
                metadata={"step": step}
            )
        
        # 2. 不确定性检测
        if self._has_uncertainty(description):
            return PauseContext(
                reason=PauseReason.UNCERTAINTY,
                message=f"🤔 需要确认：{description}",
                current_step=step_index,
                total_steps=total_steps,
                options=[
                    {"id": "proceed", "label": "继续", "style": "primary"},
                    {"id": "modify", "label": "修改步骤", "style": "warning"},
                ],
                metadata={"step": step}
            )
        
        # 3. 里程碑检测（每 5 步或重要阶段汇报）
        if step_index > 0 and step_index % 5 == 0:
            return PauseContext(
                reason=PauseReason.MILESTONE,
                message=f"📍 阶段性进展：已完成 {step_index}/{total_steps} 步",
                current_step=step_index,
                total_steps=total_steps,
                options=[
                    {"id": "continue", "label": "继续执行", "style": "primary"},
                    {"id": "pause", "label": "暂停，稍后继续", "style": "default"},
                    {"id": "review", "label": "查看当前进度", "style": "info"},
                ],
                metadata={"progress": step_index / total_steps}
            )
        
        return None
    
    def _is_risky_operation(self, tool_name: str, tool_args: Dict, description: str) -> bool:
        """检测风险操作"""
        text = f"{tool_name} {json.dumps(tool_args)} {description}".lower()
        
        # 检查关键词
        for keyword in self.RISKY_KEYWORDS:
            if keyword.lower() in text:
                return True
        
        # 特定工具检查
        if tool_name == "execute_shell":
            cmd = tool_args.get("command", "").lower()
            risky_cmds = ["rm ", "del ", "format", "drop table", "truncate"]
            for rc in risky_cmds:
                if rc in cmd:
                    return True
        
        if tool_name == "write_file":
            # 检查是否覆盖重要文件
            path = tool_args.get("path", "")
            important_files = [".env", "config.json", "secrets", "credentials"]
            for imp in important_files:
                if imp in path.lower():
                    return True
        
        return False
    
    def _has_uncertainty(self, description: str) -> bool:
        """检测不确定性"""
        for keyword in self.UNCERTAINTY_KEYWORDS:
            if keyword in description.lower():
                return True
        return False
    
    def handle_user_feedback(self, feedback: UserFeedback) -> Dict[str, Any]:
        """处理用户反馈"""
        result = {"action": feedback.action, "handled": True}
        
        if feedback.action == "continue":
            # 继续执行
            result["message"] = "继续执行..."
        
        elif feedback.action == "pause":
            # 暂停任务
            self._save_pause_state()
            result["message"] = "任务已暂停，可以稍后继续"
        
        elif feedback.action == "modify":
            # 修改步骤
            if feedback.modification:
                result["modification"] = feedback.modification
                result["message"] = "步骤已修改"
        
        elif feedback.action == "cancel":
            # 取消任务
            result["message"] = "任务已取消"
        
        elif feedback.action == "skip":
            # 跳过步骤
            result["message"] = "步骤已跳过"
        
        return result
    
    def _save_pause_state(self):
        """保存暂停状态"""
        if self.last_pause:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(json.dumps(self.last_pause.to_dict(), indent=2))
            self.pause_history.append(self.last_pause)
    
    def load_pause_state(self) -> Optional[PauseContext]:
        """加载暂停状态"""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                return PauseContext(
                    reason=PauseReason(data["reason"]),
                    message=data["message"],
                    current_step=data["current_step"],
                    total_steps=data["total_steps"],
                    options=data.get("options", []),
                    metadata=data.get("metadata", {}),
                    timestamp=data.get("timestamp", ""),
                )
            except:
                pass
        return None
    
    def clear_pause_state(self):
        """清除暂停状态"""
        if self.state_file.exists():
            self.state_file.unlink()
        self.last_pause = None


# 全局实例
_pauser: Optional[SmartPauser] = None

def get_pauser() -> SmartPauser:
    """获取全局 SmartPauser 实例"""
    global _pauser
    if _pauser is None:
        _pauser = SmartPauser()
    return _pauser
