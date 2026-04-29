"""Session Manager - 智能会话管理

解决对话连续性问题：
1. 自动加载最近的对话历史
2. 智能会话窗口管理
3. 语义相似度检索相关对话
"""

from core.logging_config import get_logger

logger = get_logger(__name__)

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import json


@dataclass
class Session:
    """会话对象"""
    session_id: str
    created_at: float
    last_activity: float
    message_count: int = 0
    
    def is_expired(self, timeout: int = 3600) -> bool:
        """检查会话是否过期（默认 1 小时）"""
        return time.time() - self.last_activity > timeout
    
    def touch(self):
        """更新最后活动时间"""
        self.last_activity = time.time()
        self.message_count += 1


class SessionManager:
    """会话管理器 - 管理会话生命周期和历史加载"""
    
    def __init__(self, session_timeout: int = 3600):
        """
        Args:
            session_timeout: 会话超时时间（秒），默认 1 小时
        """
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
                
                # 检查是否过期
                if not session.is_expired(self.session_timeout):
                    self.current_session = session
                    print(f"[SessionManager] Resumed session: {session.session_id}")
                else:
                    logger.info(f"[SessionManager] Previous session expired")
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
                }))
            except Exception as e:
                print(f"[SessionManager] Failed to save session: {e}")
    
    def get_or_create_session(self) -> str:
        """获取或创建会话 ID
        
        如果当前会话未过期，继续使用；
        否则创建新会话。
        """
        now = time.time()
        
        if self.current_session and not self.current_session.is_expired(self.session_timeout):
            # 继续使用当前会话
            self.current_session.touch()
            self._save_session()
            return self.current_session.session_id
        else:
            # 创建新会话
            session_id = str(uuid.uuid4())[:8]
            self.current_session = Session(
                session_id=session_id,
                created_at=now,
                last_activity=now,
                message_count=1,
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
    limit: int = 10,
    min_similarity: float = 0.0,
    current_message: str = None,
) -> List[Dict[str, str]]:
    """从数据库加载最近的对话历史
    
    Args:
        limit: 加载的对话轮数（每轮包含 user + assistant）
        min_similarity: 最小相似度阈值（如果使用语义搜索）
        current_message: 当前消息（用于语义相似度搜索）
    
    Returns:
        OpenAI 格式的消息列表: [{"role": "user/assistant", "content": "..."}]
    """
    from core.memory_palace.memory_palace_with_graph import MemoryPalace
    from core.config import MEMORY_PALACE_DB
    
    try:
        mp = MemoryPalace(str(MEMORY_PALACE_DB))
        conn = mp._connect()
        
        # 策略 1: 如果有当前消息，尝试语义搜索相关对话
        if current_message and min_similarity > 0:
            try:
                similar = mp.search_conversations_semantic(
                    current_message, 
                    top_k=limit
                )
                
                if similar:
                    # 提取相关的对话片段
                    history = []
                    for conv, score in similar[:limit]:
                        if score >= min_similarity:
                            history.append({
                                "role": conv['role'],
                                "content": conv['content'],
                                "similarity": score,  # 添加相似度标记
                            })
                    
                    if history:
                        print(f"[SessionManager] Loaded {len(history)} semantically similar messages")
                        return history
            except ValueError as e:
                print(f"[SessionManager] Semantic search failed: {e}, falling back to recent")
        
        # 策略 2: 加载最近的对话
        rows = conn.execute('''
            SELECT role, content, created_at 
            FROM conversation_logs
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit * 2,)).fetchall()  # user + assistant
        
        if not rows:
            logger.info("[SessionManager] No conversation history found")
            return []
        
        # 转换为 OpenAI 格式（按时间正序）
        history = []
        for row in reversed(rows):
            history.append({
                "role": row['role'],
                "content": row['content'],
            })
        
        print(f"[SessionManager] Loaded {len(history)} recent messages")
        return history
        
    except ValueError as e:
        print(f"[SessionManager] Failed to load conversations: {e}")
        return []


def merge_histories(
    frontend_history: List[Dict],
    db_history: List[Dict],
    max_total: int = 20,
) -> List[Dict]:
    """合并前端历史和数据库历史
    
    策略：
    1. 如果前端历史足够长（>= max_total），直接使用前端历史
    2. 否则，用数据库历史补充
    
    Args:
        frontend_history: 前端传来的历史
        db_history: 从数据库加载的历史
        max_total: 最大总消息数
    
    Returns:
        合并后的历史
    """
    if not frontend_history and not db_history:
        return []
    
    # 如果前端历史足够，直接使用
    if len(frontend_history) >= max_total:
        return frontend_history[-max_total:]
    
    # 如果前端历史为空，使用数据库历史
    if not frontend_history:
        return db_history[-max_total:]
    
    # 合并：前端历史优先，数据库历史补充
    # 去重：基于内容的简单去重
    seen = set()
    merged = []
    
    # 先添加前端历史（保留顺序）
    for msg in frontend_history:
        content_hash = hash(msg.get('content', ''))
        if content_hash not in seen:
            seen.add(content_hash)
            merged.append(msg)
    
    # 再添加数据库历史（去重）
    for msg in db_history:
        content_hash = hash(msg.get('content', ''))
        if content_hash not in seen:
            seen.add(content_hash)
            merged.append(msg)
    
    # 限制总数
    result = merged[-max_total:]
    
    print(f"[SessionManager] Merged histories: frontend={len(frontend_history)}, db={len(db_history)}, total={len(result)}")
    return result


# 全局单例
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """获取全局 SessionManager 单例"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
