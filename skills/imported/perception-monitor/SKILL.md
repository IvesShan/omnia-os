---
name: perception-monitor
description: Active perception system to monitor environment changes and user state. Provides proactive awareness of file system, system status, time, and network conditions. Enables evolution from passive response to active service.
---

# Perception Monitor v1.0

主动感知系统 - 从被动响应到主动服务

## Perception Domains

### 1. File System Perception 👁️

**Monitor:**
- `/home/shan/omnia-os/` - 文件创建、修改、删除
- `/home/shan/omnia-os/projects/` - 项目文件变化
- `/home/shan/omnia-os/memory/` - 记忆文件更新
- `~/.openclaw/outputs/` - 输出文件生成

**Detection:**
```bash
# New file created
✅ "检测到新文件: 股东合作协议_补充协议_20260308.md"
   建议: "文件已生成，需要我解释内容吗？"

# File modified
🔄 "检测到文件更新: 正式版开发记录.md"
   建议: "课程进度已更新，当前3/16 Day完成"

# File deleted
⚠️ "检测到文件删除: Day01_PPT_配图版.pdf"
   建议: "课件被删除，需要从备份恢复吗？"
```

### 2. System Status Perception 💓

**Monitor:**
- API连接状态（Kimi/OpenAI等）
- 磁盘空间使用率
- 内存使用情况
- 网络连接状态

**Alert Levels:**
```
🟢 NORMAL: 一切正常
🟡 WARNING: 磁盘使用 >80%
🟠 ELEVATED: API响应慢
🔴 CRITICAL: 磁盘满 / API断开
```

**Proactive Alerts:**
```bash
# 磁盘空间预警
⚠️ "磁盘空间使用率 85%，建议清理"
   方案A: "自动清理7天前的备份？"
   方案B: "生成清理建议清单？"

# API异常
❌ "检测到Kimi API连接异常"
   建议: "检查配置文件或联系管理员"
   记录: "已记录到错误日志"
```

### 3. Time Perception ⏰

**Awareness:**
- 上次对话时间
- 用户活跃时间段
- 任务截止时间
- 定时任务触发时间

**Intelligent Reminders:**
```bash
# 长时间未对话
💬 "距离上次对话已过去3天"
   汇报: "期间自动完成了: 备份x6, 进度更新x3"
   询问: "需要查看课程开发进度吗？"

# 截止时间临近
⏰ "Day 04开发截止还有2天"
   状态: "目前进度: 0%，建议今天启动"
   询问: "是否需要我并行开发Day 4/5/6？"

# 定时任务提醒
🔔 "每周报告时间到"
   行动: "正在生成本周分析报告..."
```

### 4. User State Perception 👤

**Detect:**
- 用户在线/离线状态
- 当前活跃渠道（WebChat/Feishu）
- 最近关注点（从对话中提取）
- 工作节奏（上午/下午/晚上偏好）

**Adaptive Response:**
```bash
# 检测到用户在飞书
📱 "检测到你在飞书"
   同步: "WebChat的对话已同步至此"
   询问: "继续讨论课程开发吗？"

# 检测到工作时段变化
🌅 "早上好！今天是课程开发第3天"
   状态: "已完成Day 1-3，今日目标Day 4"
   建议: "开始工作前需要我汇报进度吗？"
```

## Alert Strategy

### 主动提醒模式（默认）
**原则: 重要的说，紧急的马上说，常规的等问再说**

| 事件 | 优先级 | 策略 | 示例 |
|------|--------|------|------|
| 磁盘空间满 | 🔴 Critical | 立即提醒 | "磁盘已满，无法保存新文件！" |
| API断开 | 🔴 Critical | 立即提醒 | "API连接断开，需要检查！" |
| 文件被删 | 🟠 High | 5分钟内提醒 | "课件被删除，需要恢复吗？" |
| 磁盘>80% | 🟡 Warning | 下次对话时提醒 | "顺便提醒，磁盘空间80%" |
| 进度延迟 | 🟢 Normal | 日报中提及 | "本周进度稍慢，建议加速" |
| 备份完成 | ⚪ Info | 不主动说 | 用户问时才说 |

### 静默模式（用户可选择）
**仅记录，不主动提醒，所有信息等用户询问时才提供**

## Implementation

### Scripts

#### file-watcher.sh
监控文件系统变化

#### system-check.sh
检查系统状态（API、磁盘、网络）

#### time-tracker.sh
跟踪时间相关事件

#### user-state.sh
感知用户状态

#### alert-decision.sh
决定是否需要主动提醒

## Integration

**With Attention Manager:**
- Perception Monitor检测到的事件 → Attention Manager分类优先级 → 决定是否提醒

**With Memory System:**
- 感知到的重要事件 → 自动记录到记忆

**With User Profile:**
- 学习用户对不同提醒的反应 → 优化提醒策略

## Smart Reminder Examples

### Example 1: Disk Space
```
[监控] 磁盘使用率达到85%
   ↓
[决策] 非紧急，标记为"下次对话时提醒"
   ↓
[用户消息] "今天课程进度如何？"
   ↓
[回复] "Day 3已完成..."
        "顺便提醒：磁盘空间已用85%，需要清理吗？"
```

### Example 2: File Deleted
```
[监控] Day01_PPT.pdf被删除
   ↓
[决策] 高优先级，5分钟内提醒
   ↓
[主动发送] "⚠️ 检测到Day 1的课件被删除"
            "需要从备份恢复吗？"
```

### Example 3: Long Gap
```
[监控] 距上次对话已72小时
   ↓
[决策] 中等优先级，发送友好问候+状态汇报
   ↓
[主动发送] "💬 距离上次对话已3天"
            "期间完成了：自动备份6次，课程进度更新"
            "当前：Day 3已完成，Day 4待启动"
            "需要我做什么吗？"
```

## User Preference Learning

Track user reactions to proactive alerts:
```json
{
  "alert_type": "disk_space_warning",
  "user_reaction": "positive", // positive / neutral / negative / ignore
  "frequency_adjustment": "decrease" // increase / decrease / keep
}
```

Optimize alert strategy based on feedback.
