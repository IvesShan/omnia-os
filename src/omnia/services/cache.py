"""
Omnia 缓存服务
提供内存缓存和 Redis 缓存支持
"""
import json
import asyncio
from typing import Any, Optional, Dict
from functools import lru_cache, wraps
from datetime import datetime, timedelta
from collections import OrderedDict
import threading


class TTLCache:
    """带 TTL 的 LRU 缓存"""
    
    def __init__(self, maxsize: int = 1000, ttl: int = 300):
        """
        Args:
            maxsize: 最大缓存条目数
            ttl: 缓存过期时间（秒）
        """
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache: OrderedDict = OrderedDict()
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            if key not in self.cache:
                return None
            
            value, timestamp = self.cache[key]
            
            # 检查是否过期
            if datetime.now() - timestamp > timedelta(seconds=self.ttl):
                del self.cache[key]
                return None
            
            # 移到末尾（LRU）
            self.cache.move_to_end(key)
            return value
    
    def set(self, key: str, value: Any):
        """设置缓存值"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
            
            self.cache[key] = (value, datetime.now())
            
            # 超过最大大小，删除最旧的
            while len(self.cache) > self.maxsize:
                self.cache.popitem(last=False)
    
    def delete(self, key: str):
        """删除缓存值"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self.lock:
            return {
                "size": len(self.cache),
                "maxsize": self.maxsize,
                "ttl": self.ttl,
                "usage_percent": len(self.cache) / self.maxsize * 100
            }


# 全局缓存实例
memory_cache = TTLCache(maxsize=1000, ttl=300)
tool_cache = TTLCache(maxsize=500, ttl=600)
session_cache = TTLCache(maxsize=100, ttl=3600)


def cached(ttl: int = 300, cache_instance: Optional[TTLCache] = None):
    """
    缓存装饰器
    
    Args:
        ttl: 缓存时间（秒）
        cache_instance: 使用的缓存实例
    """
    if cache_instance is None:
        cache_instance = memory_cache
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 尝试从缓存获取
            cached_value = cache_instance.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 缓存结果
            cache_instance.set(cache_key, result)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 尝试从缓存获取
            cached_value = cache_instance.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 缓存结果
            cache_instance.set(cache_key, result)
            
            return result
        
        # 根据函数类型返回不同的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class RedisCache:
    """Redis 缓存客户端（可选）"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.host = host
        self.port = port
        self.db = db
        self.client = None
        
        # 尝试连接 Redis
        try:
            import redis
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True
            )
            # 测试连接
            self.client.ping()
            print(f"[Cache] Redis connected: {host}:{port}")
        except Exception as e:
            print(f"[Cache] Redis not available, using memory cache: {e}")
            self.client = None
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if self.client is None:
            return None
        
        try:
            data = self.client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            print(f"[Cache] Redis get error: {e}")
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """设置缓存值"""
        if self.client is None:
            return
        
        try:
            self.client.setex(key, ttl, json.dumps(value))
        except Exception as e:
            print(f"[Cache] Redis set error: {e}")
    
    def delete(self, key: str):
        """删除缓存值"""
        if self.client is None:
            return
        
        try:
            self.client.delete(key)
        except Exception as e:
            print(f"[Cache] Redis delete error: {e}")
    
    def clear(self):
        """清空当前数据库"""
        if self.client is None:
            return
        
        try:
            self.client.flushdb()
        except Exception as e:
            print(f"[Cache] Redis clear error: {e}")
    
    def is_available(self) -> bool:
        """检查 Redis 是否可用"""
        return self.client is not None


# 全局 Redis 缓存实例（可选）
redis_cache = None

def init_redis_cache(host: str = "localhost", port: int = 6379, db: int = 0):
    """初始化 Redis 缓存"""
    global redis_cache
    redis_cache = RedisCache(host, port, db)
    return redis_cache


def get_cache_stats() -> Dict[str, Any]:
    """获取所有缓存的统计信息"""
    stats = {
        "memory_cache": memory_cache.get_stats(),
        "tool_cache": tool_cache.get_stats(),
        "session_cache": session_cache.get_stats(),
    }
    
    if redis_cache and redis_cache.is_available():
        stats["redis_cache"] = {
            "available": True,
            "host": redis_cache.host,
            "port": redis_cache.port,
            "db": redis_cache.db
        }
    else:
        stats["redis_cache"] = {
            "available": False
        }
    
    return stats


# 预热缓存
async def warmup_cache():
    """预热缓存，加载常用数据"""
    print("[Cache] Warming up cache...")
    
    # 预热工具 schema
    try:
        from src.omnia.services.tool_registry import tool_registry
        tools = tool_registry.get_tool_names()
        for tool_name in tools:
            schema = tool_registry.get_schema(tool_name)
            tool_cache.set(f"schema:{tool_name}", schema)
        print(f"[Cache] Cached {len(tools)} tool schemas")
    except Exception as e:
        print(f"[Cache] Tool cache warmup failed: {e}")
    
    print("[Cache] Cache warmup completed")


if __name__ == "__main__":
    # 测试缓存
    print("Testing cache...")
    
    # 测试 TTLCache
    cache = TTLCache(maxsize=3, ttl=5)
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")
    
    print(f"Get key1: {cache.get('key1')}")
    print(f"Stats: {cache.get_stats()}")
    
    # 测试装饰器
    @cached(ttl=10)
    async def test_func(x: int) -> int:
        print(f"Computing {x}...")
        return x * x
    
    import asyncio
    result = asyncio.run(test_func(5))
    print(f"Result: {result}")
    
    # 第二次调用应该从缓存获取
    result2 = asyncio.run(test_func(5))
    print(f"Result (cached): {result2}")
