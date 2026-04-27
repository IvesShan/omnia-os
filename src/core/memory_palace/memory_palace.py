"""Memory Palace 2.0 — SQLite-backed multi-layer memory for Omnia.

With shared vector service for semantic search across all layers.
Version 2.1: Added versioning, conflict detection, and status tracking.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Import shared vector service
from core.vector_ipc import get_hybrid_vector_service
from core.memory.mla_compressor import MLACompressor, create_mla_compressor


@dataclass
class MemoryQueryResult:
    layer: str
    rowid: int
    snippet: str
    score: Optional[float] = None


class MemoryPalace:
    """Omnia's persistent memory substrate with semantic search and versioning."""

    def __init__(self, db_path: str | Path = None, use_mla: bool = True):
        if db_path is None:
            from core.config import MEMORY_PALACE_DB
            db_path = MEMORY_PALACE_DB
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._vector_service = None
        self._mla_enabled = use_mla
        self._mla_compressor = None
        # 自动初始化数据库表
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    @property
    def vector_service(self):
        """Lazy-load vector service (singleton)."""
        if self._vector_service is None:
            self._vector_service = get_hybrid_vector_service()
        return self._vector_service

    @property
    def mla_compressor(self):
        """Lazy-load MLA compressor (singleton)."""
        if self._mla_compressor is None and self._mla_enabled:
            self._mla_compressor = create_mla_compressor()
        return self._mla_compressor

    def initialize(self, schema_path: Optional[Path] = None) -> None:
        """Create tables and indices from schema.sql."""
        # 先建基础表（不含新索引，避免旧表不兼容）
        conn = self._connect()
        
        # 建基础表（兼容旧表）
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                strength REAL DEFAULT 1.0,
                embedding BLOB
            );
            
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                strength REAL DEFAULT 1.0
            );
            
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                pattern TEXT NOT NULL,
                evidence TEXT,
                certainty REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_observed_at TIMESTAMP,
                embedding BLOB
            );
            
            CREATE TABLE IF NOT EXISTS timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_date DATE NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                related_facts TEXT,
                session_key TEXT,
                embedding BLOB
            );
            
            CREATE TABLE IF NOT EXISTS conversation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                persona TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                embedding BLOB,
                metadata TEXT
            );
            
            CREATE TABLE IF NOT EXISTS tool_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                turn_number INTEGER,
                tool_name TEXT NOT NULL,
                arguments TEXT NOT NULL,
                result TEXT,
                success INTEGER DEFAULT 1,
                error_message TEXT,
                duration_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                embedding BLOB
            );
        """)
        conn.commit()
        
        # 迁移旧表：添加版本化字段
        self._migrate_old_schema()
        
        # 然后建索引和 FTS（此时字段已存在）
        if schema_path is None:
            schema_path = Path(__file__).parent / "schema.sql"
        sql = schema_path.read_text(encoding="utf-8")
        
        # 只执行 FTS 和索引部分（表已经建好）
        fts_index_sql = []
        for line in sql.split('\n'):
            fts_index_sql.append(line)
            if '-- ============================================' in line:
                if 'Full-text search' in line or 'Indexes for semantic' in line or '-- 冲突检测表' in line:
                    fts_index_sql = [line]
        
        # 更稳健的方式：从 schema.sql 中提取 FTS 和索引语句
        import re
        # 找到 "Full-text search" 之后的所有内容
        fts_part = sql[sql.find('-- ============================================\n-- Full-text search'):]
        conn.executescript(fts_part)
        conn.commit()

    def _migrate_old_schema(self) -> None:
        """检查旧表并迁移（兼容旧版 schema）。"""
        conn = self._connect()
        
        migrations = []
        
        # facts
        cursor = conn.execute("PRAGMA table_info(facts)")
        columns = {row['name'] for row in cursor.fetchall()}
        
        if 'version' not in columns:
            migrations.append("ALTER TABLE facts ADD COLUMN version INTEGER DEFAULT 1")
        if 'status' not in columns:
            migrations.append("ALTER TABLE facts ADD COLUMN status TEXT DEFAULT 'active'")
        if 'supersedes' not in columns:
            migrations.append("ALTER TABLE facts ADD COLUMN supersedes INTEGER")
        if 'tags' not in columns:
            migrations.append("ALTER TABLE facts ADD COLUMN tags TEXT")
        if 'compressed_embedding' not in columns:
            migrations.append("ALTER TABLE facts ADD COLUMN compressed_embedding BLOB")
        if 'priority' not in columns:
            migrations.append("ALTER TABLE facts ADD COLUMN priority INTEGER DEFAULT 0")
            
        # relations
        cursor = conn.execute("PRAGMA table_info(relations)")
        rel_columns = {row['name'] for row in cursor.fetchall()}
        
        if 'version' not in rel_columns:
            migrations.append("ALTER TABLE relations ADD COLUMN version INTEGER DEFAULT 1")
        if 'status' not in rel_columns:
            migrations.append("ALTER TABLE relations ADD COLUMN status TEXT DEFAULT 'active'")
        if 'supersedes' not in rel_columns:
            migrations.append("ALTER TABLE relations ADD COLUMN supersedes INTEGER")
        if 'evidence' not in rel_columns:
            migrations.append("ALTER TABLE relations ADD COLUMN evidence TEXT")
        if 'updated_at' not in rel_columns:
            migrations.append("ALTER TABLE relations ADD COLUMN updated_at TIMESTAMP DEFAULT '1970-01-01 00:00:00'")
            
        # habits
        cursor = conn.execute("PRAGMA table_info(habits)")
        hab_columns = {row['name'] for row in cursor.fetchall()}
        
        if 'version' not in hab_columns:
            migrations.append("ALTER TABLE habits ADD COLUMN version INTEGER DEFAULT 1")
        if 'status' not in hab_columns:
            migrations.append("ALTER TABLE habits ADD COLUMN status TEXT DEFAULT 'active'")
        if 'supersedes' not in hab_columns:
            migrations.append("ALTER TABLE habits ADD COLUMN supersedes INTEGER")
        if 'observation_count' not in hab_columns:
            migrations.append("ALTER TABLE habits ADD COLUMN observation_count INTEGER DEFAULT 1")
            
        # timeline
        cursor = conn.execute("PRAGMA table_info(timeline)")
        tl_columns = {row['name'] for row in cursor.fetchall()}
        
        if 'version' not in tl_columns:
            migrations.append("ALTER TABLE timeline ADD COLUMN version INTEGER DEFAULT 1")
        if 'status' not in tl_columns:
            migrations.append("ALTER TABLE timeline ADD COLUMN status TEXT DEFAULT 'active'")
        if 'supersedes' not in tl_columns:
            migrations.append("ALTER TABLE timeline ADD COLUMN supersedes INTEGER")
        
        # conversation_logs
        cursor = conn.execute("PRAGMA table_info(conversation_logs)")
        conv_columns = {row['name'] for row in cursor.fetchall()}
        
        if 'extracted' not in conv_columns:
            migrations.append("ALTER TABLE conversation_logs ADD COLUMN extracted INTEGER DEFAULT 0")
        if 'extraction_notes' not in conv_columns:
            migrations.append("ALTER TABLE conversation_logs ADD COLUMN extraction_notes TEXT")
        
        # 执行迁移

        # 额外迁移：添加 compressed_embedding 列（MLA 压缩）
        cursor = conn.execute("PRAGMA table_info(facts)")
        extra_columns = {row['name'] for row in cursor.fetchall()}
        if 'compressed_embedding' not in extra_columns:
            try:
                conn.execute("ALTER TABLE facts ADD COLUMN compressed_embedding BLOB")
                conn.execute("ALTER TABLE habits ADD COLUMN compressed_embedding BLOB")
                conn.execute("ALTER TABLE timeline ADD COLUMN compressed_embedding BLOB")
                conn.execute("ALTER TABLE conversation_logs ADD COLUMN compressed_embedding BLOB")
                conn.execute("ALTER TABLE tool_logs ADD COLUMN compressed_embedding BLOB")
            except sqlite3.OperationalError:
                pass
        
        for sql in migrations:
            try:
                conn.execute(sql)
            except sqlite3.OperationalError as e:
                if 'duplicate column' not in str(e).lower():
                    raise  # 非重复列错误，继续抛出
        
        conn.commit()

    # ------------------------------------------------------------------
    # 版本化工具方法
    # ------------------------------------------------------------------
    def _ensure_versioning_tables(self):
        """确保版本化和冲突检测表存在。"""
        conn = self._connect()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                layer TEXT NOT NULL,
                entity_key TEXT NOT NULL,
                old_id INTEGER,
                new_id INTEGER,
                old_value TEXT,
                new_value TEXT,
                source TEXT,
                resolved TEXT DEFAULT 'pending',
                resolution_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            )
        """)
        conn.commit()

    # ------------------------------------------------------------------
    # Layer 1: Facts（带版本化）
    # ------------------------------------------------------------------
    def remember_fact(
        self,
        category: str,
        key: str,
        value: str,
        source: str = "conversation",
        strength: float = 1.0,
        tags: Optional[List[str]] = None,
        priority: int = 0,
    ) -> Dict[str, Any]:
        """存储事实，自动版本化。
        
        如果 (category, key) 已存在且值不同：
        1. 旧版本标记为 deprecated
        2. 创建新版本，version+1
        3. 记录冲突
        """
        # 确保旧表兼容
        self._migrate_old_schema()
        self._ensure_versioning_tables()
        
        # Generate embedding for the value
        embedding = self.vector_service.encode(value)
        embedding_blob = embedding.tobytes()
        # MLA 压缩
        compressed_embedding_blob = None
        if self.mla_compressor:
            compressed = self.mla_compressor.compress(embedding)
            compressed_embedding_blob = compressed.tobytes()
        tags_json = json.dumps(tags, ensure_ascii=False) if tags else None

        conn = self._connect()
        
        # 1. 查找是否已有 active 版本
        existing = conn.execute(
            """SELECT * FROM facts 
               WHERE category = ? AND key = ? AND status = 'active'
               LIMIT 1""",
            (category, key)
        ).fetchone()
        
        if existing:
            old_id = existing['id']
            old_value = existing['value']
            old_version = existing['version']
            
            if old_value == value:
                # 值相同，只更新 strength/updated_at
                conn.execute(
                    """UPDATE facts SET strength = ?, updated_at = CURRENT_TIMESTAMP, 
                       embedding = ?, source = ?, priority = ?, tags = ?
                       WHERE id = ?""",
                    (strength, embedding_blob, source, priority, tags_json, old_id)
                )
                conn.commit()
                # 返回完整的最新数据
                result = conn.execute("SELECT * FROM facts WHERE id = ?", (old_id,)).fetchone()
                return dict(result)
            
            # 值不同 → 版本化
            # 2. 标记旧版本为 deprecated
            conn.execute(
                """UPDATE facts SET status = 'deprecated', updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (old_id,)
            )
            
            # 3. 创建新版本
            new_version = old_version + 1
            cursor = conn.execute(
                """INSERT INTO facts 
                   (category, key, value, source, strength, embedding, 
                    version, status, supersedes, tags, priority)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)""",
                (category, key, value, source, strength, embedding_blob,
                 new_version, old_id, tags_json, priority)
            )
            new_id = cursor.lastrowid
            
            # 4. 记录冲突
            conn.execute(
                """INSERT OR IGNORE INTO conflicts 
                   (layer, entity_key, old_id, new_id, old_value, new_value, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ('facts', f'{category}:{key}', old_id, new_id, 
                 old_value[:200] if old_value else '', value[:200], source)
            )
            conn.commit()
            
            result = conn.execute("SELECT * FROM facts WHERE id = ?", (new_id,)).fetchone()
            return dict(result)
        else:
            # 全新事实
            cursor = conn.execute(
                """INSERT INTO facts 
                   (category, key, value, source, strength, embedding, 
                    version, status, tags, priority)
                   VALUES (?, ?, ?, ?, ?, ?, 1, 'active', ?, ?)""",
                (category, key, value, source, strength, embedding_blob,
                 tags_json, priority)
            )
            conn.commit()
            new_id = cursor.lastrowid
            result = conn.execute("SELECT * FROM facts WHERE id = ?", (new_id,)).fetchone()
            return dict(result)

    def recall_facts(
        self, 
        category: Optional[str] = None, 
        key: Optional[str] = None,
        include_deprecated: bool = False,
        status_filter: Optional[str] = 'active',
    ) -> List[Dict[str, Any]]:
        """召回事实，默认只返回 active 版本。
        
        Args:
            category: 按分类筛选
            key: 按关键词模糊匹配
            include_deprecated: 是否包含 deprecated 版本（覆盖 status_filter）
            status_filter: 状态筛选，默认 'active'，设为 None 返回所有
        """
        conn = self._connect()
        sql = "SELECT * FROM facts WHERE 1=1"
        params: List[Any] = []
        
        if category:
            sql += " AND category = ?"
            params.append(category)
        if key:
            sql += " AND key LIKE ?"
            params.append(f"%{key}%")
        if not include_deprecated and status_filter:
            sql += " AND status = ?"
            params.append(status_filter)
        
        sql += " ORDER BY strength DESC, updated_at DESC"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_fact_history(self, category: str, key: str) -> List[Dict[str, Any]]:
        """获取事实的完整版本历史，从旧到新排列。"""
        conn = self._connect()
        rows = conn.execute(
            """SELECT * FROM facts 
               WHERE category = ? AND key = ?
               ORDER BY version ASC""",
            (category, key)
        ).fetchall()
        return [dict(r) for r in rows]

    def activate_fact_version(self, fact_id: int) -> None:
        """手动将某个版本设为 active（用于冲突解决后回滚）。"""
        conn = self._connect()
        fact = conn.execute("SELECT * FROM facts WHERE id = ?", (fact_id,)).fetchone()
        if not fact:
            return
        
        # 将当前 active 版本标记为 deprecated
        conn.execute(
            """UPDATE facts SET status = 'deprecated' 
               WHERE category = ? AND key = ? AND status = 'active'""",
            (fact['category'], fact['key'])
        )
        # 将指定版本设为 active
        conn.execute(
            "UPDATE facts SET status = 'active' WHERE id = ?",
            (fact_id,)
        )
        conn.commit()

    def search_facts_semantic(self, query: str, top_k: int = 10, active_only: bool = True) -> List[Tuple[Dict[str, Any], float]]:
        """Semantic search across facts (with MLA acceleration)."""    
        return self._search_with_mla(query, 'facts', top_k, active_only)

    def forget_fact(self, fact_id: int) -> None:
        conn = self._connect()
        conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        conn.commit()

    # ------------------------------------------------------------------
    # Layer 2: Relations（带版本化）
    # ------------------------------------------------------------------
    def relate(
        self, 
        subject: str, 
        predicate: str, 
        object: str, 
        context: str = "", 
        strength: float = 1.0,
        evidence: Optional[str] = None,
    ) -> Dict[str, Any]:
        """存储关系，带版本化。"""
        self._migrate_old_schema()
        self._ensure_versioning_tables()
        conn = self._connect()
        
        existing = conn.execute(
            """SELECT id, context FROM relations 
               WHERE subject = ? AND predicate = ? AND object = ? AND status = 'active'
               LIMIT 1""",
            (subject, predicate, object)
        ).fetchone()
        
        if existing:
            old_id = existing['id']
            old_context = existing['context']
            
            if old_context == context:
                conn.execute(
                    "UPDATE relations SET strength = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (strength, old_id)
                )
                conn.commit()
                result = conn.execute("SELECT * FROM relations WHERE id = ?", (old_id,)).fetchone()
                return dict(result)
            
            # 版本化
            conn.execute(
                "UPDATE relations SET status = 'deprecated', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (old_id,)
            )
            
            # 获取最大版本号
            max_ver = conn.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM relations WHERE subject = ? AND predicate = ? AND object = ?",
                (subject, predicate, object)
            ).fetchone()[0]
            
            cursor = conn.execute(
                """INSERT INTO relations (subject, predicate, object, context, strength, 
                   version, status, supersedes, evidence)
                   VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
                (subject, predicate, object, context, strength,
                 max_ver, old_id, evidence)
            )
            new_id = cursor.lastrowid
            
            conn.execute(
                """INSERT OR IGNORE INTO conflicts (layer, entity_key, old_id, new_id, old_value, new_value, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ('relations', f'{subject}|{predicate}|{object}', old_id, new_id,
                 old_context[:200] if old_context else '', context[:200], 'relate')
            )
            conn.commit()
            
            result = conn.execute("SELECT * FROM relations WHERE id = ?", (new_id,)).fetchone()
            return dict(result)
        else:
            cursor = conn.execute(
                """INSERT INTO relations (subject, predicate, object, context, strength, 
                   version, status, evidence)
                   VALUES (?, ?, ?, ?, ?, 1, 'active', ?)""",
                (subject, predicate, object, context, strength, evidence)
            )
            conn.commit()
            new_id = cursor.lastrowid
            result = conn.execute("SELECT * FROM relations WHERE id = ?", (new_id,)).fetchone()
            return dict(result)

    def recall_relations(
        self, 
        entity: str, 
        direction: str = "both",
        include_deprecated: bool = False,
    ) -> List[Dict[str, Any]]:
        conn = self._connect()
        status_filter = "" if include_deprecated else (" AND status = 'active'" if domain else " WHERE status = 'active'")
        
        if direction == "out":
            sql = f"SELECT * FROM relations WHERE subject = ?{status_filter}"
        elif direction == "in":
            sql = f"SELECT * FROM relations WHERE object = ?{status_filter}"
        else:
            sql = f"SELECT * FROM relations WHERE (subject = ? OR object = ?){status_filter}"
        
        params = [entity] if direction != "both" else [entity, entity]
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Layer 3: Habits（带版本化）
    # ------------------------------------------------------------------
    def observe_habit(
        self,
        domain: str,
        pattern: str,
        evidence: str = "",
        certainty: float = 0.5,
    ) -> Dict[str, Any]:
        """存储习惯观察，带版本化。"""
        self._migrate_old_schema()
        self._ensure_versioning_tables()
        
        embedding = self.vector_service.encode(pattern)
        embedding_blob = embedding.tobytes()
        # MLA 压缩
        compressed_embedding_blob = None
        if self.mla_compressor:
            compressed = self.mla_compressor.compress(embedding)
            compressed_embedding_blob = compressed.tobytes()

        conn = self._connect()
        
        existing = conn.execute(
            """SELECT id, evidence, certainty, observation_count FROM habits 
               WHERE domain = ? AND pattern = ? AND status = 'active'
               LIMIT 1""",
            (domain, pattern)
        ).fetchone()
        
        if existing:
            old_id = existing['id']
            old_certainty = existing['certainty']
            new_certainty = max(certainty, old_certainty)
            obs_count = (existing['observation_count'] or 1) + 1
            
            if existing['evidence'] == evidence and new_certainty == old_certainty:
                conn.execute(
                    """UPDATE habits SET observation_count = ?, last_observed_at = CURRENT_TIMESTAMP
                       WHERE id = ?""",
                    (obs_count, old_id)
                )
                conn.commit()
                result = conn.execute("SELECT * FROM habits WHERE id = ?", (old_id,)).fetchone()
                return dict(result)
            
            # 版本化
            conn.execute(
                "UPDATE habits SET status = 'deprecated' WHERE id = ?",
                (old_id,)
            )
            
            max_ver = conn.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM habits WHERE domain = ? AND pattern = ?",
                (domain, pattern)
            ).fetchone()[0]
            
            cursor = conn.execute(
                """INSERT INTO habits (domain, pattern, evidence, certainty, embedding,
                   version, status, supersedes, observation_count, last_observed_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, CURRENT_TIMESTAMP)""",
                (domain, pattern, evidence, new_certainty, embedding_blob,
                 max_ver, old_id, obs_count)
            )
            new_id = cursor.lastrowid
            
            conn.commit()
            result = conn.execute("SELECT * FROM habits WHERE id = ?", (new_id,)).fetchone()
            return dict(result)
        else:
            cursor = conn.execute(
                """INSERT INTO habits (domain, pattern, evidence, certainty, embedding,
                   version, status, observation_count, last_observed_at)
                   VALUES (?, ?, ?, ?, ?, 1, 'active', 1, CURRENT_TIMESTAMP)""",
                (domain, pattern, evidence, certainty, embedding_blob)
            )
            conn.commit()
            new_id = cursor.lastrowid
            result = conn.execute("SELECT * FROM habits WHERE id = ?", (new_id,)).fetchone()
            return dict(result)

    def recall_habits(
        self, 
        domain: Optional[str] = None,
        include_deprecated: bool = False,
    ) -> List[Dict[str, Any]]:
        conn = self._connect()
        status_filter = "" if include_deprecated else " WHERE status = 'active'"
        
        if domain:
            rows = conn.execute(
                f"SELECT * FROM habits WHERE domain = ?{status_filter} ORDER BY certainty DESC",
                (domain,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM habits{status_filter} ORDER BY domain, certainty DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def search_habits_semantic(self, query: str, top_k: int = 10, active_only: bool = True) -> List[Tuple[Dict[str, Any], float]]:
        """Semantic search across habits (with MLA acceleration)."""
        return self._search_with_mla(query, 'habits', top_k, active_only)

    def record_event(
        self,
        event_date: date,
        event_type: str,
        title: str,
        description: str = "",
        tags: str = "",
        related_facts: Optional[List[int]] = None,
        session_key: str = "",
    ) -> int:
        """记录时间线事件，带版本化。"""
        self._migrate_old_schema()
        
        text = f"{title} {description}"
        embedding = self.vector_service.encode(text)
        embedding_blob = embedding.tobytes()
        # MLA 压缩
        compressed_embedding_blob = None
        if self.mla_compressor:
            compressed = self.mla_compressor.compress(embedding)
            compressed_embedding_blob = compressed.tobytes()

        conn = self._connect()
        
        # 检查是否已有相同标题的事件
        existing = conn.execute(
            """SELECT id FROM timeline WHERE title = ? AND status = 'active' LIMIT 1""",
            (title,)
        ).fetchone()
        
        if existing:
            old_id = existing['id']
            conn.execute(
                "UPDATE timeline SET status = 'deprecated' WHERE id = ?",
                (old_id,)
            )
            
            max_ver = conn.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM timeline WHERE title = ?",
                (title,)
            ).fetchone()[0]
            
            cursor = conn.execute(
                """INSERT INTO timeline 
                   (event_date, event_type, title, description, tags, related_facts, 
                    session_key, embedding, version, status, supersedes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)""",
                (event_date.isoformat(), event_type, title, description, tags,
                 json.dumps(related_facts or []), session_key, embedding_blob,
                 max_ver, old_id)
            )
            conn.commit()
            return cursor.lastrowid
        
        cursor = conn.execute(
            """INSERT INTO timeline 
               (event_date, event_type, title, description, tags, related_facts, 
                session_key, embedding, version, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 'active')""",
            (event_date.isoformat(), event_type, title, description, tags,
             json.dumps(related_facts or []), session_key, embedding_blob)
        )
        conn.commit()
        return cursor.lastrowid

    def remember_timeline(
        self,
        event_type: str,
        content: str,
        title: str = None,
        tags: str = None,
        metadata: dict = None,
    ) -> Optional[int]:
        """Store a timeline event with semantic embedding.
        
        Returns:
            rowid if successful, None if skipped (duplicate or invalid)
        """
        from datetime import date
        import logging
        logger = logging.getLogger(__name__)
        
        if not content or not content.strip():
            logger.warning(f"[MemoryPalace] 跳过空内容")
            return None
        
        if 'Sender (untrusted metadata)' in content:
            logger.warning(f"[MemoryPalace] 跳过异常数据: {content[:50]}...")
            return None
        
        if content.strip().startswith('```') and 'label' in content.lower():
            logger.warning(f"[MemoryPalace] 跳过代码块异常数据: {content[:50]}...")
            return None
        
        if len(content.strip()) < 3:
            logger.warning(f"[MemoryPalace] 跳过过短内容: {content}")
            return None
        
        title = title or content[:100]
        
        conn = self._connect()
        existing = conn.execute(
            "SELECT id FROM timeline WHERE title = ? AND status = 'active' LIMIT 1",
            (title,)
        ).fetchone()
        
        if existing:
            logger.info(f"[MemoryPalace] 跳过重复记忆: {title[:50]}...")
            return existing['id']
        
        embedding = self.vector_service.encode(content)
        embedding_blob = embedding.tobytes()
        # MLA 压缩
        compressed_embedding_blob = None
        if self.mla_compressor:
            compressed = self.mla_compressor.compress(embedding)
            compressed_embedding_blob = compressed.tobytes()
        
        event_date = date.today().isoformat()
        tags = tags or event_type
        
        cursor = conn.execute(
            """INSERT INTO timeline (event_date, event_type, title, description, tags, embedding, version, status)
               VALUES (?, ?, ?, ?, ?, ?, 1, 'active')""",
            (event_date, event_type, title, content, tags, embedding_blob),
        )
        conn.commit()
        
        rowid = cursor.lastrowid
        logger.debug(f"[MemoryPalace] 存储记忆 #{rowid}: {title[:50]}...")
        return rowid

    def remember_relation(
        self,
        subject: str,
        predicate: str,
        object: str,
        context: str = None,
        strength: float = 1.0,
    ) -> None:
        """Store a relation between entities."""
        self.relate(subject, predicate, object, context or "", strength)

    def remember_habit(
        self,
        domain: str,
        pattern: str,
        evidence: str = None,
        certainty: float = 0.5,
    ) -> None:
        """Store a user habit with semantic embedding."""
        self.observe_habit(domain, pattern, evidence or "", certainty)

    def recall_timeline(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        event_type: Optional[str] = None,
        tags: Optional[str] = None,
        include_deprecated: bool = False,
    ) -> List[Dict[str, Any]]:
        conn = self._connect()
        sql = "SELECT * FROM timeline WHERE 1=1"
        params: List[Any] = []
        
        if not include_deprecated:
            sql += " AND status = 'active'"
        if start_date:
            sql += " AND event_date >= ?"
            params.append(start_date.isoformat())
        if end_date:
            sql += " AND event_date <= ?"
            params.append(end_date.isoformat())
        if event_type:
            sql += " AND event_type = ?"
            params.append(event_type)
        if tags:
            sql += " AND tags LIKE ?"
            params.append(f"%{tags}%")
        sql += " ORDER BY event_date DESC"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def search_timeline_semantic(self, query: str, top_k: int = 10, active_only: bool = True) -> List[Tuple[Dict[str, Any], float]]:
        """Semantic search across timeline events (with MLA acceleration)."""
        return self._search_with_mla(query, 'timeline', top_k, active_only)

    def _search_with_mla(self, query: str, table: str, top_k: int = 10, 
                            active_only: bool = True) -> List[Tuple[Dict[str, Any], float]]:
        """使用 MLA 压缩空间加速语义搜索。
        
        在压缩空间（48维）中计算相似度，相比原始空间（384维）快 ~8x。
        如果 MLA 未启用或没有压缩嵌入，自动回退到原始空间搜索。
        """
        query_vec = self.vector_service.encode(query)
        conn = self._connect()
        
        # 检查是否可以使用 MLA
        has_mla = self._mla_enabled and self.mla_compressor is not None
        
        # 检查表是否有 compressed_embedding 列
        if has_mla:
            cursor = conn.execute(f"PRAGMA table_info({table})")
            cols = {row['name'] for row in cursor.fetchall()}
            if 'compressed_embedding' not in cols:
                has_mla = False
        
        # 构建查询
        if has_mla:
            where = " AND status = 'active'" if active_only and table != 'conversation_logs' else ""
            sql = f"SELECT *, embedding IS NOT NULL as has_embed FROM {table} WHERE compressed_embedding IS NOT NULL{where}"
        else:
            where = " AND status = 'active'" if active_only and table != 'conversation_logs' else ""
            sql = f"SELECT * FROM {table} WHERE embedding IS NOT NULL{where}"
        
        rows = conn.execute(sql).fetchall()
        
        if not rows:
            return []
        
        if has_mla:
            # 使用 MLA 压缩空间加速检索
            query_compressed = self.mla_compressor.compress(query_vec)
            compressed_vectors = []
            row_map = []
            
            for row in rows:
                if row['compressed_embedding']:
                    cv = np.frombuffer(row['compressed_embedding'], dtype=np.float32)
                    compressed_vectors.append(cv)
                    row_map.append(row)
            
            if compressed_vectors:
                results = self.mla_compressor.retrieve_with_mla(
                    query_vec, compressed_vectors, top_k
                )
                output = []
                for idx, score in results:
                    output.append((dict(row_map[idx]), score))
                return output
        
        # 回退到原始空间搜索
        results = []
        for row in rows:
            if row['embedding']:
                stored_vec = np.frombuffer(row['embedding'], dtype=np.float32)
                similarity = self.vector_service.similarity(query_vec, stored_vec)
                results.append((dict(row), similarity))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def search_all_semantic(self, query: str, top_k: int = 10, active_only: bool = True) -> Dict[str, List[Tuple[Dict[str, Any], float]]]:
        """Search across all memory layers semantically."""
        return {
            "facts": self.search_facts_semantic(query, top_k, active_only),
            "habits": self.search_habits_semantic(query, top_k, active_only),
            "timeline": self.search_timeline_semantic(query, top_k, active_only),
        }

    # ------------------------------------------------------------------
    # 冲突管理
    # ------------------------------------------------------------------
    def list_conflicts(self, resolved: Optional[str] = 'pending') -> List[Dict[str, Any]]:
        """列出冲突记录。
        
        Args:
            resolved: 'pending', 'resolved', 'ignored', None 返回所有
        """
        self._ensure_versioning_tables()
        conn = self._connect()
        if resolved:
            rows = conn.execute(
                "SELECT * FROM conflicts WHERE resolved = ? ORDER BY created_at DESC",
                (resolved,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM conflicts ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def resolve_conflict(self, conflict_id: int, resolution: str = 'resolved', notes: str = "") -> None:
        """解决冲突。
        
        Args:
            conflict_id: 冲突 ID
            resolution: 'resolved' 或 'ignored'
            notes: 解决备注
        """
        conn = self._connect()
        conn.execute(
            """UPDATE conflicts SET resolved = ?, resolution_notes = ?, resolved_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (resolution, notes, conflict_id)
        )
        conn.commit()

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ------------------------------------------------------------------
    # Layer 5: Conversation Logs
    # ------------------------------------------------------------------
    def log_conversation(
        self,
        session_id: str,
        turn_number: int,
        role: str,
        content: str,
        persona: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Log a complete conversation turn with semantic embedding."""
        embedding = self.vector_service.encode(content)
        embedding_blob = embedding.tobytes()
        # MLA 压缩
        compressed_embedding_blob = None
        if self.mla_compressor:
            compressed = self.mla_compressor.compress(embedding)
            compressed_embedding_blob = compressed.tobytes()
        
        metadata_json = json.dumps(metadata) if metadata else None

        conn = self._connect()
        cursor = conn.execute(
            """INSERT INTO conversation_logs 
               (session_id, turn_number, role, content, persona, embedding, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, turn_number, role, content, persona, embedding_blob, metadata_json),
        )
        conn.commit()
        return cursor.lastrowid

    def recall_conversations(
        self,
        session_id: Optional[str] = None,
        role: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Recall conversation logs with optional filters."""
        conn = self._connect()
        sql = "SELECT * FROM conversation_logs WHERE 1=1"
        params: List[Any] = []
        
        if session_id:
            sql += " AND session_id = ?"
            params.append(session_id)
        if role:
            sql += " AND role = ?"
            params.append(role)
        
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def search_conversations_semantic(
        self, query: str, top_k: int = 10
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Semantic search across conversation logs (with MLA acceleration)."""
        return self._search_with_mla(query, 'conversation_logs', top_k, active_only=True)


    def get_conversation_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all turns of a specific conversation session."""
        conn = self._connect()
        rows = conn.execute(
            """SELECT * FROM conversation_logs 
               WHERE session_id = ? 
               ORDER BY turn_number ASC""",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Layer 6: Tool Logs
    # ------------------------------------------------------------------
    def log_tool_use(
        self,
        session_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        turn_number: Optional[int] = None,
    ) -> int:
        """Log a tool invocation with complete details."""
        args_json = json.dumps(arguments, ensure_ascii=False)
        embedding_text = f"{tool_name}: {args_json}"
        embedding = self.vector_service.encode(embedding_text)
        embedding_blob = embedding.tobytes()

        conn = self._connect()
        cursor = conn.execute(
            """INSERT INTO tool_logs
               (session_id, turn_number, tool_name, arguments, result, success, 
                error_message, duration_ms, embedding)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, turn_number, tool_name, args_json, result, 
             1 if success else 0, error_message, duration_ms, embedding_blob),
        )
        conn.commit()
        return cursor.lastrowid

    def recall_tool_logs(
        self,
        session_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        success_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Recall tool logs with optional filters."""
        conn = self._connect()
        sql = "SELECT * FROM tool_logs WHERE 1=1"
        params: List[Any] = []
        
        if session_id:
            sql += " AND session_id = ?"
            params.append(session_id)
        if tool_name:
            sql += " AND tool_name = ?"
            params.append(tool_name)
        if success_only:
            sql += " AND success = 1"
        
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def search_tools_semantic(
        self, query: str, top_k: int = 10
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Semantic search across tool logs."""
        query_vec = self.vector_service.encode(query)
        
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM tool_logs WHERE embedding IS NOT NULL"
        ).fetchall()
        
        results = []
        for row in rows:
            if row['embedding']:
                stored_vec = np.frombuffer(row['embedding'], dtype=np.float32)
                similarity = self.vector_service.similarity(query_vec, stored_vec)
                results.append((dict(row), similarity))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def get_tool_stats(self) -> Dict[str, Any]:
        """Get statistics about tool usage."""
        conn = self._connect()
        
        total = conn.execute("SELECT COUNT(*) FROM tool_logs").fetchone()[0]
        successful = conn.execute(
            "SELECT COUNT(*) FROM tool_logs WHERE success = 1"
        ).fetchone()[0]
        
        tool_counts = conn.execute(
            """SELECT tool_name, COUNT(*) as count 
               FROM tool_logs 
               GROUP BY tool_name 
               ORDER BY count DESC 
               LIMIT 10"""
        ).fetchall()
        
        return {
            "total_invocations": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0,
            "most_used": [dict(r) for r in tool_counts],
        }
