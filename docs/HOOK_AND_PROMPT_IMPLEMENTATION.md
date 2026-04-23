# Hook 系统和动态系统提示实现报告

**日期**: 2026-04-13
**架构**: Hermes + FreeCode 混合方案

---

## 实现内容

### 1. Hook 系统（FreeCode 风格）

**文件**: `src/core/plugin/hooks.py`

```python
class HookType(Enum):
    PRE_TOOL_USE = "pre_tool_use"           # 工具执行前
    POST_TOOL_USE = "post_tool_use"         # 工具执行后
    ON_MESSAGE = "on_message"               # 消息处理
    ON_TOOL_PATTERN = "on_tool_pattern"     # 检测到工具格式
    ON_COMPACT = "on_compact"               # 压缩事件
    ON_ERROR = "on_error"                   # 错误处理
```

**核心类**:
- `HookRegistry` - 钩子注册表
- `HookContext` - 钩子上下文
- `@register_hook` - 装饰器

**使用示例**:
```python
@register_hook(HookType.POST_TOOL_USE, priority=10)
async def log_tool_call(context: HookContext):
    print(f"Tool executed: {context.tool_name}")
```

### 2. 动态系统提示（Hermes 风格）

**文件**: `src/core/cognition/prompt_builder.py`

**三种模式**:

#### Normal 模式（正常对话）
```
你是 Omnia，一个有性格的 AI 助手。

工具使用规则：
1. 需要时可以通过 tool_calls API 调用工具
2. 工具会帮助你读取文件、执行命令、搜索网络等
3. 不要在文本中输出工具调用格式
4. 用自然语言与用户交流
```

#### Summarize 模式（工具执行后）
```
工具已执行完成。现在请：
1. 分析工具返回的数据
2. 用自然语言总结关键发现
3. 回答用户的原始问题

**重要规则**：
- ❌ 绝对禁止输出任何工具调用格式（XML/JSON/函数调用）
- ❌ 绝对禁止再次调用工具
- ✅ 立即用自然语言回复用户
- ✅ 像和朋友聊天一样自然

已执行的工具：read_file, list_directory
```

#### Error 模式（错误处理）
```
发生了错误。请：
1. 向用户解释发生了什么
2. 提供可能的解决方案
3. 保持友好和有帮助的态度

错误信息：File not found
```

### 3. Provider 适配

**Qianfan 特殊处理**:
```python
if provider in ("qianfan", "baiduqianfancodingplan"):
    extra = "\n\n特别提醒：千帆模型，请确保回复中不要包含任何工具调用格式的文本。"
    return base_prompt + extra
```

### 4. 工具格式清理 Hook

**文件**: `src/core/plugin/tool_cleaner_hook.py`

**策略**:
1. 提取工具调用之前的内容
2. 如果没有有效内容，返回 None 让主流程处理
3. 记录日志以便调试

### 5. 集成到 chat_handler

**核心流程**:

```python
# 1. 构建初始提示
prompt_context = PromptContext(mode="normal", tool_calls_executed=False)
dynamic_prompt = prompt_builder.build_for_provider(provider, prompt_context)

# 2. 工具执行后更新提示
if tool_calls_executed:
    prompt_context.mode = "summarize"
    prompt_context.tool_calls_executed = True
    prompt_context.tool_names = [s['tool'] for s in steps]
    
    # 更新系统提示
    new_system_prompt = prompt_builder.build_for_provider(provider, prompt_context)

# 3. 触发 Hook
hooks.trigger(HookType.PRE_TOOL_USE, context)
# ... 执行工具 ...
hooks.trigger(HookType.POST_TOOL_USE, context)

# 4. 检测到工具格式时触发 Hook
if tool_pattern_in_text:
    hooks.trigger(HookType.ON_TOOL_PATTERN, context)
```

---

## 对比三家架构

| 特性 | Hermes | FreeCode | OpenClaw | Omnia (现在) |
|------|--------|----------|----------|--------------|
| **Hook 系统** | ✅ 生命周期事件 | ✅ pre/post 钩子 | ✅ 事件驱动 | ✅ 6 种钩子 |
| **动态提示** | ✅ Prompt Builder | ⚠️ 简单 | ⚠️ | ✅ 3 种模式 |
| **Provider 适配** | ✅ 3 API Modes | ❌ Anthropic only | ✅ 多提供商 | ✅ Qianfan 优化 |
| **工具格式清理** | ✅ API 模式 | ✅ Hook 清理 | ⚠️ 后处理 | ✅ Hook 清理 |

---

## 测试结果

### Hook 系统测试
```bash
$ python3 -c "from core.plugin.hooks import get_hook_registry; print(get_hook_registry().list_hooks())"
['post_tool_use:log_tool_call', 'on_error:error_handler']
```

### 动态提示测试
```bash
$ python3 -c "from core.cognition.prompt_builder import *; ..."
✅ Hook system and Prompt builder working!
```

### 不同模式的提示对比
- **Normal 模式**: 允许工具调用，正常指令
- **Summarize 模式**: 禁止工具调用，强制自然语言，列出已执行工具
- **Error 模式**: 错误解释和解决方案

---

## 日志输出示例

### 正常流程
```
[Chat] Round 1, messages: 3, use_tools: True
[Chat] Model called 2 tools
[Hook] Tool executed: read_file
[Hook] Tool executed: list_directory
[Chat] Updated system prompt for summarize mode
[Chat] Round 2, messages: 7, use_tools: False
[Chat] Processing reply, length: 150
[Chat] Final reply length: 150
```

### 检测到工具格式
```
[Chat] Detected XML tool format: <list_directory
[Hook:clean_tool_pattern] Processing output of 300 chars
[Hook:clean_tool_pattern] Stopping at tool XML tag
[Hook:clean_tool_pattern] Extracted 50 chars
[Chat] Using extracted content
```

---

## 下一步优化

### 优先级 P0
- [ ] 添加更多内置 Hook（权限检查、性能监控）
- [ ] 完善 Provider 适配（支持 Anthropic、Google）
- [ ] 添加 Hook 配置文件

### 优先级 P1
- [ ] 实现 Hook 链式调用
- [ ] 添加 Hook 中断机制
- [ ] 实现 Hook 性能统计

### 优先级 P2
- [ ] 可视化 Hook 调用链
- [ ] Hook 调试工具
- [ ] Hook 单元测试

---

## 相关文件

- `src/core/plugin/hooks.py` - Hook 系统核心
- `src/core/plugin/tool_cleaner_hook.py` - 工具格式清理
- `src/core/cognition/prompt_builder.py` - 动态系统提示
- `src/omnia/chat_handler.py` - 集成实现
- `docs/TOOL_CALL_SOLUTION_COMPARISON.md` - 架构对比

---

_实现时间: 2026-04-13_
_架构风格: Hermes + FreeCode 混合_
