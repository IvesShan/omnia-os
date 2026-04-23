"""
OpenMythos Integration for Omnia

循环推理引擎 + 自适应停机 + 记忆压缩

核心组件：
- ACTPlanner: 自适应计算时间规划器
- RecurrentReasoning: 循环推理引擎
- MLACompression: 记忆压缩模块
- IntegrationBridge: Omnia 集成桥接
"""

from .act_planner import ACTPlanner, ComplexityLevel
from .recurrent_engine import RecurrentReasoning
from .mla_compression import MLACompression
from .integration import IntegrationBridge

__all__ = [
    'ACTPlanner',
    'ComplexityLevel', 
    'RecurrentReasoning',
    'MLACompression',
    'IntegrationBridge',
]

__version__ = '1.0.0'
