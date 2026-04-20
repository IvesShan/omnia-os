"""Context Manager - 自动加载最后一次上下文

每次启动时，自动加载最近的对话上下文，确保 Omnia "记得" 之前在做什么。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
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
    raw_conversation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionContext":
        return cls(**data)


class ContextManager:
    """上下文管理器 - 持久化最近的会话上下文"""
    
    def __init__(self, omnia_home: Path):
        self.omnia_home = omnia_home
        self.context_file = omnia_home / "last_context.json"
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
            print(f"[ContextManager] Failed to load context: {e}")
            return None
    
    def clear_context(self) -> None:
        """清除上下文"""
        if self.context_file.exists():
            self.context_file.unlink()
    
    def has_context(self) -> bool:
        """检查是否有上下文"""
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
        
        if ctx.active_files:
            lines.append(f"📄 活跃文件: {', '.join(ctx.active_files[:3])}")
        
        if ctx.key_decisions:
            lines.append(f"✅ 关键决策:")
            for decision in ctx.key_decisions[:3]:
                lines.append(f"   - {decision}")
        
        if ctx.next_steps:
            lines.append(f"➡️ 下一步:")
            for step in ctx.next_steps[:3]:
                lines.append(f"   - {step}")
        
        return '\n'.join(lines)


def save_current_context(
    topic: str,
    summary: str,
    active_project: Optional[str] = None,
    active_files: Optional[list] = None,
    key_decisions: Optional[list] = None,
    next_steps: Optional[list] = None,
    raw_conversation: Optional[str] = None,
) -> None:
    """保存当前上下文（便捷函数）"""
    from core.config import OMNIA_HOME
    
    manager = ContextManager(OMNIA_HOME)
    context = SessionContext(
        timestamp=datetime.now().isoformat(timespec='seconds'),
        topic=topic,
        summary=summary,
        active_project=active_project,
        active_files=active_files,
        key_decisions=key_decisions,
        next_steps=next_steps,
        raw_conversation=raw_conversation,
    )
    manager.save_context(context)


def load_last_context() -> Optional[SessionContext]:
    """加载最后一次上下文（便捷函数）"""
    from core.config import OMNIA_HOME
    
    manager = ContextManager(OMNIA_HOME)
    return manager.load_context()
