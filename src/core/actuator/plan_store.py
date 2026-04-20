"""PlanStore — Plan 持久化存储层

支持：
- 状态持久化（SQLite）
- 断点续传
- 执行历史追踪
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Step:
    """单个执行步骤"""
    id: str
    description: str
    tool_name: str
    tool_args: Dict[str, Any]
    status: str = StepStatus.PENDING.value
    result: Optional[Dict[str, Any]] = None
    observation: str = ""
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Step":
        return cls(**data)


@dataclass
class Plan:
    """执行计划"""
    id: str
    goal: str
    steps: List[Step]
    context: Dict[str, Any] = field(default_factory=dict)
    current_step_index: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "context": self.context,
            "current_step_index": self.current_step_index,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Plan":
        steps = [Step.from_dict(s) for s in data["steps"]]
        return cls(
            id=data["id"],
            goal=data["goal"],
            steps=steps,
            context=data.get("context", {}),
            current_step_index=data.get("current_step_index", 0),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class PlanStore:
    """Plan 持久化存储"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(PLAN_STORE_DB)
        
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                goal TEXT,
                context TEXT,
                current_step_index INTEGER,
                status TEXT DEFAULT 'running',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS steps (
                id TEXT PRIMARY KEY,
                plan_id TEXT,
                description TEXT,
                tool_name TEXT,
                tool_args TEXT,
                status TEXT,
                result TEXT,
                observation TEXT,
                dependencies TEXT,
                step_index INTEGER,
                FOREIGN KEY (plan_id) REFERENCES plans(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_plan(self, plan: Plan, session_id: str = None) -> None:
        """保存 Plan 到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 更新时间
        plan.updated_at = datetime.now().isoformat()
        
        # 保存 plan
        cursor.execute("""
            INSERT OR REPLACE INTO plans 
            (id, session_id, goal, context, current_step_index, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            plan.id,
            session_id,
            plan.goal,
            json.dumps(plan.context),
            plan.current_step_index,
            plan.created_at,
            plan.updated_at,
        ))
        
        # 保存 steps
        for idx, step in enumerate(plan.steps):
            cursor.execute("""
                INSERT OR REPLACE INTO steps
                (id, plan_id, description, tool_name, tool_args, status, result, observation, dependencies, step_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                step.id,
                plan.id,
                step.description,
                step.tool_name,
                json.dumps(step.tool_args),
                step.status,
                json.dumps(step.result) if step.result else None,
                step.observation,
                json.dumps(step.dependencies),
                idx,
            ))
        
        conn.commit()
        conn.close()
    
    def load_plan(self, plan_id: str = None, session_id: str = None) -> Optional[Plan]:
        """从数据库加载 Plan"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查找 plan
        if plan_id:
            cursor.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
        elif session_id:
            cursor.execute("SELECT * FROM plans WHERE session_id = ? ORDER BY updated_at DESC LIMIT 1", (session_id,))
        else:
            conn.close()
            return None
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        
        # 加载 steps
        cursor.execute("SELECT * FROM steps WHERE plan_id = ? ORDER BY step_index", (row["id"],))
        step_rows = cursor.fetchall()
        
        steps = []
        for sr in step_rows:
            step = Step(
                id=sr["id"],
                description=sr["description"],
                tool_name=sr["tool_name"],
                tool_args=json.loads(sr["tool_args"]) if sr["tool_args"] else {},
                status=sr["status"],
                result=json.loads(sr["result"]) if sr["result"] else None,
                observation=sr["observation"] or "",
                dependencies=json.loads(sr["dependencies"]) if sr["dependencies"] else [],
            )
            steps.append(step)
        
        plan = Plan(
            id=row["id"],
            goal=row["goal"],
            steps=steps,
            context=json.loads(row["context"]) if row["context"] else {},
            current_step_index=row["current_step_index"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        
        conn.close()
        return plan
    
    def update_step(self, plan_id: str, step_id: str, status: str = None, result: Dict = None, observation: str = None):
        """更新单个步骤状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if status:
            updates.append("status = ?")
            params.append(status)
        if result is not None:
            updates.append("result = ?")
            params.append(json.dumps(result))
        if observation is not None:
            updates.append("observation = ?")
            params.append(observation)
        
        if updates:
            params.extend([step_id, plan_id])
            cursor.execute(f"""
                UPDATE steps SET {', '.join(updates)}
                WHERE id = ? AND plan_id = ?
            """, params)
            
            # 更新 plan 的 updated_at
            cursor.execute("""
                UPDATE plans SET updated_at = ? WHERE id = ?
            """, (datetime.now().isoformat(), plan_id))
            
            conn.commit()
        
        conn.close()
    
    def list_active_plans(self, limit: int = 10) -> List[Dict]:
        """列出所有活跃的 Plan"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, goal, status, created_at, updated_at
            FROM plans 
            WHERE status = 'running'
            ORDER BY updated_at DESC
            LIMIT ?
        """, (limit,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def mark_plan_completed(self, plan_id: str, status: str = "completed"):
        """标记 Plan 完成"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE plans SET status = ?, updated_at = ? WHERE id = ?
        """, (status, datetime.now().isoformat(), plan_id))
        
        conn.commit()
        conn.close()


# 全局实例
_store: Optional[PlanStore] = None

def get_plan_store() -> PlanStore:
    """获取全局 PlanStore 实例"""
    global _store
    if _store is None:
        _store = PlanStore()
    return _store
