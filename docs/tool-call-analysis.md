# 工具调用问题深入分析报告

**分析时间**: 2026-04-30  
**分析者**: Omnia  
**问题背景**: 用户报告"工具不调用"问题，需要深入分析系统架构和潜在问题点

---

## 一、系统架构概览

### 1.1 工具调用流程

```
用户消息
    ↓
web_server.py (/api/chat)
    ↓
tool_preroll.py (前置工具检查钩子)
    ↓
assemble_wake_prompt() (组装系统提示)
    ↓
chat_handler.py (核心处理器)
    ↓
_call_model_messages() (调用模型)
    ↓
[模型返回 tool_calls]
    ↓
dispatch_tool() (执行工具)
    ↓
返回结果 → 下一轮对话
```

### 1.2 关键组件

| 组件 | 文件 | 职责 |
|------|------|------|
| 前置钩子 | `tool_preroll.py` | 在消息发给 LLM 前，强制检查是否需要工具验证 |
| 核心处理器 | `chat_handler.py` | 管理对话流程、工具调用循环、消息重建 |
| 工具注册 | `tool_registry.py` | 定义工具 schema、执行工具、安全检查 |
| API 适配 | `kimi_anthropic.py` | 转换消息格式、支持 Prompt Caching |
| 系统提示 | `wake.py` | 组装完整的系统提示，包含工具调用规则 |

---

## 二、工具调用机制详解

### 2.1 三层保障机制

#### 第一层：前置工具检查钩子 (tool_preroll.py)

**触发条件**：用户消息命中关键词触发器

**关键词规则**：
```python
TRIGGER_RULES = [
    # 通用"检查/分析"动词（兜底）
    (r"(检查|确认|验证|核实|查一下|看看|检查一下|检测|测试|试一下|跑一下|分析|重新分析|完整分析|全面分析|改好了吗|生效了吗|有没有生效|状态怎么样|怎么样了|完成了吗|成功了吗|好了没|有没有问题)",
     [
         ("通用检查 - Git状态", "git status --short"),
         ("通用检查 - 最近提交", "git log --oneline -5"),
         ("通用检查 - 端口监听", "ss -tlnp | grep -E '5001|8765'"),
     ]),
    # ... 其他规则
]
```

**工作机制**：
1. 在消息发给 LLM 之前，先检查用户消息是否命中关键词
2. 如果命中，**直接执行 shell 命令**并将结果注入系统提示
3. LLM 收到的消息已经包含了工具验证结果，**无法跳过**

**优点**：
- 强制性：LLM 无法选择不调用工具
- 低延迟：在 LLM 处理前就完成工具调用
- 可追溯：所有前置检查都有日志

**缺点**：
- 可能误触发：关键词匹配不够精准
- 不够灵活：无法根据上下文动态调整

#### 第二层：智能工具选择 (chat_handler.py)

**函数**: `should_require_tool()`

**策略**：
```python
def should_require_tool(user_message: str, provider: str) -> str | None:
    """
    返回值：
    - "required" - 强制调用工具（仅对支持的 provider）
    - "auto" - 建议模型考虑调用工具
    - None - 不传此参数，使用 API 默认行为
    """
    trigger_keywords = [
        "检查", "确认", "验证", "查看", "读取", "读文件",
        "改好了吗", "生效了吗", "有没有", "状态",
        "检查一下", "看一下", "看一下代码", "看看代码",
        "分析", "重新分析", "完整分析", "全面分析",
        "check", "verify", "confirm", "read", "analyze",
    ]
    
    # 根据 provider 决定策略
    providers_support_required = ["kimi", "openai", "anthropic"]
    
    if provider.lower() in providers_support_required:
        return "required"  # 强制调用
    else:
        return "auto"  # 依赖系统提示引导
```

**Provider 支持情况**：
| Provider | 支持 tool_choice: "required" | 策略 |
|----------|------------------------------|------|
| Kimi | ✅ | 强制调用 |
| OpenAI | ✅ | 强制调用 |
| Anthropic | ✅ | 强制调用 |
| DeepSeek | ❌ | 依赖系统提示引导 |
| 千帆 | ❌ | 依赖系统提示引导 |

**问题**：
- DeepSeek 和千帆不支持 `tool_choice: "required"`
- 只能依赖系统提示引导，效果不稳定

#### 第三层：系统提示引导 (wake.py)

**核心规则**：
```markdown
### 🔴 硬规矩：必须先调用工具再回答

**任何需要读取文件、查询状态、验证结果的场景，都必须先调用工具再回答。**

典型场景包括（不仅限于）：
- 用户说"检查""确认""验证""查看""读文件""看看效果""分析""重新分析"
- 用户问"有没有生效""改好了吗""提交了吗""检查一下""怎么样了""状态"
- 用户说"调用工具""用工具查""跑一下"
- 涉及查询文件内容、Git 状态、服务运行状态、代码分析

违规后果：如果未调用工具就直接声称"已完成""已修改"，一律视为错误。
```

**优点**：
- 明确的规则和示例
- 包含正确/错误示例
- 强调违规后果

**缺点**：
- 依赖模型遵守指令的能力
- 对于不支持 `tool_choice: "required"` 的 provider 效果不稳定

---

## 三、潜在问题点分析

### 3.1 问题一：关键词匹配不够精准

**现象**：
- `tool_preroll.py` 使用正则匹配关键词
- 可能误触发（如用户说"检查一下天气"会触发 Git 检查）
- 也可能漏触发（如用户用不同的表达方式）

**示例**：
```python
# 当前规则
(r"(检查|确认|验证|核实|查一下|看看|检查一下)", ...)

# 潜在问题
- "检查一下天气" → 误触发 Git 检查
- "帮我看看这个文件" → 漏触发（没有"检查"关键词）
```

**建议改进**：
1. 增加**否定规则**：排除明显不需要工具的场景
   ```python
   # 否定规则
   NEGATIVE_RULES = [
       r"(天气|时间|日期|笑话|故事|诗歌)",  # 纯知识问答
       r"(你好|再见|谢谢)",  # 闲聊
   ]
   ```
2. 增加**上下文感知**：结合上一轮对话判断
3. 使用**意图识别**：通过轻量级分类器判断是否需要工具

### 3.2 问题二：工具执行后消息重建导致信息丢失

**现象**：
- `chat_handler.py` 在工具执行后会**完全重建消息列表**
- 只保留系统提示和当前用户消息，丢弃历史对话

**代码**：
```python
# 策略 1: 工具执行后完全重建（FreeCode 方案）
if tool_calls_executed:
    # 清空消息列表，只保留系统提示和关键信息
    messages = [{"role": "system", "content": dynamic_prompt}]
    
    # 添加极简的总结提示
    messages.append({
        "role": "user",
        "content": f"基于之前的工具执行结果，请回答：{original_message}"
    })
```

**问题**：
- 如果用户的问题是多轮对话的一部分，可能丢失上下文
- 例如：
  - 用户："修改 config.py"
  - 助手："已修改"
  - 用户："检查一下有没有生效"
  - **问题**：重建后丢失了"修改 config.py"的上下文

**建议改进**：
1. **保留关键历史**：保留最近 3-5 轮对话
2. **智能压缩**：将历史压缩为摘要，而不是完全丢弃
3. **上下文标记**：在重建时添加上下文标记
   ```python
   messages.append({
       "role": "system",
       "content": "[上下文] 用户之前要求修改 config.py，现在检查是否生效"
   })
   ```

### 3.3 问题三：JSON 参数解析失败

**现象**：
- 模型返回的 `tool_calls` 参数是 JSON 字符串
- 如果模型格式错误，会导致解析失败

**代码**：
```python
raw_arguments = tc.get("function", {}).get("arguments", "{}")

try:
    tool_args = json.loads(raw_arguments)
except json.JSONDecodeError as e:
    print(f"JSON parse error: {e}, raw={raw_arguments}")
    tool_args = {}
```

**问题**：
- 解析失败时，`tool_args = {}` 会导致工具执行失败
- 例如：`read_file()` 需要 `path` 参数，但传入 `{}` 会失败

**建议改进**：
1. **参数验证**：检查必需参数是否存在
   ```python
   def validate_tool_args(tool_name: str, args: dict) -> bool:
       required_params = {
           "read_file": ["path"],
           "write_file": ["path", "content"],
           "execute_shell": ["command"],
           # ...
       }
       required = required_params.get(tool_name, [])
       return all(p in args for p in required)
   ```
2. **错误恢复**：如果参数缺失，返回错误提示而不是空字典
3. **重试机制**：如果解析失败，要求模型重新生成

### 3.4 问题四：工具调用循环

**现象**：
- 工具执行后，模型可能继续调用工具而不是生成回答
- 导致无限循环，直到达到 `MAX_TOOL_ROUNDS` 上限

**代码**：
```python
MAX_TOOL_ROUNDS = 5

for round_num in range(MAX_TOOL_ROUNDS):
    # ... 调用模型
    if not tool_calls:
        # 没有工具调用，返回结果
        return {"reply": content, "steps": steps}
    
    # 有工具调用，继续循环
    # ...
```

**问题**：
- 如果模型在第 5 轮仍然调用工具，会返回错误消息
- 用户看到"抱歉，工具调用次数超过限制"

**建议改进**：
1. **智能终止**：检测是否陷入循环
   ```python
   def is_stuck(steps: list) -> bool:
       """检测是否陷入工具调用循环"""
       if len(steps) < 3:
           return False
       
       # 检查最近 3 次是否重复调用同一工具
       recent_tools = [s["tool"] for s in steps[-3:]]
       if len(set(recent_tools)) == 1:
           return True
       
       # 检查是否重复相同的参数
       recent_args = [s["arguments"] for s in steps[-3:]]
       if all(args == recent_args[0] for args in recent_args):
           return True
       
       return False
   ```
2. **强制终止**：如果检测到循环，强制生成回答
3. **反馈机制**：告诉模型"已经调用了 X 次工具，请基于现有结果回答"

### 3.5 问题五：Provider 差异导致的策略不一致

**现象**：
- 不同 Provider 对 `tool_choice` 的支持不同
- DeepSeek 和千帆不支持强制调用

**当前策略**：
```python
providers_support_required = ["kimi", "openai", "anthropic"]

if provider.lower() in providers_support_required:
    return "required"  # 强制调用
else:
    return "auto"  # 依赖系统提示引导
```

**问题**：
- DeepSeek 用户可能遇到工具不调用的问题
- 系统提示引导效果不稳定

**建议改进**：
1. **增强系统提示**：针对不支持的 Provider，强化系统提示
   ```python
   if provider in ["deepseek", "qianfan"]:
       dynamic_prompt += """
   
   ### ⚠️ 重要提示
   
   你必须调用工具来验证你的回答。不要直接声称已完成或已修改。
   
   示例：
   - 用户："检查文件" → 调用 read_file
   - 用户："执行命令" → 调用 execute_shell
   - 用户："查看状态" → 调用 execute_shell
   """
   ```
2. **后验证机制**：如果模型返回文本而没有调用工具，自动触发工具验证
3. **用户反馈**：告知用户当前 Provider 的限制

---

## 四、历史问题记录

从记忆系统中检索到的相关记录：

| 时间 | 事件类型 | 描述 |
|------|----------|------|
| 2026-04-18 | achievement | 工具调用修复、长任务优化、协作系统、神经图谱 |
| 2026-04-18 | error | API 启动后工具调用成功，但模型请求卡住 13 分钟 |
| 2026-04-20 | error | 用户要求检查工具调用是否有问题 |

**关键发现**：
1. **2026-04-18**: 已经修复过工具调用问题
2. **2026-04-18**: 出现过"工具执行成功后，模型请求卡住"的问题
3. **2026-04-20**: 用户再次报告工具调用问题

---

## 五、当前系统状态

### 5.1 MCP 工具状态

```
[MCP] ✓ Connected to 'filesystem' with 14 tools
[MCP] ✓ Connected to 'git' with 12 tools
[MCP] ✓ Connected to 'fetch' with 1 tools
[MCP] ✓ Connected to 'puppeteer' with 7 tools
[MCP] Connected: 4/4 servers, 34 tools available
```

**说明**：MCP 工具正常连接，共 34 个外部工具可用。

### 5.2 原生工具

```python
TOOLS_SCHEMA = [
    "read_file",      # 读取文件
    "write_file",     # 写入文件
    "execute_shell",  # 执行 shell 命令
    "list_directory", # 列出目录
    "web_search",     # 网络搜索
    "query_memory",   # 查询记忆
]
```

**说明**：6 个原生工具正常注册。

### 5.3 前置工具检查状态

**当前触发关键词**：
- 检查、确认、验证、核实、查一下、看看、检查一下
- 检测、测试、试一下、跑一下、分析、重新分析、完整分析、全面分析
- 改好了吗、生效了吗、有没有生效、状态怎么样、怎么样了
- 完成了吗、成功了吗、好了没、有没有问题

**说明**：前置工具检查机制正常工作，覆盖了常见的检查类关键词。

---

## 六、根本原因分析

### 6.1 为什么会出现"工具不调用"？

综合以上分析，可能的原因包括：

1. **Provider 限制**：
   - DeepSeek 和千帆不支持 `tool_choice: "required"`
   - 只能依赖系统提示引导，效果不稳定

2. **模型行为**：
   - 模型可能忽略系统提示中的工具调用指令
   - 特别是在复杂场景或多轮对话中

3. **上下文丢失**：
   - 工具执行后重建消息列表，可能丢失关键上下文
   - 导致模型无法理解用户意图

4. **关键词匹配不足**：
   - 用户使用的表达方式可能不在关键词列表中
   - 导致前置工具检查未触发

5. **模型幻觉**：
   - 模型可能直接生成"已完成"的回答，而没有实际调用工具
   - 特别是在用户没有明确要求验证的场景

### 6.2 为什么"工具调用超限"？

从上次会话上下文看：
```
📝 摘要: 工具调用超限
➡️ 下一步: 简化请求
```

可能的原因：
1. **循环调用**：模型在工具执行后继续调用工具，陷入循环
2. **复杂请求**：用户请求过于复杂，需要多次工具调用
3. **模型行为**：模型没有正确理解"基于工具结果回答"的指令

---

## 七、改进建议

### 7.1 短期改进（立即可实施）

1. **增强关键词匹配**：
   ```python
   # 增加更多关键词
   TRIGGER_RULES = [
       (r"(检查|确认|验证|核实|查一下|看看|检查一下|检测|测试|试一下|跑一下|分析|重新分析|完整分析|全面分析|改好了吗|生效了吗|有没有生效|状态怎么样|怎么样了|完成了吗|成功了吗|好了没|有没有问题|帮我看看|帮我查|帮我检查|验证一下|确认一下|核实一下)", ...),
   ]
   ```

2. **优化消息重建策略**：
   ```python
   if tool_calls_executed:
       # 保留最近 3 轮对话
       messages = [{"role": "system", "content": dynamic_prompt}]
       messages.extend(history[-3:])  # 保留最近 3 轮
       messages.append({
           "role": "user",
           "content": f"基于之前的工具执行结果，请回答：{original_message}"
       })
   ```

3. **增强错误恢复**：
   ```python
   try:
       tool_args = json.loads(raw_arguments)
   except json.JSONDecodeError as e:
       # 返回错误提示，要求模型重新生成
       return {
           "error": f"参数解析失败: {e}。请重新生成工具调用，确保参数格式正确。"
       }
   ```

### 7.2 中期改进（需要测试）

1. **意图识别系统**：
   - 训练轻量级分类器，判断用户意图是否需要工具
   - 替代简单的关键词匹配

2. **上下文压缩**：
   - 将历史对话压缩为摘要，保留关键信息
   - 避免完全丢弃上下文

3. **智能终止检测**：
   - 检测工具调用循环
   - 自动强制终止并生成回答

### 7.3 长期改进（需要架构调整）

1. **统一工具调用接口**：
   - 为不支持 `tool_choice: "required"` 的 Provider 实现替代方案
   - 例如：后验证机制

2. **工具调用可观测性**：
   - 记录所有工具调用的详细信息
   - 提供可视化界面查看工具调用链

3. **用户反馈机制**：
   - 允许用户标记"工具未调用"的情况
   - 收集数据改进系统

---

## 八、测试建议

### 8.1 测试用例

| 场景 | 用户消息 | 预期行为 |
|------|----------|----------|
| 文件检查 | "检查一下 wake.py 的内容" | 调用 read_file |
| Git 状态 | "看看 Git 状态" | 调用 execute_shell |
| 服务状态 | "检查一下服务有没有启动" | 调用 execute_shell |
| 修改验证 | "修改生效了吗" | 调用相应验证工具 |
| 多轮对话 | "修改 config.py" → "检查一下有没有生效" | 保留上下文，调用验证工具 |
| 复杂请求 | "分析整个项目的代码结构" | 多次工具调用，但不超过上限 |

### 8.2 测试方法

1. **手动测试**：
   - 通过 Web UI 发送测试用例
   - 观察日志中的工具调用记录

2. **自动化测试**：
   ```python
   def test_tool_call():
       result = handle_chat(
           message="检查一下 wake.py 的内容",
           history=[],
           api_key="...",
           provider="kimi",
           system_prompt="...",
       )
       
       assert result["tool_calls_executed"] == True
       assert "read_file" in [s["tool"] for s in result["steps"]]
   ```

3. **压力测试**：
   - 测试多轮对话场景
   - 测试复杂请求场景
   - 测试不同 Provider 的行为差异

---

## 九、总结

### 9.1 核心发现

1. **三层保障机制**：前置工具检查、智能工具选择、系统提示引导
2. **Provider 差异**：DeepSeek 和千帆不支持强制调用
3. **消息重建问题**：工具执行后可能丢失上下文
4. **循环调用风险**：模型可能陷入工具调用循环

### 9.2 优先级建议

| 优先级 | 改进项 | 预期效果 |
|--------|--------|----------|
| P0 | 增强关键词匹配 | 减少漏触发 |
| P0 | 优化消息重建策略 | 保留上下文 |
| P1 | 增强错误恢复 | 提高容错性 |
| P1 | 智能终止检测 | 防止循环调用 |
| P2 | 意图识别系统 | 提高精准度 |
| P2 | 上下文压缩 | 平衡性能和准确性 |

### 9.3 下一步行动

1. **立即实施**：P0 改进项
2. **测试验证**：执行测试用例，验证改进效果
3. **监控观察**：记录工具调用情况，收集问题数据
4. **持续优化**：根据实际使用情况调整策略

---

**报告完成时间**: 2026-04-30  
**报告版本**: v1.0  
**下次审查**: 1 周后或发现新问题时
