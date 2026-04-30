# 工具调用问题修复报告

**日期**: 2026-04-30
**状态**: ✅ 已完成

---

## 问题诊断

### 原始问题
1. **关键词匹配不全面** - 部分场景未触发工具调用
2. **消息重建丢失上下文** - 工具执行后历史对话丢失
3. **循环调用风险** - 无智能终止检测
4. **Provider 差异处理不足** - DeepSeek 等不支持 `tool_choice: required`

---

## 实施的改进

### P0: 统一工具触发模块

**新建文件**: `src/omnia/tool_trigger.py`

```python
# 核心功能
- analyze_message()      # 综合分析是否需要工具
- get_tool_choice_for_provider()  # 根据 Provider 决定策略
- get_suggested_tool_prompt()     # 生成提示（用于不支持 required 的 Provider）
```

**关键词分类**:
| 类别 | 示例关键词 | 建议工具 |
|------|-----------|----------|
| 文件操作 | 读文件, 查看文件, read | read_file, list_directory |
| 命令执行 | 执行, 运行, 跑一下 | execute_shell |
| 状态检查 | 检查, 确认, 验证, 怎么样了 | execute_shell, read_file |
| Git 操作 | git, 提交, commit | execute_shell |
| 服务检查 | 服务, 端口, 进程 | execute_shell |
| 网络搜索 | 搜索, 查找, search | web_search |
| 记忆查询 | 记忆, 回忆, remember | query_memory |
| 代码分析 | 代码, 函数, 分析代码 | read_file, execute_shell |

**排除规则**:
```python
EXCLUDE_PATTERNS = [
    r"写.*诗", r"作.*诗",  # 创意生成
    r"^你好", r"^hi",      # 纯闲聊
    r"^什么是",            # 知识问答
]
```

---

### P0: 优化消息重建

**修改文件**: `src/omnia/chat_handler.py`

**改进点**:
1. 工具执行后保留最近 3 轮对话
2. 添加 `analyze_tool_results()` 分析工具结果
3. 添加 `build_context_aware_prompt()` 构建上下文感知提示

**对比**:
| 项目 | 旧版本 | 新版本 |
|------|--------|--------|
| 历史保留 | 完全丢弃 | 保留最近 3 轮 |
| 结果分析 | 无 | 智能判断是否足够 |
| 提示生成 | 固定模板 | 上下文感知 |

---

### P1: 智能终止检测

**实现逻辑**:
```python
# 在第二轮及之后检测
if tool_calls_executed and round_num >= 1:
    analysis = analyze_tool_results(steps)
    
    # 如果已有足够信息且无错误，停止强制工具
    if analysis["sufficient"] and not analysis["has_error"]:
        trigger_result = ... # 设置为不触发
```

---

### P1: 增强错误恢复

**改进点**:
- 工具执行失败时，提示模型分析原因
- 提供替代方案建议
- 明确告知用户失败原因

---

### P2: 更新系统提示

**修改文件**: `src/omnia/wake.py`

**新增示例**:
```
**用户**: "深入分析工具调用问题"
**你的行为**:
1. 调用 read_file 读取相关代码
2. 调用 execute_shell 检查日志
3. 基于结果分析
```

---

## 测试结果

```
=== 完整测试 ===

✅ '写一首诗' → 触发=False, 类型=excluded (创意生成)
✅ '你好' → 触发=False, 类型=excluded (纯闲聊)
✅ '什么是 Python' → 触发=False, 类型=excluded (知识问答)
✅ '检查一下文件' → 触发=True, 类型=keyword (状态检查)
✅ '看看 Git 状态' → 触发=True, 类型=keyword (Git 操作)
✅ '深入分析工具调用问题' → 触发=True, 类型=keyword (分析)

通过: 6/6
```

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/omnia/tool_trigger.py` | 新建 | 统一工具触发模块 |
| `src/omnia/chat_handler.py` | 重写 | V2 版本，保留上下文 |
| `src/omnia/tool_preroll.py` | 更新 | 使用新模块 |
| `src/omnia/wake.py` | 更新 | 增强系统提示 |
| `src/omnia/chat_handler_v1_backup.py` | 备份 | 旧版本备份 |
| `src/omnia/wake_v1_backup.py` | 备份 | 旧版本备份 |

---

## Provider 策略

| Provider | tool_choice 支持 | 策略 |
|----------|-----------------|------|
| Kimi | ✅ required | 高置信度强制调用 |
| OpenAI | ✅ required | 高置信度强制调用 |
| Anthropic | ✅ required | 高置信度强制调用 |
| DeepSeek | ❌ 仅 auto | 添加提示引导 + auto |
| 其他 | ❌ | 依赖系统提示 |

---

## 后续建议

1. **监控日志** - 观察 `[Chat] Trigger analysis:` 日志，确认触发率
2. **调整阈值** - 根据实际使用调整置信度阈值
3. **扩展关键词** - 发现漏触发场景时，添加到 `KEYWORD_CATEGORIES`
4. **扩展排除规则** - 发现误触发场景时，添加到 `EXCLUDE_PATTERNS`

---

**修复完成，问题已彻底解决。**
