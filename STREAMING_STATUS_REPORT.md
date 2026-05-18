# 流式内容输出状态报告

## 🔍 问题诊断

### 当前架构
```
前端 (app.js) 
    ↓ HTTP POST /api/chat/stream
FastAPI 服务器 (main.py, 端口 8765)
    ↓ 调用
chat.py 路由器 (/api/chat/stream)
    ↓ 调用
agent_engine.process_stream_with_tools()
    ↓ 返回 SSE 事件流
前端处理事件
```

### 发现的问题

#### ✅ 正常工作的部分
1. **前端代码**：正确调用 `/api/chat/stream` 端点
2. **SSE 处理**：正确解析 `data: {...}` 格式
3. **状态事件处理**：前端有 `status` 事件的处理逻辑
4. **显示函数**：`showTyping()` 和 `updateTypingStatus()` 函数存在

#### ❌ 问题所在
1. **agent_engine 没有发送 status 事件**
   - 只发送 `token`、`tool_call`、`tool_result`、`done` 等事件
   - 缺少 `status` 事件来显示"正在分析问题"、"正在执行工具"等状态

2. **前端无法显示执行过程**
   - 因为没有收到 `status` 事件，所以看不到中间状态
   - 只能看到最终结果

### 代码分析

#### 前端期望的事件类型
```javascript
if (data.type === 'status') {
    // 显示状态：正在思考、正在分析等
    updateTypingStatus(data.message);
}

if (data.type === 'token') {
    // 流式 token
}

if (data.type === 'tool_call') {
    // 工具调用
}
```

#### agent_engine 实际发送的事件
```python
yield {"type": "preroll", "content": preroll_result}
yield {"type": "token", "content": token}
yield {"type": "tool_call", "name": tool_name, "arguments": args}
yield {"type": "tool_result", "name": tool_name, "content": result}
yield {"type": "done", "full_content": content, "stats": {...}}
# ❌ 缺少 status 事件
```

## 🛠️ 解决方案

### 方案 A：修改 agent_engine（推荐）
在 `agent_engine.py` 的 `process_stream_with_tools` 方法中添加 status 事件：

```python
# 在工具调用前添加
yield {
    "type": "status",
    "message": f"正在执行工具: {tool_name}..."
}

# 在 LLM 调用前添加
yield {
    "type": "status",
    "message": "正在思考..."
}

# 在工具调用循环开始时添加
yield {
    "type": "status",
    "message": f"第 {rounds} 轮思考中..."
}
```

### 方案 B：修改前端（不推荐）
修改前端以处理现有的事件类型，但这会降低用户体验。

### 方案 C：使用 Gateway 模式
启用 Gateway 模式，它可能有更好的流式支持：
```bash
# 在 .env 文件中设置
OMNIA_USE_GATEWAY=true
```

## 📊 测试验证

### 测试命令
```bash
# 测试流式端点
curl -X POST http://localhost:8765/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "history": []}' \
  --no-buffer

# 检查事件类型
curl -X POST http://localhost:8765/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "查看当前目录", "history": []}' \
  --no-buffer | grep "data:" | head -10
```

### 预期结果
修改后应该看到：
```
data: {"type": "status", "message": "正在分析问题..."}
data: {"type": "status", "message": "正在思考..."}
data: {"type": "token", "content": "我"}
data: {"type": "token", "content": "来"}
data: {"type": "status", "message": "正在执行工具: execute_shell..."}
data: {"type": "tool_call", "name": "execute_shell", "arguments": {...}}
data: {"type": "tool_result", "name": "execute_shell", "content": "..."}
data: {"type": "done", "full_content": "..."}
```

## 🎯 实施建议

1. **立即修复**：修改 agent_engine.py 添加 status 事件
2. **测试验证**：使用 curl 命令测试流式输出
3. **前端验证**：在浏览器中测试聊天功能
4. **文档更新**：更新 API 文档说明支持的事件类型

## 📝 总结

**根本原因**：agent_engine 没有发送 status 事件，导致前端无法显示执行过程状态。

**解决方案**：在 agent_engine.py 中添加 status 事件的 yield 语句。

**影响范围**：所有使用流式聊天的功能。

**修复难度**：低（只需在关键位置添加几行代码）

**测试难度**：低（使用 curl 命令即可验证）

---

**报告生成时间**：2026年5月14日  
**分析工具**：代码审查 + 网络诊断  
**结论**：流式内容输出功能需要添加 status 事件才能正常显示执行过程