"""Omnia 统一配置"""
from pathlib import Path

# ============================================
# 数据库路径配置 - 统一使用 ~/.omnia/
# ============================================

# 统一使用 ~/.omnia/ 作为数据目录
OMNIA_HOME = Path.home() / ".omnia"

# ============================================
# 核心数据库 - 统一使用 memory_palace.db
# ============================================

# Memory Palace 数据库（包含所有记忆层）
MEMORY_PALACE_DB = OMNIA_HOME / "memory_palace.db"

# Neural Graph 数据库 - 与 Memory Palace 共用同一个数据库
# 图谱表 (neural_nodes, neural_edges) 存储在 memory_palace.db 中
NEURAL_GRAPH_DB = MEMORY_PALACE_DB  # 统一！

# ============================================
# 其他存储
# ============================================

# Vector Store 目录
VECTOR_STORE_DIR = OMNIA_HOME / "vector_store"

# Plan Store 数据库
PLAN_STORE_DB = OMNIA_HOME / "plans.db"

# Workflow 日志目录
WORKFLOW_LOG_DIR = OMNIA_HOME / "workflows"

# Scheduler 任务存储
SCHEDULER_TASKS_FILE = OMNIA_HOME / "scheduler_tasks.json"

# Collaboration 状态文件
COLLABORATION_STATE_FILE = OMNIA_HOME / "collaboration_state.json"

# Smart Pauser 状态文件
PAUSE_STATE_FILE = OMNIA_HOME / "pause_state.json"

# 确保目录存在
OMNIA_HOME.mkdir(parents=True, exist_ok=True)
VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
WORKFLOW_LOG_DIR.mkdir(parents=True, exist_ok=True)
