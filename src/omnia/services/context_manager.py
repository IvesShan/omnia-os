"""
Context Manager — 会话上下文持久化

移植自 Flask 版 core/context_manager.py
适配 FastAPI 异步架构

核心功能：
1. 保存最近一次对话的上下文（主题/摘要/项目/下一步）
2. 启动时加载上次上下文，保持连续性
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict


@dataclass
class SessionContext:
    """会话上下文"""
    timestamp: str
    topic: str
    summary: str
    active_project: Optional[str] = None
    active_files: Optional[list] = None
    key_decisions: Optional[list] = None
    next_steps: Optional[list] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionContext":
        # 过滤掉未知字段
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


class ContextManager:
    """上下文管理器"""

    def __init__(self, omnia_home: Path = None):
        if omnia_home is None:
            omnia_home = Path.home() / ".openclaw" / "workspace" / "omnia-os"
        self.omnia_home = Path(omnia_home)
        self.context_file = self.omnia_home / "last_context.json"
        self.omnia_home.mkdir(parents=True, exist_ok=True)

    def save_context(self, context: SessionContext) -> None:
        """保存当前上下文"""
        with open(self.context_file, 'w', encoding='utf-8') as f:
            json.dump(context.to_dict(), f, ensure_ascii=False, indent=2)

    def load_context(self) -> Optional[SessionContext]:
        """加载最后一次上下文"""
        if not self.context_file.exists():
            return None
        try:
            with open(self.context_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return SessionContext.from_dict(data)
        except Exception as e:
            print(f"[ContextManager] Failed to load: {e}")
            return None

    def has_context(self) -> bool:
        return self.context_file.exists()

    def get_context_summary(self) -> str:
        """获取上下文摘要（用于启动时显示）"""
        ctx = self.load_context()
        if not ctx:
            return "无上次会话记录"

        lines = [
            f"📅 时间: {ctx.timestamp}",
            f"📌 主题: {ctx.topic}",
            f"📝 摘要: {ctx.summary}",
        ]

        if ctx.active_project:
            lines.append(f"🏗️ 项目: {ctx.active_project}")

        if ctx.next_steps:
            lines.append(f"➡️ 下一步:")
            for step in ctx.next_steps[:3]:
                lines.append(f"   - {step}")

        return '\n'.join(lines)


# ─── 便捷函数 ───

_default_manager: Optional[ContextManager] = None


def _get_manager() -> ContextManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = ContextManager()
    return _default_manager


def save_current_context(
    topic: str,
    summary: str,
    active_project: Optional[str] = None,
    active_files: Optional[list] = None,
    key_decisions: Optional[list] = None,
    next_steps: Optional[list] = None,
) -> None:
    """保存当前上下文（便捷函数）"""
    manager = _get_manager()
    context = SessionContext(
        timestamp=datetime.now().isoformat(timespec='seconds'),
        topic=topic,
        summary=summary,
        active_project=active_project,
        active_files=active_files,
        key_decisions=key_decisions,
        next_steps=next_steps,
    )
    manager.save_context(context)


def load_last_context() -> Optional[SessionContext]:
    """加载最后一次上下文（便捷函数）"""
    return _get_manager().load_context()


def extract_topic(message: str) -> str:
    """从消息中提取主题"""
    topic = message.strip()[:50]
    if len(message) > 50:
        topic += "..."
    return topic


def extract_next_steps(reply: str) -> List[str]:
    """从回复中提取下一步"""
    if "下一步" in reply:
        lines = reply.split("\n")
        steps = []
        for line in lines:
            if "下一步" in line or line.strip().startswith("-"):
                steps.append(line.strip())
        return steps[:3]
    return []
