# 架构对比分析：Hermes / FreeCode / OpenClaw / Omnia

## 0. Hermes Agent 架构（Nous Research）

### 核心定位
> "The self-improving AI agent that grows with you"

**核心特性**：
- **自学习循环**：从经验创建技能，使用中改进
- **记忆持久化**：FTS5 会话搜索 + LLM 总结
- **多通道**：Telegram, Discord, Slack, WhatsApp, Signal, CLI
- **多终端后端**：local, Docker, SSH, Daytona, Singularity, Modal
- **Provider 抽象**：18+ 提供商，OAuth 流程，凭证池

### 架构图
```
┌─────────────────────────────────────────────────────────────────────┐
│ Entry Points                                                        │
│   CLI (cli.py)  │  Gateway (gateway/run.py)  │  ACP (acp_adapter/)  │
│   Batch Runner  │  API Server             │  Python Library      │
└──────────┬──────────────┬───────────────────────┬──────────────────┘
           │              │                       │
           ▼              ▼                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│ AIAgent (run_agent.py)                                              │
│   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                │
│   │ Prompt       │ │ Provider     │ │ Tool         │                │
│   │ Builder      │ │ Resolution   │ │ Dispatch     │                │
│   └──────────────┘ └──────────────┘ └──────────────┘                │
│   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                │
│   │ Compression  │ │ 3 API Modes  │ │ Tool Registry│                │
│   │ & Caching    │ │ chat_compl.  │ │ 48 tools     │                │
│   │              │ │ codex_resp.  │ │ 40 toolsets  │                │
│   └──────────────┘ └──────────────┘ └──────────────┘                │
└─────────────────────────────────────────────────────────────────────┘
           │              │
           ▼              ▼
┌───────────────────┐ ┌──────────────────────┐
│ Session Storage   │ │ Tool Backends        │
│ (SQLite + FTS5)   │ │ Terminal (6 backends)│
│                   │ │ Browser (5 backends) │
│                   │ │ Web (4 backends)     │
│                   │ │ MCP (dynamic)        │
└───────────────────┘ └──────────────────────┘
```

### 目录结构
```
hermes-agent/
├── run_agent.py           # AIAgent — 核心对话循环 (~9,200 行)
├── cli.py                 # HermesCLI — 交互式终端 UI (~8,500 行)
├── model_tools.py         # 工具发现、schema 收集、分发
├── toolsets.py            # 工具分组和平台预设
├── hermes_state.py        # SQLite 会话/状态数据库 + FTS5
├── agent/                 # Agent 内部实现
│   ├── prompt_builder.py  # 系统 prompt 组装
│   ├── context_engine.py  # ContextEngine ABC (可插拔)
│   ├── context_compressor.py
│   ├── prompt_caching.py  # Anthropic prompt caching
│   ├── auxiliary_client.py
│   └── memory_manager.py
├── hermes_cli/            # CLI 子命令
│   ├── main.py            # 入口点 (~5,500 行)
│   ├── commands.py        # COMMAND_REGISTRY — 斜杠命令定义
│   ├── auth.py            # PROVIDER_REGISTRY
│   ├── runtime_provider.py
│   └── setup.py           # 交互式设置向导 (~3,100 行)
├── tools/                 # 工具实现
│   ├── registry.py        # 中央工具注册表
│   ├── approval.py        # 危险命令检测
│   ├── terminal_tool.py   # 终端编排
│   ├── mcp_tool.py        # MCP 客户端 (~2,200 行)
│   └── environments/      # 终端后端
├── gateway/               # 消息平台网关
│   ├── run.py             # GatewayRunner (~7,500 行)
│   ├── session.py         # SessionStore
│   ├── delivery.py        # 出站消息投递
│   └── platforms/         # 15 个适配器
├── cron/                  # 调度器
├── plugins/               # 插件系统
│   ├── memory/            # 记忆提供者插件
│   └── context_engine/    # 上下文引擎插件
└── skills/                # 内置技能
```

### 关键设计模式

**1. Provider 抽象**
```python
# 18+ 提供商，统一接口
# 支持三种 API 模式：chat_completions, codex_responses, anthropic_messages
(runtime_provider, api_key, base_url) = resolve_runtime_provider(provider, model)
```

**2. Tool Registry**
```python
# 47 个工具，20 个 toolsets
# 每个工具文件自注册
class Tool:
    name: str
    description: str
    parameters: dict
    async def execute(args, context): ...
```

**3. Session Storage (FTS5)**
```sql
-- SQLite + FTS5 全文搜索
CREATE VIRTUAL TABLE messages_fts USING fts5(content);
-- 支持 LLM 总结的跨会话召回
```

**4. 插件系统**
```python
# 可插拔的 ContextEngine 和 MemoryProvider
class ContextEngine(ABC):
    async def compress(self, messages, max_tokens): ...
    
class MemoryProvider(ABC):
    async def search(self, query): ...
    async def store(self, content, metadata): ...
```

---

## 1. 规模对比

| 项目 | 语言 | 源文件数 | 代码规模 |
|------|------|----------|----------|
| **FreeCode** | TypeScript | ~100+ | 中型（修改自 Claude Code） |
| **OpenClaw** | TypeScript/JS | 9129 | 大型（企业级平台） |
| **Omnia** | Python | 32 | 小型（轻量级） |

---

## 2. FreeCode 架构（Claude Code 修改版）

### 核心结构
```
src/
├── assistant/      # 助手核心
├── bridge/         # IDE 桥接
├── cli/            # 命令行接口
├── commands/       # 斜杠命令
├── context/        # 上下文管理
├── coordinator/    # 协调器
├── hooks/          # 钩子系统
├── ink/            # 终端 UI（React）
├── memdir/         # 内存目录
├── query/          # 查询引擎
├── schemas/        # 数据模式
├── server/         # 服务器
├── services/       # 服务层
├── skills/         # 技能系统
├── state/          # 状态管理
├── tasks/          # 任务系统
├── tools/          # 工具系统
├── utils/          # 工具函数
├── vendor/         # 第三方
├── vim/            # Vim 模式
└── voice/          # 语音模式
```

### 关键特性
- **88+ Feature Flags**: 编译时特性开关
- **Tool 抽象**: `Tool<Input, Output, Progress>` 泛型
- **Task 系统**: 本地/远程任务管理
- **QueryEngine**: 核心查询循环
- **Hook 系统**: 工具调用前后钩子
- **权限系统**: `checkPermissions`, `PermissionResult`
- **MCP 集成**: Model Context Protocol

### 工具定义模式
```typescript
type Tool<Input, Output, Progress> = {
  name: string
  inputSchema: Input
  call(args, context, canUseTool, parentMessage, onProgress): Promise<ToolResult<Output>>
  checkPermissions(input, context): Promise<PermissionResult>
  isConcurrencySafe(input): boolean
  isReadOnly(input): boolean
  isDestructive?(input): boolean
  // ... 渲染、进度、UI 相关方法
}
```

---

## 3. OpenClaw 架构

### 核心模块（从文件名推断）
```
├── agent/          # Agent 运行时
├── channel*/       # 多通道支持（Signal, Telegram, Discord 等）
├── cron/           # 定时任务
├── gateway/        # 网关服务
├── memory*/        # 记忆系统
├── model*/         # 模型抽象层
├── provider*/      # 多提供商支持
├── session*/       # 会话管理
├── skills/         # 技能系统
├── tools/          # 工具注册
└── subagent/       # 子代理
```

### 关键设计
- **多通道架构**: 统一消息抽象，支持 20+ 通道
- **Provider 抽象**: 统一模型接口（OpenAI, Anthropic, Gemini, Kimi, Qianfan...）
- **记忆系统**: 向量嵌入 + 持久化存储
- **网关模式**: 远程部署 + 本地执行
- **权限分离**: 敏感操作需审批

---

## 4. Omnia 当前架构

```
src/
├── core/
│   ├── actuator/       # 执行器
│   │   ├── tool_registry.py    # 工具注册
│   │   ├── plan_executor.py    # 计划执行器
│   │   ├── agent_swarm.py      # 多代理
│   │   └── safety_gate.py      # 安全门控
│   ├── cognition/      # 认知
│   │   ├── context_compressor.py
│   │   ├── token_budget.py
│   │   └── ultraplan.py
│   ├── memory_palace/  # 记忆宫殿
│   ├── neuro_center/   # 神经中枢
│   ├── personas/       # 人格系统
│   └── skill_forge/    # 技能锻造
├── omnia/
│   ├── chat.py         # 聊天接口
│   ├── chat_handler.py # 处理器
│   ├── wake.py         # 唤醒
│   └── web_server.py   # Web 服务
└── scripts/
    └── start_daemon.py # 守护进程
```

### MCP 工具生态（2025-01 启用）

**已启用的 MCP Server：**

| MCP Server | 功能 | 工具数量 | 状态 |
|-----------|------|---------|------|
| **playwright** | 浏览器自动化 | 15+ | ✅ 已启用 |
| **fetch** | HTTP 请求 | 3 | ✅ 已启用 |
| **git** | Git 操作 | 10+ | ✅ 已启用 |
| **filesystem** | 文件系统 | 8 | ✅ 已启用 |

**Playwright 浏览器自动化能力：**
- `playwright_navigate` - 导航到网页
- `playwright_screenshot` - 截图
- `playwright_click` - 点击元素
- `playwright_fill` - 填写表单
- `playwright_evaluate` - 执行 JavaScript
- `playwright_get_text` - 获取文本内容
- 支持 143 种设备模拟（iPhone, iPad, Android 等）

**工具架构：**
```
┌─────────────────────────────────────────────────────────┐
│                    Omnia 工具层                          │
├─────────────────────────────────────────────────────────┤
│  内置工具 (6)           │  MCP 工具 (35+)                │
│  ─────────────────────  │  ─────────────────────────────  │
│  • read_file            │  • playwright_navigate         │
│  • write_file           │  • playwright_screenshot       │
│  • list_directory       │  • playwright_click            │
│  • execute_shell        │  • playwright_fill             │
│  • query_memory         │  • fetch_get/post              │
│  • web_search           │  • git_status/commit/push      │
│                         │  • filesystem_read/write       │
└─────────────────────────────────────────────────────────┘
```

---

## 5. 架构差距分析

### 四系统核心能力对比

| 能力 | Hermes | FreeCode | OpenClaw | Omnia |
|------|--------|----------|----------|-------|
| **工具系统** | ✅ Registry + 47工具 | ✅ 泛型+权限+渲染 | ✅ 统一注册 | ⚠️ 简单字典 |
| **任务系统** | ✅ AIAgent 循环 | ✅ Task 抽象 | ✅ Session+Task | ⚠️ PlanExecutor 简化版 |
| **Hook 系统** | ✅ 生命周期事件 | ✅ pre/post 钩子 | ✅ 事件驱动 | ❌ 无 |
| **权限系统** | ✅ approval.py | ✅ checkPermissions | ✅ 审批流程 | ⚠️ 简单安全检查 |
| **并发控制** | ✅ 后台进程管理 | ✅ isConcurrencySafe | ✅ 子代理管理 | ❌ 无 |
| **多通道** | ✅ 15 适配器 | ❌ CLI only | ✅ 20+ 通道 | ❌ Web only |
| **记忆系统** | ✅ FTS5 + 插件 | ✅ memdir | ✅ 向量+持久化 | ⚠️ SQLite 基础版 |
| **模型抽象** | ✅ 18+ Provider | ❌ Anthropic only | ✅ 多提供商 | ⚠️ 简单封装 |
| **Feature Flags** | ❌ | ✅ 88+ flags | ❌ | ❌ |
| **UI 渲染** | ✅ CLI + 多通道 | ✅ React/Ink | ✅ 多通道适配 | ⚠️ 简单 Web |
| **浏览器自动化** | ✅ 5 backends | ❌ | ⚠️ Puppeteer | ✅ **Playwright MCP** |
| **自学习** | ✅ 技能自动创建 | ❌ | ⚠️ Skill Forge | ⚠️ 规划中 |
| **多终端** | ✅ 6 后端 | ❌ | ⚠️ | ❌ |
| **调度系统** | ✅ Cron + 投递 | ⚠️ | ✅ Cron | ❌ |
| **插件系统** | ✅ 可插拔引擎 | ❌ | ✅ | ❌ |

---

## 6. 建议优化方向

### 优先级 P0（核心架构）

1. **工具系统重构**
   - 引入 `Tool` 泛型类（类似 FreeCode）
   - 添加 `checkPermissions` 方法
   - 添加 `isConcurrencySafe` 方法
   - 支持工具调用进度回调

2. **Hook 系统**
   - `pre_tool_use`: 工具调用前
   - `post_tool_use`: 工具调用后
   - `on_message`: 消息处理
   - `on_compact`: 压缩事件

3. **任务系统**
   - `Task` 抽象（pending/running/completed/failed/killed）
   - 任务持久化
   - 任务恢复机制

### 优先级 P1（功能增强）

4. **并发控制**
   - 工具并发安全标记
   - 批量工具执行
   - 死锁检测

5. **记忆系统增强**
   - 向量嵌入（已有 Chroma）
   - 记忆分层（facts/habits/relations/timeline）
   - 自动记忆提取

6. **模型抽象层**
   - Provider 接口统一
   - 模型能力探测
   - 降级策略

### 优先级 P2（生态扩展）

7. **多通道支持**
   - 抽象 `Channel` 接口
   - 适配 Telegram/Discord/Signal

8. **Feature Flags**
   - 编译时特性开关
   - 实验性功能隔离

---

## 7. 具体代码改进建议

### 7.1 Tool 基类（参考 FreeCode）

```python
# src/core/actuator/tool_base.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any
from pydantic import BaseModel

InputT = TypeVar('InputT', bound=BaseModel)
OutputT = TypeVar('OutputT')

class PermissionResult:
    allow: bool
    reason: str | None = None
    updated_input: dict | None = None

class Tool(ABC, Generic[InputT, OutputT]):
    name: str
    input_schema: type[InputT]
    
    @abstractmethod
    async def call(self, args: InputT, context: 'ToolContext') -> OutputT:
        pass
    
    def check_permissions(self, args: InputT, context: 'ToolContext') -> PermissionResult:
        return PermissionResult(allow=True)
    
    def is_concurrency_safe(self, args: InputT) -> bool:
        return False
    
    def is_read_only(self, args: InputT) -> bool:
        return False
    
    def is_destructive(self, args: InputT) -> bool:
        return False
```

### 7.2 Hook 系统

```python
# src/core/hooks.py
from dataclasses import dataclass
from typing import Callable, Any
from enum import Enum

class HookType(Enum):
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    ON_MESSAGE = "on_message"
    ON_COMPACT = "on_compact"

@dataclass
class HookContext:
    type: HookType
    tool_name: str | None
    args: dict | None
    result: Any | None
    error: Exception | None

HookCallback = Callable[[HookContext], None]

class HookRegistry:
    def __init__(self):
        self._hooks: dict[HookType, list[HookCallback]] = {}
    
    def register(self, hook_type: HookType, callback: HookCallback):
        if hook_type not in self._hooks:
            self._hooks[hook_type] = []
        self._hooks[hook_type].append(callback)
    
    async def trigger(self, context: HookContext):
        for callback in self._hooks.get(context.type, []):
            await callback(context)
```

### 7.3 任务系统

```python
# src/core/actuator/task.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
import uuid

TaskStatus = Literal["pending", "running", "completed", "failed", "killed"]

@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: str = "local_bash"
    status: TaskStatus = "pending"
    description: str = ""
    tool_use_id: str | None = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    output_file: str = ""
    
    def is_terminal(self) -> bool:
        return self.status in ("completed", "failed", "killed")
```

---

## 8. Hermes 核心学习点

### 自学习循环（Omnia 应实现）

```python
# Hermes 的自学习流程
1. 完成复杂任务
2. 提取可复用模式
3. 自动创建技能
4. 使用中改进
5. 持久化到技能库
```

**Omnia 实现**：
```python
# src/core/skill_forge/auto_learner.py
class AutoSkillCreator:
    async def analyze_trajectory(self, messages: list, tools_used: list):
        # 分析对话轨迹，提取可复用模式
        pattern = await self.extract_pattern(messages, tools_used)
        if pattern.is_reusable:
            skill = await self.create_skill(pattern)
            return skill
    
    async def create_skill(self, pattern: Pattern) -> Skill:
        # 生成技能文件
        skill_md = f"""# {pattern.name}

## Description
{pattern.description}

## Triggers
{pattern.triggers}

## Procedure
{pattern.steps}
"""
        # 写入技能库
        self.skill_dir.write_text(f"{pattern.name}.md", skill_md)
```

### FTS5 会话搜索

```python
# Hermes 使用 SQLite FTS5 进行全文搜索
CREATE VIRTUAL TABLE messages_fts USING fts5(
    content,
    tokenize='porter unicode61'
);

-- Omnia 应实现类似功能
# src/core/memory_palace/fts_search.py
import sqlite3

class FTSSearch:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts 
            USING fts5(content, role, timestamp)
        ''')
    
    def search(self, query: str, limit: int = 10) -> list[dict]:
        cursor = self.conn.execute('''
            SELECT content, role, timestamp, rank
            FROM messages_fts
            WHERE messages_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        ''', (query, limit))
        return [dict(row) for row in cursor.fetchall()]
```

### 多终端后端

```python
# Hermes 支持 6 种终端后端
class TerminalBackend(ABC):
    @abstractmethod
    async def execute(self, command: str) -> ExecuteResult: ...

# Omnia 应实现类似抽象
class LocalTerminal(TerminalBackend):
    async def execute(self, command: str) -> ExecuteResult:
        proc = await asyncio.create_subprocess_shell(command)
        stdout, stderr = await proc.communicate()
        return ExecuteResult(stdout, stderr, proc.returncode)

class DockerrTerminal(TerminalBackend):
    async def execute(self, command: str) -> ExecuteResult:
        # Docker 执行
        ...

class SSHTerminal(TerminalBackend):
    async def execute(self, command: str) -> ExecuteResult:
        # SSH 远程执行
        ...
```

---

## 9. 总结

### Omnia vs 行业标准

| 维度 | Omnia 当前 | 行业标准 (Hermes) | 差距 |
|------|-----------|-----------------|------|
| 代码规模 | 32 文件 | ~100 文件 | 3x |
| 工具数量 | 6 | 47 | 8x |
| 多通道 | 1 | 15 | 15x |
| Provider | 3 | 18+ | 6x |
| 记忆 | SQLite | FTS5 + 插件 | 功能差距 |
| 自学习 | 规划中 | 已实现 | 核心缺失 |

### 优先行动项

1. **FTS5 全文搜索** - 提升记忆检索效率
2. **Tool Registry 重构** - 参考 Hermes 的注册机制
3. **Provider 抽象层** - 支持 18+ 提供商
4. **自学习循环** - 自动技能创建
5. **多终端后端** - Docker/SSH 支持

---

_最后更新: 2026-04-13_
_基于 Hermes Agent, FreeCode, OpenClaw 架构分析_
