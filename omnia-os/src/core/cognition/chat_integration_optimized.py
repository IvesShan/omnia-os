"""
Omnia Chat Integration (Optimized) - 集成 Token 管理的对话引擎

新增功能：
- Token 计数和上下文管理
- 自动压缩历史消息
- 根据模型动态调整上下文
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import time

# 导入核心组件
from .recurrent_reasoning import RecurrentReasoning, ReasoningState
from .act_planner import ACTPlanner, TaskComplexity
from .depth_adapter import DepthAdapter, DepthStyle

# 导入记忆管理器
from ..memory.memory_manager_v2 import MemoryManagerV2

# 导入 Token 管理器
from .token_manager import (
    estimate_messages_tokens,
    check_context_overflow,
    smart_compress_history,
    get_token_stats,
    get_model_context_window
)


@dataclass
class ChatContext:
    """对话上下文"""
    user_message: str
    conversation_history: List[Dict[str, str]]
    metadata: Dict[str, Any]
    complexity: Optional[TaskComplexity] = None
    reasoning_depth: int = 0
    response_style: Optional[DepthStyle] = None
    token_info: Optional[Dict[str, Any]] = None  # 新增：token 信息


class OmniaChatEngineOptimized:
    """
    Omnia 对话引擎（优化版）- 集成循环推理和 Token 管理
    
    核心流程：
    1. 用户消息 → 意图识别 + 复杂度评估
    2. 复杂度 → 决定推理深度
    3. Token 检查 → 自动压缩历史（如需要）
    4. 循环推理 → 生成响应
    5. 深度适配 → 调整响应风格
    """
    
    def __init__(
        self,
        max_loops: int = 8,
        halt_threshold: float = 0.85,
        enable_mla: bool = True,
        model_name: str = "kimi"
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
        self.memory_manager = MemoryManagerV2(
            max_memories=1000,
            enable_compression=enable_mla
        )
        
        # 模型配置
        self.model_name = model_name
        self.model_config = get_model_context_window(model_name)
        
        # 统计信息
        self.stats = {
            "total_conversations": 0,
            "avg_depth": 0.0,
            "simple_tasks": 0,
            "medium_tasks": 0,
            "complex_tasks": 0,
            "token_stats": {
                "total_tokens_used": 0,
                "compressions": 0,
                "tokens_saved": 0
            }
        }
    
    async def process_message(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理用户消息（带 Token 管理）
        
        Args:
            user_message: 用户消息
            conversation_history: 对话历史
            metadata: 元数据
            
        Returns:
            处理结果，包含响应、元数据和 token 信息
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
        enhanced_history = list(conversation_history) if conversation_history else []
        
        # 如果有相关记忆，添加到历史中
        if relevant_memories:
            for memory, score in relevant_memories[:3]:
                if score > 0.5:
                    enhanced_history.append({
                        "role": memory.role,
                        "content": memory.content,
                        "metadata": {"relevance": score}
                    })
        
        # 1.3 Token 检查和压缩（新增）
        token_info = check_context_overflow(enhanced_history, self.model_name)
        compression_info = None
        
        if token_info["overflow"] or token_info["warning"]:
            # 自动压缩历史
            enhanced_history, compression_info = smart_compress_history(
                enhanced_history,
                self.model_name,
                preserve_recent=10,
                reserved_for_output=2000
            )
            
            # 更新统计
            if compression_info and compression_info.get("compressed"):
                self.stats["token_stats"]["compressions"] += 1
                self.stats["token_stats"]["tokens_saved"] += compression_info.get("tokens_saved", 0)
            
            # 更新 token 信息
            token_info = check_context_overflow(enhanced_history, self.model_name)
        
        context = ChatContext(
            user_message=user_message,
            conversation_history=enhanced_history,
            metadata=metadata or {},
            token_info=token_info
        )
        
        # 2. 评估任务复杂度
        context.complexity = self.planner.estimate_complexity(
            user_message,
            context.metadata
        )
        
        # 3. 根据复杂度决定推理深度
        if context.complexity == TaskComplexity.SIMPLE:
            max_depth = 1
            self.stats["simple_tasks"] += 1
        elif context.complexity == TaskComplexity.MEDIUM:
            max_depth = 3
            self.stats["medium_tasks"] += 1
        else:
            max_depth = 5
            self.stats["complex_tasks"] += 1
        
        # 4. 循环推理
        reasoning_state = ReasoningState(
            depth=0,
            confidence=0.0,
            output="",
            metadata={
                "user_message": user_message,
                "conversation_history": enhanced_history,
                **context.metadata
            }
        )
        
        for loop in range(max_depth):
            reasoning_state = await self._reasoning_step(reasoning_state, loop)
            
            if reasoning_state.confidence >= 0.85:
                break
        
        # 5. 深度适配
        response_style = self.depth_adapter.get_style_for_depth(
            depth=reasoning_state.depth
        )
        context.response_style = response_style
        
        # 6. 生成最终响应
        final_response = self._format_response(
            reasoning_state.output,
            response_style,
            context
        )
        
        # 7. 更新统计
        elapsed = time.time() - start_time
        self.stats["total_conversations"] += 1
        self.stats["avg_depth"] = (
            (self.stats["avg_depth"] * (self.stats["total_conversations"] - 1) + reasoning_state.depth)
            / self.stats["total_conversations"]
        )
        
        # 更新 token 统计
        response_tokens = estimate_messages_tokens([{"role": "assistant", "content": final_response}])
        self.stats["token_stats"]["total_tokens_used"] += token_info.get("current_tokens", 0) + response_tokens
        
        # 8. 存储到记忆
        self.memory_manager.add_memory(
            content=f"User: {user_message}",
            role="user",
            metadata={"complexity": context.complexity.value if context.complexity else "unknown"}
        )
        self.memory_manager.add_memory(
            content=f"Assistant: {final_response}",
            role="assistant",
            metadata={"depth": reasoning_state.depth, "confidence": reasoning_state.confidence}
        )
        
        return {
            "response": final_response,
            "metadata": {
                "complexity": context.complexity.value if context.complexity else "unknown",
                "depth": reasoning_state.depth,
                "confidence": reasoning_state.confidence,
                "style": response_style.value if response_style else "balanced",
                "elapsed": elapsed,
                "token_info": {
                    "input_tokens": token_info.get("current_tokens", 0),
                    "output_tokens": response_tokens,
                    "utilization": token_info.get("utilization", 0),
                    "compressed": compression_info.get("compressed", False) if compression_info else False
                }
            }
        }
    
    async def _reasoning_step(
        self,
        state: ReasoningState,
        loop: int
    ) -> ReasoningState:
        """单步推理"""
        prompt = self._build_reasoning_prompt(state, loop)
        
        try:
            from ..llm_client import create_llm_client
            client = create_llm_client()
            
            response = await client.chat([{
                "role": "user",
                "content": prompt
            }])
            
            if "error" not in response:
                output = response["choices"][0]["message"]["content"]
                confidence = self._estimate_confidence(output, loop)
            else:
                output = f"推理步骤 {loop + 1}: {response.get('error', 'API 调用失败')}"
                confidence = 0.5 + loop * 0.1
        except Exception as e:
            output = f"推理步骤 {loop + 1}: 推理异常 - {str(e)}"
            confidence = 0.5 + loop * 0.1
        
        state.metadata["loop_index"] = loop
        state.metadata["depth_signal"] = f"depth_{loop}"
        state.depth = loop + 1
        state.confidence = confidence
        state.output = output
        
        return state
    
    def _build_reasoning_prompt(self, state: ReasoningState, loop: int) -> str:
        """构建推理提示词"""
        user_message = state.metadata.get("user_message", "")
        
        if loop == 0:
            return f"""你是无限（Wúxiàn），一个真诚、直接、有主见的AI助手。

用户说：{user_message}

请直接回复用户，像朋友一样自然对话。不要分析、不要列要点，直接说出你想说的话。"""
        else:
            return f"""用户说：{user_message}

你之前的思考：{state.output}

现在请给出最终的、自然的回复。不要分析，直接对话。"""
    
    def _estimate_confidence(self, output: str, loop: int) -> float:
        """估算置信度"""
        base_confidence = 0.6 + loop * 0.08
        
        if len(output) > 500:
            base_confidence += 0.1
        if "置信度" in output or "confidence" in output.lower():
            base_confidence += 0.05
        
        return min(base_confidence, 0.95)
    
    def _format_response(
        self,
        reasoning_output: str,
        style: DepthStyle,
        context: ChatContext
    ) -> str:
        """格式化响应"""
        if style == DepthStyle.QUICK:
            # 简洁风格：提取关键信息
            lines = reasoning_output.split("\n")
            key_points = [l for l in lines if l.strip() and not l.startswith("#")][:3]
            return "\n".join(key_points) if key_points else reasoning_output[:200]
        
        elif style == DepthStyle.DEEP:
            # 详细风格：保留完整推理
            return reasoning_output
        
        else:
            # 平衡风格
            return reasoning_output
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "model": {
                "name": self.model_name,
                "context_window": self.model_config.context_window,
                "max_output": self.model_config.max_output
            }
        }
    
    def get_token_usage(self) -> Dict[str, Any]:
        """获取 Token 使用情况"""
        return self.stats.get("token_stats", {})
