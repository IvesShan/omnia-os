# 记忆宫殿使用规范 v2.0

> 最后更新: 2026-05-29
> 状态: 正式生效

## 一、核心原则

**记忆不是数据库，是认知基础设施。**

每次对话开始时，我应该：
1. 查询与当前话题相关的记忆
2. 用记忆来个性化回答
3. 对话结束时，存储有价值的新信息

---

## 二、各层用途定义

### Facts（事实层）- 结构化知识

**用途**：存储稳定的、可查询的事实数据

**格式**：
```
category: 业务领域（business, product, user, company, technical）
key: 简洁的标识符
value: 结构化的信息（不是对话内容）
```

**示例**：
| category | key | value |
|----------|-----|-------|
| user | name | 原点 |
| company | UOSUN | 南京物熵科技有限公司，品牌UOSUN |
| business | 主推课程 | 线下30天，15800元包住宿 |
| product | 喵修匠定位 | 无人机维修SaaS平台 |
| technical | DJI_USB协议 | Interface 5=主通信, Interface 3=调试总线 |

**禁止存储**：
- ❌ 对话原文（"用户说..."、"我回答..."）
- ❌ 临时状态（"正在开发..."）
- ❌ 测试数据
- ❌ 带格式标记的内容（**粗体**、代码块）

---

### Relations（关系层）- 实体关系图谱

**用途**：表达实体之间的关系，支持图谱查询

**格式**：
```
subject --[predicate]--> object
```

**示例**：
```
UOSUN --[offers]--> OPC一人公司方案
原点 --[owns]--> 喵修匠
喵修匠 --[deployed_on]--> CloudBase
```

**好的谓词**：
- owns, created, operates, provides, offers
- is_a, part_of, depends_on, uses
- has_feature, deployed_on, integrates_with

**坏的谓词**：
- ❌ 正在进行、正在做（临时状态）
- ❌ 经营（过度泛化）
- ❌ 是（太模糊）

---

### Habits（习惯层）- 用户偏好

**用途**：记录用户的工作习惯和偏好

**示例**：
| 习惯 | 说明 |
|------|------|
| 偏好简洁回复 | 不喜欢废话 |
| 喜欢蓝色 | 设计偏好 |
| 用闲鱼获客 | 维修业务的主要获客渠道 |

---

### Timeline（时间线）- 事件记录

**用途**：记录重要事件，支持时间维度查询

**格式**：
```
event: 简洁描述
timestamp: ISO格式
context: 相关背景
```

---

## 三、查询时机

### 必须查询的场景

| 场景 | 查询什么 |
|------|----------|
| 用户问业务问题 | 查 business, company facts |
| 用户问技术问题 | 查 technical, dji facts |
| 用户问个人问题 | 查 user facts + habits |
| 用户问项目进展 | 查 project facts + timeline |
| 涉及UOSUN/物熵 | 查 company, solutions, contact facts |

### 不需要查询的场景

| 场景 | 原因 |
|------|------|
| 闲聊 | 无实际信息需求 |
| 简单计算 | 无记忆需求 |
| 通用知识问答 | 不涉及个人信息 |

---

## 四、存储规则

### 存储前检查清单

- [ ] 这是稳定的信息吗？（不是临时状态）
- [ ] 这是结构化的吗？（不是对话原文）
- [ ] 这是有价值的吗？（不是测试数据）
- [ ] 这个信息不会很快过时吗？
- [ ] 这个信息不重复吗？

### 存储分类指南

| 信息类型 | 存到哪里 |
|----------|----------|
| 用户身份信息 | facts (user category) |
| 公司/业务信息 | facts (company/business) |
| 产品信息 | facts (product) |
| 技术知识 | facts (technical) |
| 实体关系 | relations |
| 用户偏好 | habits |
| 重要事件 | timeline |

---

## 五、清理维护

### 定期检查

1. **每周**：检查是否有重复关系
2. **每月**：检查是否有过时的facts
3. **每季度**：检查是否有低价值记忆

### 清理脚本

```bash
python3 /home/shan/omnia-os/scripts/cleanup_memory.py
```

---

## 六、质量指标

| 指标 | 目标 |
|------|------|
| 重复关系数 | 0 |
| 垃圾facts数 | 0 |
| 查询命中率 | >80% |
| 存储信息准确率 | 100% |

---

*这份规范是记忆宫殿的"宪法"，所有存储和查询操作都应该遵循。*
