# Omnia 性能优化指南

## 📊 性能优化概览

本文档记录 Omnia 2.0 的性能优化策略和实施细节。

---

## 🚀 已实施的优化

### 1. 数据库优化

#### 1.1 连接池管理
```python
# src/omnia/database/connection_pool.py
class ConnectionPool:
    """SQLite 连接池，减少连接开销"""
    - 最大连接数: 10
    - 连接复用: 启用
    - 自动清理: 30秒无活动关闭
```

#### 1.2 索引优化
```sql
-- Memory Palace 索引
CREATE INDEX idx_memory_layer ON memory_palace(layer);
CREATE INDEX idx_memory_created ON memory_palace(created_at);
CREATE INDEX idx_memory_content ON memory_palace(content);

-- FTS5 全文搜索
CREATE VIRTUAL TABLE memory_fts USING fts5(content, layer, metadata);
```

#### 1.3 查询优化
- 批量插入代替单条插入
- 使用事务减少磁盘 I/O
- 预编译 SQL 语句

---

### 2. 缓存策略

#### 2.1 内存缓存
```python
# src/omnia/services/cache.py
from functools import lru_cache
from datetime import datetime, timedelta

# LRU 缓存配置
MAX_CACHE_SIZE = 1000
CACHE_TTL = 300  # 5分钟

# 缓存装饰器
@lru_cache(maxsize=MAX_CACHE_SIZE)
def get_tool_schema(tool_name: str):
    """缓存工具 schema"""
    return tool_registry.get_schema(tool_name)

# 会话缓存
session_cache = TTLCache(maxsize=100, ttl=3600)
```

#### 2.2 Redis 缓存（可选）
```python
# src/omnia/services/redis_cache.py
import redis

redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

# 缓存热点数据
def cache_hot_data(key: str, value: Any, ttl: int = 300):
    redis_client.setex(key, ttl, json.dumps(value))

def get_cached_data(key: str) -> Optional[Any]:
    data = redis_client.get(key)
    return json.loads(data) if data else None
```

---

### 3. 异步处理优化

#### 3.1 并发控制
```python
# src/omnia/services/concurrency.py
import asyncio
from typing import List

# 信号量限制并发
MAX_CONCURRENT_REQUESTS = 100
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

async def process_with_limit(task: Callable, *args):
    """限制并发请求数"""
    async with semaphore:
        return await task(*args)
```

#### 3.2 批量处理
```python
# 批量向量搜索
async def batch_vector_search(queries: List[str]):
    """批量处理向量搜索请求"""
    tasks = [vector_search(q) for q in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

---

### 4. 内存优化

#### 4.1 对象池
```python
# src/omnia/services/object_pool.py
from queue import Queue

class ObjectPool:
    """对象池，减少对象创建开销"""
    def __init__(self, factory, max_size=100):
        self.factory = factory
        self.pool = Queue(maxsize=max_size)
    
    def get(self):
        return self.pool.get() if not self.pool.empty() else self.factory()
    
    def put(self, obj):
        if not self.pool.full():
            self.pool.put(obj)
```

#### 4.2 内存监控
```python
# src/omnia/services/memory_monitor.py
import psutil
import gc

def check_memory_usage():
    """检查内存使用情况"""
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    
    if memory_mb > 500:  # 超过 500MB
        gc.collect()  # 强制垃圾回收
    
    return memory_mb
```

---

### 5. 网络优化

#### 5.1 HTTP 连接复用
```python
# src/omnia/services/http_client.py
import aiohttp

# 全局连接池
connector = aiohttp.TCPConnector(
    limit=100,           # 最大连接数
    limit_per_host=20,   # 每个主机最大连接数
    keepalive_timeout=30 # 保活时间
)

http_client = aiohttp.ClientSession(connector=connector)
```

#### 5.2 响应压缩
```python
# src/omnia/main.py
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(
    GZipMiddleware,
    minimum_size=1000  # 超过 1KB 才压缩
)
```

---

### 6. 向量搜索优化

#### 6.1 批量嵌入
```python
# src/core/memory/vector_store.py
async def batch_embed(texts: List[str]):
    """批量生成嵌入向量"""
    # 使用批处理减少 API 调用
    batch_size = 20
    embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_embeddings = await embedding_model.encode(batch)
        embeddings.extend(batch_embeddings)
    
    return embeddings
```

#### 6.2 向量索引优化
```python
# Chroma 配置优化
chroma_client = chromadb.Client(
    Settings(
        chroma_db_impl="duckdb+parquet",
        persist_directory="./chroma_db",
        anonymized_telemetry=False
    )
)

collection = chroma_client.get_or_create_collection(
    name="omnia_memory",
    metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
)
```

---

### 7. MCP 工具优化

#### 7.1 工具预热
```python
# 启动时预热常用工具
async def warmup_tools():
    """预热工具，减少首次调用延迟"""
    hot_tools = ["read_file", "write_file", "execute_shell"]
    
    for tool_name in hot_tools:
        schema = tool_registry.get_schema(tool_name)
        # 预加载工具模块
        _ = tool_registry.get_tool(tool_name)
```

#### 7.2 工具结果缓存
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_tool_result(tool_name: str, params_hash: str):
    """缓存工具结果（适用于幂等操作）"""
    return execute_tool(tool_name, params)
```

---

## 📈 性能监控

### 1. 性能指标收集
```python
# src/omnia/services/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# 请求计数
request_count = Counter(
    'omnia_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

# 响应时间
response_time = Histogram(
    'omnia_response_time_seconds',
    'Response time in seconds',
    ['method', 'endpoint']
)

# 内存使用
memory_usage = Gauge(
    'omnia_memory_usage_mb',
    'Memory usage in MB'
)
```

### 2. 性能日志
```python
import logging
import time

logger = logging.getLogger("omnia.performance")

def log_performance(func):
    """性能日志装饰器"""
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start
        
        logger.info(f"{func.__name__} took {duration:.3f}s")
        
        if duration > 1.0:  # 超过 1 秒记录警告
            logger.warning(f"Slow operation: {func.__name__} ({duration:.3f}s)")
        
        return result
    return wrapper
```

---

## 🎯 性能基准

### 目标性能指标

| 指标 | 目标值 | 当前值 |
|------|--------|--------|
| API 响应时间 (P50) | < 100ms | - |
| API 响应时间 (P95) | < 500ms | - |
| API 响应时间 (P99) | < 1000ms | - |
| 并发请求处理 | 100 req/s | - |
| 内存使用 | < 500MB | ~100MB |
| CPU 使用率 | < 50% | < 5% |
| 数据库查询时间 | < 50ms | - |
| 向量搜索时间 | < 200ms | - |

---

## 🔧 性能调优建议

### 1. 系统层面
- 使用 SSD 存储数据库
- 增加系统内存（推荐 8GB+）
- 调整文件描述符限制：`ulimit -n 65535`

### 2. 应用层面
- 启用 GZip 压缩
- 使用连接池
- 启用缓存
- 批量处理请求

### 3. 数据库层面
- 定期 VACUUM 数据库
- 使用 WAL 模式
- 创建合适的索引
- 定期清理旧数据

### 4. 向量搜索
- 使用 GPU 加速（如果有）
- 调整 HNSW 参数
- 批量嵌入

---

## 📝 性能测试

### 测试脚本
```bash
# 使用 wrk 进行压力测试
wrk -t12 -c400 -d30s http://localhost:8765/api/status

# 使用 ab 进行测试
ab -n 1000 -c 100 http://localhost:8765/api/status
```

### 性能分析
```python
# 使用 cProfile 分析性能瓶颈
import cProfile

profiler = cProfile.Profile()
profiler.enable()

# ... 运行代码 ...

profiler.disable()
profiler.print_stats(sort='cumulative')
```

---

## 🚨 性能问题排查

### 常见问题

**1. 响应慢**
- 检查数据库查询
- 检查网络延迟
- 检查内存使用

**2. 内存泄漏**
- 使用 memory_profiler 分析
- 检查未关闭的连接
- 检查缓存策略

**3. CPU 占用高**
- 使用 py-spy 分析
- 检查死循环
- 检查频繁 GC

---

## 📚 参考资料

- [FastAPI 性能优化](https://fastapi.tiangolo.com/deployment/concepts/)
- [SQLite 性能优化](https://www.sqlite.org/optoverview.html)
- [Chroma 向量数据库优化](https://docs.trychroma.com/usage-guide)
- [Python 异步编程最佳实践](https://docs.python.org/3/library/asyncio.html)

---

*最后更新: 2026-05-12*
