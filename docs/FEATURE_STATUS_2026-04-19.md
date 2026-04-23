# Omnia 核心功能自动启用配置

## 📋 更新摘要

**日期**: 2026-04-19  
**问题**: 核心功能（自进化、向量记忆、工作流引擎等）默认关闭，需要手动启用  
**解决**: 将核心功能分类为 `CORE`，默认启用；实验性功能保持默认关闭

---

## 🎯 功能分类

### ✅ 核心功能 (CORE) - 默认启用

| 功能名称 | 说明 |
|---------|------|
| `CORE_SELF_EVOLUTION` | 自进化引擎 - 自动学习新技能、优化现有能力 |
| `CORE_INTENT_ENGINE` | 意图识别引擎 - 理解用户意图并路由到正确的技能 |
| `CORE_MEMORY_VECTOR_STORE` | 向量记忆系统 - 语义搜索和相似度匹配 |
| `CORE_WORKFLOW_ENGINE` | 工作流引擎 - DAG 多步骤任务编排 |
| `CORE_NEURAL_GRAPH` | 神经图谱 - 实体关系图谱和上下文增强 |
| `CORE_AGENT_SWARM` | 代理集群 - 并行子代理执行 |

### 🧪 实验性功能 (EXPERIMENTAL) - 默认关闭

| 功能名称 | 说明 |
|---------|------|
| `EXPERIMENTAL_VERIFIED_EXECUTION` | 可验证执行 - 执行证明和回滚机制 |
| `EXPERIMENTAL_PROGRESSIVE_CAPABILITY` | 渐进式能力解锁 |
| `EXPERIMENTAL_PERSONA_CONTINUITY` | 跨会话人格连续性 |
| `EXPERIMENTAL_REFLECTION` | 反思模块 - 自动总结和改进 |

---

## 🚀 自动初始化机制

### 1. Bootstrap 模块 (`src/core/bootstrap.py`)

```python
from core import bootstrap_omnia, print_status

# 启动时自动初始化（延迟模式，不加载模型）
result = bootstrap_omnia(workspace_root, lazy=True)

# 查看功能状态
print_status()
```

### 2. Daemon 集成

Persona Daemon 启动时自动调用 `bootstrap_omnia()`，确保所有核心功能可用。

### 3. 延迟初始化

为了避免启动时加载大型模型（如 sentence-transformers），默认使用延迟初始化：
- 只检查模块是否可导入
- 不立即加载模型或创建实例
- 首次使用时才真正初始化

---

## 📊 当前状态

运行 `python -m core.bootstrap` 查看：

```
============================================================
🚀 Omnia 核心功能状态
============================================================

📦 核心功能 (CORE):
  ✅ CORE_SELF_EVOLUTION
  ✅ CORE_INTENT_ENGINE
  ✅ CORE_MEMORY_VECTOR_STORE
  ✅ CORE_WORKFLOW_ENGINE
  ✅ CORE_NEURAL_GRAPH
  ✅ CORE_AGENT_SWARM

🧪 实验性功能 (EXPERIMENTAL):
  ❌ EXPERIMENTAL_VERIFIED_EXECUTION
  ❌ EXPERIMENTAL_PROGRESSIVE_CAPABILITY
  ❌ EXPERIMENTAL_PERSONA_CONTINUITY
  ❌ EXPERIMENTAL_REFLECTION

💾 记忆功能 (MEMORY):
  ✅ MEMORY_AUTO_PERSIST
  ✅ MEMORY_FTS_SEARCH
  ✅ MEMORY_GRAPH_SYNC
  ✅ MEMORY_IDLE_INDEXING

⚡ 执行功能 (EXECUTION):
  ✅ EXECUTION_PARALLEL_TOOLS
  ✅ EXECUTION_AUTO_RETRY
  ✅ EXECUTION_TIMEOUT_GUARD
  ❌ EXECUTION_SANDBOX

============================================================
```

---

## 🔧 手动控制

### 启用/禁用功能

```python
from core.feature.flags import FeatureFlags as FF

# 启用实验性功能
FF.enable("EXPERIMENTAL_VERIFIED_EXECUTION")

# 禁用核心功能（不推荐）
FF.disable("CORE_SELF_EVOLUTION")

# 重置为默认值
FF.reset("CORE_SELF_EVOLUTION")

# 查看所有功能
FF.list_all()
```

### 配置持久化

配置保存在 `.omnia/feature_flags.json`，重启后保持。

---

## 📁 相关文件

- `src/core/feature/flags.py` - Feature Flags 定义和管理
- `src/core/bootstrap.py` - 启动初始化
- `src/core/neuro_center/persona_daemon.py` - Daemon 集成
- `.omnia/feature_flags.json` - 配置持久化

---

## ✅ 完成的工作

1. ✅ 将核心功能分类为 `CORE` 类别
2. ✅ 所有 `CORE` 功能默认启用
3. ✅ 创建 `bootstrap.py` 自动初始化模块
4. ✅ 集成到 Persona Daemon 启动流程
5. ✅ 实现延迟初始化避免启动卡顿
6. ✅ 保持实验性功能默认关闭

---

## 🎉 结果

现在 Omnia 启动时，所有核心功能自动启用，无需手动配置！
