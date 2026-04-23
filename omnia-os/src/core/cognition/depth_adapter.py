"""
Depth Adapter - 深度适配器

借鉴 OpenMythos 的 LoRA Adapter 思想：
- 不同循环深度使用不同的"思考模式"
- 类似 LoRA 的低秩适配，但用于人格/策略
- 浅层：快速响应，简洁直接
- 中层：平衡模式，详细分析
- 深层：深度思考，全面考虑
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class DepthStyle(Enum):
    """深度风格"""
    QUICK = "quick"          # 快速模式：简洁、直接、高效
    BALANCED = "balanced"    # 平衡模式：适中、详细、友好
    DEEP = "deep"            # 深度模式：全面、细致、多角度


@dataclass
class AdapterWeights:
    """
    适配器权重 - 类似 LoRA 的 A、B 矩阵
    
    但这里不是数值矩阵，而是风格参数：
    - verbosity: 详细程度 (0-1)
    - formality: 正式程度 (0-1)
    - creativity: 创造性 (0-1)
    - thoroughness: 周全性 (0-1)
    """
    verbosity: float = 0.5
    formality: float = 0.5
    creativity: float = 0.5
    thoroughness: float = 0.5
    
    def get_style_params(self) -> Dict[str, float]:
        """获取风格参数"""
        return {
            "verbosity": self.verbosity,
            "formality": self.formality,
            "creativity": self.creativity,
            "thoroughness": self.thoroughness
        }


class DepthAdapter:
    """
    深度适配器
    
    根据推理深度调整响应风格，借鉴 OpenMythos 的 LoRA Adapter：
    
    - 深度 0-2: 快速响应，简洁直接
    - 深度 3-5: 中等深度，详细分析
    - 深度 6-8: 深度思考，全面考虑
    
    每个"深度区间"有独立的适配参数，类似 LoRA 的低秩适配。
    """
    
    def __init__(self, max_depth: int = 8):
        self.max_depth = max_depth
        
        # 为每个深度区间创建适配器权重
        # 类似 OpenMythos 的 depth-specific LoRA weights
        self.depth_adapters = {
            DepthStyle.QUICK: AdapterWeights(
                verbosity=0.3,      # 简洁
                formality=0.4,      # 随意
                creativity=0.6,     # 有创意
                thoroughness=0.3    # 不追求周全
            ),
            DepthStyle.BALANCED: AdapterWeights(
                verbosity=0.6,      # 适中
                formality=0.5,      # 平衡
                creativity=0.5,     # 平衡
                thoroughness=0.6    # 较周全
            ),
            DepthStyle.DEEP: AdapterWeights(
                verbosity=0.8,      # 详细
                formality=0.6,      # 稍正式
                creativity=0.4,     # 稳重
                thoroughness=0.9    # 非常周全
            )
        }
    
    def get_style_for_depth(self, depth: int) -> DepthStyle:
        """
        根据深度获取风格
        
        Args:
            depth: 推理深度 (0-max_depth)
        
        Returns:
            DepthStyle: 对应的风格
        """
        if depth <= 2:
            return DepthStyle.QUICK
        elif depth <= 5:
            return DepthStyle.BALANCED
        else:
            return DepthStyle.DEEP
    
    def get_adapter_weights(self, depth: int) -> AdapterWeights:
        """
        获取指定深度的适配器权重
        
        类似 LoRA 的 get_weights_for_depth(depth)
        """
        style = self.get_style_for_depth(depth)
        return self.depth_adapters[style]
    
    def adapt_response(
        self,
        base_response: str,
        depth: int,
        context: Optional[Dict] = None
    ) -> str:
        """
        根据深度调整响应风格
        
        Args:
            base_response: 基础响应
            depth: 当前推理深度
            context: 上下文信息
        
        Returns:
            str: 调整后的响应
        """
        weights = self.get_adapter_weights(depth)
        style = self.get_style_for_depth(depth)
        
        if style == DepthStyle.QUICK:
            return self._adapt_quick(base_response, weights, context)
        elif style == DepthStyle.BALANCED:
            return self._adapt_balanced(base_response, weights, context)
        else:
            return self._adapt_deep(base_response, weights, context)
    
    def _adapt_quick(
        self,
        response: str,
        weights: AdapterWeights,
        context: Optional[Dict]
    ) -> str:
        """
        快速模式适配
        
        特点：
        - 简洁直接
        - 重点突出
        - 快速响应
        """
        # 如果响应过长，提取关键信息
        if len(response) > 200:
            # 提取第一句和最后一句
            sentences = response.split("。")
            if len(sentences) > 2:
                key_points = [sentences[0], sentences[-2]]
                response = "。".join(key_points) + "。"
        
        # 添加快速模式标记（可选）
        # response = f"⚡ {response}"
        
        return response
    
    def _adapt_balanced(
        self,
        response: str,
        weights: AdapterWeights,
        context: Optional[Dict]
    ) -> str:
        """
        平衡模式适配
        
        特点：
        - 详细适中
        - 结构清晰
        - 友好自然
        """
        # 保持原样，但可以添加结构化元素
        if context and "needs_structure" in context:
            # 添加结构化标记
            if not response.startswith("##"):
                response = f"### 分析\n\n{response}"
        
        return response
    
    def _adapt_deep(
        self,
        response: str,
        weights: AdapterWeights,
        context: Optional[Dict]
    ) -> str:
        """
        深度模式适配
        
        特点：
        - 全面细致
        - 多角度分析
        - 深度思考
        """
        # 添加深度分析标记
        prefix = "### 深度分析\n\n"
        
        # 如果有上下文，添加多角度分析
        if context and "multiple_angles" in context:
            angles = context.get("angles", [])
            if angles:
                angle_analysis = "\n\n#### 多角度分析\n"
                for angle in angles:
                    angle_analysis += f"\n- **{angle}**: ..."
                response = prefix + response + angle_analysis
            else:
                response = prefix + response
        else:
            response = prefix + response
        
        return response
    
    def get_system_prompt_modifier(self, depth: int) -> str:
        """
        获取系统提示词修饰符
        
        根据深度调整 Persona 的系统提示词
        """
        style = self.get_style_for_depth(depth)
        
        modifiers = {
            DepthStyle.QUICK: """
响应风格：简洁、直接、高效
- 优先给出核心答案
- 避免冗长解释
- 使用简短句子
- 重点突出
""",
            DepthStyle.BALANCED: """
响应风格：详细、友好、平衡
- 给出完整答案
- 适当解释原因
- 结构清晰
- 友好自然
""",
            DepthStyle.DEEP: """
响应风格：全面、细致、深度
- 多角度分析问题
- 考虑各种可能性
- 提供详细推理过程
- 深入探讨
"""
        }
        
        return modifiers.get(style, "")
    
    def get_reasoning_budget(self, depth: int) -> Dict[str, int]:
        """
        获取推理预算
        
        根据深度分配不同的"思考资源"
        """
        style = self.get_style_for_depth(depth)
        
        budgets = {
            DepthStyle.QUICK: {
                "max_tokens": 500,
                "max_tools": 2,
                "max_memories": 3
            },
            DepthStyle.BALANCED: {
                "max_tokens": 1000,
                "max_tools": 5,
                "max_memories": 10
            },
            DepthStyle.DEEP: {
                "max_tokens": 2000,
                "max_tools": 10,
                "max_memories": 20
            }
        }
        
        return budgets.get(style, budgets[DepthStyle.BALANCED])


# 便捷函数
def create_depth_adapter(max_depth: int = 8) -> DepthAdapter:
    """创建深度适配器实例"""
    return DepthAdapter(max_depth=max_depth)
