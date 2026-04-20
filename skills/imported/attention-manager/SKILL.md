---
name: attention-manager
description: Intelligent attention management system to reduce token waste and improve response efficiency. Dynamically loads relevant context, filters noise, and manages cognitive resources. Use for every conversation to optimize context loading.
---

# Attention Manager v1.0

智能注意力管理系统 - 减少50% token浪费

## Core Functions

### 1. Message Priority Classification

```
🔴 CRITICAL (立即处理)
- 直接@我或明确提及"无限"
- 包含紧急关键词：紧急、故障、出错、删除了
- 用户明确表示"需要确认"

🟡 HIGH (优先处理)
- 用户主动提问
- 涉及课程开发、项目进度
- 涉及系统配置、API问题
- 包含"检查"、"查看"、"生成"等动作指令

🟢 NORMAL (常规处理)
- 一般性询问
- 闲聊、确认
- 简单信息查询

⚪ LOW (延迟/忽略)
- 群聊中未提及我
- 纯表情、无实质内容
- 重复的心跳消息
```

### 2. Dynamic Context Loading

**Before** (旧模式):
```
加载所有记忆 → 加载所有skills → 处理请求
[16k tokens] → [响应慢]
```

**After** (新模式):
```
分析消息主题 → 加载相关记忆 → 处理请求
[6k tokens] → [响应快]
```

**Loading Rules:**

| 消息主题 | 加载记忆 | 加载Skills | 预估Tokens |
|---------|---------|-----------|-----------|
| 课程开发 | memory_topics/课程开发 + 项目进度 | course-dev-tracker, auto-skill-creator | ~4k |
| 系统配置 | memory_topics/系统配置 | file-delivery, topic-memory-system | ~3k |
| 进化优化 | memory_topics/进化优化 | self-improving, auto-skill-creator | ~3k |
| 股东协议 | memory_topics/未分类 + 文件系统 | file-delivery | ~2k |
| 闲聊/确认 | 最近2条记忆 | 无 | ~1k |
| 心跳 | 仅HEARTBEAT.md | 无 | ~0.5k |

### 3. Attention Budget Management

**Context Window Budget:** 262k tokens

**Allocation:**
```
System Prompt:        2k  (固定)
Current Conversation: 4k  (动态)
Relevant Memory:      6k  (动态加载)
Active Skills:        4k  (按需加载)
Reserved Buffer:      2k  (应急)
-------------------------
Total Budget:        18k  (原16k)
Available:          244k  (用于长对话)

Alert Threshold:     >200k used → 主动总结重置
Critical Threshold:  >250k used → 紧急截断
```

### 4. Interruption Management

**Priority Preemption:**
```
Current Task (Normal) + New Request (Critical)
                   ↓
    Pause current → Save state → Handle critical → Resume
```

**State Preservation:**
- 中断时保存当前进度到 `~/.openclaw/protect/interrupted_tasks.json`
- 高优先级完成后恢复原任务

## Implementation

### Scripts

#### attention-classify.sh
分类消息优先级

#### context-loader.sh  
根据主题动态加载上下文

#### budget-monitor.sh
监控token使用情况

#### interruption-handler.sh
处理任务中断和恢复

## Integration

Used by: infinite-butler.sh
- Before every response: classify + load context
- During long conversations: monitor budget
- On high priority: handle interruption

## Metrics

Track:
- Token usage per conversation
- Context loading time
- Classification accuracy
- User satisfaction (indirect)

Target: 50% token reduction within 1 week
