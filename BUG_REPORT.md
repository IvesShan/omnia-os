# 🔍 Omnia OS Bug 深度检查报告

**检查时间**: 2026-04-29  
**检查范围**: 全部源代码  
**检查方法**: 静态代码分析 + 人工审查

---

## 📊 检查统计

| 指标 | 数量 |
|------|------|
| 检查文件数 | 50+ |
| 数据库连接未使用 with | 20+ 处 |
| 异常捕获 (except Exception) | 108 处 |
| TODO/FIXME 标记 | 21 处 |
| print() 调用 | 1710 处 |

---

## 🐛 发现的 Bug 列表

### 🔴 高优先级 Bug

#### Bug #1: web_server.py - 数据库连接未使用 with 语句

**位置**: `src/omnia/web_server.py:118-131`

**问题代码**:
```python
def _memory_counts() -> dict:
    db_file = MEMORY_PALACE_DB
    counts = {}
    if db_file.exists():
        import sqlite3
        conn = sqlite3.connect(str(db_file))  # ❌ 未使用 with 语句
        cursor = conn.cursor()
        for table in ["facts", "relations", "habits", "timeline", "conversation_logs"]:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                counts[table] = 0
        # ❌ 缺少 conn.close()，资源泄漏！
    return counts
```

**影响**: 如果操作过程中发生异常，数据库连接不会被关闭，导致资源泄漏。

**修复方案**: 使用 `with sqlite3.connect() as conn:`

**状态**: ✅ 已修复

---

#### Bug #2: prompt_builder.py - 导入语句在 docstring 内部

**位置**: `src/core/cognition/prompt_builder.py:2`

**问题代码**:
```python
"""Prompt Builder - 参考 Hermes 的动态系统提示
from core.config import MEMORY_PALACE_DB    # ❌ 导入在 docstring 内部！

根据对话阶段、工具执行状态等动态构建系统提示。
"""
```

**影响**: 导入语句在 docstring 内部，不会被执行，导致后续代码中 `MEMORY_PALACE_DB` 未定义。

**修复方案**: 将导入语句移到 docstring 外部

**状态**: ✅ 已修复

---

#### Bug #3: verification.py - 重复的类定义

**位置**: `src/core/execution/verification.py:35` 和 `241`

**问题代码**:
```python
# 第35行
class CapabilityLevel(Enum):
    """能力等级"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ...

# 第241行（重复！）
class CapabilityLevel(Enum):
    """能力等级"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ...
```

**影响**: 代码冗余，第二个定义会覆盖第一个。

**修复方案**: 删除重复定义

**状态**: ✅ 已修复

---

#### Bug #4: builder.py - 数据库连接未使用 with 语句

**位置**: `src/core/neural_graph/builder.py` (多处)

**问题代码**:
```python
conn = sqlite3.connect(self.db_path)
# ... 操作 ...
conn.close()  # ❌ 如果中间发生异常，连接不会关闭
```

**影响**: 如果操作过程中发生异常，数据库连接不会被关闭。

**修复方案**: 使用 `with sqlite3.connect() as conn:`

**状态**: ✅ 已修复

---

#### Bug #5: start_daemon.py - 文件句柄泄漏

**位置**: `scripts/start_daemon.py:230`

**问题代码**:
```python
log_fd = open(LOG_FILE, 'a', encoding='utf-8')

proc = subprocess.Popen(
    [python_exe, "-u", str(RUNNER_FILE)],
    stdout=log_fd,
    stderr=log_fd,
    stdin=subprocess.DEVNULL,
    start_new_session=True,
)
# ❌ log_fd 从未关闭！
```

**影响**: 每次启动守护进程都会泄漏一个文件句柄。

**修复方案**: 添加 `log_fd.close()`

**状态**: ✅ 已修复

---

#### Bug #6: watchdog.py - 文件句柄泄漏

**位置**: `scripts/watchdog.py:168`

**问题代码**:
```python
web_log_fd = open(web_log, 'a', encoding='utf-8')

subprocess.Popen(
    [sys.executable, str(PROJECT_ROOT / "src" / "omnia" / "web_server.py")],
    stdout=web_log_fd,
    stderr=subprocess.STDOUT,
    start_new_session=True,
)
# ❌ web_log_fd 从未关闭！
```

**影响**: 每次 watchdog 重启 web_server 都会泄漏一个文件句柄。

**修复方案**: 添加 `web_log_fd.close()`

**状态**: ✅ 已修复

---

### 🟡 中优先级 Bug

#### Bug #7: 大量数据库连接未使用 with 语句

**位置**: 多个文件

**受影响文件**:
- `src/omnia/__main__.py`
- `src/core/neural_graph/context_enhancer.py` (3处)
- `src/core/neural_graph/conversation_processor.py` (2处)
- `src/core/neural_graph/vector_store.py`
- `src/core/neural_graph/vector_integration.py` (4处)
- `src/core/neural_graph/graph.py` (7处)
- `src/core/topic_recognizer.py`

**问题**: 使用 `conn = sqlite3.connect()` 后手动调用 `conn.close()`，如果中间发生异常，连接不会被关闭。

**修复方案**: 全部改用 `with sqlite3.connect() as conn:`

**状态**: ⏳ 待修复

---

#### Bug #8: 过度捕获异常

**位置**: 全局，108 处 `except Exception:`

**问题**: 过度捕获异常会隐藏真正的错误，导致调试困难。

**建议**: 
- 只捕获预期的异常类型
- 记录完整的异常信息
- 避免使用空的 `except:` 或 `except Exception: pass`

**状态**: ⏳ 待审查

---

#### Bug #9: 过多的 print() 调用

**位置**: 全局，1710 处

**问题**: 
- 生产环境不应该有大量 print 输出
- 应该使用统一的日志系统

**建议**: 
- 使用 Python 的 logging 模块
- 配置日志级别
- 生产环境关闭调试日志

**状态**: ⏳ 待优化

---

#### Bug #10: TODO/FIXME 未处理

**位置**: 全局，21 处

**问题**: 代码中有未完成的 TODO 和 FIXME 标记。

**建议**: 
- 逐个检查并处理
- 或转换为 GitHub Issues

**状态**: ⏳ 待处理

---

### 🟢 低优先级 Bug

#### Bug #11: plan_executor.py - 无限重试风险

**位置**: `src/core/actuator/plan_executor.py:113-123`

**问题代码**:
```python
while retry_count < max_retries:
    try:
        result = await self._execute_step(step)
        if result.get("success"):
            break
    except Exception as e:
        logger.warning(f"步骤执行失败: {e}")
    
    retry_count += 1
    await asyncio.sleep(2 ** retry_count)  # 指数退避
# ❌ 如果所有重试都失败，没有返回失败状态！
```

**影响**: 如果所有重试都失败，函数没有明确的失败返回值。

**建议**: 添加失败状态返回

**状态**: ⏳ 待修复

---

#### Bug #12: manager.py - 超时设置过短

**位置**: `src/core/collaboration/manager.py:45`

**问题代码**:
```python
self.timeout = 30  # 默认超时30秒
```

**影响**: 对于复杂任务（如代码分析、文件搜索），30 秒可能不够。

**建议**: 根据任务类型动态调整超时时间

**状态**: ⏳ 待优化

---

## 📈 修复进度

| 优先级 | 总计 | 已修复 | 待修复 | 进度 |
|--------|------|--------|--------|------|
| 🔴 高 | 6 | 6 | 0 | 100% |
| 🟡 中 | 5 | 0 | 5 | 0% |
| 🟢 低 | 2 | 0 | 2 | 0% |
| **总计** | **13** | **6** | **7** | **46%** |

---

## 🔧 修复建议

### 1. 数据库连接统一使用 with 语句

**修改前**:
```python
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
# ... 操作 ...
conn.close()
```

**修改后**:
```python
with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    # ... 操作 ...
# 自动关闭连接
```

---

### 2. 异常处理最佳实践

**不推荐**:
```python
try:
    # ...
except Exception:
    pass  # 隐藏错误
```

**推荐**:
```python
try:
    # ...
except (FileNotFoundError, PermissionError) as e:
    logger.error(f"文件操作失败: {e}")
    raise  # 或返回明确的错误状态
```

---

### 3. 使用日志系统

**不推荐**:
```python
print(f"[Module] Message")
```

**推荐**:
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Message")
```

---

## 📝 下一步行动

1. **立即修复**: Bug #7 (数据库连接未使用 with)
2. **审查异常处理**: 逐个检查 108 处 `except Exception:`
3. **优化日志系统**: 替换 print() 为 logging
4. **处理 TODO**: 检查并处理 21 处 TODO/FIXME

---

**报告生成时间**: 2026-04-29T02:54:00Z  
**检查工具**: 静态代码分析 + 人工审查
