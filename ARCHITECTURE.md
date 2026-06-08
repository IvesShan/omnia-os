
# Omnia OS 架构全景图

## 概述

Omnia OS 是一个**自主 AI 操作系统**，由 31 个核心模块组成，
分布在 3 个架构层中：核心层（core）、应用层（omnia）、外部层。

---

## 三层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      🖥️ 外部层 (External)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ VS Code 扩展  │  │   Web UI     │  │   MCP 服务器集群       │   │
│  │ IDE 上下文    │  │  前端界面     │  │   外部工具集成         │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘   │
│         │                 │                     │               │
├─────────┼─────────────────┼─────────────────────┼───────────────┤
│         ▼                 ▼                     ▼               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              🧠 应用层 (Omnia Services)                    │   │
│  │                                                          │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐    │   │
│  │  │  对话引擎     │  │  Agent 引擎   │  │  工具注册表   │    │   │
│  │  │ chat/stream  │  │ agent_engine │  │ tool_registry│    │   │
│  │  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘    │   │
│  │         │                │                  │            │   │
│  │  ┌──────┴──────┐  ┌─────┴──────┐  ┌───────┴────────┐   │   │
│  │  │  Wake Cycle  │  │ 工具触发器  │  │  会话管理器    │   │   │
│  │  │  系统提示词   │  │ tool_trigger│  │ session_mgr  │   │   │
│  │  └─────────────┘  └────────────┘  └────────────────┘   │   │
│  │                                                          │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐    │   │
│  │  │  长任务处理   │  │  智能暂停器   │  │  自动记忆     │    │   │
│  │  │ long_task    │  │ smart_pauser │  │ auto_memory  │    │   │
│  │  └─────────────┘  └──────────────┘  └──────────────┘    │   │
│  │                                                          │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐    │   │
│  │  │  中断管理器   │  │  上下文管理   │  │  API 路由层   │    │   │
│  │  │ interrupt_mgr│  │ context_mgr  │  │  routers/    │    │   │
│  │  └─────────────┘  └──────────────┘  └──────────────┘    │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │                                                       │
├─────────┼───────────────────────────────────────────────────────┤
│         ▼                                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              ⚙️ 核心层 (Core)                              │   │
│  │                                                          │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │                   🧠 认知引擎                        │ │   │
│  │  │  IntentEngine │ ContextCompressor │ TopicRecognizer │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  │                                                          │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │                   💾 记忆系统                        │ │   │
│  │  │  MemoryPalace │ NeuralGraph │ VectorStore           │ │   │
│  │  │  (SQLite)      │ (知识图谱)  │ (向量检索)            │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  │                                                          │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │                   🔧 执行器层                        │ │   │
│  │  │  PlanExecutor │ AgentSwarm │ ToolRegistry           │ │   │
│  │  │  (任务规划)    │ (并行执行)  │ (工具调度)            │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  │                                                          │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │                   🎯 编排层                          │ │   │
│  │  │  WorkflowEngine │ Scheduler │ LongTaskHandler       │ │   │
│  │  │  (DAG 工作流)   │ (定时任务) │ (长任务分解)          │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  │                                                          │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │                   🛡️ 基础设施                        │ │   │
│  │  │  FeatureFlags │ Bootstrap │ Hooks │ SafetyGate      │ │   │
│  │  │  (模块开关)    │ (启动引导) │ (钩子) │ (安全门)      │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  │                                                          │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │                   🤝 协作层                          │ │   │
│  │  │  CollaborationManager │ PersonaDaemon │ Heartbeat   │ │   │
│  │  │  (Omnia ↔ 无限)       │ (常驻守护)    │ (健康检查)  │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 核心执行流程

### 1. 标准对话流程 (SSE 流式)

```
用户消息
  │
  ▼
stream_chat.py (SSE 入口)
  │
  ▼
Wake Cycle (wake.py)
  ├─ 系统提示词组装
  ├─ 身份注入 (persona_identity)
  ├─ 工具感知 (tool_schemas)
  ├─ 学术引擎 (academic_engine)
  ├─ 雇主协议 (employer_agreement)
  └─ 安全门提示 (safety_gate)
  │
  ▼
AgentEngine.process_stream_with_tools()
  │
  ├─ ① AutoMemory.log_user_message()
  │     └─ 写入 conversation_logs 表
  │
  ├─ ② ToolTrigger.analyze_message()
  │     └─ 关键词匹配 → 工具提示注入
  │
  ├─ ③ LLM 调用 (DeepSeek/Kimi/Qwen...)
  │     ├─ 流式返回 tokens
  │     └─ 检测 tool_calls
  │
  ├─ ④ 工具调用循环 (最多 5000 轮)
  │     ├─ SafetyGate.check() → 拦截危险操作
  │     ├─ ToolRegistry.execute() → 执行工具
  │     ├─ 结果注入 messages
  │     ├─ 截断优化 (保留完整 tool 对)
  │     └─ 循环直到模型不再调用工具
  │
  ├─ ⑤ AutoMemory.log_assistant_reply()
  │     └─ 写入 conversation_logs 表
  │
  └─ ⑥ 流式输出 → 前端
```

### 2. 长任务流程 (自动分解)

```
用户消息 (复杂任务)
  │
  ▼
LongTaskHandler.analyze_task_complexity()
  │
  ├─ 估计步骤数 > 5 或复杂关键词 → 进入长任务模式
  │
  ▼
LongTaskHandler.generate_plan_with_llm()
  │
  ├─ LLM 生成执行计划 (JSON)
  │     └─ 每步: description + tool_name + tool_args + dependencies
  │
  ▼
LongTaskHandler.execute_plan_stream()
  │
  ├─ 逐步执行 (PlanStore 持久化)
  │     ├─ dispatch_tool() → 执行工具
  │     ├─ 更新进度条 → 前端
  │     ├─ 失败时 → 错误恢复选项
  │     └─ 断点续传支持
  │
  └─ 完成 → 生成总结
```

### 3. AgentSwarm 并行执行流程

```
用户消息 (跨领域任务)
  │
  ▼
AgentSwarm.decompose()
  │
  ├─ LLM 分解为 1-3 个子任务
  │     ├─ frontend: HTML/CSS/JS
  │     ├─ backend: Python/API
  │     ├─ devops: 部署/配置
  │     ├─ research: 搜索/分析
  │     └─ general: 通用
  │
  ▼
SwarmOrchestrator.run()
  │
  ├─ ThreadPoolExecutor (max_workers=3)
  │     ├─ SubAgent 1: frontend → PlanExecutor
  │     ├─ SubAgent 2: backend → PlanExecutor
  │     └─ SubAgent 3: devops → PlanExecutor
  │
  ├─ 并行执行，结果收集
  │
  ▼
SwarmOrchestrator.synthesize()
  │
  ├─ LLM 聚合所有结果
  ├─ 写入 MemoryPalace (自动)
  └─ 返回综合报告
```

### 4. 工具调用验证流程

```
模型输出
  │
  ├─ 有 tool_calls → 直接执行
  │
  └─ 无 tool_calls → ToolCallValidator
        │
        ├─ 文本中表达"我要调用 xxx"?
        │     └─ 是 → text_fallback → 执行工具
        │
        ├─ 声称已调用但没有?
        │     └─ 是 → 构建 retry_hint → 重试 (最多 2 次)
        │
        └─ 正常回答 → 直接返回
```

---

## 模块依赖关系图

```
                    ┌─────────────┐
                    │  config.py  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ feature/ │ │ memory_  │ │ neural_  │
        │ flags.py │ │ palace/  │ │ graph/   │
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │            │            │
             ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │bootstrap │ │ cognition│ │ skill_   │
        │   .py    │ │  /intent │ │ forge/   │
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │            │            │
             ▼            ▼            ▼
        ┌──────────────────────────────────────┐
        │          actuator/                    │
        │  tool_registry → tool_executor       │
        │  plan_executor → agent_swarm         │
        │  safety_gate                         │
        └──────────────────┬───────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ plugin/  │ │collabora-│ │neuro_    │
        │ hooks    │ │tion/     │ │center/   │
        └──────────┘ └──────────┘ └──────────┘
```

---

## 关键设计模式

### 1. 单例模式
- `AgentEngine._instance`
- `HookRegistry._instance`
- `MemoryPalace` (通过 `get_memory_palace()`)

### 2. 观察者模式
- `HookRegistry`: 7 种钩子类型，支持优先级排序
- `PersonaDaemon`: 文件系统监控 + 心跳检查

### 3. 策略模式
- `IntentEngine`: 规则匹配 → LLM 识别 (两阶段)
- `PlanExecutor`: 文本解析 → tool_calls API (双路径)

### 4. 工厂模式
- `Wake Cycle`: 动态组装系统提示词
- `AgentSwarm`: 按角色创建 SubAgent

### 5. 管道模式
- 消息处理: AutoMemory → ToolTrigger → AgentEngine → Hooks
- 工具执行: SafetyGate → ToolRegistry → ToolExecutor

---

## 数据流

```
┌─────────┐    ┌──────────────┐    ┌──────────────┐
│ 用户消息  │───▶│conversation_ │───▶│ MemoryPalace │
└─────────┘    │    logs      │    │  (长期记忆)   │
               └──────────────┘    └──────────────┘
                      │
                      ▼
               ┌──────────────┐    ┌──────────────┐
               │  AgentEngine │───▶│   工具执行    │
               │  (5000轮)    │    │  结果回注     │
               └──────────────┘    └──────────────┘
                      │
                      ▼
               ┌──────────────┐    ┌──────────────┐
               │  LLM 响应    │───▶│  流式输出     │
               │  (tokens)    │    │  (SSE)       │
               └──────────────┘    └──────────────┘
```

---

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI (uvicorn) |
| 数据库 | SQLite (MemoryPalace, NeuralGraph, Session) |
| 向量检索 | ChromaDB / FAISS |
| LLM 提供商 | DeepSeek, Kimi, Qwen, OpenAI, Claude, 小米 |
| 前端 | HTML/CSS/JS (单页应用) |
| IDE 集成 | VS Code 扩展 (TypeScript) |
| 进程管理 | systemd (user mode) |
| 部署 | 本地部署 (localhost:8080) |

---

## 文件结构

```
src/
├── core/                          # 核心层
│   ├── config.py                  # 全局配置
│   ├── bootstrap.py               # 启动引导
│   ├── feature/flags.py           # Feature Flags
│   ├── cognition/                 # 认知引擎
│   │   ├── intent_engine.py       # 意图识别
│   │   ├── context_compressor.py  # 上下文压缩
│   │   └── ultraplan.py           # 超级规划
│   ├── memory_palace/             # 记忆宫殿
│   ├── neural_graph/              # 神经图谱
│   ├── skill_forge/               # 技能锻造
│   ├── orchestration/             # 编排层
│   │   ├── workflow_engine.py     # 工作流引擎
│   │   └── scheduler.py           # 调度器
│   ├── actuator/                  # 执行器
│   │   ├── plan_executor.py       # 计划执行器
│   │   ├── agent_swarm.py         # Agent 集群
│   │   ├── tool_registry.py       # 工具注册
│   │   └── safety_gate.py         # 安全门
│   ├── plugin/hooks.py            # Hook 系统
│   ├── collaboration/             # 协作管理
│   └── neuro_center/              # 神经中枢
│       ├── persona_daemon.py      # 常驻守护
│       └── heartbeat.py           # 心跳检查
│
├── omnia/                         # 应用层
│   ├── main.py                    # FastAPI 入口
│   ├── chat.py                    # 非流式对话
│   ├── stream_chat.py             # 流式对话 (SSE)
│   ├── wake.py                    # Wake Cycle
│   ├── agent_engine.py            # Agent 引擎
│   ├── long_task_handler.py       # 长任务处理
│   ├── smart_pauser.py            # 智能暂停
│   ├── interrupt_manager.py       # 中断管理
│   ├── services/                  # 服务层
│   │   ├── auto_memory.py         # 自动记忆
│   │   ├── session_manager.py     # 会话管理
│   │   ├── tool_registry.py       # 工具注册
│   │   ├── tool_trigger.py        # 工具触发
│   │   └── context_manager.py     # 上下文管理
│   └── routers/                   # API 路由
│
└── skills/                        # 技能定义
```
