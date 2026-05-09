"""
Omnia 依赖注入
管理共享实例的生命周期
"""

from functools import lru_cache
from typing import Optional

from fastapi import Depends

from src.omnia.config import settings


@lru_cache()
def get_memory_palace():
    """获取 MemoryPalace 实例（单例）"""
    try:
        from src.core.memory_palace.memory_palace import MemoryPalace
        return MemoryPalace()
    except Exception as e:
        print(f"[WARNING] Failed to load MemoryPalace: {e}")
        return None


@lru_cache()
def get_neural_graph():
    """获取 NeuralGraph 实例（单例）"""
    try:
        from src.core.neural_graph import NeuralGraph
        return NeuralGraph()
    except Exception as e:
        print(f"[WARNING] Failed to load NeuralGraph: {e}")
        return None


@lru_cache()
def get_llm_client():
    """获取 LLM 客户端实例（单例）"""
    from src.omnia.services.llm_client import LLMClient
    return LLMClient()


def get_current_provider() -> Optional[str]:
    """获取当前 Provider"""
    return settings.current_provider


def get_settings():
    """获取配置"""
    return settings


# 类型别名，方便使用
MemoryPalaceDep = Depends(get_memory_palace)
NeuralGraphDep = Depends(get_neural_graph)
LLMClientDep = Depends(get_llm_client)
SettingsDep = Depends(get_settings)
CurrentProviderDep = Depends(get_current_provider)
