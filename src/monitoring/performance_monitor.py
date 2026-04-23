"""
性能监控系统
监控响应时间、内存使用、数据库性能等
"""

import time
import psutil
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import threading
from collections import deque


@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: datetime
    response_time_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    db_query_time_ms: float
    vector_search_time_ms: float
    active_sessions: int


@dataclass
class PerformanceStats:
    """性能统计"""
    avg_response_time_ms: float
    p95_response_time_ms: float
    avg_memory_usage_mb: float
    avg_cpu_usage_percent: float
    avg_db_query_time_ms: float
    avg_vector_search_time_ms: float
    total_requests: int
    error_count: int


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, db_path: Optional[str] = None, history_size: int = 1000):
        self.db_path = db_path or str(
            Path.home() / ".omnia" / "performance.db"
        )
        self.history_size = history_size
        self._init_db()
        
        # 响应时间历史
        self.response_times = deque(maxlen=history_size)
        self.db_query_times = deque(maxlen=history_size)
        self.vector_search_times = deque(maxlen=history_size)
        
        # 错误计数
        self.error_count = 0
        self.total_requests = 0
        
        # 锁
        self._lock = threading.Lock()
    
    def _init_db(self):
        """初始化性能数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                response_time_ms REAL,
                memory_usage_mb REAL,
                cpu_usage_percent REAL,
                db_query_time_ms REAL,
                vector_search_time_ms REAL,
                active_sessions INTEGER
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS slow_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                query_type TEXT NOT NULL,
                duration_ms REAL NOT NULL,
                details TEXT
            )
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON performance_metrics(timestamp)
        ''')
        
        conn.commit()
        conn.close()
    
    def record_response_time(self, response_time_ms: float):
        """记录响应时间"""
        with self._lock:
            self.response_times.append(response_time_ms)
            self.total_requests += 1
    
    def record_db_query_time(self, query_time_ms: float, query_type: str = "unknown"):
        """记录数据库查询时间"""
        with self._lock:
            self.db_query_times.append(query_time_ms)
            
            # 慢查询阈值：100ms
            if query_time_ms > 100:
                self._record_slow_query(query_type, query_time_ms)
    
    def record_vector_search_time(self, search_time_ms: float):
        """记录向量搜索时间"""
        with self._lock:
            self.vector_search_times.append(search_time_ms)
    
    def record_error(self):
        """记录错误"""
        with self._lock:
            self.error_count += 1
    
    def _record_slow_query(self, query_type: str, duration_ms: float, details: str = ""):
        """记录慢查询"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            INSERT INTO slow_queries (query_type, duration_ms, details)
            VALUES (?, ?, ?)
        ''', (query_type, duration_ms, details))
        conn.commit()
        conn.close()
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """获取当前性能指标"""
        # 获取系统指标
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent(interval=0.1)
        
        # 获取平均响应时间
        avg_response = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times else 0
        )
        
        # 获取平均查询时间
        avg_db_query = (
            sum(self.db_query_times) / len(self.db_query_times)
            if self.db_query_times else 0
        )
        
        # 获取平均向量搜索时间
        avg_vector_search = (
            sum(self.vector_search_times) / len(self.vector_search_times)
            if self.vector_search_times else 0
        )
        
        return PerformanceMetrics(
            timestamp=datetime.now(),
            response_time_ms=avg_response,
            memory_usage_mb=memory_mb,
            cpu_usage_percent=cpu_percent,
            db_query_time_ms=avg_db_query,
            vector_search_time_ms=avg_vector_search,
            active_sessions=0  # TODO: 从会话管理器获取
        )
    
    def get_stats(self, hours: int = 24) -> PerformanceStats:
        """获取性能统计"""
        with self._lock:
            if not self.response_times:
                return PerformanceStats(
                    avg_response_time_ms=0,
                    p95_response_time_ms=0,
                    avg_memory_usage_mb=0,
                    avg_cpu_usage_percent=0,
                    avg_db_query_time_ms=0,
                    avg_vector_search_time_ms=0,
                    total_requests=self.total_requests,
                    error_count=self.error_count
                )
            
            # 计算平均值和 P95
            sorted_times = sorted(self.response_times)
            p95_index = int(len(sorted_times) * 0.95)
            p95 = sorted_times[p95_index] if p95_index < len(sorted_times) else 0
            
            return PerformanceStats(
                avg_response_time_ms=sum(self.response_times) / len(self.response_times),
                p95_response_time_ms=p95,
                avg_memory_usage_mb=0,  # TODO: 从历史数据计算
                avg_cpu_usage_percent=0,
                avg_db_query_time_ms=sum(self.db_query_times) / len(self.db_query_times) if self.db_query_times else 0,
                avg_vector_search_time_ms=sum(self.vector_search_times) / len(self.vector_search_times) if self.vector_search_times else 0,
                total_requests=self.total_requests,
                error_count=self.error_count
            )
    
    def get_slow_queries(self, limit: int = 10) -> List[Dict]:
        """获取慢查询列表"""
        conn = sqlite3.connect(self.db_path)
        
        rows = conn.execute('''
            SELECT timestamp, query_type, duration_ms, details
            FROM slow_queries
            ORDER BY duration_ms DESC
            LIMIT ?
        ''', (limit,)).fetchall()
        
        conn.close()
        
        return [
            {
                'timestamp': row[0],
                'query_type': row[1],
                'duration_ms': row[2],
                'details': row[3]
            }
            for row in rows
        ]
    
    def save_metrics_snapshot(self):
        """保存性能指标快照"""
        metrics = self.get_current_metrics()
        
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            INSERT INTO performance_metrics 
            (timestamp, response_time_ms, memory_usage_mb, cpu_usage_percent,
             db_query_time_ms, vector_search_time_ms, active_sessions)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            metrics.timestamp.isoformat(),
            metrics.response_time_ms,
            metrics.memory_usage_mb,
            metrics.cpu_usage_percent,
            metrics.db_query_time_ms,
            metrics.vector_search_time_ms,
            metrics.active_sessions
        ))
        conn.commit()
        conn.close()
    
    def get_performance_trend(self, hours: int = 24) -> List[Dict]:
        """获取性能趋势"""
        conn = sqlite3.connect(self.db_path)
        
        cutoff = datetime.now() - timedelta(hours=hours)
        
        rows = conn.execute('''
            SELECT timestamp, response_time_ms, memory_usage_mb, cpu_usage_percent
            FROM performance_metrics
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT 100
        ''', (cutoff.isoformat(),)).fetchall()
        
        conn.close()
        
        return [
            {
                'timestamp': row[0],
                'response_time_ms': row[1],
                'memory_usage_mb': row[2],
                'cpu_usage_percent': row[3]
            }
            for row in rows
        ]
    
    def export_metrics(self, output_path: str):
        """导出性能指标"""
        stats = self.get_stats()
        trend = self.get_performance_trend()
        slow_queries = self.get_slow_queries()
        
        data = {
            'stats': asdict(stats),
            'trend': trend,
            'slow_queries': slow_queries,
            'exported_at': datetime.now().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return output_path


# 全局性能监控实例
_perf_monitor_instance: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控实例"""
    global _perf_monitor_instance
    if _perf_monitor_instance is None:
        _perf_monitor_instance = PerformanceMonitor()
    return _perf_monitor_instance


# 装饰器：自动记录函数执行时间
def monitor_performance(func):
    """性能监控装饰器"""
    def wrapper(*args, **kwargs):
        monitor = get_performance_monitor()
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            monitor.record_error()
            raise
        finally:
            elapsed_ms = (time.time() - start_time) * 1000
            monitor.record_response_time(elapsed_ms)
    
    return wrapper
