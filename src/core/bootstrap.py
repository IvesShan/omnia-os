"""
from core.logging_config import get_logger

logger = get_logger(__name__)

Omnia Bootstrap - 启动时自动初始化核心功能

在 daemon 启动或首次对话时调用，确保所有核心功能自动启用。
"""
from core.config import OMNIA_HOME

from pathlib import Path
from typing import Optional

from .feature.flags import FeatureFlags as FF, FeatureCategory
from .config import MEMORY_PALACE_DB, NEURAL_GRAPH_DB, VECTOR_STORE_DIR


def bootstrap_omnia(workspace_root: Optional[Path] = None, lazy: bool = True) -> dict:
    """
    启动时初始化 Omnia 核心功能
    
    Args:
        workspace_root: 工作区根目录，用于确定配置文件位置
        lazy: 是否延迟初始化（不立即加载模块）
    
    Returns:
        初始化结果报告
    """
    report = {
        "status": "success",
        "enabled_features": [],
        "initialized_modules": [],
        "errors": [],
    }
    
    # 1. 加载 Feature Flags 配置
    if workspace_root:
        config_file = OMNIA_HOME / "feature_flags.json"
        FF.set_config_file(config_file)
    
    # 2. 确保所有 CORE 类别的功能启用
    core_flags = FF.get_by_category(FeatureCategory.CORE)
    for flag_name, is_enabled in core_flags.items():
        if not is_enabled:
            FF.enable(flag_name)
            report["enabled_features"].append(flag_name)
    
    # 3. 如果是延迟初始化，只检查模块可用性，不实际初始化
    if lazy:
        modules_to_check = [
            ("CORE_MEMORY_VECTOR_STORE", "VectorStore", ".neural_graph.vector_store"),
            ("CORE_NEURAL_GRAPH", "NeuralGraph", ".neural_graph.graph"),
            ("CORE_SELF_EVOLUTION", "SelfEvolutionEngine", ".skill_forge.auto_evolution"),
            ("CORE_WORKFLOW_ENGINE", "WorkflowEngine", ".orchestration.workflow_engine"),
            ("CORE_INTENT_ENGINE", "IntentEngine", ".cognition.intent_engine"),
        ]
        
        for flag_name, module_name, import_path in modules_to_check:
            if FF.is_enabled(flag_name):
                try:
                    __import__(f"core{import_path}", fromlist=[module_name])
                    report["initialized_modules"].append(f"{module_name} (lazy)")
                except ImportError as e:
                    report["errors"].append(f"{module_name}: {e}")
    else:
        # 完整初始化（可能较慢）
        try:
            if FF.is_enabled("CORE_MEMORY_VECTOR_STORE"):
                from .neural_graph import VectorStore
                vector_store = VectorStore(persist_dir=VECTOR_STORE_DIR)
                report["initialized_modules"].append("VectorStore")
        except Exception as e:
            report["errors"].append(f"VectorStore: {e}")
        
        try:
            if FF.is_enabled("CORE_NEURAL_GRAPH"):
                from .neural_graph import NeuralGraph
                graph = NeuralGraph(db_path=NEURAL_GRAPH_DB)
                report["initialized_modules"].append("NeuralGraph")
        except Exception as e:
            report["errors"].append(f"NeuralGraph: {e}")
        
        try:
            if FF.is_enabled("CORE_SELF_EVOLUTION"):
                from .skill_forge import SelfEvolutionEngine
                evolution_engine = SelfEvolutionEngine()
                report["initialized_modules"].append("SelfEvolutionEngine")
        except Exception as e:
            report["errors"].append(f"SelfEvolutionEngine: {e}")
        
        try:
            if FF.is_enabled("CORE_WORKFLOW_ENGINE"):
                from .orchestration import WorkflowEngine
                workflow_engine = WorkflowEngine()
                report["initialized_modules"].append("WorkflowEngine")
        except Exception as e:
            report["errors"].append(f"WorkflowEngine: {e}")
        
        try:
            if FF.is_enabled("CORE_INTENT_ENGINE"):
                from .cognition import IntentEngine
                intent_engine = IntentEngine()
                report["initialized_modules"].append("IntentEngine")
        except Exception as e:
            report["errors"].append(f"IntentEngine: {e}")
    
    return report


def get_bootstrap_status() -> dict:
    """获取当前启动状态"""
    return {
        "memory_palace_db": str(MEMORY_PALACE_DB),
        "neural_graph_db": str(NEURAL_GRAPH_DB),
        "vector_store_dir": str(VECTOR_STORE_DIR),
        "memory_palace_exists": MEMORY_PALACE_DB.exists(),
        "neural_graph_exists": NEURAL_GRAPH_DB.exists(),
        "vector_store_exists": VECTOR_STORE_DIR.exists(),
    }


def get_feature_status() -> dict:
    """获取 Feature Flags 状态"""
    return FF.get_all_flags()


def print_status():
    """打印启动状态"""
    status = get_bootstrap_status()
    logger.info("=" * 50)
    logger.info("Omnia Bootstrap Status")
    logger.info("=" * 50)
    for key, value in status.items():
        print(f"  {key}: {value}")
    logger.info("=" * 50)
