---
name: verbatim-memory
description: MemPalace-style verbatim memory system. Stores every conversation word-for-word with semantic search.
version: 1.0.0
---

# Verbatim Memory Skill v1.0

MemPalace 风格的原话记忆系统 —— 保存每一句对话原文。

## 核心能力

1. **全量存储** — 用户说的每句话、助手的每次回复、工具调用结果
2. **语义搜索** — 通过向量相似度找到相关对话
3. **时间索引** — 按日期组织，支持时间范围搜索
4. **会话追踪** — 保持对话连续性
5. **敏感信息脱敏** — 自动隐藏 API keys、密码等

## 使用方式

### 自动模式（推荐）

系统在每次对话后自动存储：
- 用户输入 → `verbatim_bridge.store_user_message()`
- 助手回复 → `verbatim_bridge.store_assistant_message()`
- 工具调用 → `verbatim_bridge.store_tool_call()`

### 手动搜索

```python
from verbatim_bridge import VerbatimBridge

bridge = VerbatimBridge(session_id="current")

# 搜索历史
results = bridge.search_history("喵修匠发货流程", n_results=5)

# 获取上下文
for r in results:
    context = bridge.vm.get_context_window(r['id'], window_size=3)
    # 展示上下文对话
```

### 命令行工具

```bash
# 存储消息
python3 verbatim_bridge.py user "这是用户说的话"
python3 verbatim_bridge.py assistant "这是助手的回复"

# 搜索历史
python3 verbatim_bridge.py search "发货流程"

# 查看最近消息
python3 verbatim_bridge.py recent 20
```

## 存储结构

```
verbatim_db/
├── config.json              # 系统配置
├── index.json               # 消息索引
├── embeddings/
│   ├── 2026-04-08.json      # 按日期分片
│   └── 2026-04-07.json
└── sessions/
    └── session_id.json      # 会话元数据
```

## 消息格式

```json
{
  "id": "a1b2c3d4e5f6",
  "timestamp": "2026-04-08T15:10:23.456789",
  "date": "2026-04-08",
  "type": "user|assistant|tool_call|tool_result|system",
  "session_id": "session_001",
  "content": "消息原文",
  "content_length": 123,
  "embedding": [0.1, 0.2, ...],  // 向量表示
  "metadata": {}
}
```

## 搜索能力

### 基本搜索
```python
results = vm.search("发货流程")
```

### 高级过滤
```python
results = vm.search(
    query="喵修匠",
    n_results=10,
    msg_type="user",              # 只搜用户说的话
    date_from="2026-04-01",       # 开始日期
    date_to="2026-04-08",         # 结束日期
    session_id="current"          # 指定会话
)
```

### 获取上下文
```python
context = vm.get_context_window(msg_id, window_size=3)
# 返回目标消息前后各3条消息
```

## 与旧记忆系统的区别

| 特性 | 旧系统 | Verbatim Memory |
|------|--------|-----------------|
| 存储内容 | 摘要提取 | 原文完整保存 |
| 粒度 | 段落级别 | 消息级别 |
| 召回率 | ~70% | ~96% (MemPalace 风格) |
| 搜索方式 | 关键词 | 语义向量 |
| 上下文 | 无 | 完整的对话流 |

## 性能考量

**存储成本:**
- 纯文本：~20MB/年（100轮/天）
- 向量：~500MB/年（含 embedding）

**搜索性能:**
- 10万条消息：<100ms
- 使用本地 embedding 模型（无 API 成本）

## 安装要求

```bash
# 必需（已安装）
pip install sentence-transformers

# embedding 模型（首次使用自动下载）
# all-MiniLM-L6-v2（80MB，支持离线）
```

## 故障排除

### 模型下载失败
```bash
# 手动下载模型
huggingface-cli download sentence-transformers/all-MiniLM-L6-v2
```

### 使用纯关键词搜索
embedding 不可用时自动 fallback 到关键词搜索，无需干预。

---

_记住每一句话，就像 MemPalace 一样。_
