# 上下文自动加载功能

## 功能说明

Omnia 现在支持**自动加载最后一次上下文**。每次启动后台服务时，会自动显示上次的会话内容，确保 Omnia "记得" 之前在做什么。

## 使用方法

### 1. 保存当前上下文

在对话结束时，使用 `save_context.py` 保存上下文：

```bash
python3 scripts/save_context.py "主题" "摘要" \
  --project "项目名称" \
  --files "文件1" "文件2" \
  --decisions "决策1" "决策2" \
  --next "下一步1" "下一步2"
```

**示例**：
```bash
python3 scripts/save_context.py \
  "DJI无人机故障诊断系统开发" \
  "完成了知识库建设、通信模块开发、USB通信测试成功" \
  --project "DJI诊断系统" \
  --files "knowledge_base/dji/dji_knowledge_base.md" \
  --decisions "使用USB接口4进行通信" \
  --next "修复Web前端问题" "完善诊断工具功能"
```

### 2. 启动时自动加载

启动守护进程时，会自动加载并显示上次保存的上下文：

```bash
python3 scripts/start_daemon.py
```

**输出示例**：
```
============================================================
📖 上次会话上下文:
============================================================
📅 时间: 2026-04-19T20:56:39
📌 主题: DJI无人机故障诊断系统开发
📝 摘要: 完成了知识库建设、通信模块开发、USB通信测试成功
🏗️ 项目: DJI诊断系统
📄 文件: knowledge_base/dji/dji_knowledge_base.md
➡️ 下一步:
   - 修复Web前端无法打开的问题
   - 完善诊断工具功能
   - 测试更多DJI设备
============================================================
```

### 3. 上下文存储位置

上下文保存在：`~/.omnia/last_context.json`

## 上下文字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `timestamp` | string | 保存时间（ISO格式） |
| `topic` | string | 会话主题 |
| `summary` | string | 会话摘要 |
| `active_project` | string | 活跃项目名称 |
| `active_files` | list | 活跃文件列表 |
| `key_decisions` | list | 关键决策 |
| `next_steps` | list | 下一步计划 |
| `raw_conversation` | string | 原始对话内容 |

## 编程接口

### 保存上下文

```python
from core.context_manager import save_current_context

save_current_context(
    topic="DJI诊断工具开发",
    summary="完成了USB通信模块",
    active_project="DJI诊断系统",
    active_files=["dji_knowledge_base.md"],
    key_decisions=["使用USB接口4"],
    next_steps=["修复Web前端"],
)
```

### 加载上下文

```python
from core.context_manager import load_last_context

ctx = load_last_context()
if ctx:
    print(f"上次主题: {ctx.topic}")
    print(f"下一步: {ctx.next_steps}")
```

## 最佳实践

1. **每次重要对话结束时保存上下文**
   - 记录关键决策
   - 列出下一步计划
   - 标注活跃文件

2. **启动时查看上下文**
   - 快速恢复工作状态
   - 了解上次进度
   - 继续未完成的任务

3. **定期更新上下文**
   - 完成重要里程碑时更新
   - 发现新问题时更新
   - 改变方向时更新

## 注意事项

- 上下文文件存储在 `~/.omnia/` 目录
- 每次保存会覆盖之前的上下文
- 启动时如果没有上下文，会显示 "No previous context found, starting fresh."

---

**创建时间**: 2026-04-19
**相关文件**:
- `src/core/context_manager.py` - 上下文管理器
- `scripts/save_context.py` - 保存脚本
- `scripts/start_daemon.py` - 启动脚本（已集成自动加载）
