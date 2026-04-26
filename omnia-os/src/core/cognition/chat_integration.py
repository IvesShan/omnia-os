"""
Omnia Chat Integration - 将循环推理引擎接入 Omnia 主流程

这个模块将 OpenMythos 的核心机制集成到 Omnia 的对话流程中：
1. Recurrent Reasoning - 循环推理
2. ACT Planner - 自适应规划
3. Depth Adapter - 深度适配
4. MLA Compressor - 记忆压缩
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import time

# 导入核心组件
from .recurrent_reasoning import RecurrentReasoning, ReasoningState
from .act_planner import ACTPlanner, TaskComplexity
from .depth_adapter import DepthAdapter, DepthStyle

# 导入记忆管理器
from ..memory.memory_adapter import MemoryAdapter as MemoryManagerV2


@dataclass
class ChatContext:
    """对话上下文"""
    user_message: str
    conversation_history: List[Dict[str, str]]
    metadata: Dict[str, Any]
    complexity: Optional[TaskComplexity] = None
    reasoning_depth: int = 0
    response_style: Optional[DepthStyle] = None


class OmniaChatEngine:
    """
    Omnia 对话引擎 - 集成循环推理
    
    核心流程：
    1. 用户消息 → 意图识别 + 复杂度评估
    2. 复杂度 → 决定推理深度
    3. 循环推理 → 生成响应
    4. 深度适配 → 调整响应风格
    """
    
    def __init__(
        self,
        max_loops: int = 8,
        halt_threshold: float = 0.85,
        enable_mla: bool = True
    ):
        # 核心组件
        self.reasoning_engine = RecurrentReasoning(
            max_loops=max_loops,
            halt_threshold=halt_threshold
        )
        
        self.planner = ACTPlanner()
        self.depth_adapter = DepthAdapter(max_depth=max_loops)
        
        # MLA 压缩器（可选）
        self.enable_mla = enable_mla
        if enable_mla:
            try:
                from ..memory.mla_compressor import MLACompressor
                self.compressor = MLACompressor(dim=768, kv_lora_rank=64)
            except ImportError:
                self.compressor = None
        else:
            self.compressor = None
        
        # 记忆管理器
        self.memory_manager = MemoryManagerV2()
        
        # 统计信息
        self.stats = {
            "total_conversations": 0,
            "avg_depth": 0.0,
            "simple_tasks": 0,
            "medium_tasks": 0,
            "complex_tasks": 0,
        }
    
    async def process_message(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理用户消息
        
        Args:
            user_message: 用户消息
            conversation_history: 对话历史
            metadata: 元数据
        
        Returns:
            处理结果，包含响应和元数据
        """
        start_time = time.time()
        
        # 1. 创建上下文
        # 1.1 检索相关记忆
        relevant_memories = self.memory_manager.retrieve_relevant(
            user_message,
            top_k=5,
            min_score=0.3
        )
        
        # 1.2 构建增强的对话历史
        enhanced_history = conversation_history or []
        
        # 如果有相关记忆，添加到历史中
        if relevant_memories:
            # 只添加最近的相关记忆（避免历史过长）
            for memory, score in relevant_memories[:3]:
                if score > 0.5:  # 只添加高相关度的记忆
                    enhanced_history.append({
                        "role": memory.role,
                        "content": memory.content,
                        "metadata": {"relevance": score}
                    })
        
        context = ChatContext(
            user_message=user_message,
            conversation_history=enhanced_history,
            metadata=metadata or {}
        )
        
        # 2. 评估任务复杂度
        context.complexity = self.planner.estimate_complexity(
            user_message,
            context.metadata
        )
        
        # 3. 根据复杂度决定推理深度
        max_depth = self._get_max_depth_for_complexity(context.complexity)
        
        # 4. 循环推理
        reasoning_result = await self._run_reasoning(context, max_depth)
        
        # 5. 深度适配
        context.reasoning_depth = reasoning_result["depth"]
        context.response_style = self.depth_adapter.get_style_for_depth(
            context.reasoning_depth
        )
        
        # 6. 生成最终响应
        response = self._generate_response(context, reasoning_result)
        
        # 7. 更新统计
        elapsed = time.time() - start_time
        self._update_stats(context, elapsed)
        
        # 7. 保存对话到记忆
        self.memory_manager.add_memory(
            content=user_message,
            role="user",
            metadata={"complexity": context.complexity.value if context.complexity else "unknown"}
        )
        
        self.memory_manager.add_memory(
            content=response,
            role="assistant",
            metadata={
                "reasoning_depth": context.reasoning_depth,
                "response_style": context.response_style.value if context.response_style else "unknown"
            }
        )
        
        return {
            "response": response,
            "metadata": {
                "complexity": context.complexity.value,
                "reasoning_depth": context.reasoning_depth,
                "response_style": context.response_style.value,
                "elapsed_time": elapsed,
                "reasoning_confidence": reasoning_result.get("confidence", 0.0),
            }
        }
    
    def _get_max_depth_for_complexity(self, complexity: TaskComplexity) -> int:
        """根据复杂度决定最大推理深度"""
        depth_map = {
            TaskComplexity.SIMPLE: 2,
            TaskComplexity.MEDIUM: 4,
            TaskComplexity.COMPLEX: 6,
            TaskComplexity.CRITICAL: 8,
        }
        return depth_map.get(complexity, 4)
    
    async def _run_reasoning(
        self,
        context: ChatContext,
        max_depth: int
    ) -> Dict[str, Any]:
        """
        运行循环推理
        
        这里是核心的循环推理逻辑：
        - 每轮推理都会评估置信度
        - 达到阈值或最大深度时停机
        """
        # 初始化状态
        state = ReasoningState(
            depth=0,
            confidence=0.0,
            metadata={
                "user_message": context.user_message,
                "history": context.conversation_history,
                "user_metadata": context.metadata
            }
        )
        
        reasoning_trace = []
        
        # 循环推理
        for loop in range(max_depth):
            # 推理步骤
            state = await self._reasoning_step(state, loop)
            
            reasoning_trace.append({
                "depth": state.depth,
                "confidence": state.confidence,
                "output": state.output[:100] if state.output else ""
            })
            
            # 检查是否应该停机
            if self.reasoning_engine.act.should_halt(state):
                break
        
        return {
            "depth": state.depth,
            "confidence": state.confidence,
            "output": state.output,
            "trace": reasoning_trace
        }
    
    async def _reasoning_step(
        self,
        state: ReasoningState,
        loop: int
    ) -> ReasoningState:
        """
        单步推理
        
        在实际应用中，这里应该调用 LLM 进行推理
        这里使用模拟逻辑进行演示
        """
        # 1. 构建提示词
        prompt = self._build_reasoning_prompt(state, loop)
        
        # 2. 调用 LLM API
        try:
            from ..llm_client import create_llm_client
            client = create_llm_client()
            
            # 直接 await 异步调用
            response = await client.chat([{
                "role": "user",
                "content": prompt
            }])
            
            # 3. 解析响应
            if "error" not in response:
                output = response["choices"][0]["message"]["content"]
                # 简单的置信度估算（基于响应长度和关键词）
                confidence = self._estimate_confidence(output, loop)
            else:
                # 如果 API 调用失败，回退到模拟
                output = f"推理步骤 {loop + 1}: {response.get('error', 'API 调用失败')}"
                confidence = 0.5 + loop * 0.1
        except Exception as e:
            # 如果出现异常，回退到模拟
            output = f"推理步骤 {loop + 1}: 推理异常 - {str(e)}"
            confidence = 0.5 + loop * 0.1
        
        # 注入循环索引信号（确保循环稳定性）
        state.metadata["loop_index"] = loop
        state.metadata["depth_signal"] = f"depth_{loop}"
        
        # 更新状态
        state.depth = loop + 1  # 更新推理深度
        state.confidence = confidence
        state.output = output
        
        return state
    
    def _build_reasoning_prompt(self, state: ReasoningState, loop: int) -> str:
        """
        构建推理提示词
        
        根据当前推理深度和历史结果构建提示词
        """
        user_message = state.metadata.get("user_message", "")
        
        # 基础提示词
        if loop == 0:
            prompt = f"""你是一个智能推理引擎。请分析以下用户请求，并给出你的推理结果。

用户请求：{user_message}

请分析：
1. 用户的核心意图是什么？
2. 需要什么信息或操作？
3. 你的置信度是多少？（0.0-1.0）

请简洁回答。"""
        else:
            # 后续推理，包含历史信息
            previous_outputs = state.output if state.output else ""
            prompt = f"""你是一个智能推理引擎。这是第 {loop + 1} 轮推理。

用户请求：{user_message}

上一轮推理结果：
{previous_outputs}

请继续深入分析，提供更详细的推理。
你的置信度是多少？（0.0-1.0）

请简洁回答。"""
        
        return prompt
    
    def _estimate_confidence(self, output: str, loop: int) -> float:
        """
        估算置信度
        
        基于响应内容和推理深度估算置信度
        """
        # 基础置信度（随深度增加）
        base_confidence = 0.5 + loop * 0.1
        
        # 根据响应长度调整
        if len(output) > 200:
            base_confidence += 0.1
        elif len(output) < 50:
            base_confidence -= 0.1
        
        # 根据关键词调整
        confidence_keywords = ["确定", "明确", "完成", "解决", "确认"]
        if any(kw in output for kw in confidence_keywords):
            base_confidence += 0.15
        
        # 确保在 0-1 范围内
        return min(max(base_confidence, 0.0), 1.0)
    
    def _generate_response(
        self,
        context: ChatContext,
        reasoning_result: Dict[str, Any]
    ) -> str:
        """
        生成最终响应
        
        根据推理深度和风格适配响应
        """
        base_response = reasoning_result.get("output", "我理解了您的问题。")
        
        # 使用深度适配器调整响应风格
        adapted_response = self.depth_adapter.adapt_response(
            base_response,
            depth=context.reasoning_depth,
            context={
                "user_message": context.user_message,
                "complexity": context.complexity.value
            }
        )
        
        return adapted_response
    
    def _update_stats(self, context: ChatContext, elapsed: float):
        """更新统计信息"""
        self.stats["total_conversations"] += 1
        
        # 更新平均深度
        total = self.stats["total_conversations"]
        current_avg = self.stats["avg_depth"]
        self.stats["avg_depth"] = (
            (current_avg * (total - 1) + context.reasoning_depth) / total
        )
        
        # 更新复杂度统计
        if context.complexity == TaskComplexity.SIMPLE:
            self.stats["simple_tasks"] += 1
        elif context.complexity == TaskComplexity.MEDIUM:
            self.stats["medium_tasks"] += 1
        elif context.complexity == TaskComplexity.COMPLEX:
            self.stats["complex_tasks"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()


# 便捷函数
def create_chat_engine(
    max_loops: int = 8,
    halt_threshold: float = 0.85,
    enable_mla: bool = True
) -> OmniaChatEngine:
    """创建对话引擎实例"""
    return OmniaChatEngine(
        max_loops=max_loops,
        halt_threshold=halt_threshold,
        enable_mla=enable_mla
    )


# 示例用法
if __name__ == "__main__":
    # 创建引擎
    engine = create_chat_engine(max_loops=8, halt_threshold=0.85)
    
    # 测试对话
    test_messages = [
        "今天天气怎么样？",
        "帮我写一个 Python 脚本",
        "分析项目架构并给出重构方案",
    ]
    
    print("=" * 60)
    print("Omnia Chat Engine 测试")
    print("=" * 60)
    
    for msg in test_messages:
        print(f"\n用户: {msg}")
        result = engine.process_message(msg)
        print(f"响应: {result['response']}")
        print(f"元数据: {result['metadata']}")
    
    print("\n" + "=" * 60)
    print("统计信息:")
    print(engine.get_stats())
    print("=" * 60)
