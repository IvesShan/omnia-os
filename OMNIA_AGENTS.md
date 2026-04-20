# OMNIA_AGENTS.md - Omnia's Operational Manual

Omnia 的操作手册 - 告诉模型怎么正确使用工具和系统。

## 记忆系统

**你有 Memory Palace 记忆宫殿系统！**

- 数据库位置：`.omnia/memory_palace.db`
- 已有记录：600+ 条（事实、时间线、关系、习惯）

### 使用 query_memory 工具

**搜索技巧：**
- 用简单关键词，不要用复杂句子
- ✅ 好：`query_memory("OpenClaw")`
- ✅ 好：`query_memory("用户")`
- ❌ 差：`query_memory("记忆系统 记忆宫殿 记忆连续性")`

**常见搜索词：**
- 项目名：OpenClaw, Omnia, 喵修匠, 懂机帝
- 人名：原点, 无限
- 概念：守护进程, 记忆, 偏好

**记住：你已经有记忆了，搜索就能找到！**

## 工具调用规范

### 核心原则

**永远传递 `tools` 参数** - 这是 OpenClaw 的方式！

```python
# ✅ 正确
data = _call_model_messages(
    api_key, provider, messages,
    tools=TOOLS_SCHEMA,  # 告诉模型有哪些工具
)

# ❌ 错误
data = _call_model_messages(
    api_key, provider, messages,
    # 没有 tools 参数，模型不知道有工具可用
)
```

### 工具列表

| 工具 | 用途 | 参数 |
|------|------|------|
| `read_file` | 读取文件内容 | `path` |
| `write_file` | 写入文件 | `path`, `content` |
| `execute_shell` | 执行 shell 命令 | `command` |
| `list_directory` | 列出目录内容 | `path` |
| `web_search` | 搜索网页 | `query` |
| `query_memory` | 查询记忆宫殿 | `query`, `layer` |

### 触发关键词

当用户提到以下关键词时，**必须**触发工具调用：

**项目相关：**
- "守护进程", "daemon", "服务", "进程", "systemd"
- "Omnia", "omnia-os", "项目"

**行动相关：**
- "帮我", "检查", "看看", "找找", "在哪里"
- "去读", "去看", "去查", "去了解", "去搜"
- "github", "网上", "网页"

**记忆相关：**
- "记忆", "memory", "mempalace", "之前的", "上次"

**状态相关：**
- "读完了吗", "做完了吗", "好了吗"

## 项目关键路径

### Omnia 项目

```
/home/shan/.openclaw/workspace/omnia-os/
├── src/
│   ├── omnia/           # Web 服务器
│   ├── core/
│   │   ├── actuator/    # 工具执行层
│   │   ├── memory_palace/  # 记忆系统
│   │   └── neuro_center/   # 守护进程
│   └── omnia/chat.py    # API 调用
├── scripts/
│   ├── start_daemon.py  # 启动守护进程
│   └── stop_daemon.py   # 停止守护进程
├── web/
│   ├── index.html       # Web UI
│   ├── app.js           # 前端逻辑
│   └── styles.css       # 样式
└── .omnia/
    ├── memory_palace.db # 记忆数据库
    ├── daemon.pid       # 守护进程 PID
    └── daemon.log       # 守护进程日志
```

### OpenClaw 安装位置

```
~/.openclaw/
├── workspace/           # 工作空间
│   ├── omnia-os/        # Omnia 项目
│   ├── miaoxiujiang/    # 喵修匠
│   ├── memory/          # 记忆文件
│   └── .omnia/          # Omnia 运行时数据
└── openclaw.json        # OpenClaw 配置
```

## 常见任务

### 启动守护进程

```python
# 正确的方式
execute_shell("python3 /home/shan/.openclaw/workspace/omnia-os/scripts/start_daemon.py")
```

### 查询记忆

```python
# 搜索所有记忆层
query_memory(query="OpenClaw", layer="all")

# 只搜索事实层
query_memory(query="用户偏好", layer="facts")
```

### 检查项目状态

```python
# 列出项目目录
list_directory(path="/home/shan/.openclaw/workspace/omnia-os")

# 读取配置文件
read_file(path="/home/shan/.openclaw/workspace/omnia-os/config/omnia.yaml")
```

## 错误处理

### 模型返回工具调用格式

如果模型在 `content` 里返回了工具调用格式（而不是通过 `tool_calls` API），说明有问题：

```json
// ❌ 错误：模型在文本里输出
{"content": "list_directory({\"path\": \"...\"})"}

// ✅ 正确：模型通过 tool_calls 返回
{"tool_calls": [{"function": {"name": "list_directory", "arguments": "..."}}]}
```

**解决方案：**
1. 检查是否传递了 `tools` 参数
2. 检查 `TOOLS_SCHEMA` 是否正确
3. 检查 API 是否支持工具调用

### 解析失败

如果 `_parse_steps_from_text` 失败，检查：
1. JSON 格式是否正确
2. 字段名是否匹配（支持多种格式）
3. 是否有空步骤

## 红线

- ❌ 不要在文本里输出工具调用格式
- ❌ 不要说"让我看看"然后什么都不做
- ❌ 不要猜测路径或参数
- ✅ 如果不确定，调用工具查一下
- ✅ 如果需要执行，先确认再执行

## 调试技巧

### 查看日志

```bash
tail -f /tmp/omnia.log
```

### 检查工具调用

```python
# 在 plan() 中添加日志
print(f"[PlanExecutor.plan] tool_calls: {tool_calls}")
print(f"[PlanExecutor.plan] content: {content[:200]}")
```

### 测试工具

```python
# 直接测试工具
from core.actuator.tool_registry import dispatch_tool
result = dispatch_tool("read_file", {"path": "/path/to/file"})
print(result)
```

---

## 更新记录

- 2026-04-12: 初始版本，定义工具调用规范和项目路径
