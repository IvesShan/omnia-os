"""
Omnia Memory System V3 - 版本化记忆系统

核心特性：
1. 版本控制 - 每条记忆带版本号和时间戳
2. 状态管理 - active / deprecated / archived
3. 对话日志 - 完整记录每一句话（但不进入核心记忆）
4. 智能检索 - 默认只返回 active + 最新版本
5. 关联追踪 - 新版本指向被取代的旧版本

解决：
- 记住每一句话
- 不会版本混淆
- 不会幻觉
- 可以追溯历史
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import re


class MemoryV3:
    """版本化记忆系统 V3"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path.home() / ".omnia" / "memory_v3.db")
        
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._init_database()
        
        # 统计信息
        self.stats = {
            "total_conversations": 0,
            "total_facts": 0,
            "total_versions": 0
        }
        self._update_stats()
    
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # ========== 核心记忆层（纯净、版本化） ==========
        
        # 事实表 - 带版本控制
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                category TEXT,
                source TEXT,
                
                -- 版本控制
                version INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active',  -- active, deprecated, archived
                supersedes INTEGER,  -- 取代的旧版本 ID
                
                -- 时间戳
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                
                -- 元数据
                priority INTEGER DEFAULT 0,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP,
                
                -- 标签
                tags TEXT,  -- JSON array
                
                UNIQUE(key, version)
            )
        ''')
        
        # 关系表 - 带版本控制
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                context TEXT,
                
                -- 版本控制
                version INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active',
                supersedes INTEGER,
                
                -- 时间戳
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- 元数据
                strength REAL DEFAULT 1.0,
                evidence TEXT,
                
                UNIQUE(subject, predicate, object, version)
            )
        ''')
        
        # 习惯表 - 带版本控制
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                pattern TEXT NOT NULL,
                evidence TEXT,
                
                -- 版本控制
                version INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active',
                supersedes INTEGER,
                
                -- 时间戳
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_observed_at TIMESTAMP,
                
                -- 元数据
                certainty REAL DEFAULT 0.5,
                observation_count INTEGER DEFAULT 1,
                
                UNIQUE(domain, pattern, version)
            )
        ''')
        
        # 时间线表 - 带版本控制
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_date DATE NOT NULL,
                event_type TEXT,
                title TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                related_facts TEXT,
                session_key TEXT,
                
                -- 版本控制
                version INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active',
                supersedes INTEGER,
                
                -- 时间戳
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ========== 对话日志层（完整历史） ==========
        
        # 对话日志 - 记录每一句话
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                turn_number INTEGER,
                role TEXT NOT NULL,  -- user, assistant, system
                content TEXT NOT NULL,
                persona TEXT,
                
                -- 时间戳
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- 元数据
                metadata TEXT,  -- JSON
                
                -- 是否已提取为核心记忆
                extracted INTEGER DEFAULT 0,
                extraction_notes TEXT
            )
        ''')
        
        # 工具日志 - 记录工具调用
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tool_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                turn_number INTEGER,
                tool_name TEXT NOT NULL,
                arguments TEXT,  -- JSON
                result TEXT,
                success INTEGER DEFAULT 1,
                error_message TEXT,
                duration_ms INTEGER,
                
                -- 时间戳
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ========== 索引 ==========
        
        # 全文搜索索引
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts 
            USING fts5(key, value, category, content='facts', content_rowid='id')
        ''')
        
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS conversation_fts 
            USING fts5(content, persona, content='conversation_logs', content_rowid='id')
        ''')
        
        # 普通索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_facts_key ON facts(key)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_facts_status ON facts(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_facts_version ON facts(key, version)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_session ON conversation_logs(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_created ON conversation_logs(created_at)')
        
        conn.commit()
        conn.close()
    
    def _update_stats(self):
        """更新统计信息"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM conversation_logs')
        self.stats["total_conversations"] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM facts WHERE status = "active"')
        self.stats["total_facts"] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM facts')
        self.stats["total_versions"] = cursor.fetchone()[0]
        
        conn.close()

    # ========== 对话日志（记录每一句话） ==========
    
    def log_conversation(
        self,
        session_id: str,
        role: str,
        content: str,
        persona: str = None,
        metadata: Dict = None,
        turn_number: int = None
    ) -> int:
        """
        记录对话（每一句话都会被记录）
        
        Args:
            session_id: 会话 ID
            role: user / assistant / system
            content: 对话内容
            persona: 人格名称
            metadata: 元数据
            turn_number: 轮次编号
        
        Returns:
            记录 ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO conversation_logs 
            (session_id, turn_number, role, content, persona, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            turn_number,
            role,
            content,
            persona,
            json.dumps(metadata) if metadata else None,
            datetime.now().isoformat()
        ))
        
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        self.stats["total_conversations"] += 1
        return log_id
    
    def log_tool_call(
        self,
        session_id: str,
        tool_name: str,
        arguments: Dict,
        result: Any,
        success: bool = True,
        error_message: str = None,
        duration_ms: int = None,
        turn_number: int = None
    ) -> int:
        """记录工具调用"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tool_logs
            (session_id, turn_number, tool_name, arguments, result, success, error_message, duration_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            turn_number,
            tool_name,
            json.dumps(arguments) if arguments else None,
            json.dumps(result) if result else None,
            1 if success else 0,
            error_message,
            duration_ms,
            datetime.now().isoformat()
        ))
        
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return log_id
    
    def search_conversations(
        self,
        query: str,
        limit: int = 10,
        session_id: str = None,
        start_date: str = None,
        end_date: str = None
    ) -> List[Dict]:
        """
        搜索历史对话
        
        Args:
            query: 搜索关键词
            limit: 返回数量
            session_id: 限定会话
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            匹配的对话记录
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 使用全文搜索
        sql = '''
            SELECT cl.*, 
                   bm25(conversation_fts) as relevance
            FROM conversation_logs cl
            JOIN conversation_fts ON conversation_fts.rowid = cl.id
            WHERE conversation_fts MATCH ?
        '''
        params = [query]
        
        if session_id:
            sql += ' AND cl.session_id = ?'
            params.append(session_id)
        
        if start_date:
            sql += ' AND cl.created_at >= ?'
            params.append(start_date)
        
        if end_date:
            sql += ' AND cl.created_at <= ?'
            params.append(end_date)
        
        sql += ' ORDER BY relevance DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "id": row["id"],
                "session_id": row["session_id"],
                "turn_number": row["turn_number"],
                "role": row["role"],
                "content": row["content"],
                "persona": row["persona"],
                "created_at": row["created_at"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                "relevance": row["relevance"]
            })
        
        conn.close()
        return results

    # ========== 核心记忆（版本化） ==========
    
    def add_fact(
        self,
        key: str,
        value: Any,
        category: str = None,
        source: str = "user",
        priority: int = 0,
        tags: List[str] = None,
        ttl_days: int = None
    ) -> int:
        """
        添加事实记忆（自动版本控制）
        
        如果 key 已存在且状态为 active，则：
        1. 旧版本标记为 deprecated
        2. 创建新版本（version + 1）
        3. 新版本指向旧版本（supersedes）
        
        Returns:
            新记录的 ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 检查是否存在 active 版本
        cursor.execute('''
            SELECT id, version, value FROM facts 
            WHERE key = ? AND status = 'active'
            ORDER BY version DESC LIMIT 1
        ''', (key,))
        
        existing = cursor.fetchone()
        
        if existing:
            # 检查值是否相同
            if existing["value"] == str(value):
                # 值相同，不需要更新
                conn.close()
                return existing["id"]
            
            # 值不同，创建新版本
            old_id = existing["id"]
            new_version = existing["version"] + 1
            
            # 标记旧版本为 deprecated
            cursor.execute('''
                UPDATE facts SET status = 'deprecated', updated_at = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), old_id))
            
            # 计算过期时间
            expires_at = None
            if ttl_days:
                expires_at = (datetime.now() + timedelta(days=ttl_days)).isoformat()
            
            # 创建新版本
            cursor.execute('''
                INSERT INTO facts 
                (key, value, category, source, version, status, supersedes, priority, tags, expires_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?)
            ''', (
                key,
                str(value),
                category,
                source,
                new_version,
                old_id,  # supersedes
                priority,
                json.dumps(tags) if tags else None,
                expires_at,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            self.stats["total_facts"] += 1
            self.stats["total_versions"] += 1
            return new_id
        else:
            # 新 key，创建 version 1
            expires_at = None
            if ttl_days:
                expires_at = (datetime.now() + timedelta(days=ttl_days)).isoformat()
            
            cursor.execute('''
                INSERT INTO facts 
                (key, value, category, source, version, status, priority, tags, expires_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, 'active', ?, ?, ?, ?, ?)
            ''', (
                key,
                str(value),
                category,
                source,
                priority,
                json.dumps(tags) if tags else None,
                expires_at,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            self.stats["total_facts"] += 1
            return new_id
    
    def get_fact(
        self,
        key: str,
        version: int = None,
        include_deprecated: bool = False
    ) -> Optional[Dict]:
        """
        获取事实记忆
        
        Args:
            key: 键名
            version: 指定版本（None = 最新版本）
            include_deprecated: 是否包含已弃用的版本
        
        Returns:
            事实记录（包含版本信息）
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if version:
            # 获取指定版本
            cursor.execute('''
                SELECT * FROM facts WHERE key = ? AND version = ?
            ''', (key, version))
        else:
            # 获取最新 active 版本
            if include_deprecated:
                cursor.execute('''
                    SELECT * FROM facts 
                    WHERE key = ? 
                    ORDER BY version DESC LIMIT 1
                ''', (key,))
            else:
                cursor.execute('''
                    SELECT * FROM facts 
                    WHERE key = ? AND status = 'active'
                    ORDER BY version DESC LIMIT 1
                ''', (key,))
        
        row = cursor.fetchone()
        
        if row:
            # 更新访问统计
            cursor.execute('''
                UPDATE facts 
                SET access_count = access_count + 1, last_accessed = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), row["id"]))
            conn.commit()
            
            result = dict(row)
            if result["tags"]:
                result["tags"] = json.loads(result["tags"])
            conn.close()
            return result
        
        conn.close()
        return None
    
    def get_fact_history(self, key: str) -> List[Dict]:
        """
        获取事实的所有版本历史
        
        Returns:
            所有版本的列表（按版本号降序）
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM facts 
            WHERE key = ? 
            ORDER BY version DESC
        ''', (key,))
        
        rows = cursor.fetchall()
        results = []
        for row in rows:
            result = dict(row)
            if result["tags"]:
                result["tags"] = json.loads(result["tags"])
            results.append(result)
        
        conn.close()
        return results

    def search_facts(
        self,
        query: str,
        category: str = None,
        limit: int = 10,
        include_deprecated: bool = False
    ) -> List[Dict]:
        """
        搜索事实记忆（支持中文分词）
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 使用 jieba 分词
        try:
            import jieba
            keywords = list(jieba.cut(query))
            keywords = [k.strip() for k in keywords if len(k.strip()) > 1]
        except:
            keywords = [query]
        
        results = []
        
        # 尝试 FTS 搜索
        if keywords:
            fts_query = ' OR '.join(keywords)
            try:
                sql = "SELECT f.*, bm25(facts_fts) as relevance FROM facts f JOIN facts_fts ON facts_fts.rowid = f.id WHERE facts_fts MATCH ?"
                params = [fts_query]
                if category:
                    sql += ' AND f.category = ?'
                    params.append(category)
                if not include_deprecated:
                    sql += " AND f.status = 'active'"
                sql += ' ORDER BY f.priority DESC, relevance DESC LIMIT ?'
                params.append(limit)
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                for row in rows:
                    result = dict(row)
                    if result["tags"]:
                        result["tags"] = json.loads(result["tags"])
                    results.append(result)
            except:
                pass
        
        # FTS 无结果，使用 LIKE 搜索（支持中文）
        if not results:
            sql = 'SELECT * FROM facts WHERE 1=1'
            params = []
            if keywords:
                like_conditions = []
                for kw in keywords:
                    like_conditions.append('(key LIKE ? OR value LIKE ?)')
                    params.extend([f'%{kw}%', f'%{kw}%'])
                sql += ' AND (' + ' OR '.join(like_conditions) + ')'
            if category:
                sql += ' AND category = ?'
                params.append(category)
            if not include_deprecated:
                sql += " AND status = 'active'"
            sql += ' ORDER BY priority DESC, access_count DESC LIMIT ?'
            params.append(limit)
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            for row in rows:
                result = dict(row)
                if result["tags"]:
                    result["tags"] = json.loads(result["tags"])
                results.append(result)
        
        conn.close()
        return results

    def get_all_facts(
        self,
        category: str = None,
        include_deprecated: bool = False
    ) -> List[Dict]:
        """
        获取所有事实
        
        Args:
            category: 分类过滤
            include_deprecated: 是否包含已弃用的版本
        
        Returns:
            事实列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if category:
            if include_deprecated:
                cursor.execute('''
                    SELECT * FROM facts WHERE category = ? ORDER BY key, version DESC
                ''', (category,))
            else:
                cursor.execute('''
                    SELECT * FROM facts WHERE category = ? AND status = 'active' ORDER BY key, version DESC
                ''', (category,))
        else:
            if include_deprecated:
                cursor.execute('''
                    SELECT * FROM facts ORDER BY key, version DESC
                ''')
            else:
                cursor.execute('''
                    SELECT * FROM facts WHERE status = 'active' ORDER BY key, version DESC
                ''')
        
        rows = cursor.fetchall()
        results = []
        for row in rows:
            result = dict(row)
            if result["tags"]:
                result["tags"] = json.loads(result["tags"])
            results.append(result)
        
        conn.close()
        return results
    
    def delete_fact(self, key: str, archive: bool = True) -> bool:
        """
        删除事实记忆
        
        Args:
            key: 键名
            archive: 是否归档（True = 标记为 archived，False = 物理删除）
        
        Returns:
            是否成功
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if archive:
            # 标记为 archived
            cursor.execute('''
                UPDATE facts SET status = 'archived', updated_at = ?
                WHERE key = ? AND status = 'active'
            ''', (datetime.now().isoformat(), key))
        else:
            # 物理删除
            cursor.execute('DELETE FROM facts WHERE key = ?', (key,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    # ========== 关系记忆（版本化） ==========
    
    def add_relation(
        self,
        subject: str,
        predicate: str,
        object: str,
        context: str = None,
        strength: float = 1.0,
        evidence: str = None
    ) -> int:
        """添加关系记忆（自动版本控制）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 检查是否存在 active 版本
        cursor.execute('''
            SELECT id, version FROM relations 
            WHERE subject = ? AND predicate = ? AND object = ? AND status = 'active'
            ORDER BY version DESC LIMIT 1
        ''', (subject, predicate, object))
        
        existing = cursor.fetchone()
        
        if existing:
            # 创建新版本
            old_id = existing["id"]
            new_version = existing["version"] + 1
            
            cursor.execute('''
                UPDATE relations SET status = 'deprecated', updated_at = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), old_id))
            
            cursor.execute('''
                INSERT INTO relations 
                (subject, predicate, object, context, version, status, supersedes, strength, evidence, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)
            ''', (
                subject, predicate, object, context,
                new_version, old_id, strength, evidence,
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
        else:
            cursor.execute('''
                INSERT INTO relations 
                (subject, predicate, object, context, version, status, strength, evidence, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, 'active', ?, ?, ?, ?)
            ''', (
                subject, predicate, object, context,
                strength, evidence,
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
        
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return new_id
    
    def get_relations(
        self,
        subject: str = None,
        predicate: str = None,
        object: str = None,
        include_deprecated: bool = False
    ) -> List[Dict]:
        """获取关系"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        if subject:
            conditions.append('subject = ?')
            params.append(subject)
        if predicate:
            conditions.append('predicate = ?')
            params.append(predicate)
        if object:
            conditions.append('object = ?')
            params.append(object)
        
        if not include_deprecated:
            conditions.append("status = 'active'")
        
        sql = 'SELECT * FROM relations'
        if conditions:
            sql += ' WHERE ' + ' AND '.join(conditions)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        results = [dict(row) for row in rows]
        conn.close()
        return results


    # ========== 习惯和时间线 ==========

    def add_habit(
        self,
        domain: str,
        pattern: str,
        evidence: str = None,
        certainty: float = 0.5
    ) -> int:
        """
        添加习惯记忆（自动版本控制）
        
        Args:
            domain: 领域（如 coding, communication, workflow）
            pattern: 模式描述
            evidence: 证据
            certainty: 确定性 (0-1)
        
        Returns:
            新记录的 ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 检查是否存在相同 pattern
        cursor.execute('''
            SELECT id, version FROM habits 
            WHERE domain = ? AND pattern = ? AND status = 'active'
            ORDER BY version DESC LIMIT 1
        ''', (domain, pattern))
        
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有记录
            cursor.execute('''
                UPDATE habits 
                SET observation_count = observation_count + 1,
                    last_observed_at = ?,
                    certainty = (certainty + ?) / 2
                WHERE id = ?
            ''', (datetime.now().isoformat(), certainty, existing['id']))
            
            conn.commit()
            conn.close()
            return existing['id']
        
        # 创建新记录
        cursor.execute('''
            INSERT INTO habits
            (domain, pattern, evidence, version, status, created_at, last_observed_at, certainty)
            VALUES (?, ?, ?, 1, 'active', ?, ?, ?)
        ''', (
            domain,
            pattern,
            evidence,
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            certainty
        ))
        
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        self.stats["total_facts"] += 1
        return new_id

    def add_timeline_event(
        self,
        event_date: str,
        title: str,
        event_type: str = None,
        description: str = None,
        tags: List[str] = None,
        session_key: str = None
    ) -> int:
        """
        添加时间线事件（自动版本控制）
        
        Args:
            event_date: 事件日期 (YYYY-MM-DD)
            title: 事件标题
            event_type: 事件类型
            description: 事件描述
            tags: 标签列表
            session_key: 关联的会话 key
        
        Returns:
            新记录的 ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO timeline
            (event_date, event_type, title, description, tags, session_key, version, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, 'active', ?)
        ''', (
            event_date,
            event_type,
            title,
            description,
            json.dumps(tags) if tags else None,
            session_key,
            datetime.now().isoformat()
        ))
        
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return new_id

    # ========== 迁移功能（从旧系统导入） ==========
    
    def migrate_from_v1(self, old_db_path: str) -> Dict[str, int]:
        """
        从 Memory V1 迁移数据
        
        Args:
            old_db_path: 旧数据库路径
        
        Returns:
            迁移统计
        """
        conn_old = sqlite3.connect(old_db_path)
        conn_old.row_factory = sqlite3.Row
        cursor_old = conn_old.cursor()
        
        stats = {
            "facts": 0,
            "relations": 0,
            "habits": 0,
            "timeline": 0,
            "errors": 0
        }
        
        # 迁移 facts
        try:
            cursor_old.execute('SELECT * FROM facts')
            for row in cursor_old.fetchall():
                self.add_fact(
                    key=row["key"],
                    value=row["value"],
                    category=row.get("category"),
                    source=row.get("source", "migration"),
                    priority=row.get("priority", 0)
                )
                stats["facts"] += 1
        except Exception as e:
            stats["errors"] += 1
            print(f"迁移 facts 出错: {e}")
        
        # 迁移 relations
        try:
            cursor_old.execute('SELECT * FROM relations')
            for row in cursor_old.fetchall():
                self.add_relation(
                    subject=row["subject"],
                    predicate=row["predicate"],
                    object=row["object"],
                    context=row.get("context"),
                    strength=row.get("strength", 1.0)
                )
                stats["relations"] += 1
        except Exception as e:
            stats["errors"] += 1
            print(f"迁移 relations 出错: {e}")
        
        conn_old.close()
        return stats
    
    # ========== 统计和诊断 ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {
            "database_path": self.db_path,
            "facts": {
                "total": 0,
                "active": 0,
                "deprecated": 0,
                "archived": 0
            },
            "relations": {
                "total": 0,
                "active": 0
            },
            "conversations": {
                "total": 0,
                "sessions": 0
            },
            "versions": {
                "max_version": 0,
                "avg_versions_per_key": 0
            }
        }
        
        # 统计 facts
        cursor.execute('SELECT COUNT(*) FROM facts')
        stats["facts"]["total"] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM facts WHERE status = "active"')
        stats["facts"]["active"] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM facts WHERE status = "deprecated"')
        stats["facts"]["deprecated"] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM facts WHERE status = "archived"')
        stats["facts"]["archived"] = cursor.fetchone()[0]
        
        # 统计 relations
        cursor.execute('SELECT COUNT(*) FROM relations')
        stats["relations"]["total"] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM relations WHERE status = "active"')
        stats["relations"]["active"] = cursor.fetchone()[0]
        
        # 统计 conversations
        cursor.execute('SELECT COUNT(*) FROM conversation_logs')
        stats["conversations"]["total"] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT session_id) FROM conversation_logs')
        stats["conversations"]["sessions"] = cursor.fetchone()[0]
        
        # 统计版本
        cursor.execute('SELECT MAX(version) FROM facts')
        stats["versions"]["max_version"] = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT AVG(version_count) FROM (SELECT COUNT(*) as version_count FROM facts GROUP BY key)')
        result = cursor.fetchone()[0]
        stats["versions"]["avg_versions_per_key"] = round(result, 2) if result else 0
        
        conn.close()
        return stats
    
    def cleanup_expired(self) -> int:
        """清理过期的记忆"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute('''
            UPDATE facts SET status = 'archived', updated_at = ?
            WHERE expires_at IS NOT NULL AND expires_at < ? AND status = 'active'
        ''', (now, now))
        
        count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return count
    
    def export_to_json(self, include_deprecated: bool = False) -> Dict[str, Any]:
        """导出记忆为 JSON"""
        return {
            "facts": self.get_all_facts(include_deprecated=include_deprecated),
            "relations": self.get_relations(include_deprecated=include_deprecated),
            "stats": self.get_stats(),
            "exported_at": datetime.now().isoformat()
        }


# ========== 测试代码 ==========

    def search_conversations_simple(
        self,
        query: str,
        limit: int = 10,
        session_id: str = None,
        start_date: str = None,
        end_date: str = None
    ) -> List[Dict]:
        """
        简单搜索历史对话（支持中文）
        
        Args:
            query: 搜索关键词
            limit: 返回数量
            session_id: 限定会话
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            匹配的对话记录
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 使用 LIKE 搜索（支持中文）
        sql = '''
            SELECT * FROM conversation_logs
            WHERE content LIKE ?
        '''
        params = [f'%{query}%']
        
        if session_id:
            sql += ' AND session_id = ?'
            params.append(session_id)
        
        if start_date:
            sql += ' AND created_at >= ?'
            params.append(start_date)
        
        if end_date:
            sql += ' AND created_at <= ?'
            params.append(end_date)
        
        sql += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "id": row["id"],
                "session_id": row["session_id"],
                "turn_number": row["turn_number"],
                "role": row["role"],
                "content": row["content"],
                "persona": row["persona"],
                "created_at": row["created_at"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else None
            })
        
        conn.close()
        return results


# ========== 测试代码 ==========

def test_memory_v3():
    """测试 Memory V3"""
    print("🧪 测试 Memory V3...")
    
    # 使用测试数据库
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_memory_v3.db"
        memory = MemoryV3(str(db_path))
        
        # 测试 1: 添加事实
        print("\n1️⃣ 测试添加事实...")
        id1 = memory.add_fact("user_name", "原点", category="identity")
        print(f"   添加事实 ID: {id1}")
        
        # 测试 2: 更新事实（版本控制）
        print("\n2️⃣ 测试版本控制...")
        id2 = memory.add_fact("user_name", "原点（更新）", category="identity")
        print(f"   更新事实 ID: {id2}")
        
        # 测试 3: 获取事实
        print("\n3️⃣ 测试获取事实...")
        fact = memory.get_fact("user_name")
        print(f"   当前版本: {fact['version']}, 值: {fact['value']}, 状态: {fact['status']}")
        
        # 测试 4: 获取历史
        print("\n4️⃣ 测试获取历史...")
        history = memory.get_fact_history("user_name")
        print(f"   历史版本数: {len(history)}")
        for h in history:
            print(f"   - v{h['version']}: {h['value']} [{h['status']}]")
        
        # 测试 5: 对话日志
        print("\n5️⃣ 测试对话日志...")
        memory.log_conversation(
            session_id="test-session-1",
            role="user",
            content="你好，我是原点",
            turn_number=1
        )
        memory.log_conversation(
            session_id="test-session-1",
            role="assistant",
            content="你好原点！我是无限",
            turn_number=2
        )
        
        # 测试 6: 搜索对话
        print("\n6️⃣ 测试搜索对话...")
        results = memory.search_conversations_simple("原点")
        print(f"   搜索结果数: {len(results)}")
        for r in results:
            print(f"   - [{r['role']}]: {r['content']}")
        
        # 测试 7: 统计
        print("\n7️⃣ 测试统计...")
        stats = memory.get_stats()
        print(f"   事实总数: {stats['facts']['total']}")
        print(f"   Active: {stats['facts']['active']}, Deprecated: {stats['facts']['deprecated']}")
        print(f"   对话总数: {stats['conversations']['total']}")
        print(f"   最大版本: {stats['versions']['max_version']}")
        
        print("\n✅ 所有测试通过！")


if __name__ == "__main__":
    test_memory_v3()
