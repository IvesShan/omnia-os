"""Memory Palace 2.0 with Neural Graph Integration

扩展版 MemoryPalace，集成：
1. 向量语义搜索（从 memory_palace.py 合并）
2. NeuralGraphUpdater 的混合更新机制
from core.config import MEMORY_PALACE_DB
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import numpy as np

# Import shared vector service
from core.shared_vector_service import get_vector_service

if TYPE_CHECKING:
    from ..neural_graph.updater import NeuralGraphUpdater


@dataclass
class MemoryQueryResult:
    layer: str
    rowid: int
    snippet: str
    score: Optional[float] = None


class MemoryPalace:
    """Omnia's persistent memory substrate with semantic search and Neural Graph integration."""

    def __init__(
        self,
        db_path: str | Path = None,
        graph_updater: NeuralGraphUpdater = None,
    ):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._vector_service = None
        
        # Neural Graph Updater（可选）
        self.graph_updater = graph_updater
        
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
            self._vector_service = get_vector_service()
        return self._vector_service

    def initialize(self, schema_path: Optional[Path] = None) -> None:
        """Create tables and indices from schema.sql."""
        if schema_path is None:
            schema_path = Path(__file__).parent / "schema.sql"
        sql = schema_path.read_text(encoding="utf-8")
        conn = self._connect()
        conn.executescript(sql)
        conn.commit()

    def set_graph_updater(self, updater: NeuralGraphUpdater) -> None:
        """设置 Neural Graph Updater"""
        self.graph_updater = updater

    # ------------------------------------------------------------------
    # Layer 1: Facts
    # ------------------------------------------------------------------
    def remember_fact(
        self,
        category: str,
        key: str,
        value: str,
        source: str = "conversation",
        strength: float = 1.0,
    ) -> None:
        """Store a fact with semantic embedding and Neural Graph update."""
        # Generate embedding for the value
        embedding = self.vector_service.encode(value)
        embedding_blob = embedding.tobytes()

        conn = self._connect()
        conn.execute(
            """
            INSERT INTO facts (category, key, value, source, strength, embedding, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(category, key) DO UPDATE SET
                value=excluded.value,
                source=excluded.source,
                strength=excluded.strength,
                embedding=excluded.embedding,
                updated_at=CURRENT_TIMESTAMP
            """,
            (category, key, value, source, strength, embedding_blob),
        )
        conn.commit()
        
        # Hook: 触发图谱更新
        if self.graph_updater:
            memory_id = f"fact:{category}:{key}"
            text = f"{category}: {key} = {value}"
            self.graph_updater.on_memory_write(
                memory_id=memory_id,
                text=text,
                layer="facts",
                metadata={"category": category, "key": key, "source": source},
            )

    def recall_facts(self, category: Optional[str] = None, key: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._connect()
        sql = "SELECT * FROM facts WHERE 1=1"
        params: List[Any] = []
        if category:
            sql += " AND category = ?"
            params.append(category)
        if key:
            sql += " AND key LIKE ?"
            params.append(f"%{key}%")
        sql += " ORDER BY strength DESC, updated_at DESC"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def search_facts_semantic(self, query: str, top_k: int = 10) -> List[Tuple[Dict[str, Any], float]]:
        """Semantic search across facts."""
        query_vec = self.vector_service.encode(query)
        
        conn = self._connect()
        rows = conn.execute("SELECT * FROM facts WHERE embedding IS NOT NULL").fetchall()
        
        results = []
        for row in rows:
            if row['embedding']:
                stored_vec = np.frombuffer(row['embedding'], dtype=np.float32)
                similarity = self.vector_service.similarity(query_vec, stored_vec)
                results.append((dict(row), similarity))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def forget_fact(self, fact_id: int) -> None:
        """Delete a fact by ID."""
        conn = self._connect()
        conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        conn.commit()

    # ------------------------------------------------------------------
    # Layer 2: Relations (Entity Relationships)
    # ------------------------------------------------------------------
    def remember_relation(
        self,
        subject: str,
        predicate: str,
        object: str,
        context: str = None,
        strength: float = 1.0,
    ) -> None:
        """Store a relation with semantic embedding and Neural Graph update."""
        # Generate embedding for the full relation
        relation_text = f"{subject} {predicate} {object}"
        if context:
            relation_text += f" ({context})"
        
        embedding = self.vector_service.encode(relation_text)
        embedding_blob = embedding.tobytes()

        conn = self._connect()
        conn.execute(
            """
            INSERT INTO relations (subject, predicate, object, context, strength, embedding, created_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (subject, predicate, object, context, strength, embedding_blob),
        )
        conn.commit()
        
        # Hook: 触发图谱更新
        if self.graph_updater:
            memory_id = f"relation:{subject}:{predicate}:{object}"
            self.graph_updater.on_memory_write(
                memory_id=memory_id,
                text=relation_text,
                layer="relations",
                metadata={"subject": subject, "predicate": predicate, "object": object, "context": context},
            )

    def recall_relations(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        conn = self._connect()
        sql = "SELECT * FROM relations WHERE 1=1"
        params: List[Any] = []
        if subject:
            sql += " AND subject = ?"
            params.append(subject)
        if predicate:
            sql += " AND predicate = ?"
            params.append(predicate)
        if object:
            sql += " AND object = ?"
            params.append(object)
        sql += " ORDER BY strength DESC, created_at DESC"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def search_relations_semantic(self, query: str, top_k: int = 10) -> List[Tuple[Dict[str, Any], float]]:
        """Semantic search across relations."""
        query_vec = self.vector_service.encode(query)
        
        conn = self._connect()
        rows = conn.execute("SELECT * FROM relations WHERE embedding IS NOT NULL").fetchall()
        
        results = []
        for row in rows:
            if row['embedding']:
                stored_vec = np.frombuffer(row['embedding'], dtype=np.float32)
                similarity = self.vector_service.similarity(query_vec, stored_vec)
                results.append((dict(row), similarity))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    # ------------------------------------------------------------------
    # Layer 3: Habits (User Behavior Patterns)
    # ------------------------------------------------------------------
    def remember_habit(
        self,
        domain: str,
        pattern: str,
        evidence: str = None,
        certainty: float = 0.5,
    ) -> None:
        """Store a user habit with semantic embedding and Neural Graph update."""
        # Generate embedding for the pattern
        embedding = self.vector_service.encode(pattern)
        embedding_blob = embedding.tobytes()
        
        conn = self._connect()
        conn.execute(
            """
            INSERT INTO habits (domain, pattern, evidence, certainty, embedding, last_observed_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (domain, pattern, evidence, certainty, embedding_blob),
        )
        conn.commit()
        
        # Hook: 触发图谱更新
        if self.graph_updater:
            memory_id = f"habit:{domain}:{pattern[:30]}"
            self.graph_updater.on_memory_write(
                memory_id=memory_id,
                text=f"{domain}: {pattern}",
                layer="habits",
                metadata={"domain": domain, "pattern": pattern, "evidence": evidence},
            )

    def recall_habits(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._connect()
        sql = "SELECT * FROM habits WHERE 1=1"
        params: List[Any] = []
        if domain:
            sql += " AND domain = ?"
            params.append(domain)
        sql += " ORDER BY certainty DESC, last_observed_at DESC"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def search_habits_semantic(self, query: str, top_k: int = 10) -> List[Tuple[Dict[str, Any], float]]:
        """Semantic search across habits."""
        query_vec = self.vector_service.encode(query)
        
        conn = self._connect()
        rows = conn.execute("SELECT * FROM habits WHERE embedding IS NOT NULL").fetchall()
        
        results = []
        for row in rows:
            if row['embedding']:
                stored_vec = np.frombuffer(row['embedding'], dtype=np.float32)
                similarity = self.vector_service.similarity(query_vec, stored_vec)
                results.append((dict(row), similarity))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    # ------------------------------------------------------------------
    # Layer 4: Timeline (Chronological Events)
    # ------------------------------------------------------------------
    def remember_event(
        self,
        event_date: date,
        event_type: str,
        title: str,
        description: str = None,
        tags: str = None,
    ) -> None:
        """Store a timeline event with semantic embedding and Neural Graph update."""
        # Generate embedding for the description
        text_to_embed = description or title
        embedding = self.vector_service.encode(text_to_embed)
        embedding_blob = embedding.tobytes()

        conn = self._connect()
        conn.execute(
            """
            INSERT INTO timeline (event_date, event_type, title, description, tags, embedding, created_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (event_date.isoformat(), event_type, title, description, tags, embedding_blob),
        )
        conn.commit()
        
        # Hook: 触发图谱更新
        if self.graph_updater:
            memory_id = f"timeline:{event_date.isoformat()}:{event_type}"
            self.graph_updater.on_memory_write(
                memory_id=memory_id,
                text=f"{title}: {description}",
                layer="timeline",
                metadata={"event_date": event_date.isoformat(), "event_type": event_type, "tags": tags},
            )

    def recall_timeline(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        event_type: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        conn = self._connect()
        sql = "SELECT * FROM timeline WHERE 1=1"
        params: List[Any] = []
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

    def search_timeline_semantic(self, query: str, top_k: int = 10) -> List[Tuple[Dict[str, Any], float]]:
        """Semantic search across timeline events."""
        query_vec = self.vector_service.encode(query)
        
        conn = self._connect()
        rows = conn.execute("SELECT * FROM timeline WHERE embedding IS NOT NULL").fetchall()
        
        results = []
        for row in rows:
            if row['embedding']:
                stored_vec = np.frombuffer(row['embedding'], dtype=np.float32)
                similarity = self.vector_service.similarity(query_vec, stored_vec)
                results.append((dict(row), similarity))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    # ------------------------------------------------------------------
    # Cross-layer semantic search
    # ------------------------------------------------------------------
    def search_all_semantic(self, query: str, top_k: int = 10) -> Dict[str, List[Tuple[Dict[str, Any], float]]]:
        """Search across all memory layers semantically."""
        return {
            "facts": self.search_facts_semantic(query, top_k),
            "relations": self.search_relations_semantic(query, top_k),
            "habits": self.search_habits_semantic(query, top_k),
            "timeline": self.search_timeline_semantic(query, top_k),
        }

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Layer 5: Conversation Logs (complete dialogue history)
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
        # Generate embedding for the content
        embedding = self.vector_service.encode(content)
        embedding_blob = embedding.tobytes()
        
        metadata_json = json.dumps(metadata) if metadata else None

        conn = self._connect()
        cursor = conn.execute(
            """
            INSERT INTO conversation_logs 
            (session_id, turn_number, role, content, persona, embedding, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, turn_number, role, content, persona, embedding_blob, metadata_json),
        )
        conn.commit()
        return cursor.lastrowid

    def log_tool_use(
        self,
        session_id: str,
        turn_number: int,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any,
        success: bool = True,
    ) -> int:
        """Log a tool use event."""
        conn = self._connect()
        cursor = conn.execute(
            """
            INSERT INTO tool_logs
            (session_id, turn_number, tool_name, arguments, result, success)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, turn_number, tool_name, json.dumps(arguments), json.dumps(result), success),
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
    # Stats
    # ------------------------------------------------------------------
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        conn = self._connect()
        
        stats = {}
        for table in ["facts", "relations", "habits", "timeline"]:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            with_embedding = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE embedding IS NOT NULL").fetchone()[0]
            stats[table] = {
                "total": count,
                "with_embedding": with_embedding,
                "coverage": f"{with_embedding/count*100:.1f}%" if count > 0 else "N/A"
            }
        
        return stats
