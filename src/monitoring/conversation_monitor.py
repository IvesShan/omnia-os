"""
对话质量监控系统
实时监控对话质量，收集优化数据
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import threading


@dataclass
class ConversationMetrics:
    """对话质量指标"""
    session_id: str
    turn_count: int
    duration_seconds: float
    context_hit_rate: float  # 上下文命中率
    topic_shifts: int  # 主题切换次数
    avg_response_time: float
    user_satisfaction_score: Optional[float]  # 用户满意度（0-1）
    created_at: datetime


@dataclass
class SessionStats:
    """会话统计"""
    total_sessions: int
    avg_turn_count: float
    avg_duration: float
    avg_context_hit_rate: float
    total_topic_shifts: int
    active_sessions: int


class ConversationMonitor:
    """对话质量监控器"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(
            Path.home() / ".omnia" / "monitoring.db"
        )
        self._init_db()
        self._lock = threading.Lock()
        
        # 会话跟踪
        self.active_sessions: Dict[str, dict] = {}
    
    def _init_db(self):
        """初始化监控数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS conversation_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                turn_count INTEGER DEFAULT 0,
                duration_seconds REAL DEFAULT 0,
                context_hit_rate REAL DEFAULT 0,
                topic_shifts INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0,
                user_satisfaction_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS response_times (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                message_id TEXT,
                response_time REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS context_hits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                hit_type TEXT NOT NULL,
                hit_count INTEGER DEFAULT 0,
                miss_count INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_session_id 
            ON conversation_metrics(session_id)
        ''')
        
        conn.commit()
        conn.close()
    
    def start_session(self, session_id: str):
        """开始新会话"""
        with self._lock:
            self.active_sessions[session_id] = {
                'start_time': time.time(),
                'turn_count': 0,
                'response_times': [],
                'context_hits': 0,
                'context_misses': 0,
                'topic_shifts': 0,
                'topics': []
            }
    
    def record_turn(self, session_id: str, response_time: float):
        """记录对话轮次"""
        with self._lock:
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                session['turn_count'] += 1
                session['response_times'].append(response_time)
    
    def record_context_hit(self, session_id: str, hit: bool = True):
        """记录上下文命中"""
        with self._lock:
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                if hit:
                    session['context_hits'] += 1
                else:
                    session['context_misses'] += 1
    
    def record_topic_shift(self, session_id: str, old_topic: str, new_topic: str):
        """记录主题切换"""
        with self._lock:
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                session['topic_shifts'] += 1
                session['topics'].append({
                    'from': old_topic,
                    'to': new_topic,
                    'time': time.time()
                })
    
    def end_session(self, session_id: str, satisfaction_score: Optional[float] = None):
        """结束会话并保存指标"""
        with self._lock:
            if session_id not in self.active_sessions:
                return
            
            session = self.active_sessions[session_id]
            end_time = time.time()
            duration = end_time - session['start_time']
            
            # 计算平均响应时间
            avg_response_time = (
                sum(session['response_times']) / len(session['response_times'])
                if session['response_times'] else 0
            )
            
            # 计算上下文命中率
            total_context = session['context_hits'] + session['context_misses']
            context_hit_rate = (
                session['context_hits'] / total_context
                if total_context > 0 else 0
            )
            
            # 保存到数据库
            metrics = ConversationMetrics(
                session_id=session_id,
                turn_count=session['turn_count'],
                duration_seconds=duration,
                context_hit_rate=context_hit_rate,
                topic_shifts=session['topic_shifts'],
                avg_response_time=avg_response_time,
                user_satisfaction_score=satisfaction_score,
                created_at=datetime.now()
            )
            
            self._save_metrics(metrics)
            
            # 从活动会话中移除
            del self.active_sessions[session_id]
            
            return metrics
    
    def _save_metrics(self, metrics: ConversationMetrics):
        """保存指标到数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            INSERT INTO conversation_metrics 
            (session_id, turn_count, duration_seconds, context_hit_rate,
             topic_shifts, avg_response_time, user_satisfaction_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metrics.session_id,
            metrics.turn_count,
            metrics.duration_seconds,
            metrics.context_hit_rate,
            metrics.topic_shifts,
            metrics.avg_response_time,
            metrics.user_satisfaction_score,
            metrics.created_at.isoformat()
        ))
        conn.commit()
        conn.close()
    
    def get_session_stats(self, days: int = 7) -> SessionStats:
        """获取会话统计"""
        conn = sqlite3.connect(self.db_path)
        
        cutoff = datetime.now() - timedelta(days=days)
        
        rows = conn.execute('''
            SELECT session_id, turn_count, duration_seconds, context_hit_rate,
                   topic_shifts, user_satisfaction_score
            FROM conversation_metrics
            WHERE created_at >= ?
        ''', (cutoff.isoformat(),)).fetchall()
        
        conn.close()
        
        if not rows:
            return SessionStats(
                total_sessions=0,
                avg_turn_count=0,
                avg_duration=0,
                avg_context_hit_rate=0,
                total_topic_shifts=0,
                active_sessions=len(self.active_sessions)
            )
        
        total = len(rows)
        avg_turns = sum(r[1] for r in rows) / total
        avg_duration = sum(r[2] for r in rows) / total
        avg_hit_rate = sum(r[3] for r in rows) / total
        total_shifts = sum(r[4] for r in rows)
        
        return SessionStats(
            total_sessions=total,
            avg_turn_count=avg_turns,
            avg_duration=avg_duration,
            avg_context_hit_rate=avg_hit_rate,
            total_topic_shifts=total_shifts,
            active_sessions=len(self.active_sessions)
        )
    
    def get_quality_trend(self, days: int = 30) -> List[Dict]:
        """获取质量趋势"""
        conn = sqlite3.connect(self.db_path)
        
        cutoff = datetime.now() - timedelta(days=days)
        
        rows = conn.execute('''
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as session_count,
                AVG(turn_count) as avg_turns,
                AVG(context_hit_rate) as avg_hit_rate,
                AVG(avg_response_time) as avg_response_time
            FROM conversation_metrics
            WHERE created_at >= ?
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        ''', (cutoff.isoformat(),)).fetchall()
        
        conn.close()
        
        return [
            {
                'date': row[0],
                'session_count': row[1],
                'avg_turns': row[2],
                'avg_hit_rate': row[3],
                'avg_response_time': row[4]
            }
            for row in rows
        ]
    
    def get_top_topics(self, limit: int = 10) -> List[Dict]:
        """获取热门主题"""
        conn = sqlite3.connect(self.db_path)
        
        # 从 metadata 中提取主题
        rows = conn.execute('''
            SELECT metadata
            FROM conversation_metrics
            WHERE metadata IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 100
        ''').fetchall()
        
        conn.close()
        
        # TODO: 实现主题提取和统计
        return []
    
    def export_metrics(self, output_path: str, days: int = 30):
        """导出指标数据"""
        stats = self.get_session_stats(days)
        trend = self.get_quality_trend(days)
        
        data = {
            'stats': asdict(stats),
            'trend': trend,
            'exported_at': datetime.now().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return output_path


# 全局监控实例
_monitor_instance: Optional[ConversationMonitor] = None


def get_monitor() -> ConversationMonitor:
    """获取全局监控实例"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = ConversationMonitor()
    return _monitor_instance
