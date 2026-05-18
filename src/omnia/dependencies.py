"""
依赖注入
提供全局实例的获取方法
"""
import sys
from pathlib import Path
from typing import Optional

# 添加 src 到 Python 路径
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from src.omnia.config import settings


# ========== Memory Palace ==========

_memory_palace = None


async def get_memory_palace():
    """获取 MemoryPalace 实例（单例）"""
    global _memory_palace
    
    if _memory_palace is None:
        from src.core.memory_palace.memory_palace import MemoryPalace
        
        _memory_palace = MemoryPalace(db_path=str(settings.memory_palace_db))
        _memory_palace.initialize()
    
    return _memory_palace


# ========== Neural Graph ==========

_neural_graph = None


async def get_neural_graph():
    """获取 NeuralGraph 实例（单例）"""
    global _neural_graph
    
    if _neural_graph is None:
        from src.core.neural_graph import NeuralGraph
        
        _neural_graph = NeuralGraph()
    
    return _neural_graph


# ========== LLM Client ==========

_llm_client = None


async def get_llm_client():
    """获取 LLM 客户端实例（单例）"""
    global _llm_client
    
    if _llm_client is None:
        from src.omnia.services.llm_client import LLMClient
        
        _llm_client = LLMClient()
    
    return _llm_client


# ========== Provider ==========

def get_current_provider() -> Optional[str]:
    """获取当前 Provider"""
    return settings.current_provider
