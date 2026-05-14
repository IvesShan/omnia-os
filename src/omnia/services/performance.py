"""
并发控制和性能监控
"""
import asyncio
import time
import psutil
import gc
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
import logging

logger = logging.getLogger("omnia.performance")


# ========== 并发控制 ==========

class ConcurrencyLimiter:
    """并发限制器"""
    
    def __init__(self, max_concurrent: int = 100):
        """
        Args:
            max_concurrent: 最大并发数
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_count = 0
        self.total_requests = 0
    
    async def acquire(self):
        """获取许可"""
        await self.semaphore.acquire()
        self.active_count += 1
        self.total_requests += 1
    
    def release(self):
        """释放许可"""
        self.semaphore.release()
        self.active_count -= 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "max_concurrent": self.max_concurrent,
            "active_count": self.active_count,
            "available": self.semaphore._value,
            "total_requests": self.total_requests
        }


# 全局并发限制器
global_limiter = ConcurrencyLimiter(max_concurrent=100)


def rate_limit(limiter: Optional[ConcurrencyLimiter] = None):
    """
    速率限制装饰器
    
    Args:
        limiter: 并发限制器实例
    """
    if limiter is None:
        limiter = global_limiter
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            await limiter.acquire()
            try:
                return await func(*args, **kwargs)
            finally:
                limiter.release()
        
        return wrapper
    
    return decorator


# ========== 性能监控 ==========

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.slow_operations: List[Dict[str, Any]] = []
        self.max_slow_operations = 100
    
    def record(self, operation: str, duration: float, metadata: Optional[Dict] = None):
        """
        记录操作性能
        
        Args:
            operation: 操作名称
            duration: 耗时（秒）
            metadata: 元数据
        """
        # 记录指标
        if operation not in self.metrics:
            self.metrics[operation] = []
        
        self.metrics[operation].append(duration)
        
        # 保留最近 1000 条记录
        if len(self.metrics[operation]) > 1000:
            self.metrics[operation] = self.metrics[operation][-1000:]
        
        # 记录慢操作（超过 1 秒）
        if duration > 1.0:
            slow_op = {
                "operation": operation,
                "duration": duration,
                "timestamp": time.time(),
                "metadata": metadata or {}
            }
            
            self.slow_operations.append(slow_op)
            
            # 保留最近 100 条
            if len(self.slow_operations) > self.max_slow_operations:
                self.slow_operations = self.slow_operations[-self.max_slow_operations:]
            
            logger.warning(f"Slow operation: {operation} took {duration:.3f}s")
    
    def get_stats(self, operation: str) -> Dict[str, Any]:
        """获取操作统计"""
        if operation not in self.metrics:
            return {"operation": operation, "count": 0}
        
        durations = self.metrics[operation]
        
        if not durations:
            return {"operation": operation, "count": 0}
        
        sorted_durations = sorted(durations)
        
        return {
            "operation": operation,
            "count": len(durations),
            "min": min(durations),
            "max": max(durations),
            "avg": sum(durations) / len(durations),
            "p50": sorted_durations[len(sorted_durations) // 2],
            "p95": sorted_durations[int(len(sorted_durations) * 0.95)] if len(sorted_durations) >= 20 else None,
            "p99": sorted_durations[int(len(sorted_durations) * 0.99)] if len(sorted_durations) >= 100 else None,
        }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有统计"""
        return {
            "operations": {
                op: self.get_stats(op)
                for op in self.metrics.keys()
            },
            "slow_operations_count": len(self.slow_operations),
            "recent_slow_operations": self.slow_operations[-10:]  # 最近 10 条
        }
    
    def clear(self):
        """清空统计数据"""
        self.metrics.clear()
        self.slow_operations.clear()


# 全局性能监控器
performance_monitor = PerformanceMonitor()


def monitor_performance(operation: Optional[str] = None):
    """
    性能监控装饰器
    
    Args:
        operation: 操作名称（默认使用函数名）
    """
    def decorator(func):
        op_name = operation or func.__name__
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                performance_monitor.record(op_name, duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                performance_monitor.record(op_name, duration)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# ========== 系统资源监控 ==========

class SystemMonitor:
    """系统资源监控"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.history: List[Dict[str, Any]] = []
        self.max_history = 100
    
    def get_current_stats(self) -> Dict[str, Any]:
        """获取当前系统状态"""
        try:
            memory_info = self.process.memory_info()
            cpu_percent = self.process.cpu_percent(interval=0.1)
            
            return {
                "timestamp": time.time(),
                "memory_mb": memory_info.rss / 1024 / 1024,
                "memory_percent": self.process.memory_percent(),
                "cpu_percent": cpu_percent,
                "threads": self.process.num_threads(),
                "open_files": len(self.process.open_files()),
                "connections": len(self.process.connections()),
            }
        except Exception as e:
            return {
                "timestamp": time.time(),
                "error": str(e)
            }
    
    def record(self):
        """记录当前状态到历史"""
        stats = self.get_current_stats()
        self.history.append(stats)
        
        # 保留最近 100 条
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取历史记录"""
        return self.history[-limit:]
    
    def check_memory_pressure(self) -> bool:
        """检查内存压力"""
        stats = self.get_current_stats()
        memory_mb = stats.get("memory_mb", 0)
        
        # 超过 500MB 认为有压力
        if memory_mb > 500:
            logger.warning(f"High memory usage: {memory_mb:.1f}MB")
            return True
        
        return False
    
    def optimize_memory(self):
        """优化内存使用"""
        if self.check_memory_pressure():
            # 强制垃圾回收
            collected = gc.collect()
            logger.info(f"Garbage collected {collected} objects")
            
            # 再次检查
            stats = self.get_current_stats()
            memory_mb = stats.get("memory_mb", 0)
            logger.info(f"Memory after GC: {memory_mb:.1f}MB")


# 全局系统监控器
system_monitor = SystemMonitor()


# ========== 定时监控任务 ==========

async def start_monitoring(interval: int = 60):
    """
    启动定时监控
    
    Args:
        interval: 监控间隔（秒）
    """
    print(f"[Monitor] Starting system monitoring (interval: {interval}s)")
    
    while True:
        try:
            # 记录系统状态
            system_monitor.record()
            
            # 检查内存压力
            system_monitor.optimize_memory()
            
            # 定期清理性能数据
            if len(performance_monitor.metrics) > 50:
                # 保留最近 30 个操作的统计
                keys_to_remove = list(performance_monitor.metrics.keys())[:-30]
                for key in keys_to_remove:
                    del performance_monitor.metrics[key]
        
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
        
        await asyncio.sleep(interval)


def get_full_report() -> Dict[str, Any]:
    """获取完整性能报告"""
    return {
        "timestamp": time.time(),
        "system": system_monitor.get_current_stats(),
        "performance": performance_monitor.get_all_stats(),
        "concurrency": global_limiter.get_stats(),
        "cache": {},  # 由 cache.py 提供
    }


if __name__ == "__main__":
    # 测试性能监控
    print("Testing performance monitor...")
    
    @monitor_performance("test_operation")
    async def test_func():
        await asyncio.sleep(0.1)
        return "done"
    
    # 运行测试
    async def main():
        for i in range(10):
            await test_func()
        
        # 获取统计
        stats = performance_monitor.get_stats("test_operation")
        print(f"Stats: {stats}")
        
        # 获取系统状态
        system_stats = system_monitor.get_current_stats()
        print(f"System: {system_stats}")
    
    asyncio.run(main())
