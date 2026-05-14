"""auto_memory.py — 自动记忆记录系统

在对话过程中自动：
1. 记录对话到 conversation_logs（保持连续性）
2. 提取关键信息保存为 facts
3. 更新习惯模式
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.omnia.config import settings


class AutoMemory:
    """自动记忆记录器 — 单例"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # 从 Flask 配置加载记忆库路径
        self.db_path = None
        self._find_db()

    def _find_db(self):
        """查找记忆库数据库"""
        from src.omnia.config import settings
        candidates = [
            Path(str(settings.memory_palace_db)),
            settings.omnia_home / "memory_palace.db",
            Path.home() / ".openclaw" / "memory_palace.db",
            Path.home() / ".omnia" / "memory_palace.db",
        ]

        for p in candidates:
            if p.exists():
                self.db_path = str(p)
                print(f"[AutoMemory] Using database: {self.db_path}")
                return
        self.db_path = str(candidates[0])
        print(f"[AutoMemory] Database not found, will create: {self.db_path}")

    def _connect(self):
        """连接数据库"""
        if not self.db_path:
            return None
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.row_factory = sqlite3.Row
            # 检测现有的 conversation_logs 表结构
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_logs'")
            table_exists = cursor.fetchone()
            if not table_exists:
                conn.execute('''
                    CREATE TABLE conversation_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT,
                        turn_number INTEGER DEFAULT 0,
                        role TEXT,
                        content TEXT,
                        created_at REAL,
                        metadata TEXT
                    )
                ''')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_conversation_session ON conversation_logs(session_id, created_at)')
                conn.commit()
            return conn
        except Exception as e:
            print(f"[AutoMemory] DB connect error: {e}")
            return None

    def _get_current_turn(self, conn, session_id: str) -> int:
        """获取当前会话的下一轮 turn_number"""
        try:
            cursor = conn.execute(
                "SELECT COALESCE(MAX(turn_number), -1) + 1 FROM conversation_logs WHERE session_id = ?",
                (session_id,)
            )
            return cursor.fetchone()[0] or 0
        except (sqlite3.OperationalError, KeyError):
            return 0

    def _detect_columns(self, conn) -> List[str]:
        """检测 conversation_logs 表的列"""
        try:
            cursor = conn.execute("PRAGMA table_info(conversation_logs)")
            return [row["name"] for row in cursor.fetchall()]
        except Exception:
            return []

    def log_conversation(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
    ):
        """记录一条对话到记忆库。兼容不同表结构。"""
        if not content:
            return
        conn = None
        try:
            conn = self._connect()
            if not conn:
                return

            columns = self._detect_columns(conn)

            # 通用插入：只插入存在的列
            col_map = {
                "session_id": session_id,
                "role": role,
                "content": content,
                "created_at": time.time(),
                "metadata": json.dumps(metadata or {}, ensure_ascii=False),
            }

            # turn_number 可能不存在，也可能 NOT NULL
            if "turn_number" in columns:
                turn = self._get_current_turn(conn, session_id)
                col_map["turn_number"] = turn

            # 动态构建 SQL
            valid_cols = [c for c in col_map if c in columns]
            placeholders = ["?" for _ in valid_cols]
            values = [col_map[c] for c in valid_cols]

            sql = f"INSERT INTO conversation_logs ({', '.join(valid_cols)}) VALUES ({', '.join(placeholders)})"
            conn.execute(sql, values)
            conn.commit()

        except Exception as e:
            print(f"[AutoMemory] Failed to log conversation: {e}")
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def log_user_message(self, session_id: str, message: str):
        """记录用户消息"""
        self.log_conversation(session_id, "user", message)

    def log_assistant_reply(self, session_id: str, reply: str, tool_calls_made: int = 0):
        """记录助手回复"""
        self.log_conversation(session_id, "assistant", reply, {
            "tool_calls": tool_calls_made,
        })

    def save_key_fact(self, content: str, source: str = "conversation"):
        """保存关键事实到记忆库"""
        if not content:
            return
        conn = None
        try:
            conn = self._connect()
            if not conn:
                return
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='facts'")
            if cursor.fetchone():
                conn.execute(
                    "INSERT INTO facts (content, source, created_at) VALUES (?, ?, ?)",
                    (content, source, time.time()),
                )
                conn.commit()
        except Exception as e:
            print(f"[AutoMemory] Failed to save fact: {e}")
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def query_conversations(self, session_id: str, limit: int = 20) -> List[Dict]:
        """查询指定会话的对话记录"""
        conn = None
        try:
            conn = self._connect()
            if not conn:
                return []
            rows = conn.execute(
                "SELECT role, content, created_at FROM conversation_logs WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
                (session_id, limit),
            ).fetchall()
            return [{"role": r["role"], "content": r["content"]} for r in rows]
        except Exception as e:
            print(f"[AutoMemory] Query error: {e}")
            return []
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass


# 全局单例
auto_memory = AutoMemory()
