"""
智能提醒引擎
基于上下文的主动提醒、任务追踪提醒、重要事件提醒
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import re


class ReminderType(Enum):
    """提醒类型"""
    TASK_DEADLINE = "task_deadline"  # 任务截止
    FOLLOW_UP = "follow_up"  # 跟进提醒
    PERIODIC_REVIEW = "periodic_review"  # 定期回顾
    ANOMALY_ALERT = "anomaly_alert"  # 异常提醒
    CONTEXT_BASED = "context_based"  # 基于上下文


@dataclass
class Reminder:
    """提醒"""
    reminder_id: str
    reminder_type: ReminderType
    content: str
    trigger_time: datetime
    created_at: datetime
    session_id: Optional[str]
    context: Dict
    priority: int = 3  # 1-5
    status: str = "pending"  # pending, triggered, dismissed
    triggered_at: Optional[datetime] = None


class ReminderEngine:
    """智能提醒引擎"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(
            Path.home() / ".omnia" / "reminders.db"
        )
        self._init_db()
        
        # 时间关键词映射
        self.time_keywords = {
            '今天': 0,
            '明天': 1,
            '后天': 2,
            '下周': 7,
            '下个月': 30,
            '一周后': 7,
            '一个月后': 30
        }
        
        # 跟进关键词
        self.follow_up_keywords = [
            '再聊', '回头说', '之后讨论', '继续',
            '下次', '稍后', '待会'
        ]
        
        # 任务关键词
        self.task_keywords = [
            '需要', '要', '计划', '准备', '安排',
            '待办', '任务', '完成'
        ]
    
    def _init_db(self):
        """初始化提醒数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reminder_id TEXT UNIQUE NOT NULL,
                    reminder_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    trigger_time TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT,
                    context TEXT,
                    priority INTEGER DEFAULT 3,
                    status TEXT DEFAULT 'pending',
                    triggered_at TIMESTAMP
                )
            ''')
        
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_trigger_time
                ON reminders(trigger_time)
            ''')
        
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_status
                ON reminders(status)
            ''')
        
            conn.commit()
    
    def analyze_context(self, context: Dict) -> List[Reminder]:
        """分析上下文，识别提醒点"""
        reminders = []
        
        # 检查任务截止
        task_reminders = self._detect_task_deadlines(context)
        reminders.extend(task_reminders)
        
        # 检查跟进需求
        follow_up_reminders = self._detect_follow_ups(context)
        reminders.extend(follow_up_reminders)
        
        return reminders
    
    def _detect_task_deadlines(self, context: Dict) -> List[Reminder]:
        """检测任务截止"""
        reminders = []
        
        message = context.get('message', '')
        next_steps = context.get('next_steps', [])
        
        # 检查时间关键词
        for keyword, days in self.time_keywords.items():
            if keyword in message:
                # 提取任务内容
                task = self._extract_task(message)
                if task:
                    trigger_time = datetime.now() + timedelta(days=days)
                    
                    reminder = Reminder(
                        reminder_id=f"task_{datetime.now().timestamp()}",
                        reminder_type=ReminderType.TASK_DEADLINE,
                        content=task,
                        trigger_time=trigger_time,
                        created_at=datetime.now(),
                        session_id=context.get('session_id'),
                        context={'keyword': keyword, 'days': days},
                        priority=4 if days <= 1 else 3
                    )
                    reminders.append(reminder)
        
        return reminders
    
    def _detect_follow_ups(self, context: Dict) -> List[Reminder]:
        """检测跟进需求"""
        reminders = []
        
        message = context.get('message', '')
        
        # 检查跟进关键词
        for keyword in self.follow_up_keywords:
            if keyword in message:
                # 默认 1 天后提醒
                trigger_time = datetime.now() + timedelta(days=1)
                
                reminder = Reminder(
                    reminder_id=f"follow_{datetime.now().timestamp()}",
                    reminder_type=ReminderType.FOLLOW_UP,
                    content=f"跟进: {message[:100]}",
                    trigger_time=trigger_time,
                    created_at=datetime.now(),
                    session_id=context.get('session_id'),
                    context={'keyword': keyword},
                    priority=3
                )
                reminders.append(reminder)
        
        return reminders
    
    def _extract_task(self, message: str) -> Optional[str]:
        """提取任务内容"""
        # 查找任务关键词
        for keyword in self.task_keywords:
            if keyword in message:
                # 提取包含关键词的句子
                sentences = re.split(r'[。！？\n]', message)
                for sent in sentences:
                    if keyword in sent and len(sent) > 5:
                        return sent.strip()
        
        return None
    
    def create_reminder(self, content: str, trigger_time: datetime,
                       reminder_type: ReminderType = ReminderType.CONTEXT_BASED,
                       priority: int = 3, session_id: str = None,
                       context: Dict = None) -> Reminder:
        """创建提醒"""
        reminder = Reminder(
            reminder_id=f"custom_{datetime.now().timestamp()}",
            reminder_type=reminder_type,
            content=content,
            trigger_time=trigger_time,
            created_at=datetime.now(),
            session_id=session_id,
            context=context or {},
            priority=priority
        )
        
        self._save_reminder(reminder)
        
        return reminder
    
    def _save_reminder(self, reminder: Reminder):
        """保存提醒"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO reminders 
                (reminder_id, reminder_type, content, trigger_time, created_at,
                 session_id, context, priority, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                reminder.reminder_id,
                reminder.reminder_type.value,
                reminder.content,
                reminder.trigger_time.isoformat(),
                reminder.created_at.isoformat(),
                reminder.session_id,
                json.dumps(reminder.context),
                reminder.priority,
                reminder.status
            ))
            conn.commit()
    
    def check_reminders(self) -> List[Reminder]:
        """检查到期提醒"""
        with sqlite3.connect(self.db_path) as conn:
        
            now = datetime.now()
        
            rows = conn.execute('''
                SELECT reminder_id, reminder_type, content, trigger_time,
                       created_at, session_id, context, priority, status, triggered_at
                FROM reminders
                WHERE status = 'pending' AND trigger_time <= ?
                ORDER BY priority DESC, trigger_time ASC
            ''', (now.isoformat(),)).fetchall()
        
        
        reminders = []
        for row in rows:
            reminder = Reminder(
                reminder_id=row[0],
                reminder_type=ReminderType(row[1]),
                content=row[2],
                trigger_time=datetime.fromisoformat(row[3]),
                created_at=datetime.fromisoformat(row[4]),
                session_id=row[5],
                context=json.loads(row[6]) if row[6] else {},
                priority=row[7],
                status=row[8],
                triggered_at=datetime.fromisoformat(row[9]) if row[9] else None
            )
            reminders.append(reminder)
        
        return reminders
    
    def trigger_reminder(self, reminder_id: str):
        """触发提醒"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE reminders
                SET status = 'triggered', triggered_at = ?
                WHERE reminder_id = ?
            ''', (datetime.now().isoformat(), reminder_id))
            conn.commit()
    
    def dismiss_reminder(self, reminder_id: str):
        """关闭提醒"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE reminders
                SET status = 'dismissed'
                WHERE reminder_id = ?
            ''', (reminder_id,))
            conn.commit()
    
    def get_pending_reminders(self, limit: int = 20) -> List[Reminder]:
        """获取待处理提醒"""
        with sqlite3.connect(self.db_path) as conn:
        
            rows = conn.execute('''
                SELECT reminder_id, reminder_type, content, trigger_time,
                       created_at, session_id, context, priority, status, triggered_at
                FROM reminders
                WHERE status = 'pending'
                ORDER BY trigger_time ASC
                LIMIT ?
            ''', (limit,)).fetchall()
        
        
        reminders = []
        for row in rows:
            reminder = Reminder(
                reminder_id=row[0],
                reminder_type=ReminderType(row[1]),
                content=row[2],
                trigger_time=datetime.fromisoformat(row[3]),
                created_at=datetime.fromisoformat(row[4]),
                session_id=row[5],
                context=json.loads(row[6]) if row[6] else {},
                priority=row[7],
                status=row[8],
                triggered_at=datetime.fromisoformat(row[9]) if row[9] else None
            )
            reminders.append(reminder)
        
        return reminders
    
    def get_reminder_stats(self, days: int = 7) -> Dict:
        """获取提醒统计"""
        with sqlite3.connect(self.db_path) as conn:
        
            cutoff = datetime.now() - timedelta(days=days)
        
        # 按类型统计
            type_stats = conn.execute('''
                SELECT reminder_type, COUNT(*) as count
                FROM reminders
                WHERE created_at >= ?
                GROUP BY reminder_type
            ''', (cutoff.isoformat(),)).fetchall()
        
        # 按状态统计
            status_stats = conn.execute('''
                SELECT status, COUNT(*) as count
                FROM reminders
                WHERE created_at >= ?
                GROUP BY status
            ''', (cutoff.isoformat(),)).fetchall()
        
        # 待处理数量
            pending = conn.execute('''
                SELECT COUNT(*) FROM reminders
                WHERE status = 'pending'
            ''').fetchone()[0]
        
        
        return {
            'by_type': {row[0]: row[1] for row in type_stats},
            'by_status': {row[0]: row[1] for row in status_stats},
            'total': sum(row[1] for row in type_stats),
            'pending': pending
        }
    
    def create_periodic_review(self, review_type: str = 'daily'):
        """创建定期回顾提醒"""
        if review_type == 'daily':
            trigger_time = datetime.now().replace(hour=20, minute=0, second=0)
            if trigger_time < datetime.now():
                trigger_time += timedelta(days=1)
            
            content = "今日回顾：总结今天的工作和对话"
        
        elif review_type == 'weekly':
            # 下周一上午 10 点
            days_ahead = 7 - datetime.now().weekday()
            trigger_time = datetime.now() + timedelta(days=days_ahead)
            trigger_time = trigger_time.replace(hour=10, minute=0, second=0)
            
            content = "本周回顾：总结本周的工作和进展"
        
        else:
            return None
        
        return self.create_reminder(
            content=content,
            trigger_time=trigger_time,
            reminder_type=ReminderType.PERIODIC_REVIEW,
            priority=2
        )


# 全局提醒引擎实例
_engine_instance: Optional[ReminderEngine] = None


def get_reminder_engine() -> ReminderEngine:
    """获取全局提醒引擎实例"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ReminderEngine()
    return _engine_instance
