# 工具调用循环问题 - 三家架构解决方案对比

**问题**: 模型在工具执行后，有时会在文本中输出工具调用格式，而不是自然语言总结

---

## 1. Hermes Agent 解决方案

### 核心架构

```
┌─────────────────────────────────────────────────────────────────────┐
│ AIAgent (run_agent.py) - 核心对话循环 (~9,200 行)                   │
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
```

### 关键设计：3 API Modes

**Hermes 支持 3 种 API 模式**：
1. `chat_completions` - 标准 OpenAI 格式
2. `codex_responses` - DeepSeek/Codex 格式
3. `anthropic_messages` - Anthropic 格式

**问题解决策略**：

#### A. Prompt Builder 分离

```python
# agent/prompt_builder.py
class PromptBuilder:
    def build_system_prompt(self, tools: list) -> str:
        """为不同 API 模式生成不同的系统提示"""
        
        if self.api_mode == "codex_responses":
            # Codex 模式需要更强的指令
            return """You are Hermes, an AI assistant.

When using tools:
1. Call tools via the tool_calls API
2. After receiving tool results, respond naturally
3. NEVER output tool calls in text format
4. NEVER use XML tags like <tool_call>
"""
        
        elif self.api_mode == "anthropic_messages":
            # Anthropic 有更好的工具支持
            return """You are Hermes, an AI assistant with tool capabilities.

Use tools when needed via the tool_use blocks provided by the API."""
        
        else:
            # 标准 OpenAI 格式
            return "You are Hermes, an AI assistant."
```

#### B. 工具结果后处理

```python
# run_agent.py - 核心循环
async def run_agent_loop(messages: list, tools: list):
    """Hermes 的核心对话循环"""
    
    while True:
        # 1. 调用模型
        response = await call_model(messages, tools)
        
        # 2. 检查是否有工具调用
        if response.tool_calls:
            # 3. 执行工具
            tool_results = await execute_tools(response.tool_calls)
            
            # 4. 添加工具结果到消息
            messages.append(response.message)
            for result in tool_results:
                messages.append({
                    "role": "tool",
                    "content": result.content,
                    "tool_call_id": result.id
                })
            
            # 5. 🔑 关键：设置标志，下次不传 tools
            tools = None  # 或 tools = [] 强制模型总结
            
            # 6. 继续循环，让模型总结
            continue
        
        # 7. 没有工具调用，返回结果
        return response.content
```

#### C. Context Compressor

```python
# agent/context_compressor.py
class ContextCompressor:
    """压缩工具输出，防止 token 爆炸"""
    
    def compress_tool_result(self, result: str, max_tokens: int = 500) -> str:
        """压缩工具结果"""
        
        if len(result) <= max_tokens:
            return result
        
        # 使用 LLM 总结
        summary = self.llm.summarize(
            f"Summarize this tool output in {max_tokens} tokens:\n\n{result}"
        )
        
        return summary
```

---

## 2. FreeCode 解决方案

### 核心架构

```
src/
├── assistant/      # 助手核心
├── tools/          # 工具系统
├── context/        # 上下文管理
├── hooks/          # 钩子系统
└── query/          # 查询引擎
```

### 关键设计：Tool 泛型 + Hook 系统

#### A. Tool 泛型类

```typescript
// src/tools/Tool.ts
type Tool<Input, Output, Progress> = {
  name: string
  inputSchema: Input
  call(args, context): Promise<ToolResult<Output>>
  
  // 🔑 关键：检查权限和并发安全
  checkPermissions(input, context): Promise<PermissionResult>
  isConcurrencySafe(input): boolean
  
  // 🔑 关键：渲染方法（控制输出格式）
  render(input, output): React.ReactNode
}
```

#### B. Hook 系统

```typescript
// src/hooks/HookSystem.ts
enum HookType {
  PRE_TOOL_USE = "pre_tool_use",
  POST_TOOL_USE = "post_tool_use",  // 🔑 关键
  ON_MESSAGE = "on_message",
  ON_TOOL_ERROR = "on_tool_error"
}

class HookSystem {
  // 工具执行后触发
  @hook(HookType.POST_TOOL_USE)
  async postToolUse(context: ToolContext) {
    // 1. 检查模型输出是否包含工具格式
    if (this.hasToolPattern(context.output)) {
      // 2. 清理或重新生成
      context.output = await this.cleanToolPattern(context.output)
    }
    
    // 3. 记录到记忆系统
    await this.memory.record({
      tool: context.tool_name,
      input: context.input,
      output: context.output
    })
  }
  
  hasToolPattern(text: string): boolean {
    // 检测所有可能的工具格式
    const patterns = [
      /<\w+>[\s\S]*?<\/\w+>/,  // XML
      /\w+\s*\(\s*\{/,          // Function call
      /```\w*\n[\s\S]*?```/,   // Code block
    ]
    
    return patterns.some(p => p.test(text))
  }
}
```

#### C. QueryEngine 核心循环

```typescript
// src/query/QueryEngine.ts
async function* queryLoop(
  messages: Message[],
  tools: Tool[]
): AsyncGenerator<Response> {
  
  let toolCallsExecuted = false
  
  while (true) {
    // 1. 构建提示
    const systemPrompt = buildSystemPrompt({
      tools: toolCallsExecuted ? [] : tools,  // 🔑 关键
      mode: toolCallsExecuted ? "summarize" : "normal"
    })
    
    // 2. 调用模型
    const response = await callModel(messages, {
      tools: toolCallsExecuted ? undefined : tools,
      system: systemPrompt
    })
    
    // 3. 处理工具调用
    if (response.toolCalls && !toolCallsExecuted) {
      // 执行工具
      const results = await executeTools(response.toolCalls)
      
      // 添加结果
      messages.push(response.message)
      messages.push(...results)
      
      // 🔑 关键：设置标志
      toolCallsExecuted = true
      
      // 触发 Hook
      await hooks.trigger(HookType.POST_TOOL_USE, {
        tools: response.toolCalls,
        results
      })
      
      continue
    }
    
    // 4. 检查输出格式
    if (hasToolPattern(response.content)) {
      // 触发清理 Hook
      response.content = await hooks.trigger(
        HookType.POST_TOOL_USE,
        { output: response.content }
      )
    }
    
    // 5. 返回最终结果
    yield response
    break
  }
}
```

---

## 3. OpenClaw 解决方案

### 核心架构

```
├── agent/          # Agent 运行时
├── provider*/      # 多提供商支持
├── session*/       # 会话管理
└── subagent/       # 子代理
```

### 关键设计：多通道适配 + 统一消息抽象

#### A. Provider 抽象层

```python
# model/provider.py
class Provider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list,
        tools: list | None = None,
        **kwargs
    ) -> ChatResponse:
        """统一聊天接口"""
        pass
    
    @abstractmethod
    def parse_tool_calls(self, response: dict) -> list[ToolCall]:
        """解析工具调用（处理不同格式）"""
        pass

# OpenAI Provider
class OpenAIProvider(Provider):
    async def chat(self, messages, tools, **kwargs):
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools
        )
        
        return ChatResponse(
            content=response.choices[0].message.content,
            tool_calls=self.parse_tool_calls(response)
        )
    
    def parse_tool_calls(self, response):
        """OpenAI 标准格式"""
        return response.choices[0].message.tool_calls or []

# Anthropic Provider  
class AnthropicProvider(Provider):
    async def chat(self, messages, tools, **kwargs):
        # Anthropic 使用不同的 API 格式
        response = await self.client.messages.create(
            model=self.model,
            messages=messages,
            tools=self._convert_tools(tools)
        )
        
        return ChatResponse(
            content=self._extract_text(response),
            tool_calls=self._extract_tool_use(response)
        )
    
    def _extract_tool_use(self, response):
        """Anthropic 使用 tool_use blocks"""
        return [
            ToolCall(id=block.id, name=block.name, args=block.input)
            for block in response.content
            if block.type == "tool_use"
        ]
```

#### B. 会话管理

```python
# session/SessionManager.py
class SessionManager:
    def __init__(self):
        self.sessions = {}  # session_id -> Session
        self.tool_history = {}  # session_id -> [tool_calls]
    
    async def process_message(
        self,
        session_id: str,
        message: str,
        tools: list
    ) -> Response:
        """处理消息的核心方法"""
        
        session = self.sessions.get(session_id)
        
        # 1. 检查是否已经执行过工具
        if session.tool_calls_executed:
            # 🔑 关键：强制模型总结
            return await self.force_summarize(session, message)
        
        # 2. 正常处理
        response = await self.provider.chat(
            messages=session.messages + [message],
            tools=tools
        )
        
        # 3. 处理工具调用
        if response.tool_calls:
            # 执行工具
            results = await self.execute_tools(response.tool_calls)
            
            # 记录
            session.add_tool_calls(response.tool_calls)
            session.add_messages(results)
            
            # 🔑 关键：设置标志
            session.tool_calls_executed = True
            
            # 继续循环
            return await self.process_message(
                session_id,
                "",  # 空消息，让模型总结
                tools=[]  # 不传工具
            )
        
        # 4. 清理输出
        if self.has_tool_pattern(response.content):
            response.content = self.clean_tool_pattern(response.content)
        
        return response
    
    async def force_summarize(self, session, message: str) -> Response:
        """强制模型生成自然语言总结"""
        
        prompt = f"""Based on the tool execution results, please:

1. Summarize what was found
2. Answer the user's question: {message}

DO NOT output any tool call formats. Respond naturally."""

        return await self.provider.chat(
            messages=session.messages + [{"role": "user", "content": prompt}],
            tools=None  # 不传工具
        )
```

---

## 4. 对比总结

| 方案 | Hermes | FreeCode | OpenClaw | Omnia |
|------|--------|----------|----------|-------|
| **核心策略** | 3 API Modes | Tool 泛型 + Hook | Provider 抽象 + Session | 标志位 + 清理 |
| **检测时机** | Prompt Builder | Hook 系统 | 输出后处理 | 输出后处理 |
| **清理方式** | API 模式适配 | Hook 清理 | Provider 清理 | 重新生成 |
| **最佳实践** | ✅ 最完善 | ✅ 类型安全 | ✅ 可扩展 | ⚠️ 简单有效 |

---

## 5. Omnia 应采用的方案

### 推荐：混合方案（Hermes + FreeCode）

```python
# src/core/actuator/tool_executor.py

class ToolExecutor:
    """融合 Hermes 和 FreeCode 的工具执行器"""
    
    def __init__(self):
        self.hooks = HookRegistry()  # FreeCode 风格
        self.api_mode = "chat_completions"  # Hermes 风格
    
    async def execute_with_hooks(
        self,
        messages: list,
        tools: list,
        api_key: str,
        provider: str
    ) -> dict:
        """执行工具并处理结果"""
        
        tool_calls_executed = False
        
        for round_num in range(5):  # 最多 5 轮
            # 1. 构建系统提示（Hermes 风格）
            system_prompt = self.build_system_prompt(
                mode="summarize" if tool_calls_executed else "normal"
            )
            
            # 2. 调用模型
            response = await self.call_model(
                messages=messages,
                tools=None if tool_calls_executed else tools,
                system=system_prompt
            )
            
            # 3. 检查工具调用
            if not response.tool_calls:
                # 触发 POST_TOOL_USE Hook（FreeCode 风格）
                if tool_calls_executed:
                    await self.hooks.trigger(HookType.POST_TOOL_USE, {
                        "output": response.content,
                        "tools_used": self.tools_used
                    })
                
                # 检查并清理工具格式
                if self.has_tool_pattern(response.content):
                    response.content = await self.clean_or_regenerate(
                        response.content,
                        messages,
                        api_key,
                        provider
                    )
                
                return {"reply": response.content}
            
            # 4. 执行工具
            messages.append(response.message)
            
            for tool_call in response.tool_calls:
                # 触发 PRE_TOOL_USE Hook
                await self.hooks.trigger(HookType.PRE_TOOL_USE, {
                    "tool": tool_call.name,
                    "args": tool_call.args
                })
                
                # 执行
                result = await self.execute_tool(tool_call)
                
                # 触发 POST_TOOL_USE Hook
                await self.hooks.trigger(HookType.POST_TOOL_USE, {
                    "tool": tool_call.name,
                    "result": result
                })
                
                messages.append({
                    "role": "tool",
                    "content": result,
                    "tool_call_id": tool_call.id
                })
            
            tool_calls_executed = True
    
    def build_system_prompt(self, mode: str) -> str:
        """Hermes 风格的动态系统提示"""
        
        if mode == "summarize":
            return """Tools have been executed. Now:
1. Analyze the results
2. Answer the user's question naturally
3. DO NOT output tool call formats
4. Respond as if talking to a friend"""
        
        return """You are Omnia, an AI assistant with tool capabilities.

Use tools when needed via the tool_calls API provided by the system.
After receiving tool results, respond naturally to the user."""
    
    async def clean_or_regenerate(
        self,
        content: str,
        messages: list,
        api_key: str,
        provider: str
    ) -> str:
        """清理或重新生成"""
        
        # 策略1: 提取有效内容
        cleaned = self.extract_clean_content(content)
        if cleaned:
            return cleaned
        
        # 策略2: 强制重新生成
        return await self.force_regenerate(messages, api_key, provider)
```

---

## 6. 实施建议

### 优先级 P0

1. **实现 Hook 系统**（参考 FreeCode）
   - `PRE_TOOL_USE`: 工具执行前
   - `POST_TOOL_USE`: 工具执行后
   - `ON_TOOL_PATTERN`: 检测到工具格式时

2. **动态系统提示**（参考 Hermes）
   - 正常模式：允许工具调用
   - 总结模式：禁止工具调用，强制自然语言

### 优先级 P1

3. **Provider 抽象增强**（参考 OpenClaw）
   - 支持不同 Provider 的工具格式解析
   - 统一的错误处理

4. **上下文压缩器**（参考 Hermes）
   - 工具结果压缩
   - Token 预算管理

### 优先级 P2

5. **Tool 泛型类**（参考 FreeCode）
   - 类型安全的工具定义
   - 权限检查
   - 并发控制

---

_最后更新: 2026-04-13_
_基于 Hermes, FreeCode, OpenClaw 架构研究_
