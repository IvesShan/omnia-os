"""
Memory Palace v2 - Omnia 2.0

四层记忆架构：
1. Facts - 事实性知识（用户偏好、项目信息）
2. Relations - 关系图谱（实体关系、依赖）
3. Habits - 行为习惯（常用命令、工作模式）
4. Timeline - 时间线（事件序列、决策历史）

特性：
- SQLite + FTS5 存储
- 向量嵌入搜索
- 自动记忆提取
- 跨会话持久化

Usage:
    from core.memory.palace import MemoryPalace
    
    palace = MemoryPalace()
    
    # 存储记忆
    palace.store_fact("user", "name", "原点", category="user")
    palace.store_event("milestone", "完成 Phase 1 核心架构")
    
    # 搜索记忆
    results = palace.search_facts("原点")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
import sqlite3

# 统一使用 config.py 中的路径配置
from core.config import MEMORY_PALACE_DB


class MemoryLayer(Enum):
    """记忆层级"""
    FACTS = "facts"           # 事实
    RELATIONS = "relations"   # 关系
    HABITS = "habits"         # 习惯
    TIMELINE = "timeline"     # 时间线


class MemoryPalace:
    """
    记忆宫殿
    
    四层记忆系统 + 智能检索
    """
    
    def __init__(self, db_path: str | Path = None):
        # 统一使用 config.py 中的路径
        if db_path is None:
            self.db_path = MEMORY_PALACE_DB
        else:
            self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    # ==================== Facts ====================
    
    def store_fact(self, category: str, key: str, value: str, 
                   source: str = "manual", strength: float = 1.0) -> int:
        """存储事实
        
        Args:
            category: 分类（user, project, preference, system等）
            key: 键名
            value: 值
            source: 来源（manual, conversation, tool等）
            strength: 记忆强度
        
        Returns:
            fact_id
        """
        with self._get_connection() as conn:
            # 检查是否已存在
            cursor = conn.execute("""
                SELECT id FROM facts WHERE category = ? AND key = ?
            """, (category, key))
            existing = cursor.fetchone()
            
            if existing:
                # 更新
                conn.execute("""
                    UPDATE facts SET value = ?, source = ?, strength = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (value, source, strength, existing['id']))
                fact_id = existing['id']
            else:
                # 插入
                cursor = conn.execute("""
                    INSERT INTO facts (category, key, value, source, strength)
                    VALUES (?, ?, ?, ?, ?)
                """, (category, key, value, source, strength))
                fact_id = cursor.lastrowid
            
            conn.commit()
        
        return fact_id
    
    def search_facts(self, query: str, limit: int = 10) -> list:
        """搜索事实"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM facts 
                WHERE key LIKE ? OR value LIKE ? OR category LIKE ?
                ORDER BY strength DESC, updated_at DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_facts(self, category: str = None) -> list:
        """获取所有事实"""
        with self._get_connection() as conn:
            if category:
                cursor = conn.execute("""
                    SELECT * FROM facts WHERE category = ?
                    ORDER BY strength DESC, updated_at DESC
                """, (category,))
            else:
                cursor = conn.execute("""
                    SELECT * FROM facts 
                    ORDER BY strength DESC, updated_at DESC
                """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== Relations ====================
    
    def store_relation(self, subject: str, predicate: str, object: str,
                       context: str = None, strength: float = 1.0) -> int:
        """存储关系
        
        Args:
            subject: 主体
            predicate: 谓词（喜欢、属于、依赖等）
            object: 客体
            context: 上下文
            strength: 关系强度
        
        Returns:
            relation_id
        """
        with self._get_connection() as conn:
            # 检查是否已存在
            cursor = conn.execute("""
                SELECT id FROM relations WHERE subject = ? AND predicate = ? AND object = ?
            """, (subject, predicate, object))
            existing = cursor.fetchone()
            
            if existing:
                # 更新强度
                conn.execute("""
                    UPDATE relations SET strength = ? WHERE id = ?
                """, (strength, existing['id']))
                relation_id = existing['id']
            else:
                # 插入
                cursor = conn.execute("""
                    INSERT INTO relations (subject, predicate, object, context, strength)
                    VALUES (?, ?, ?, ?, ?)
                """, (subject, predicate, object, context, strength))
                relation_id = cursor.lastrowid
            
            conn.commit()
        
        return relation_id
    
    def get_relations(self, subject: str = None, object: str = None) -> list:
        """获取关系"""
        with self._get_connection() as conn:
            if subject and object:
                cursor = conn.execute("""
                    SELECT * FROM relations 
                    WHERE subject = ? AND object = ?
                    ORDER BY strength DESC, created_at DESC
                """, (subject, object))
            elif subject:
                cursor = conn.execute("""
                    SELECT * FROM relations WHERE subject = ?
                    ORDER BY strength DESC, created_at DESC
                """, (subject,))
            elif object:
                cursor = conn.execute("""
                    SELECT * FROM relations WHERE object = ?
                    ORDER BY strength DESC, created_at DESC
                """, (object,))
            else:
                cursor = conn.execute("""
                    SELECT * FROM relations 
                    ORDER BY strength DESC, created_at DESC
                """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== Habits ====================
    
    def store_habit(self, domain: str, pattern: str, evidence: str = None,
                    certainty: float = 0.5) -> int:
        """存储习惯
        
        Args:
            domain: 领域（coding, communication, workflow等）
            pattern: 行为模式
            evidence: 证据
            certainty: 确定程度
        
        Returns:
            habit_id
        """
        with self._get_connection() as conn:
            # 检查是否已存在
            cursor = conn.execute("""
                SELECT id, certainty FROM habits WHERE domain = ? AND pattern = ?
            """, (domain, pattern))
            existing = cursor.fetchone()
            
            if existing:
                # 更新确定度和观察时间
                new_certainty = min(1.0, existing['certainty'] + 0.1)
                conn.execute("""
                    UPDATE habits SET certainty = ?, last_observed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_certainty, existing['id']))
                habit_id = existing['id']
            else:
                # 插入
                cursor = conn.execute("""
                    INSERT INTO habits (domain, pattern, evidence, certainty)
                    VALUES (?, ?, ?, ?)
                """, (domain, pattern, evidence, certainty))
                habit_id = cursor.lastrowid
            
            conn.commit()
        
        return habit_id
    
    def get_habits(self, domain: str = None, min_certainty: float = 0.0) -> list:
        """获取习惯"""
        with self._get_connection() as conn:
            if domain:
                cursor = conn.execute("""
                    SELECT * FROM habits 
                    WHERE domain = ? AND certainty >= ?
                    ORDER BY certainty DESC, last_observed_at DESC
                """, (domain, min_certainty))
            else:
                cursor = conn.execute("""
                    SELECT * FROM habits 
                    WHERE certainty >= ?
                    ORDER BY certainty DESC, last_observed_at DESC
                """, (min_certainty,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== Timeline ====================
    
    def store_event(self, event_type: str, title: str, description: str = None,
                    event_date: str = None, tags: str = None) -> int:
        """存储时间线事件
        
        Args:
            event_type: 事件类型（milestone, decision, error, achievement等）
            title: 标题
            description: 描述
            event_date: 日期（默认今天）
            tags: 标签
        
        Returns:
            event_id
        """
        if event_date is None:
            event_date = datetime.now().strftime("%Y-%m-%d")
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO timeline (event_date, event_type, title, description, tags)
                VALUES (?, ?, ?, ?, ?)
            """, (event_date, event_type, title, description, tags))
            event_id = cursor.lastrowid
            conn.commit()
        
        return event_id
    
    def get_timeline(self, event_type: str = None, limit: int = 100) -> list:
        """获取时间线"""
        with self._get_connection() as conn:
            if event_type:
                cursor = conn.execute("""
                    SELECT * FROM timeline 
                    WHERE event_type = ?
                    ORDER BY event_date DESC, created_at DESC
                    LIMIT ?
                """, (event_type, limit))
            else:
                cursor = conn.execute("""
                    SELECT * FROM timeline 
                    ORDER BY event_date DESC, created_at DESC
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== Stats ====================
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._get_connection() as conn:
            stats = {}
            
            try:
                cursor = conn.execute("SELECT COUNT(*) FROM facts")
                stats['facts'] = cursor.fetchone()[0]
            except Exception:
                stats['facts'] = 0
            
            try:
                cursor = conn.execute("SELECT COUNT(*) FROM relations")
                stats['relations'] = cursor.fetchone()[0]
            except Exception:
                stats['relations'] = 0
            
            try:
                cursor = conn.execute("SELECT COUNT(*) FROM habits")
                stats['habits'] = cursor.fetchone()[0]
            except Exception:
                stats['habits'] = 0
            
            try:
                cursor = conn.execute("SELECT COUNT(*) FROM timeline")
                stats['timeline'] = cursor.fetchone()[0]
            except Exception:
                stats['timeline'] = 0
            
            try:
                cursor = conn.execute("SELECT COUNT(*) FROM conversation_logs")
                stats['conversations'] = cursor.fetchone()[0]
            except Exception:
                stats['conversations'] = 0
            
            return stats
    
    def close(self):
        """关闭连接"""
        pass  # SQLite 连接在使用后自动关闭
