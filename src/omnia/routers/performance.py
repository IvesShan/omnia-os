"""
性能监控 API
"""
from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/api/performance", tags=["performance"])


@router.get("/status")
async def get_performance_status():
    """获取性能监控状态"""
    from src.omnia.services.performance import (
        performance_monitor,
        system_monitor,
        global_limiter
    )
    
    return {
        "system": system_monitor.get_current_stats(),
        "concurrency": global_limiter.get_stats(),
        "performance": {
            "operations_count": len(performance_monitor.metrics),
            "slow_operations_count": len(performance_monitor.slow_operations)
        }
    }


@router.get("/report")
async def get_full_report():
    """获取完整性能报告"""
    from src.omnia.services.performance import get_full_report
    from src.omnia.services.cache import get_cache_stats
    
    report = get_full_report()
    report["cache"] = get_cache_stats()
    
    return report


@router.get("/operations")
async def list_operations():
    """列出所有监控的操作"""
    from src.omnia.services.performance import performance_monitor
    
    return {
        "operations": list(performance_monitor.metrics.keys()),
        "count": len(performance_monitor.metrics)
    }


@router.get("/operations/{operation}")
async def get_operation_stats(operation: str):
    """获取特定操作的统计"""
    from src.omnia.services.performance import performance_monitor
    
    stats = performance_monitor.get_stats(operation)
    
    if stats["count"] == 0:
        return {"error": f"Operation '{operation}' not found"}
    
    return stats


@router.get("/slow-operations")
async def get_slow_operations(limit: int = Query(20, ge=1, le=100)):
    """获取慢操作列表"""
    from src.omnia.services.performance import performance_monitor
    
    return {
        "count": len(performance_monitor.slow_operations),
        "operations": performance_monitor.slow_operations[-limit:]
    }


@router.get("/system")
async def get_system_stats():
    """获取系统资源统计"""
    from src.omnia.services.performance import system_monitor
    
    return system_monitor.get_current_stats()


@router.get("/system/history")
async def get_system_history(limit: int = Query(20, ge=1, le=100)):
    """获取系统历史记录"""
    from src.omnia.services.performance import system_monitor
    
    return {
        "count": len(system_monitor.history),
        "history": system_monitor.get_history(limit)
    }


@router.post("/optimize")
async def optimize_memory():
    """触发内存优化"""
    from src.omnia.services.performance import system_monitor
    
    before = system_monitor.get_current_stats()
    system_monitor.optimize_memory()
    after = system_monitor.get_current_stats()
    
    return {
        "before": before,
        "after": after,
        "memory_freed_mb": before.get("memory_mb", 0) - after.get("memory_mb", 0)
    }


@router.post("/clear")
async def clear_performance_data():
    """清空性能数据"""
    from src.omnia.services.performance import performance_monitor
    
    performance_monitor.clear()
    
    return {"ok": True, "message": "Performance data cleared"}


@router.get("/cache")
async def get_cache_stats():
    """获取缓存统计"""
    from src.omnia.services.cache import get_cache_stats
    
    return get_cache_stats()


@router.post("/cache/clear")
async def clear_cache():
    """清空缓存"""
    from src.omnia.services.cache import (
        memory_cache,
        tool_cache,
        session_cache
    )
    
    memory_cache.clear()
    tool_cache.clear()
    session_cache.clear()
    
    return {"ok": True, "message": "All caches cleared"}


@router.get("/database")
async def get_database_stats():
    """获取数据库连接池统计"""
    from src.omnia.database.connection_pool import get_all_pool_stats
    
    return get_all_pool_stats()
