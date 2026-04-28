"""
增强会话管理器 - Session Manager Enhanced
支持会话持久化、状态恢复、智能切换
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import hashlib


@dataclass
class Session:
    """会话数据结构"""
    session_id: str
    channel: str  # webchat, feishu, etc.
    created_at: datetime
    last_active: datetime
    status: str  # active, paused, closed
    topic: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    message_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'session_id': self.session_id,
            'channel': self.channel,
            'created_at': self.created_at.isoformat(),
            'last_active': self.last_active.isoformat(),
            'status': self.status,
            'topic': self.topic,
            'context': self.context,
            'message_count': self.message_count,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Session':
        return cls(
            session_id=data['session_id'],
            channel=data['channel'],
            created_at=datetime.fromisoformat(data['created_at']),
            last_active=datetime.fromisoformat(data['last_active']),
            status=data['status'],
            topic=data.get('topic'),
            context=data.get('context', {}),
            message_count=data.get('message_count', 0),
            metadata=data.get('metadata', {})
        )


class SessionManagerEnhanced:
    """增强会话管理器"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Path.home() / ".omnia" / "sessions.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self.current_session: Optional[Session] = None
        
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    channel TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_active TEXT NOT NULL,
                    status TEXT NOT NULL,
                    topic TEXT,
                    context TEXT,
                    message_count INTEGER DEFAULT 0,
                    metadata TEXT
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_channel 
                ON sessions(channel)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_status 
                ON sessions(status)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_last_active 
                ON sessions(last_active)
            ''')
    
    def create_session(self, channel: str, context: Dict = None) -> Session:
        """创建新会话"""
        session_id = self._generate_session_id(channel)
        now = datetime.now()
        
        session = Session(
            session_id=session_id,
            channel=channel,
            created_at=now,
            last_active=now,
            status='active',
            context=context or {}
        )
        
        self._save_session(session)
        self.current_session = session
        return session
    
    def _generate_session_id(self, channel: str) -> str:
        """生成会话ID"""
        timestamp = datetime.now().isoformat()
        raw = f"{channel}_{timestamp}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]
    
    def _save_session(self, session: Session):
        """保存会话到数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO sessions 
                (session_id, channel, created_at, last_active, status, topic, context, message_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session.session_id,
                session.channel,
                session.created_at.isoformat(),
                session.last_active.isoformat(),
                session.status,
                session.topic,
                json.dumps(session.context),
                session.message_count,
                json.dumps(session.metadata)
            ))
    
    def load_session(self, session_id: str) -> Optional[Session]:
        """加载会话"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT * FROM sessions WHERE session_id = ?
            ''', (session_id,))
            
            row = cursor.fetchone()
            if row:
                return Session(
                    session_id=row[0],
                    channel=row[1],
                    created_at=datetime.fromisoformat(row[2]),
                    last_active=datetime.fromisoformat(row[3]),
                    status=row[4],
                    topic=row[5],
                    context=json.loads(row[6]) if row[6] else {},
                    message_count=row[7],
                    metadata=json.loads(row[8]) if row[8] else {}
                )
        return None
    
    def get_active_sessions(self, channel: str = None, limit: int = 10) -> List[Session]:
        """获取活跃会话"""
        with sqlite3.connect(self.db_path) as conn:
            if channel:
                cursor = conn.execute('''
                    SELECT * FROM sessions 
                    WHERE status = 'active' AND channel = ?
                    ORDER BY last_active DESC
                    LIMIT ?
                ''', (channel, limit))
            else:
                cursor = conn.execute('''
                    SELECT * FROM sessions 
                    WHERE status = 'active'
                    ORDER BY last_active DESC
                    LIMIT ?
                ''', (limit,))
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append(Session(
                    session_id=row[0],
                    channel=row[1],
                    created_at=datetime.fromisoformat(row[2]),
                    last_active=datetime.fromisoformat(row[3]),
                    status=row[4],
                    topic=row[5],
                    context=json.loads(row[6]) if row[6] else {},
                    message_count=row[7],
                    metadata=json.loads(row[8]) if row[8] else {}
                ))
            
            return sessions
    
    def update_session(self, session: Session):
        """更新会话"""
        session.last_active = datetime.now()
        session.message_count += 1
        self._save_session(session)
    
    def pause_session(self, session_id: str):
        """暂停会话"""
        session = self.load_session(session_id)
        if session:
            session.status = 'paused'
            self._save_session(session)
    
    def resume_session(self, session_id: str) -> Optional[Session]:
        """恢复会话"""
        session = self.load_session(session_id)
        if session:
            session.status = 'active'
            session.last_active = datetime.now()
            self._save_session(session)
            self.current_session = session
        return session
    
    def close_session(self, session_id: str):
        """关闭会话"""
        session = self.load_session(session_id)
        if session:
            session.status = 'closed'
            self._save_session(session)
    
    def find_related_sessions(self, topic: str, limit: int = 5) -> List[Session]:
        """查找相关会话（基于主题）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT * FROM sessions 
                WHERE topic LIKE ? AND status != 'closed'
                ORDER BY last_active DESC
                LIMIT ?
            ''', (f'%{topic}%', limit))
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append(Session(
                    session_id=row[0],
                    channel=row[1],
                    created_at=datetime.fromisoformat(row[2]),
                    last_active=datetime.fromisoformat(row[3]),
                    status=row[4],
                    topic=row[5],
                    context=json.loads(row[6]) if row[6] else {},
                    message_count=row[7],
                    metadata=json.loads(row[8]) if row[8] else {}
                ))
            
            return sessions
    
    def get_session_stats(self) -> Dict[str, Any]:
        """获取会话统计"""
        with sqlite3.connect(self.db_path) as conn:
            # 总会话数
            total = conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
            
            # 活跃会话数
            active = conn.execute(
                'SELECT COUNT(*) FROM sessions WHERE status = "active"'
            ).fetchone()[0]
            
            # 按渠道统计
            channels = conn.execute('''
                SELECT channel, COUNT(*) as count 
                FROM sessions 
                GROUP BY channel
            ''').fetchall()
            
            # 平均消息数
            avg_messages = conn.execute(
                'SELECT AVG(message_count) FROM sessions'
            ).fetchone()[0] or 0
            
            return {
                'total_sessions': total,
                'active_sessions': active,
                'by_channel': dict(channels),
                'avg_messages': round(avg_messages, 2)
            }
    
    def cleanup_old_sessions(self, days: int = 30):
        """清理旧会话"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute('''
                DELETE FROM sessions 
                WHERE status = 'closed' AND last_active < ?
            ''', (cutoff,))
            
            deleted = result.rowcount
            return deleted


# 使用示例
if __name__ == "__main__":
    manager = SessionManagerEnhanced()
    
    # 创建会话
    session = manager.create_session('webchat', {'user': '原点'})
    print(f"创建会话: {session.session_id}")
    
    # 更新会话
    session.topic = "Omnia 优化"
    manager.update_session(session)
    
    # 获取统计
    stats = manager.get_session_stats()
    print(f"会话统计: {stats}")
    
    # 查找相关会话
    related = manager.find_related_sessions("Omnia")
    print(f"相关会话: {len(related)} 个")
