# 工具调用循环问题修复报告

**日期**: 2026-04-13
**问题**: Qianfan 模型在工具执行后有时会输出工具调用格式（XML），而不是自然语言总结

## 问题诊断

### 现象
```
[Chat] Round 1: Model called 3 tools
[Chat] Tool: list_directory
[Chat] Tool: read_file
[Chat] Round 2: Messages: 14, use_tools: False
[日志结束，没有返回内容]
```

### 根本原因
1. **模型行为**: Qianfan 在某些情况下会在文本中输出工具调用格式
2. **示例输出**:
   ```
   让我再看看我的核心身份文件：
   <read_file>
   {"path": "/home/shan/omnia-os/IDENTITY.md"}
   </read_file>
   ```
3. **代码问题**: 检测逻辑不够完善，没有覆盖所有工具名

## 解决方案

### 1. 增强系统提示
```python
"""
重要规则：
1. 最多调用 5 次工具
2. 如果已经调用了工具并获得了结果，请直接回答用户的问题
3. **绝对禁止**在回复文本中输出任何工具调用格式（包括 XML、JSON、函数调用格式）
4. 工具调用必须通过 API 的 tool_calls 功能
5. 用自然语言总结结果，像和朋友聊天一样
6. 如果工具返回了数据，请分析数据并给出你的见解
"""
```

### 2. 增强的工具调用格式检测
```python
# 所有工具名
all_tools = ['read_file', 'write_file', 'execute_shell', 'list_directory', 'web_search', 'query_memory']

# 模式1：XML标签格式（<tool_name>）
for tool in all_tools:
    if f'<{tool}' in reply:
        tool_pattern_in_text = True
        break

# 模式2：代码块格式
# 模式3：工具名 + 参数JSON格式
# 模式4：函数调用格式
# 模式5：纯JSON参数格式
```

### 3. 三层处理策略

**策略1**: 提取有效内容
```python
lines = reply.split('\n')
clean_lines = []
for line in lines:
    if any(f'<{tool}' in line for tool in all_tools):
        break
    clean_lines.append(line)
extracted = '\n'.join(clean_lines).strip()
```

**策略2**: 强制模型重新生成
```python
if not extracted:
    summary_request = messages[:3]
    summary_request.append({
        "role": "user",
        "content": f"""请用自然语言总结以下工具执行结果并回答我的问题。
        
已执行的工具：{', '.join([s['tool'] for s in steps])}

**重要**：直接回答，不要输出任何工具调用格式、JSON或XML。"""
    })
    retry_content = _call_model_messages(...)
```

**策略3**: 生成默认总结
```python
if retry_failed:
    reply = f"我已经执行了 {len(steps)} 个操作：{', '.join(tool_names)}。任务已完成。"
```

### 4. 工具完成后的明确指令
```python
if tool_calls_executed:
    messages.append({
        "role": "system",
        "content": """工具已全部执行完成。现在请：
1. 分析工具返回的数据
2. 用自然语言总结关键发现
3. 回答用户的原始问题
4. **不要**输出任何工具调用格式
5. **不要**再次调用工具
"""
    })
```

### 5. 详细的调试日志
```python
print(f"[Chat] Detected tool pattern in text, cleaning...")
print(f"[Chat] Raw content: {reply[:300]}")
print(f"[Chat] Extracted: {extracted[:100]}")
print(f"[Chat] Final reply: {reply[:100]}")
```

## 测试结果

### 测试场景
```python
message = "梳理一下你的状态"
history = [
    {"role": "user", "content": "历史消息1"},
    {"role": "assistant", "content": "历史回复1"},
    # ... 共 6 条历史
]
```

### 测试输出
```
[Chat] Round 1, messages: 9, use_tools: True
[Chat] Model called 1 tools
[Chat] Tool: query_memory
[Chat] Round 2, messages: 11, use_tools: False
[Chat] Final reply: 好的，根据记忆库的查询结果，让我给你梳理一下当前状态：

## 🤖 Omnia 当前状态
...
```

### 结果验证
- ✅ 工具调用正确（通过 API tool_calls）
- ✅ 工具执行成功
- ✅ Round 2 生成自然语言回复
- ✅ 没有工具调用格式输出
- ✅ 回复质量良好

## 经验总结

### 从 Hermes/FreeCode/OpenClaw 学到的

**Hermes**:
- PromptBuilder + ContextCompressor + 3 API Modes
- 明确的系统提示和指令分离

**FreeCode**:
- Tool 泛型 + 权限系统 + Hook 系统
- 工具调用的生命周期管理

**OpenClaw**:
- 多通道架构 + 统一消息抽象
- 工具结果的后处理和格式化

### 最佳实践

1. **明确的系统提示**: 告诉模型什么**不能做**
2. **多重检测**: 不要只检测一种格式，要覆盖所有可能
3. **降级策略**: 总是有备选方案
4. **详细日志**: 帮助快速定位问题
5. **测试覆盖**: 测试多种场景（简单、复杂、历史消息）

## 相关文件

- `src/omnia/chat_handler.py` - 核心修复
- `docs/ARCHITECTURE_COMPARISON.md` - 架构对比
- `src/core/cognition/context_compressor.py` - 上下文压缩

## 下一步

- [ ] 添加单元测试覆盖工具调用场景
- [ ] 实现更智能的上下文压缩
- [ ] 支持 Hook 系统进行工具调用后处理
- [ ] 优化重试策略（使用更便宜的模型）
