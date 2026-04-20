"""
FTS5 Full-Text Search - Omnia 2.0

参考：Hermes 的 SQLite FTS5 实现
目的：高效的全文搜索，支持跨会话记忆召回

FTS5 特性：
- 全文搜索（支持中文需要分词器）
- BM25 排序
- 高亮显示
- 快速查询

Usage:
    from core.memory.fts_search import FTSClient
    
    fts = FTSClient()
    
    # 存储消息
    await fts.store_message(session_id, role, content)
    
    # 搜索
    results = await fts.search("用户 偏好", limit=10)
"""

from __future__ import annotations

import sqlite3
from core.config import OMNIA_HOME
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
import asyncio
from contextlib import contextmanager


@dataclass
class SearchResult:
    """搜索结果"""
    id: int
    session_id: str
    role: str
    content: str
    timestamp: datetime
    rank: float  # BM25 分数
    highlights: list[str] = field(default_factory=list)  # 高亮片段


@dataclass
class MessageRecord:
    """消息记录"""
    session_id: str
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


class FTSClient:
    """
    FTS5 全文搜索客户端
    
    使用 SQLite FTS5 实现高效全文搜索
    支持中文需要额外安装分词器（如 simpletokenizer）
    """
    
    def __init__(self, db_path: str | Path = None):
        self.db_path = Path(db_path) if db_path else OMNIA_HOME / "fts.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """初始化数据库"""
        with self._get_connection() as conn:
            # 主消息表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            # FTS5 全文索引
            # tokenize='porter unicode61' 支持英文词干提取
            # 中文需要额外分词器，这里使用 unicode61 的基本支持
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts 
                USING fts5(
                    content,
                    session_id,
                    role,
                    timestamp,
                    tokenize='unicode61'
                )
            """)
            
            # 会话表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    message_count INTEGER DEFAULT 0
                )
            """)
            
            # 索引
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session 
                ON messages(session_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
                ON messages(timestamp)
            """)
            
            conn.commit()
    
    # ========================================================================
    # Write Operations
    # ========================================================================
    
    def store_message(
        self,
        session_id: str,
        role: str,
        content: str,
        timestamp: datetime | None = None,
        metadata: dict | None = None
    ) -> int:
        """
        存储消息
        
        Args:
            session_id: 会话 ID
            role: 角色 (user/assistant/system)
            content: 消息内容
            timestamp: 时间戳
            metadata: 元数据
        
        Returns:
            消息 ID
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        timestamp_str = timestamp.isoformat()
        metadata_str = json.dumps(metadata) if metadata else None
        
        with self._get_connection() as conn:
            # 插入主表
            cursor = conn.execute("""
                INSERT INTO messages (session_id, role, content, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, role, content, timestamp_str, metadata_str))
            
            message_id = cursor.lastrowid
            
            # 插入 FTS 索引
            conn.execute("""
                INSERT INTO messages_fts (content, session_id, role, timestamp)
                VALUES (?, ?, ?, ?)
            """, (content, session_id, role, timestamp_str))
            
            # 更新会话统计
            conn.execute("""
                INSERT INTO sessions (session_id, created_at, updated_at, message_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(session_id) DO UPDATE SET 
                    updated_at = excluded.updated_at,
                    message_count = message_count + 1
            """, (session_id, timestamp_str, timestamp_str))
            
            conn.commit()
            
            return message_id
    
    def store_messages_batch(self, messages: list[MessageRecord]) -> list[int]:
        """批量存储消息"""
        ids = []
        with self._get_connection() as conn:
            for msg in messages:
                timestamp_str = msg.timestamp.isoformat()
                metadata_str = json.dumps(msg.metadata) if msg.metadata else None
                
                cursor = conn.execute("""
                    INSERT INTO messages (session_id, role, content, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (msg.session_id, msg.role, msg.content, timestamp_str, metadata_str))
                
                message_id = cursor.lastrowid
                ids.append(message_id)
                
                conn.execute("""
                    INSERT INTO messages_fts (content, session_id, role, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (msg.content, msg.session_id, msg.role, timestamp_str))
            
            conn.commit()
        
        return ids
    
    def delete_message(self, message_id: int) -> bool:
        """删除消息"""
        with self._get_connection() as conn:
            # 获取消息信息
            row = conn.execute(
                "SELECT content, session_id, role, timestamp FROM messages WHERE id = ?",
                (message_id,)
            ).fetchone()
            
            if not row:
                return False
            
            # 删除主表
            conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))
            
            # 删除 FTS 索引（需要匹配所有字段）
            conn.execute("""
                DELETE FROM messages_fts 
                WHERE content = ? AND session_id = ? AND role = ? AND timestamp = ?
            """, (row['content'], row['session_id'], row['role'], row['timestamp']))
            
            conn.commit()
            return True
    
    def clear_session(self, session_id: str) -> int:
        """清空会话所有消息"""
        with self._get_connection() as conn:
            # 删除主表
            cursor = conn.execute(
                "DELETE FROM messages WHERE session_id = ?",
                (session_id,)
            )
            deleted_count = cursor.rowcount
            
            # 删除 FTS 索引
            conn.execute(
                "DELETE FROM messages_fts WHERE session_id = ?",
                (session_id,)
            )
            
            # 删除会话记录
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            
            conn.commit()
            return deleted_count
    
    # ========================================================================
    # Search Operations
    # ========================================================================
    
    def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        session_id: str | None = None,
        role: str | None = None,
        order_by_rank: bool = True
    ) -> list[SearchResult]:
        """
        全文搜索
        
        Args:
            query: 搜索查询（支持 FTS5 查询语法）
            limit: 结果数量限制
            offset: 偏移量
            session_id: 限定会话 ID
            role: 限定角色
            order_by_rank: 是否按相关性排序
        
        Returns:
            搜索结果列表
        """
        # FTS5 查询语法
        # 简单关键词: "用户 偏好"
        # 短语搜索: '"用户偏好"'
        # 布尔搜索: '用户 AND 偏好'
        # 前缀搜索: '用户*'
        
        with self._get_connection() as conn:
            # 构建查询
            sql = """
                SELECT 
                    m.id,
                    m.session_id,
                    m.role,
                    m.content,
                    m.timestamp,
                    f.rank,
                    highlight(messages_fts, 0, '【', '】') as highlight_content
                FROM messages m
                JOIN messages_fts f ON m.content = f.content 
                    AND m.session_id = f.session_id 
                    AND m.role = f.role
                WHERE messages_fts MATCH ?
            """
            
            params = [query]
            
            # 添加过滤条件
            if session_id:
                sql += " AND m.session_id = ?"
                params.append(session_id)
            
            if role:
                sql += " AND m.role = ?"
                params.append(role)
            
            # 排序
            if order_by_rank:
                sql += " ORDER BY f.rank"
            else:
                sql += " ORDER BY m.timestamp DESC"
            
            # 分页
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            rows = conn.execute(sql, params).fetchall()
            
            results = []
            for row in rows:
                results.append(SearchResult(
                    id=row['id'],
                    session_id=row['session_id'],
                    role=row['role'],
                    content=row['content'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    rank=row['rank'],
                    highlights=[row['highlight_content']] if row['highlight_content'] else []
                ))
            
            return results
    
    def search_by_session(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> list[SearchResult]:
        """按会话 ID 获取消息"""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT id, session_id, role, content, timestamp
                FROM messages
                WHERE session_id = ?
                ORDER BY timestamp ASC
                LIMIT ? OFFSET ?
            """, (session_id, limit, offset)).fetchall()
            
            return [
                SearchResult(
                    id=row['id'],
                    session_id=row['session_id'],
                    role=row['role'],
                    content=row['content'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    rank=0.0
                )
                for row in rows
            ]
    
    def get_recent_messages(
        self,
        limit: int = 50,
        session_id: str | None = None
    ) -> list[SearchResult]:
        """获取最近消息"""
        with self._get_connection() as conn:
            sql = """
                SELECT id, session_id, role, content, timestamp
                FROM messages
            """
            params = []
            
            if session_id:
                sql += " WHERE session_id = ?"
                params.append(session_id)
            
            sql += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(sql, params).fetchall()
            
            return [
                SearchResult(
                    id=row['id'],
                    session_id=row['session_id'],
                    role=row['role'],
                    content=row['content'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    rank=0.0
                )
                for row in rows
            ]
    
    # ========================================================================
    # Statistics
    # ========================================================================
    
    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        with self._get_connection() as conn:
            total_messages = conn.execute(
                "SELECT COUNT(*) FROM messages"
            ).fetchone()[0]
            
            total_sessions = conn.execute(
                "SELECT COUNT(*) FROM sessions"
            ).fetchone()[0]
            
            role_counts = conn.execute("""
                SELECT role, COUNT(*) as count
                FROM messages
                GROUP BY role
            """).fetchall()
            
            return {
                "total_messages": total_messages,
                "total_sessions": total_sessions,
                "role_counts": {row['role']: row['count'] for row in role_counts},
            }
    
    def get_session_stats(self, session_id: str) -> dict[str, Any] | None:
        """获取会话统计"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,)
            ).fetchone()
            
            if not row:
                return None
            
            return {
                "session_id": row['session_id'],
                "user_id": row['user_id'],
                "created_at": row['created_at'],
                "updated_at": row['updated_at'],
                "message_count": row['message_count'],
            }
    
    # ========================================================================
    # Maintenance
    # ========================================================================
    
    def optimize(self):
        """优化 FTS 索引"""
        with self._get_connection() as conn:
            conn.execute("INSERT INTO messages_fts(messages_fts) VALUES('optimize')")
            conn.commit()
    
    def vacuum(self):
        """清理数据库"""
        with self._get_connection() as conn:
            conn.execute("VACUUM")
            conn.commit()
    
    def rebuild_index(self):
        """重建 FTS 索引"""
        with self._get_connection() as conn:
            # 删除旧索引
            conn.execute("DROP TABLE IF EXISTS messages_fts")
            
            # 重建索引
            conn.execute("""
                CREATE VIRTUAL TABLE messages_fts 
                USING fts5(
                    content,
                    session_id,
                    role,
                    timestamp,
                    tokenize='unicode61'
                )
            """)
            
            # 重新填充
            conn.execute("""
                INSERT INTO messages_fts (content, session_id, role, timestamp)
                SELECT content, session_id, role, timestamp FROM messages
            """)
            
            conn.commit()


# ============================================================================
# Async Wrapper
# ============================================================================

class AsyncFTSClient:
    """异步 FTS 客户端封装"""
    
    def __init__(self, db_path: str | Path = None):
        self._sync_client = FTSClient(db_path)
    
    async def store_message(self, *args, **kwargs) -> int:
        """异步存储消息"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            lambda: self._sync_client.store_message(*args, **kwargs)
        )
    
    async def search(self, *args, **kwargs) -> list[SearchResult]:
        """异步搜索"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._sync_client.search(*args, **kwargs)
        )
    
    async def get_recent_messages(self, *args, **kwargs) -> list[SearchResult]:
        """异步获取最近消息"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._sync_client.get_recent_messages(*args, **kwargs)
        )
    
    async def get_stats(self) -> dict[str, Any]:
        """异步获取统计"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._sync_client.get_stats
        )
