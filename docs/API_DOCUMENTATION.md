# Omnia API 文档

## 📚 目录

- [概述](#概述)
- [认证](#认证)
- [基础 API](#基础-api)
- [聊天 API](#聊天-api)
- [记忆 API](#记忆-api)
- [向量搜索 API](#向量搜索-api)
- [计划生成 API](#计划生成-api)
- [技能系统 API](#技能系统-api)
- [调度器 API](#调度器-api)
- [学习能力 API](#学习能力-api)
- [能力系统 API](#能力系统-api)
- [反思系统 API](#反思系统-api)
- [推理引擎 API](#推理引擎-api)
- [讨论系统 API](#讨论系统-api)
- [长任务 API](#长任务-api)
- [全文搜索 API](#全文搜索-api)
- [Gateway API](#gateway-api)
- [性能监控 API](#性能监控-api)
- [错误处理](#错误处理)

---

## 概述

**基础 URL**: `http://localhost:8765`

**API 文档**: 
- Swagger UI: `http://localhost:8765/docs`
- ReDoc: `http://localhost:8765/redoc`

**版本**: 2.0.0

---

## 认证

当前版本暂无认证要求，所有 API 都是公开的。

未来版本将支持：
- API Key 认证
- OAuth2.0
- JWT Token

---

## 基础 API

### 获取系统状态

```http
GET /api/status
```

**响应示例**:
```json
{
  "status": "running",
  "version": "2.0.0",
  "uptime": 3600,
  "provider": "deepseek",
  "tools_count": 34,
  "memory_count": 1234
}
```

### 健康检查

```http
GET /health
```

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2026-05-12T00:00:00Z"
}
```

### 列出工具

```http
GET /api/tools
```

**响应示例**:
```json
{
  "total": 34,
  "tools": ["read_file", "write_file", "execute_shell", ...],
  "schemas": {...}
}
```

---

## 聊天 API

### 发送消息（非流式）

```http
POST /api/chat
Content-Type: application/json

{
  "message": "你好",
  "session_id": "optional-session-id"
}
```

**响应示例**:
```json
{
  "response": "你好！有什么我可以帮助你的吗？",
  "session_id": "abc123",
  "tool_calls": []
}
```

### 发送消息（流式）

```http
POST /api/chat/stream
Content-Type: application/json

{
  "message": "你好"
}
```

**响应**: Server-Sent Events (SSE)

```
data: {"type": "text", "content": "你"}
data: {"type": "text", "content": "好"}
data: {"type": "done"}
```

---

## 记忆 API

### 搜索记忆

```http
GET /api/memory/search?q=测试&layer=facts&limit=10
```

**参数**:
- `q`: 搜索关键词
- `layer`: 记忆层（facts, relations, habits, timeline）
- `limit`: 返回数量

**响应示例**:
```json
{
  "results": [
    {
      "id": 1,
      "content": "测试记忆",
      "layer": "facts",
      "created_at": "2026-05-12T00:00:00Z"
    }
  ],
  "total": 1
}
```

### 保存记忆

```http
POST /api/memory
Content-Type: application/json

{
  "content": "用户喜欢使用 Python",
  "layer": "facts"
}
```

### 获取记忆统计

```http
GET /api/memory/stats
```

---

## 向量搜索 API

### 语义搜索

```http
POST /api/vector/search
Content-Type: application/json

{
  "query": "如何学习编程",
  "top_k": 5,
  "filter": {
    "layer": "facts"
  }
}
```

**响应示例**:
```json
{
  "results": [
    {
      "id": "mem_123",
      "content": "学习编程的建议",
      "score": 0.95,
      "metadata": {...}
    }
  ],
  "query_time": 0.05
}
```

### 添加向量

```http
POST /api/vector/add
Content-Type: application/json

{
  "id": "mem_123",
  "content": "这是一条记忆",
  "metadata": {
    "layer": "facts",
    "created_at": "2026-05-12T00:00:00Z"
  }
}
```

### 获取向量统计

```http
GET /api/vector/stats
```

---

## 计划生成 API

### 分析任务

```http
POST /api/plan/analyze
Content-Type: application/json

{
  "task": "读取文件并发送邮件",
  "context": {}
}
```

**响应示例**:
```json
{
  "complexity": "medium",
  "estimated_steps": 3,
  "required_tools": ["read_file", "send_email"],
  "analysis": "任务需要读取文件内容，然后发送邮件"
}
```

### 生成计划

```http
POST /api/plan/generate
Content-Type: application/json

{
  "task": "读取文件并发送邮件",
  "max_steps": 10
}
```

**响应示例**:
```json
{
  "plan_id": "plan_123",
  "steps": [
    {
      "step_id": 1,
      "action": "read_file",
      "params": {"path": "/path/to/file"},
      "description": "读取文件内容"
    },
    {
      "step_id": 2,
      "action": "send_email",
      "params": {"to": "user@example.com", "content": "..."},
      "description": "发送邮件"
    }
  ],
  "estimated_time": 5
}
```

### 执行计划

```http
POST /api/plan/execute/{plan_id}
```

### 优化计划

```http
POST /api/plan/optimize/{plan_id}
```

---

## 技能系统 API

### 获取 SkillForge 状态

```http
GET /api/skills/status
```

### 检测对话模式

```http
POST /api/skills/detect
Content-Type: application/json

{
  "conversation": [
    {"role": "user", "content": "帮我读取文件"},
    {"role": "assistant", "content": "好的，请提供文件路径"}
  ]
}
```

### 生成技能

```http
POST /api/skills/generate
Content-Type: application/json

{
  "pattern_id": "pattern_123",
  "name": "文件读取助手"
}
```

### 运行进化周期

```http
POST /api/skills/evolve
```

---

## 调度器 API

### 获取调度器状态

```http
GET /api/scheduler/status
```

### 创建定时任务

```http
POST /api/scheduler/tasks
Content-Type: application/json

{
  "name": "每日备份",
  "cron": "0 2 * * *",
  "action": "backup",
  "params": {}
}
```

### 列出所有任务

```http
GET /api/scheduler/tasks
```

### 立即运行任务

```http
POST /api/scheduler/tasks/{task_id}/run
```

### 验证 Cron 表达式

```http
GET /api/scheduler/validate-cron?expression=0%202%20*%20*%20*
```

---

## 学习能力 API

### 获取学习器状态

```http
GET /api/learner/status
```

### 分析对话历史

```http
POST /api/learner/analyze
Content-Type: application/json

{
  "conversation_id": "conv_123",
  "messages": [...]
}
```

### 从模式创建技能

```http
POST /api/learner/create-skill
Content-Type: application/json

{
  "pattern_id": "pattern_123",
  "skill_name": "文件操作助手"
}
```

### 导出技能

```http
POST /api/learner/export
Content-Type: application/json

{
  "skill_ids": ["skill_1", "skill_2"]
}
```

---

## 能力系统 API

### 获取系统状态

```http
GET /api/capability/status
```

### 获取用户进度

```http
GET /api/capability/progress/{user_id}
```

**响应示例**:
```json
{
  "user_id": "user_123",
  "level": 5,
  "level_name": "ADVANCED",
  "experience": 5000,
  "unlocked_count": 15,
  "total_count": 50,
  "achievements": [...]
}
```

### 记录使用

```http
POST /api/capability/usage/record
Content-Type: application/json

{
  "user_id": "user_123",
  "capability_id": "cap_1",
  "usage_count": 1
}
```

### 解锁能力

```http
POST /api/capability/unlock
Content-Type: application/json

{
  "user_id": "user_123",
  "capability_id": "cap_1"
}
```

### 获取能力推荐

```http
GET /api/capability/{user_id}/recommendations?limit=5
```

---

## 反思系统 API

### 获取系统状态

```http
GET /api/reflection/status
```

### 开始追踪会话

```http
POST /api/reflection/session/{session_id}/start
```

### 记录消息

```http
POST /api/reflection/session/{session_id}/message
Content-Type: application/json

{
  "role": "user",
  "content": "你好"
}
```

### 分析对话质量

```http
POST /api/reflection/analyze/quality/{session_id}
```

**响应示例**:
```json
{
  "session_id": "sess_123",
  "quality_score": 0.85,
  "metrics": {
    "response_relevance": 0.9,
    "response_completeness": 0.8,
    "response_clarity": 0.85
  },
  "improvements": [...]
}
```

### 识别知识缺口

```http
POST /api/reflection/analyze/knowledge-gaps
Content-Type: application/json

{
  "session_id": "sess_123"
}
```

### 获取改进建议

```http
GET /api/reflection/recommendations
```

---

## 推理引擎 API

### 获取推理引擎状态

```http
GET /api/reasoning/status
```

### 执行推理

```http
POST /api/reasoning/infer
Content-Type: application/json

{
  "premises": [
    "所有人类都是会死的",
    "苏格拉底是人类"
  ],
  "query": "苏格拉底会死吗？",
  "mode": "deductive"
}
```

**响应示例**:
```json
{
  "conclusion": "苏格拉底会死",
  "confidence": 0.95,
  "reasoning_chain": [...],
  "mode": "deductive"
}
```

### 分析论证

```http
POST /api/reasoning/analyze
Content-Type: application/json

{
  "argument": "因为 A，所以 B"
}
```

---

## 讨论系统 API

### 开始讨论

```http
POST /api/discuss/start
Content-Type: application/json

{
  "question": "如何优化数据库查询？",
  "agents": ["expert_db", "expert_performance"],
  "max_rounds": 3
}
```

**响应示例**:
```json
{
  "discussion_id": "disc_123",
  "question": "如何优化数据库查询？",
  "status": "in_progress",
  "rounds": []
}
```

### 提交一轮意见

```http
POST /api/discuss/round
Content-Type: application/json

{
  "discussion_id": "disc_123",
  "agent_id": "expert_db",
  "opinion": "建议创建索引..."
}
```

### 做出决策

```http
POST /api/discuss/decision
Content-Type: application/json

{
  "discussion_id": "disc_123",
  "decision": "采用索引优化方案"
}
```

---

## 长任务 API

### 分析任务复杂度

```http
POST /api/task/analyze?goal=读取文件并发送邮件
```

**响应示例**:
```json
{
  "complexity": "medium",
  "estimated_time": 300,
  "recommended_strategy": "long_task",
  "subtasks": [...]
}
```

### 创建长任务

```http
POST /api/task
Content-Type: application/json

{
  "goal": "读取文件并发送邮件",
  "steps": [...]
}
```

### 获取任务状态

```http
GET /api/task/{task_id}
```

**响应示例**:
```json
{
  "task_id": "task_123",
  "status": "running",
  "progress": 50,
  "current_step": 2,
  "total_steps": 4,
  "result": null
}
```

### 控制任务

```http
POST /api/task/{task_id}/pause
POST /api/task/{task_id}/resume
POST /api/task/{task_id}/cancel
```

---

## 全文搜索 API

### 搜索消息

```http
GET /api/fts/search?q=测试&session_id=sess_123&limit=10
```

**响应示例**:
```json
{
  "results": [
    {
      "id": 1,
      "content": "这是一条测试消息",
      "session_id": "sess_123",
      "timestamp": "2026-05-12T00:00:00Z",
      "rank": 0.95
    }
  ],
  "total": 1,
  "query_time": 0.01
}
```

### 索引消息

```http
POST /api/fts/index
Content-Type: application/json

{
  "session_id": "sess_123",
  "message_id": "msg_456",
  "content": "这是一条消息",
  "metadata": {...}
}
```

### 获取统计

```http
GET /api/fts/stats
```

---

## Gateway API

### 获取 Gateway 状态

```http
GET /api/gateway/status
```

**响应示例**:
```json
{
  "status": "running",
  "adapters": {
    "webhook": {"status": "active", "connections": 5},
    "email": {"status": "active", "connections": 2},
    "websocket": {"status": "active", "connections": 10}
  },
  "total_messages": 1234
}
```

### 发送消息

```http
POST /api/gateway/send
Content-Type: application/json

{
  "adapter": "email",
  "to": "user@example.com",
  "message": "你好"
}
```

### 列出适配器

```http
GET /api/gateway/adapters
```

---

## 性能监控 API

### 获取性能状态

```http
GET /api/performance/status
```

**响应示例**:
```json
{
  "system": {
    "memory_mb": 120.5,
    "cpu_percent": 5.2,
    "threads": 15
  },
  "concurrency": {
    "active_count": 5,
    "max_concurrent": 100
  },
  "performance": {
    "operations_count": 25,
    "slow_operations_count": 3
  }
}
```

### 获取完整报告

```http
GET /api/performance/report
```

### 获取操作统计

```http
GET /api/performance/operations/{operation}
```

**响应示例**:
```json
{
  "operation": "chat",
  "count": 1000,
  "min": 0.05,
  "max": 2.5,
  "avg": 0.15,
  "p50": 0.12,
  "p95": 0.45,
  "p99": 1.2
}
```

### 获取慢操作

```http
GET /api/performance/slow-operations?limit=20
```

### 触发内存优化

```http
POST /api/performance/optimize
```

### 清空缓存

```http
POST /api/performance/cache/clear
```

---

## 错误处理

所有 API 错误遵循统一格式：

```json
{
  "detail": "错误描述",
  "error_code": "ERROR_CODE",
  "timestamp": "2026-05-12T00:00:00Z"
}
```

### 常见错误码

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |

---

## 速率限制

当前无速率限制。

未来版本将实施：
- 每分钟最多 100 次请求
- 每小时最多 1000 次请求

---

## WebSocket 支持

### 连接

```javascript
const ws = new WebSocket('ws://localhost:8765/ws');
```

### 消息格式

```json
{
  "type": "message",
  "data": {...}
}
```

---

## 最佳实践

1. **使用流式 API** 处理长响应
2. **缓存常用数据** 减少请求
3. **批量操作** 提高效率
4. **监控性能** 及时发现问题
5. **处理错误** 提供友好提示

---

*最后更新: 2026-05-12*
