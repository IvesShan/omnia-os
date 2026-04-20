---
name: memory-2.0
description: Enhanced memory system with lifecycle management, strength weighting, and associative networks. Implements forgetting mechanism, memory consolidation, and intelligent retrieval optimization.
---

# Memory System 2.0

记忆增强系统 - 会遗忘、有强度、能联想

## Core Concepts

### 1. Memory Lifecycle 记忆生命周期

```
编码 (Encoding)
    ↓
巩固 (Consolidation) ← 睡眠/定期整理
    ↓
存储 (Storage) ← 按强度分层
    ↓
提取 (Retrieval) ← 联想激活
    ↓
遗忘/归档 (Forgetting/Archiving) ← 30天未使用
```

### 2. Memory Strength 记忆强度

**权重体系 (0-100):**
```
100: 核心身份 (IDENTITY.md, SOUL.md) - 永不遗忘
 90: 重要决策和契约 (MEMORY.md)
 80: 高频使用记忆 (每天访问)
 70: 近期重要事件 (本周)
 60: 普通工作记忆 (本月)
 50: 历史存档 (超过1个月)
 40: 低频访问 (建议归档)
 30: 待遗忘 (准备转入长期存档)
  0: 已归档 (可删除或冷存储)
```

**动态调整规则:**
```
访问一次: +5
一天内多次访问: +10 (上限)
7天未访问: -5
30天未访问: -20
标记"重要": +20
标记"错误": -30 (加速遗忘)
```

### 3. Associative Memory Network 联想记忆网络

**记忆关联图:**
```
[课程开发] ←→ [无人机维修] ←→ [物熵科技]
    ↓              ↓              ↓
[Day进度]    [工具焊接]      [股东协议]
    ↓              ↓              ↓
[Day 1-3]    [电烙铁使用]    [1元回购]
```

**联想检索:**
- 搜索"课程" → 激活"课程开发"节点 → 关联"Day进度"
- 搜索"工具" → 激活"工具焊接" → 关联"电烙铁"

### 4. Consolidation & Forgetting 巩固与遗忘

**每日凌晨02:00自动执行:**
```
1. 扫描所有记忆文件
2. 计算记忆强度
3. 调整权重
4. 低权重记忆(≤30) → 归档到 cold-storage/
5. 建立新的关联链接
6. 生成记忆摘要
```

**遗忘不是删除:**
- 遗忘 = 从"活跃记忆"转移到"归档记忆"
- 归档记忆仍可检索，但权重极低
- 被激活时可"复活"回到活跃记忆

## Implementation

### Directory Structure

```
memory/
├── active/              # 活跃记忆 (高权重)
│   ├── core/           # 核心身份 (强度100)
│   ├── working/        # 工作记忆 (强度60-90)
│   └── recent/         # 近期记忆 (强度40-70)
├── archive/            # 归档记忆 (强度≤30)
│   └── YYYY-MM/       # 按月份归档
├── associative/        # 关联网络
│   └── links.json     # 记忆间关联图
└── meta/               # 元数据
    └── strength-db.json # 记忆强度数据库
```

### Core Scripts

#### strength-calculator.sh
计算和更新记忆强度

#### memory-consolidation.sh
每日记忆巩固（遗忘+归档）

#### associative-indexer.sh
建立和更新记忆关联网络

#### smart-retrieval.sh
智能检索（考虑强度+关联）

## Usage Examples

### Example 1: Smart Retrieval
```
用户问: "课程进度如何？"

传统检索: 加载所有包含"课程"的记忆 (10+条，可能有噪音)

智能检索 2.0:
1. 激活"课程开发"主题 (强度85)
2. 关联激活"Day进度" (强度80)
3. 提取最新3条相关记忆
4. 结果: 精准、无噪音、按重要性排序
```

### Example 2: Forgetting & Revival
```
Week 1: 用户频繁询问"Day 1课件"
        → "Day 1"记忆强度 +20 → 85

Week 4: 不再提及Day 1
        → 强度逐渐下降: 80→75→70→65...

Week 8: 强度降至35，自动归档
        → 从active/移到archive/2026-03/

Month 3: 用户突然问"还记得Day 1课件吗？"
        → 从archive检索到该记忆
        → "复活": 强度重置为50，移回active/
        → 回答: "记得，Day 1课件在..."
```

### Example 3: Associative Recall
```
用户问: "股东协议里那个退出机制"

联想激活:
[股东协议] → 关联 [退出机制] → 关联 [1元回购]

即使"1元回购"这个词不在问题中，
也能通过关联网络检索到相关记忆。
```

## Metrics

**优化目标:**
- 检索准确率: 从70% → 90%
- 检索速度: 快2倍（减少无效扫描）
- Token效率: 减少30%（只加载高权重记忆）
- 记忆保鲜度: 自动保留重要，遗忘过时

## Integration

**With Attention Manager:**
- 高优先级消息 → 增强相关记忆强度

**With Perception Monitor:**
- 检测到文件变化 → 更新关联记忆

**With Topic Memory:**
- Topic分类 + 强度权重 = 双重筛选

## Migration from 1.0

**自动迁移:**
1. 扫描现有memory/目录
2. 评估每条记忆的初始强度
3. 移动到新的active/目录结构
4. 建立基础关联网络
5. 开始每日巩固循环

**无需用户干预，平滑升级。**
