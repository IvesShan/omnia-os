# WebUI 上下文管理优化指南

## 📊 问题分析

### 1. 上下文截断的原因

你提到的问题"聊着聊着突然不记得前面的事情"或"引用了很早之前的信息"，主要由以下原因导致：

#### 1.1 消息条数限制 vs Token 限制

**当前实现**：
```python
# chat_handler.py
if len(history) < 10:
    db_history = load_recent_conversations(limit=40)
    history = merge_histories(history, db_history, max_total=80)
```

**问题**：
- ❌ 只限制了**消息条数**，没有限制 **Token 数量**
- ❌ 80 条消息可能包含 50k+ tokens，远超某些模型的上下文窗口
- ❌ 长消息（如代码、日志）会占用大量 tokens

#### 1.2 模型上下文窗口不匹配

**当前 max_tokens 配置**：
```python
# Kimi
"max_tokens": 4096  # 这是输出限制，不是上下文限制！

# Qianfan
"max_tokens": 8192  # 同样是输出限制
```

**问题**：
- ❌ `max_tokens` 是**输出**限制，不是**输入上下文**限制
- ❌ 没有考虑模型的**上下文窗口**大小（Kimi: 128k, Qianfan: 8k）
- ❌ 当输入 tokens 接近上下文窗口时，模型会"遗忘"早期内容

#### 1.3 注意力机制的限制

即使模型支持 128k 上下文，当消息过长时：
- 模型的注意力机制可能无法有效关注所有历史
- 导致"引用很早之前的信息"而非最近的上下文
- 这是因为注意力权重被稀释了

---

## 🔧 解决方案

### 方案 1：Token 智能管理（已实现）

我已经创建了 `token_manager.py`，提供以下功能：

#### 1.1 Token 估算

```python
from core.cognition.token_manager import estimate_messages_tokens

messages = [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好！有什么我可以帮助你的吗？"},
]

tokens = estimate_messages_tokens(messages)
print(f"Total tokens: {tokens}")
```

#### 1.2 上下文窗口查询

```python
from core.cognition.token_manager import get_model_context_window

# Kimi K2.6
tokens = get_model_context_window("K2.6-code-preview")  # 128000

# Qianfan
tokens = get_model_context_window("qianfan-code-latest")  # 8000
```

#### 1.3 智能压缩

```python
from core.cognition.token_manager import smart_compress_history

messages = [...]  # 很长的消息列表

compressed, stats = smart_compress_history(
    messages,
    model="K2.6-code-preview",
    max_tokens=60000,  # 使用 60k tokens
)

print(f"压缩前: {stats['original_count']} 条, {stats['original_tokens']} tokens")
print(f"压缩后: {stats['final_count']} 条, {stats['final_tokens']} tokens")
print(f"压缩率: {stats['compression_ratio']:.1%}")
```

### 方案 2：配置优化

#### 2.1 调整历史加载策略

**建议修改 `chat_handler.py`**：

```python
# 根据模型上下文窗口动态调整
context_window = get_model_context_window(model_name)
max_history_messages = min(100, int(context_window / 500))  # 每 500 tokens 约 1 条消息

if len(history) < 10:
    db_history = load_recent_conversations(
        limit=max_history_messages,
        current_message=message,
        min_similarity=0.3,
    )
    history = merge_histories(history, db_history, max_total=max_history_messages * 2)
```

#### 2.2 启用 Token 检查

**在调用模型前检查**：

```python
from core.cognition.token_manager import check_context_overflow

overflow_info = check_context_overflow(messages, model_name)
print(f"上下文利用率: {overflow_info['utilization']:.1%}")

if overflow_info["overflow"]:
    # 自动压缩
    messages, stats = smart_compress_history(messages, model_name)
```

### 方案 3：WebUI 界面优化建议

#### 3.1 显示上下文状态

**建议在 WebUI 添加**：

```html
<!-- 上下文状态栏 -->
<div class="context-status">
    <span class="token-count">
        📊 上下文: 12,345 / 128,000 tokens (9.6%)
    </span>
    <span class="message-count">
        💬 消息: 45 条
    </span>
</div>
```

#### 3.2 添加上下文管理按钮

```html
<div class="context-controls">
    <button onclick="clearHistory()">🗑️ 清空历史</button>
    <button onclick="exportHistory()">📥 导出对话</button>
    <button onclick="compressHistory()">🗜️ 压缩历史</button>
</div>
```

#### 3.3 显示压缩提示

当上下文接近限制时，显示提示：

```html
<div class="context-warning" v-if="contextUtilization > 0.7">
    ⚠️ 上下文已使用 70%，建议压缩或开始新对话
</div>
```

---

## 📝 配置文件

### 用户自定义配置

创建 `~/.omnia/context_config.py`：

```python
from core.cognition.context_config import ContextConfig

CONTEXT_CONFIG = ContextConfig(
    # 更激进的压缩策略
    context_utilization_threshold=0.6,  # 60% 时开始压缩
    
    # 历史加载
    db_history_limit=50,  # 从数据库加载 50 条
    max_merged_history=100,  # 合并后最多 100 条
    
    # 压缩策略
    preserve_recent_messages=10,  # 保留最近 10 条消息
    
    # 调试
    verbose=True,  # 打印详细信息
)
```

---

## 🎯 最佳实践

### 1. 根据模型选择策略

| 模型 | 上下文窗口 | 建议策略 |
|------|-----------|---------|
| Kimi K2.6 | 128k | 保留更多历史，压缩阈值 80% |
| Qianfan | 8k | 激进压缩，压缩阈值 60% |
| GPT-4o | 128k | 同 Kimi |
| 本地模型 | 4-8k | 最激进压缩，压缩阈值 50% |

### 2. 避免上下文截断

1. **定期压缩**：当上下文超过 70% 时，主动压缩
2. **关键信息前置**：重要信息放在最近的消息中
3. **使用记忆系统**：将关键信息存储到 Memory Palace
4. **分段对话**：复杂任务分成多个独立对话

### 3. 监控上下文

```python
# 在每次对话后记录
from core.cognition.token_manager import check_context_overflow

overflow = check_context_overflow(messages, model)
if overflow["overflow"]:
    print(f"⚠️ 上下文溢出警告！当前: {overflow['current_tokens']} / {overflow['max_tokens']}")
```

---

## 🚀 实施步骤

### 第一步：集成 Token Manager

修改 `chat_handler.py`，添加 token 检查：

```python
from core.cognition.token_manager import (
    estimate_messages_tokens,
    smart_compress_history,
    check_context_overflow,
)

# 在构建消息后
overflow_info = check_context_overflow(messages, model_name)
if overflow_info["overflow"]:
    messages, stats = smart_compress_history(messages, model_name)
```

### 第二步：更新 WebUI

添加上下文状态显示（需要修改前端代码）。

### 第三步：测试

```bash
# 运行测试
python test_context_management.py
```

---

## 📈 预期效果

1. **消除上下文截断**：通过 token 管理，确保消息不会超过模型限制
2. **提高响应质量**：模型能够正确关注最近的上下文
3. **减少 API 错误**：避免因上下文过长导致的 API 错误
4. **更好的用户体验**：用户可以看到上下文使用情况

---

## 🔍 调试

### 查看 Token 统计

```python
from core.cognition.token_manager import estimate_messages_tokens

messages = [...]
tokens = estimate_messages_tokens(messages)
print(f"Total tokens: {tokens}")
```

### 查看模型配置

```python
from core.cognition.token_manager import get_model_context_window

print(f"Kimi: {get_model_context_window('kimi')} tokens")
print(f"Qianfan: {get_model_context_window('qianfan')} tokens")
```

### 查看压缩效果

```python
from core.cognition.token_manager import smart_compress_history

compressed, stats = smart_compress_history(messages, "kimi")
print(f"压缩率: {stats['compression_ratio']:.1%}")
```

---

## 📚 相关文件

- `src/core/cognition/token_manager.py` - Token 管理器
- `src/core/cognition/context_config.py` - 配置文件
- `src/omnia/chat_handler_token_optimized.py` - 优化后的聊天处理器
- `src/core/cognition/context_compressor.py` - 上下文压缩器

---

## ❓ 常见问题

### Q: 为什么 Kimi 128k 上下文还会截断？

A: 即使支持 128k，当消息过长时，模型的注意力机制可能无法有效关注所有内容。建议保持上下文在 60% 以下。

### Q: 如何知道当前上下文使用了多少 tokens？

A: 使用 `check_context_overflow()` 函数，或在 WebUI 中添加状态显示。

### Q: 压缩会丢失重要信息吗？

A: 压缩策略会保留最近的消息和系统消息，只压缩中间的历史。关键信息应该存储到 Memory Palace。

---

## 📞 支持

如有问题，请查看日志或联系开发者。
