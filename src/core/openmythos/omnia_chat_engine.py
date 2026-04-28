"""
from core.logging_config import get_logger

logger = get_logger(__name__)

Omnia Chat Engine with Recurrent Reasoning

集成循环推理引擎的聊天系统
"""

import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

from .act_planner import ACTPlanner, ComplexityLevel, TaskAnalysis
from .recurrent_engine import RecurrentReasoning, ReasoningResult
from ..providers.qianfan_client import QianfanClient


@dataclass
class ChatResponse:
    """聊天响应"""
    content: str
    complexity: str
    reasoning_depth: int
    confidence: float
    time_elapsed: float
    style: str  # quick, balanced, thorough


class OmniaChatEngine:
    """Omnia 聊天引擎"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "qianfan-code-latest",
        max_iterations: int = 8,
        confidence_threshold: float = 0.85
    ):
        """
        初始化聊天引擎
        
        Args:
            api_key: 千帆 API key
            model: 模型名称
            max_iterations: 最大推理迭代次数
            confidence_threshold: 置信度阈值
        """
        # 初始化千帆客户端
        self.llm_client = QianfanClient(api_key=api_key, model=model)
        
        # 初始化 ACT 规划器
        self.planner = ACTPlanner(max_depth=max_iterations)
        
        # 初始化循环推理引擎
        self.engine = RecurrentReasoning(
            model_call=self._model_call_wrapper,
            max_iterations=max_iterations,
            confidence_threshold=confidence_threshold
        )
    
    def _model_call_wrapper(self, prompt: str, context: Optional[Dict] = None) -> str:
        """模型调用包装器"""
        return self.llm_client.simple_call(prompt, context)
    
    def chat(
        self,
        message: str,
        context: Optional[Dict] = None,
        on_step: Optional[Callable] = None
    ) -> ChatResponse:
        """
        处理用户消息
        
        Args:
            message: 用户消息
            context: 上下文
            on_step: 推理步骤回调
            
        Returns:
            ChatResponse: 聊天响应
        """
        start_time = time.time()
        
        # 1. 分析任务复杂度
        analysis = self.planner.analyze(message, context)
        
        # 2. 根据复杂度决定推理深度
        if analysis.complexity == ComplexityLevel.SIMPLE:
            # 简单任务：直接回答
            response = self._quick_response(message)
            return ChatResponse(
                content=response,
                complexity="simple",
                reasoning_depth=1,
                confidence=0.9,
                time_elapsed=time.time() - start_time,
                style="quick"
            )
        
        elif analysis.complexity == ComplexityLevel.MEDIUM:
            # 中等任务：2-4 轮推理
            result = self.engine.reason(
                query=message,
                context=context,
                on_step=on_step
            )
            return ChatResponse(
                content=result.final_answer,
                complexity="medium",
                reasoning_depth=result.total_iterations,
                confidence=result.final_confidence,
                time_elapsed=result.time_elapsed,
                style="balanced"
            )
        
        else:
            # 复杂任务：完整推理
            result = self.engine.reason(
                query=message,
                context=context,
                on_step=on_step
            )
            return ChatResponse(
                content=result.final_answer,
                complexity="complex",
                reasoning_depth=result.total_iterations,
                confidence=result.final_confidence,
                time_elapsed=result.time_elapsed,
                style="thorough"
            )
    
    def _quick_response(self, message: str) -> str:
        """快速响应（简单任务）"""
        # 直接调用 LLM
        prompt = f"""你是一个友好、简洁的助手。请用简短、自然的方式回答用户的问题。

用户: {message}

请直接回答，不要过度展开。"""
        
        return self.llm_client.simple_call(prompt)


# 测试代码
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Omnia Chat Engine Test")
    logger.info("=" * 60)
    
    try:
        engine = OmniaChatEngine()
        logger.info("✅ Engine initialized")
        
        # 测试简单任务
        logger.info("\n📝 Test 1: Simple task")
        response = engine.chat("你好")
        print(f"   Complexity: {response.complexity}")
        print(f"   Reasoning depth: {response.reasoning_depth}")
        print(f"   Style: {response.style}")
        print(f"   Response: {response.content[:100]}...")
        print(f"   Time: {response.time_elapsed:.3f}s")
        
        # 测试中等任务
        logger.info("\n📝 Test 2: Medium task")
        response = engine.chat("帮我写一个 Python 脚本来计算斐波那契数列")
        print(f"   Complexity: {response.complexity}")
        print(f"   Reasoning depth: {response.reasoning_depth}")
        print(f"   Style: {response.style}")
        print(f"   Response: {response.content[:150]}...")
        print(f"   Time: {response.time_elapsed:.3f}s")
        
        # 测试复杂任务
        logger.info("\n📝 Test 3: Complex task")
        response = engine.chat("分析一下量子计算的基本原理，以及它在密码学领域的应用前景")
        print(f"   Complexity: {response.complexity}")
        print(f"   Reasoning depth: {response.reasoning_depth}")
        print(f"   Style: {response.style}")
        print(f"   Response: {response.content[:150]}...")
        print(f"   Time: {response.time_elapsed:.3f}s")
        
        logger.info("\n✅ All tests passed!")
        
    except (ValueError) as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
