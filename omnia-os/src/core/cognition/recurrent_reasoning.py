"""
Recurrent Reasoning Module - 借鉴 OpenMythos 的循环推理架构

核心思想：
- 简单问题：1-2 次循环就停
- 复杂问题：可以循环 4-8 次
- 每次循环注入"思考深度"信号
- LTI 注入保证循环稳定性
- ACT 风格的自适应停机
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import numpy as np
from datetime import datetime


@dataclass
class ReasoningState:
    """推理状态 - 类似 OpenMythos 的 hidden state"""
    depth: int = 0
    confidence: float = 0.0
    output: str = ""  # 当前推理输出
    plan_steps: List[str] = field(default_factory=list)
    memory_queries: List[str] = field(default_factory=list)
    tool_calls: List[Dict] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningResult:
    """推理结果"""
    final_response: str
    depth_reached: int
    confidence: float
    plan: List[str]
    memories_used: List[str]
    tools_used: List[str]
    reasoning_trace: List[str]
    halted_early: bool = False


class LTIInjection:
    """
    Linear Time-Invariant Injection - 线性时不变注入
    
    借鉴 OpenMythos 的 LTI 机制，保证循环稳定性：
    
    h_{t+1} = A·h_t + B·e + step_output
    
    其中 A = exp(-exp(log_dt + log_A)) 保证谱半径 ρ(A) < 1
    """
    
    def __init__(self, decay_rate: float = 0.9, injection_strength: float = 0.1):
        self.decay_rate = decay_rate  # A 矩阵的衰减系数
        self.injection_strength = injection_strength  # B 矩阵的注入强度
    
    def update(self, h: ReasoningState, e: ReasoningState, step_output: ReasoningState) -> ReasoningState:
        """
        LTI 风格的状态更新
        
        h_{t+1} = A·h_t + B·e + step_output
        
        - A·h_t: 衰减旧状态（遗忘不重要的信息）
        - B·e: 注入原始输入（保持核心问题）
        - step_output: 新的推理结果
        """
        # 衰减旧状态
        h.decay(self.decay_rate)
        
        # 注入原始输入
        h.inject(e, self.injection_strength)
        
        # 添加新的推理结果
        h.merge(step_output)
        
        return h


class ACTHalting:
    """
    Adaptive Computation Time Halting - 自适应计算时间停机
    
    借鉴 OpenMythos 的 ACT 机制：
    - 让简单 token 早停，困难 token 多思考
    - 根据置信度决定是否停机
    """
    
    def __init__(
        self,
        halt_threshold: float = 0.85,
        min_loops: int = 1,
        max_loops: int = 8
    ):
        self.halt_threshold = halt_threshold
        self.min_loops = min_loops
        self.max_loops = max_loops
    
    def should_halt(self, state: ReasoningState) -> bool:
        """
        判断是否应该停机
        
        停机条件：
        1. 达到最小循环次数，且置信度超过阈值
        2. 达到最大循环次数（强制停机）
        """
        if state.depth < self.min_loops:
            return False
        
        if state.depth >= self.max_loops:
            return True
        
        return state.confidence >= self.halt_threshold
    
    def compute_halt_probability(self, state: ReasoningState) -> float:
        """
        计算停机概率（类似 OpenMythos 的 halt_prob）
        
        返回 0-1 之间的概率值
        """
        if state.depth < self.min_loops:
            return 0.0
        
        # Sigmoid 风格的概率曲线
        x = state.confidence - self.halt_threshold
        prob = 1 / (1 + np.exp(-10 * x))
        
        return float(prob)


class RecurrentReasoning:
    """
    循环推理引擎 - 借鉴 OpenMythos 的 Recurrent Block
    
    核心架构：
    
    Input (user message)
        ↓
    Prelude (encode input → e)
        ↓
    for t in range(max_loops):
        h = inject_loop_signal(h, t)      # 注入循环索引
        h = plan_step(h, t)               # 规划步骤
        h = query_memory(h, t)            # 查询记忆
        h = execute_tools(h, t)           # 执行工具
        h = adapt_persona(h, t)           # 适配人格
        h = lti_update(h, e, step_out)    # LTI 稳定更新
        if should_halt(h): break          # 自适应停机
        ↓
    Coda (generate response)
        ↓
    Output (response)
    """
    
    def __init__(
        self,
        max_loops: int = 8,
        halt_threshold: float = 0.85,
        decay_rate: float = 0.9,
        injection_strength: float = 0.1
    ):
        self.max_loops = max_loops
        self.lti = LTIInjection(decay_rate, injection_strength)
        self.act = ACTHalting(halt_threshold, min_loops=1, max_loops=max_loops)
    
    async def reason(
        self,
        user_input: str,
        context: Dict[str, Any],
        plan_func,
        memory_func,
        tool_func,
        persona_func
    ) -> ReasoningResult:
        """
        执行循环推理
        
        Args:
            user_input: 用户输入
            context: 上下文信息
            plan_func: 规划函数
            memory_func: 记忆查询函数
            tool_func: 工具执行函数
            persona_func: 人格适配函数
        
        Returns:
            ReasoningResult: 推理结果
        """
        # Prelude: 编码输入
        e = self._encode_input(user_input, context)
        h = ReasoningState(depth=0)
        
        reasoning_trace = []
        
        # Recurrent Block: 循环推理
        for t in range(self.max_loops):
            h.depth = t + 1
            
            # 注入循环索引信号
            h = self._inject_loop_signal(h, t)
            reasoning_trace.append(f"[深度 {h.depth}] 开始推理...")
            
            # 规划步骤
            plan_result = await plan_func(h, user_input, context)
            h.plan_steps.extend(plan_result.get("steps", []))
            h.confidence = max(h.confidence, plan_result.get("confidence", 0))
            reasoning_trace.append(f"[深度 {h.depth}] 规划: {plan_result.get('steps', [])}")
            
            # 查询记忆
            memory_result = await memory_func(h, user_input, context)
            h.memory_queries.extend(memory_result.get("queries", []))
            h.insights.extend(memory_result.get("insights", []))
            reasoning_trace.append(f"[深度 {h.depth}] 记忆: {len(memory_result.get('insights', []))} 条")
            
            # 执行工具
            tool_result = await tool_func(h, user_input, context)
            h.tool_calls.extend(tool_result.get("calls", []))
            reasoning_trace.append(f"[深度 {h.depth}] 工具: {len(tool_result.get('calls', []))} 次")
            
            # 适配人格
            persona_result = await persona_func(h, user_input, context)
            h.metadata["persona_style"] = persona_result.get("style", "balanced")
            
            # LTI 稳定更新
            step_output = ReasoningState(
                depth=h.depth,
                confidence=h.confidence,
                insights=h.insights.copy()
            )
            h = self.lti.update(h, e, step_output)
            
            # ACT 自适应停机
            if self.act.should_halt(h):
                reasoning_trace.append(f"[深度 {h.depth}] 停机 (置信度: {h.confidence:.2f})")
                break
        
        # Coda: 生成响应
        final_response = await self._generate_response(h, user_input, context)
        
        return ReasoningResult(
            final_response=final_response,
            depth_reached=h.depth,
            confidence=h.confidence,
            plan=h.plan_steps,
            memories_used=h.memory_queries,
            tools_used=[call.get("tool") for call in h.tool_calls],
            reasoning_trace=reasoning_trace,
            halted_early=h.depth < self.max_loops
        )
    
    def _encode_input(self, user_input: str, context: Dict) -> ReasoningState:
        """
        Prelude: 编码输入
        
        类似 OpenMythos 的 prelude_layers
        """
        return ReasoningState(
            depth=0,
            metadata={
                "input": user_input,
                "context_keys": list(context.keys()),
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def _inject_loop_signal(self, h: ReasoningState, t: int) -> ReasoningState:
        """
        注入循环索引信号
        
        类似 OpenMythos 的 loop_index_embed
        让模型知道当前在哪个深度
        """
        h.metadata["loop_index"] = t
        h.metadata["depth_signal"] = f"depth_{t}"
        return h
    
    async def _generate_response(
        self,
        h: ReasoningState,
        user_input: str,
        context: Dict
    ) -> str:
        """
        Coda: 生成最终响应
        
        类似 OpenMythos 的 coda_layers
        """
        # 根据深度调整响应风格
        depth = h.depth
        
        if depth <= 2:
            style = "quick"  # 快速响应
        elif depth <= 5:
            style = "balanced"  # 平衡响应
        else:
            style = "deep"  # 深度响应
        
        # 构建响应
        response_parts = []
        
        if h.insights:
            response_parts.append("基于我的思考：")
            for insight in h.insights[-3:]:  # 最多显示 3 条关键洞察
                response_parts.append(f"- {insight}")
        
        if h.tool_calls:
            response_parts.append(f"\n我使用了 {len(h.tool_calls)} 个工具来帮助你。")
        
        # 这里应该调用 LLM 生成最终响应
        # 暂时返回简化版本
        return "\n".join(response_parts) if response_parts else "我思考了这个问题。"


# 便捷函数
def create_reasoning_engine(
    max_loops: int = 8,
    halt_threshold: float = 0.85
) -> RecurrentReasoning:
    """创建推理引擎实例"""
    return RecurrentReasoning(
        max_loops=max_loops,
        halt_threshold=halt_threshold
    )
