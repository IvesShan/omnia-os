"""Memory Palace 2.0 — SQLite-backed multi-layer memory for Omnia.

With shared vector service for semantic search across all layers.
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
from core.shared_vector_service import get_vector_service


@dataclass
class MemoryQueryResult:
    layer: str
    rowid: int
    snippet: str
    score: Optional[float] = None


class MemoryPalace:
    """Omnia's persistent memory substrate with semantic search."""

    def __init__(self, db_path: str | Path = None):
        if db_path is None:
            from core.config import MEMORY_PALACE_DB
            db_path = MEMORY_PALACE_DB
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._vector_service = None
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
        """Store a fact with semantic embedding."""
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
        
        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def forget_fact(self, fact_id: int) -> None:
        conn = self._connect()
        conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        conn.commit()

    # ------------------------------------------------------------------
    # Layer 2: Relations
    # ------------------------------------------------------------------
    def relate(self, subject: str, predicate: str, object: str, context: str = "", strength: float = 1.0) -> None:
        conn = self._connect()
        conn.execute(
            """
            INSERT INTO relations (subject, predicate, object, context, strength)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT DO UPDATE SET context=excluded.context, strength=excluded.strength
            """,
            (subject, predicate, object, context, strength),
        )
        conn.commit()

    def recall_relations(self, entity: str, direction: str = "both") -> List[Dict[str, Any]]:
        conn = self._connect()
        if direction == "out":
            sql = "SELECT * FROM relations WHERE subject = ?"
        elif direction == "in":
            sql = "SELECT * FROM relations WHERE object = ?"
        else:
            sql = "SELECT * FROM relations WHERE subject = ? OR object = ?"
        params = [entity] if direction != "both" else [entity, entity]
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Layer 3: Habits
    # ------------------------------------------------------------------
    def observe_habit(
        self,
        domain: str,
        pattern: str,
        evidence: str = "",
        certainty: float = 0.5,
    ) -> None:
        """Store a habit observation with semantic embedding."""
        # Generate embedding for the pattern
        embedding = self.vector_service.encode(pattern)
        embedding_blob = embedding.tobytes()

        conn = self._connect()
        conn.execute(
            """
            INSERT INTO habits (domain, pattern, evidence, certainty, embedding, last_observed_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(domain, pattern) DO UPDATE SET
                evidence=excluded.evidence,
                certainty=MAX(certainty, excluded.certainty),
                embedding=excluded.embedding,
                last_observed_at=CURRENT_TIMESTAMP
            """,
            (domain, pattern, evidence, certainty, embedding_blob),
        )
        conn.commit()

    def recall_habits(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._connect()
        if domain:
            rows = conn.execute(
                "SELECT * FROM habits WHERE domain = ? ORDER BY certainty DESC",
                (domain,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM habits ORDER BY domain, certainty DESC"
            ).fetchall()
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
    # Layer 4: Timeline
    # ------------------------------------------------------------------
    def record_event(
        self,
        event_date: date,
        event_type: str,
        title: str,
        description: str = "",
        tags: str = "",
        related_facts: Optional[List[int]] = None,
        session_key: str = "",
    ) -> None:
        """Record a timeline event with semantic embedding."""
        # Generate embedding for title + description
        text = f"{title} {description}"
        embedding = self.vector_service.encode(text)
        embedding_blob = embedding.tobytes()

        conn = self._connect()
        conn.execute(
            """
            INSERT INTO timeline 
            (event_date, event_type, title, description, tags, related_facts, session_key, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_date.isoformat(),
                event_type,
                title,
                description,
                tags,
                json.dumps(related_facts or []),
                session_key,
                embedding_blob,
            ),
        )
        conn.commit()

    def remember_timeline(
        self,
        event_type: str,
        content: str,
        title: str = None,
        tags: str = None,
        metadata: dict = None,
    ) -> None:
        """Store a timeline event with semantic embedding."""
        from datetime import date
        
        # Generate embedding for the content
        embedding = self.vector_service.encode(content)
        embedding_blob = embedding.tobytes()
        
        title = title or content[:50]
        event_date = date.today().isoformat()
        tags = tags or event_type
        
        conn = self._connect()
        conn.execute(
            """
            INSERT INTO timeline (event_date, event_type, title, description, tags, embedding)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (event_date, event_type, title, content, tags, embedding_blob),
        )
        conn.commit()


    def remember_relation(
        self,
        subject: str,
        predicate: str,
        object: str,
        context: str = None,
        strength: float = 1.0,
    ) -> None:
        """Store a relation between entities."""
        conn = self._connect()
        conn.execute(
            """
            INSERT INTO relations (subject, predicate, object, context, strength)
            VALUES (?, ?, ?, ?, ?)
            """,
            (subject, predicate, object, context, strength),
        )
        conn.commit()

    def remember_habit(
        self,
        domain: str,
        pattern: str,
        evidence: str = None,
        certainty: float = 0.5,
    ) -> None:
        """Store a user habit with semantic embedding."""
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
            "habits": self.search_habits_semantic(query, top_k),
            "timeline": self.search_timeline_semantic(query, top_k),
        }

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


# Convenience function for CLI

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
        """Semantic search across conversation logs."""
        query_vec = self.vector_service.encode(query)
        
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM conversation_logs WHERE embedding IS NOT NULL"
        ).fetchall()
        
        results = []
        for row in rows:
            if row['embedding']:
                stored_vec = np.frombuffer(row['embedding'], dtype=np.float32)
                similarity = self.vector_service.similarity(query_vec, stored_vec)
                results.append((dict(row), similarity))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def get_conversation_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all turns of a specific conversation session."""
        conn = self._connect()
        rows = conn.execute(
            """
            SELECT * FROM conversation_logs 
            WHERE session_id = ? 
            ORDER BY turn_number ASC
            """,
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Layer 6: Tool Logs (complete tool invocation history)
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
        # Generate embedding for the tool name + arguments
        args_json = json.dumps(arguments, ensure_ascii=False)
        embedding_text = f"{tool_name}: {args_json}"
        embedding = self.vector_service.encode(embedding_text)
        embedding_blob = embedding.tobytes()

        conn = self._connect()
        cursor = conn.execute(
            """
            INSERT INTO tool_logs
            (session_id, turn_number, tool_name, arguments, result, success, 
             error_message, duration_ms, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
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
        
        # Most used tools
        tool_counts = conn.execute(
            """
            SELECT tool_name, COUNT(*) as count 
            FROM tool_logs 
            GROUP BY tool_name 
            ORDER BY count DESC 
            LIMIT 10
            """
        ).fetchall()
        
        return {
            "total_invocations": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0,
            "most_used": [dict(r) for r in tool_counts],
        }
