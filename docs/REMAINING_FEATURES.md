# Omnia 剩余功能完善清单

## 📊 总体完成度

| 模块 | 实现状态 | FastAPI 集成 | 优先级 |
|------|---------|-------------|--------|
| **核心模块** | 95% | 85% | - |
| **路由层** | 100% | 100% | - |
| **功能完善** | 70% | - | 🔴 高 |

---

## 🔴 高优先级 - 功能实现（14 个 TODO）

### 1. Scheduler 调度器集成
**文件**: `src/omnia/routers/scheduler.py`
**TODO 数量**: 4

```python
# TODO: 实际添加到调度器
# TODO: 实际执行任务
# TODO: 实际启动调度器
# TODO: 实际停止调度器
```

**需要做**：
- 将 `src/core/orchestration/scheduler.py` 集成到路由
- 实现真正的定时任务调度
- 支持 Cron 表达式

---

### 2. 飞书消息发送
**文件**: `src/omnia/routers/feishu.py`
**TODO 数量**: 1

```python
# TODO: 实现飞书消息发送 API
```

**需要做**：
- 实现飞书 Webhook 消息发送
- 支持富文本消息

---

### 3. AutoLearner 对话历史获取
**文件**: `src/omnia/routers/learner.py`
**TODO 数量**: 2

```python
# TODO: 从记忆系统或数据库获取对话历史
# TODO: 注册到 SkillForge
```

**需要做**：
- 集成 Memory Palace 获取历史对话
- 实现技能自动注册

---

### 4. LongTask 后台执行
**文件**: `src/omnia/routers/long_task.py`
**TODO 数量**: 1

```python
# TODO: 在后台执行任务
```

**需要做**：
- 使用 FastAPI BackgroundTasks
- 实现任务队列

---

### 5. Computer Controller VL API
**文件**: `src/omnia/computer_controller.py`
**TODO 数量**: 3

```python
# TODO: 实现千帆 VL API 调用
# TODO: 解析返回的坐标
# TODO: 使用 LLM 进行任务规划
```

**需要做**：
- 集成视觉语言模型
- 实现屏幕理解
- 自动化操作规划

---

### 6. Web Server Agent 转发
**文件**: `src/omnia/web_server.py`
**TODO 数量**: 2

```python
# TODO: 转发给 Agent 处理
# TODO: 实现诊断逻辑
```

**需要做**：
- 实现 Agent 路由转发
- 系统诊断功能

---

### 7. Tool Registry MCP 执行
**文件**: `src/omnia/services/tool_registry.py`
**TODO 数量**: 1

```python
# TODO: MCP 执行
```

**需要做**：
- 集成 MCP 客户端
- 实现工具动态调用

---

## 🟡 中优先级 - 核心模块集成

### 1. 认知层模块暴露
**已实现**: `src/core/cognition/`
- `intent_engine.py` ✅
- `compressor.py` ✅
- `prompt_builder.py` ✅
- `token_manager.py` ✅
- `ultraplan.py` ✅

**需要做**：
- 添加路由暴露这些功能
- `/api/cognition/intent` - 意图识别
- `/api/cognition/compress` - 上下文压缩
- `/api/cognition/plan` - 任务规划

---

### 2. 工作流引擎集成
**已实现**: `src/core/orchestration/workflow_engine.py` ✅

**需要做**：
- 完善路由集成
- 支持工作流模板
- 工作流可视化

---

### 3. AgentSwarm 完整集成
**已实现**: `src/core/actuator/agent_swarm.py` ✅
**路由**: `src/omnia/routers/swarm.py` ✅

**需要做**：
- 实现真正的多 Agent 并行执行
- Agent 间通信
- 结果聚合

---

## 🟢 低优先级 - 增强功能

### 1. 向量数据库集成
**已实现**: `src/core/neural_graph/vector_store.py` ✅

**需要做**：
- Chroma 向量存储集成
- 语义搜索 API
- 向量索引优化

---

### 2. Neo4j 图数据库
**状态**: 未实现

**需要做**：
- 知识图谱存储
- 关系推理
- 图查询 API

---

### 3. Feature Flags 系统
**状态**: 部分实现

**需要做**：
- 动态功能开关
- A/B 测试支持
- 配置热更新

---

## 📋 实施计划

### Phase 5: 核心功能完善（预计 2-3 天）
1. ✅ 修复 Scheduler 集成
2. ✅ 实现飞书消息发送
3. ✅ 完善 AutoLearner
4. ✅ 实现后台任务执行
5. ✅ 集成 VL API

### Phase 6: 认知层暴露（预计 1-2 天）
1. 添加认知层路由
2. 实现意图识别 API
3. 实现上下文压缩 API
4. 实现任务规划 API

### Phase 7: 高级功能（预计 2-3 天）
1. 向量数据库集成
2. 工作流模板系统
3. Agent 间通信
4. 知识图谱推理

---

## 🎯 下一步行动

**立即执行**：
1. 修复 Scheduler 的 4 个 TODO
2. 实现飞书消息发送
3. 完善 AutoLearner 对话历史获取

**需要确认**：
- 是否需要实现 Neo4j 图数据库？
- 是否需要 Chroma 向量存储？
- Feature Flags 优先级？

---

## 📈 完成后预期

| 指标 | 当前 | 目标 |
|------|------|------|
| TODO 清零 | 14 个 | 0 个 |
| 核心模块集成 | 85% | 95% |
| 功能完善度 | 70% | 95% |
| **总体完成度** | **95%** | **98%** |
