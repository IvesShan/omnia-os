"""session_manager.py — 智能会话管理（移植自 Flask 版）

核心功能：
1. 自动创建/恢复会话（跨重启保持连续性）
2. 从记忆库自动加载最近的对话历史
3. 智能会话窗口管理
"""

import time
import uuid
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.omnia.config import settings


@dataclass
class Session:
    """会话对象"""
    session_id: str
    created_at: float
    last_activity: float
    message_count: int = 0
    provider: str = ""

    def is_expired(self, timeout: int = 7200) -> bool:
        """检查会话是否过期（默认 2 小时）"""
        return time.time() - self.last_activity > timeout

    def touch(self):
        """更新最后活动时间"""
        self.last_activity = time.time()
        self.message_count += 1


class SessionManager:
    """会话管理器 — 管理会话生命周期和历史加载"""

    def __init__(self, session_timeout: int = 7200):
        self.session_timeout = session_timeout
        self.current_session: Optional[Session] = None
        self.session_file = Path.home() / ".omnia" / "current_session.json"

        # 尝试恢复上次的会话
        self._load_session()

    def _load_session(self):
        """从文件加载会话"""
        if self.session_file.exists():
            try:
                data = json.loads(self.session_file.read_text())
                session = Session(**data)
                if not session.is_expired(self.session_timeout):
                    self.current_session = session
                    print(f"[SessionManager] Resumed session: {session.session_id}")
                else:
                    print(f"[SessionManager] Previous session expired")
            except Exception as e:
                print(f"[SessionManager] Failed to load session: {e}")

    def _save_session(self):
        """保存会话到文件"""
        if self.current_session:
            try:
                self.session_file.parent.mkdir(parents=True, exist_ok=True)
                self.session_file.write_text(json.dumps({
                    "session_id": self.current_session.session_id,
                    "created_at": self.current_session.created_at,
                    "last_activity": self.current_session.last_activity,
                    "message_count": self.current_session.message_count,
                    "provider": self.current_session.provider,
                }))
            except Exception as e:
                print(f"[SessionManager] Failed to save session: {e}")

    def get_or_create_session(self, provider: str = "") -> str:
        """获取或创建会话 ID"""
        now = time.time()
        if self.current_session and not self.current_session.is_expired(self.session_timeout):
            self.current_session.touch()
            if provider:
                self.current_session.provider = provider
            self._save_session()
            return self.current_session.session_id
        else:
            session_id = str(uuid.uuid4())[:8]
            self.current_session = Session(
                session_id=session_id,
                created_at=now,
                last_activity=now,
                message_count=1,
                provider=provider,
            )
            self._save_session()
            print(f"[SessionManager] Created new session: {session_id}")
            return session_id

    def force_new_session(self) -> str:
        """强制创建新会话"""
        session_id = str(uuid.uuid4())[:8]
        self.current_session = Session(
            session_id=session_id,
            created_at=time.time(),
            last_activity=time.time(),
            message_count=1,
        )
        self._save_session()
        print(f"[SessionManager] Forced new session: {session_id}")
        return session_id

    def get_session_info(self) -> Dict[str, Any]:
        """获取当前会话信息"""
        if not self.current_session:
            return {"status": "no_session"}
        age = time.time() - self.current_session.created_at
        return {
            "status": "active",
            "session_id": self.current_session.session_id,
            "message_count": self.current_session.message_count,
            "age_seconds": int(age),
            "age_human": str(timedelta(seconds=int(age))),
        }


def load_recent_conversations(
    limit: int = 20,
    current_message: str = None,
) -> List[Dict[str, str]]:
    """从记忆库加载最近的对话历史（仅最近几条）"""
    try:
        from src.omnia.config import settings
        if not settings.memory_palace_db.exists():
            return []

        conn = sqlite3.connect(str(settings.memory_palace_db))
        conn.row_factory = sqlite3.Row

        rows = conn.execute('''
            SELECT role, content, created_at
            FROM conversation_logs
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,)).fetchall()

        if not rows:
            conn.close()
            return []

        # 按时间正序
        history = []
        for row in reversed(rows):
            history.append({
                "role": row["role"],
                "content": row["content"],
            })

        conn.close()
        print(f"[SessionManager] Loaded {len(history)} recent messages from DB")
        return history

    except Exception as e:
        print(f"[SessionManager] Failed to load conversations: {e}")
        return []


def merge_histories(
    frontend_history: List[Dict],
    db_history: List[Dict],
    max_total: int = 30,
) -> List[Dict]:
    """合并前端历史和数据库历史
    
    策略：
    1. 前端历史优先且保留顺序
    2. 数据库历史补充（去重）
    3. 总条数不超过 max_total
    """
    if not frontend_history and not db_history:
        return []
    
    # 如果前端历史足够，直接使用（但截取最后一部分）
    if len(frontend_history) >= max_total:
        return frontend_history[-max_total:]
    
    # 如果前端历史为空，使用数据库历史
    if not frontend_history:
        return db_history[-max_total:]
    
    # 合并：前端历史优先，数据库历史补充（去重）
    seen = set()
    merged = []
    
    # 添加前端历史的前几条作为上下文，保留最后几条完整
    # 只保留前几条非用户消息作为系统上下文
    recent_few = frontend_history[:3] if len(frontend_history) > 10 else []
    # 保留最后 6 条（最近 3 轮）
    tail = frontend_history[-6:] if len(frontend_history) > 6 else frontend_history
    
    context_msgs = recent_few + tail
    for msg in context_msgs:
        content_hash = hash(msg.get("content", ""))
        if content_hash not in seen:
            seen.add(content_hash)
            merged.append(msg)
    
    # 用数据库历史补充（但避免重复）
    for msg in db_history:
        content_hash = hash(msg.get("content", ""))
        if content_hash not in seen:
            seen.add(content_hash)
            merged.append(msg)
    
    result = merged[-max_total:]
    print(f"[SessionManager] Merged histories: frontend_context={len(merged)}, total={len(result)}")
    return result


# 全局单例
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """获取全局 SessionManager 单例"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
