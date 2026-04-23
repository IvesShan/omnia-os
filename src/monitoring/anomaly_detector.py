"""
异常检测系统
自动检测对话中断、上下文丢失、性能异常等
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class AnomalyType(Enum):
    """异常类型"""
    CONVERSATION_INTERRUPT = "conversation_interrupt"  # 对话中断
    CONTEXT_LOSS = "context_loss"  # 上下文丢失
    VECTOR_SEARCH_FAILED = "vector_search_failed"  # 向量检索失败
    SESSION_TIMEOUT = "session_timeout"  # 会话超时
    PERFORMANCE_DEGRADATION = "performance_degradation"  # 性能下降
    HIGH_ERROR_RATE = "high_error_rate"  # 高错误率
    MEMORY_LEAK = "memory_leak"  # 内存泄漏


@dataclass
class Anomaly:
    """异常记录"""
    anomaly_type: AnomalyType
    severity: str  # low, medium, high, critical
    description: str
    session_id: Optional[str]
    timestamp: datetime
    context: Dict
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class AnomalyDetector:
    """异常检测器"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(
            Path.home() / ".omnia" / "anomalies.db"
        )
        self._init_db()
        
        # 阈值配置
        self.thresholds = {
            'response_time_ms': 5000,  # 响应时间超过 5s
            'memory_usage_mb': 1000,  # 内存使用超过 1GB
            'error_rate': 0.1,  # 错误率超过 10%
            'session_duration_hours': 2,  # 会话时长超过 2 小时
            'context_hit_rate': 0.3,  # 上下文命中率低于 30%
        }
    
    def _init_db(self):
        """初始化异常数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anomaly_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT,
                session_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                context TEXT,
                resolved BOOLEAN DEFAULT 0,
                resolved_at TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_anomaly_type
            ON anomalies(anomaly_type)
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON anomalies(timestamp)
        ''')
        
        conn.commit()
        conn.close()
    
    def detect_conversation_interrupt(self, session_id: str, last_activity: datetime) -> Optional[Anomaly]:
        """检测对话中断"""
        now = datetime.now()
        gap = (now - last_activity).total_seconds()
        
        # 如果超过 10 分钟没有活动，视为中断
        if gap > 600:
            return Anomaly(
                anomaly_type=AnomalyType.CONVERSATION_INTERRUPT,
                severity="medium",
                description=f"对话中断 {gap/60:.1f} 分钟",
                session_id=session_id,
                timestamp=now,
                context={'gap_seconds': gap}
            )
        
        return None
    
    def detect_context_loss(self, session_id: str, context_hit_rate: float) -> Optional[Anomaly]:
        """检测上下文丢失"""
        if context_hit_rate < self.thresholds['context_hit_rate']:
            return Anomaly(
                anomaly_type=AnomalyType.CONTEXT_LOSS,
                severity="high",
                description=f"上下文命中率过低: {context_hit_rate:.2%}",
                session_id=session_id,
                timestamp=datetime.now(),
                context={'hit_rate': context_hit_rate}
            )
        
        return None
    
    def detect_performance_degradation(self, avg_response_time: float) -> Optional[Anomaly]:
        """检测性能下降"""
        if avg_response_time > self.thresholds['response_time_ms']:
            severity = "critical" if avg_response_time > 10000 else "high"
            
            return Anomaly(
                anomaly_type=AnomalyType.PERFORMANCE_DEGRADATION,
                severity=severity,
                description=f"响应时间过长: {avg_response_time:.0f}ms",
                session_id=None,
                timestamp=datetime.now(),
                context={'response_time_ms': avg_response_time}
            )
        
        return None
    
    def detect_high_error_rate(self, error_rate: float) -> Optional[Anomaly]:
        """检测高错误率"""
        if error_rate > self.thresholds['error_rate']:
            severity = "critical" if error_rate > 0.3 else "high"
            
            return Anomaly(
                anomaly_type=AnomalyType.HIGH_ERROR_RATE,
                severity=severity,
                description=f"错误率过高: {error_rate:.2%}",
                session_id=None,
                timestamp=datetime.now(),
                context={'error_rate': error_rate}
            )
        
        return None
    
    def detect_memory_leak(self, memory_usage_mb: float) -> Optional[Anomaly]:
        """检测内存泄漏"""
        if memory_usage_mb > self.thresholds['memory_usage_mb']:
            return Anomaly(
                anomaly_type=AnomalyType.MEMORY_LEAK,
                severity="high",
                description=f"内存使用过高: {memory_usage_mb:.0f}MB",
                session_id=None,
                timestamp=datetime.now(),
                context={'memory_usage_mb': memory_usage_mb}
            )
        
        return None
    
    def save_anomaly(self, anomaly: Anomaly):
        """保存异常记录"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            INSERT INTO anomalies 
            (anomaly_type, severity, description, session_id, timestamp, context, resolved)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            anomaly.anomaly_type.value,
            anomaly.severity,
            anomaly.description,
            anomaly.session_id,
            anomaly.timestamp.isoformat(),
            json.dumps(anomaly.context),
            anomaly.resolved
        ))
        conn.commit()
        conn.close()
    
    def resolve_anomaly(self, anomaly_id: int):
        """解决异常"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            UPDATE anomalies
            SET resolved = 1, resolved_at = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), anomaly_id))
        conn.commit()
        conn.close()
    
    def get_recent_anomalies(self, hours: int = 24, limit: int = 100) -> List[Anomaly]:
        """获取最近的异常"""
        conn = sqlite3.connect(self.db_path)
        
        cutoff = datetime.now() - timedelta(hours=hours)
        
        rows = conn.execute('''
            SELECT id, anomaly_type, severity, description, session_id, 
                   timestamp, context, resolved, resolved_at
            FROM anomalies
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (cutoff.isoformat(), limit)).fetchall()
        
        conn.close()
        
        return [
            Anomaly(
                anomaly_type=AnomalyType(row[1]),
                severity=row[2],
                description=row[3],
                session_id=row[4],
                timestamp=datetime.fromisoformat(row[5]),
                context=json.loads(row[6]) if row[6] else {},
                resolved=bool(row[7]),
                resolved_at=datetime.fromisoformat(row[8]) if row[8] else None
            )
            for row in rows
        ]
    
    def get_unresolved_anomalies(self) -> List[Anomaly]:
        """获取未解决的异常"""
        conn = sqlite3.connect(self.db_path)
        
        rows = conn.execute('''
            SELECT id, anomaly_type, severity, description, session_id, 
                   timestamp, context, resolved, resolved_at
            FROM anomalies
            WHERE resolved = 0
            ORDER BY severity DESC, timestamp DESC
        ''').fetchall()
        
        conn.close()
        
        return [
            Anomaly(
                anomaly_type=AnomalyType(row[1]),
                severity=row[2],
                description=row[3],
                session_id=row[4],
                timestamp=datetime.fromisoformat(row[5]),
                context=json.loads(row[6]) if row[6] else {},
                resolved=bool(row[7]),
                resolved_at=datetime.fromisoformat(row[8]) if row[8] else None
            )
            for row in rows
        ]
    
    def get_anomaly_stats(self, hours: int = 24) -> Dict:
        """获取异常统计"""
        conn = sqlite3.connect(self.db_path)
        
        cutoff = datetime.now() - timedelta(hours=hours)
        
        # 按类型统计
        type_stats = conn.execute('''
            SELECT anomaly_type, COUNT(*) as count
            FROM anomalies
            WHERE timestamp >= ?
            GROUP BY anomaly_type
        ''', (cutoff.isoformat(),)).fetchall()
        
        # 按严重程度统计
        severity_stats = conn.execute('''
            SELECT severity, COUNT(*) as count
            FROM anomalies
            WHERE timestamp >= ?
            GROUP BY severity
        ''', (cutoff.isoformat(),)).fetchall()
        
        # 未解决数量
        unresolved = conn.execute('''
            SELECT COUNT(*) FROM anomalies
            WHERE resolved = 0 AND timestamp >= ?
        ''', (cutoff.isoformat(),)).fetchone()[0]
        
        conn.close()
        
        return {
            'by_type': {row[0]: row[1] for row in type_stats},
            'by_severity': {row[0]: row[1] for row in severity_stats},
            'total': sum(row[1] for row in type_stats),
            'unresolved': unresolved
        }
    
    def run_health_check(self, metrics: Dict) -> List[Anomaly]:
        """运行健康检查"""
        anomalies = []
        
        # 检查性能
        if 'avg_response_time' in metrics:
            anomaly = self.detect_performance_degradation(metrics['avg_response_time'])
            if anomaly:
                anomalies.append(anomaly)
        
        # 检查错误率
        if 'error_rate' in metrics:
            anomaly = self.detect_high_error_rate(metrics['error_rate'])
            if anomaly:
                anomalies.append(anomaly)
        
        # 检查内存
        if 'memory_usage_mb' in metrics:
            anomaly = self.detect_memory_leak(metrics['memory_usage_mb'])
            if anomaly:
                anomalies.append(anomaly)
        
        # 保存检测到的异常
        for anomaly in anomalies:
            self.save_anomaly(anomaly)
        
        return anomalies


# 全局异常检测器实例
_detector_instance: Optional[AnomalyDetector] = None


def get_anomaly_detector() -> AnomalyDetector:
    """获取全局异常检测器实例"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = AnomalyDetector()
    return _detector_instance
