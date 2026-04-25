"""
LLM Reasoning Adapter - 将 LLM 客户端集成到循环推理引擎

这个适配器提供了：
1. LLM 调用的推理函数
2. 与 chat_integration.py 的集成
3. 记忆系统集成
"""

from typing import Dict, Any, Optional, List
from .recurrent_reasoning import RecurrentReasoning, ReasoningResult, create_reasoning_engine
from ..llm_client import LLMClient, create_llm_client
from ..memory.memory_manager_v2 import MemoryManagerV2


class LLMReasoningAdapter:
    """
    LLM 推理适配器
    
    将 LLM 客户端集成到循环推理引擎中
    """
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        memory_manager: Optional[MemoryManagerV2] = None,
        max_loops: int = 8
    ):
        self.llm_client = llm_client or create_llm_client()
        self.memory_manager = memory_manager
        self.reasoning_engine = create_reasoning_engine(max_loops=max_loops)
    
    async def process(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理用户输入
        
        Args:
            user_input: 用户输入
            context: 上下文信息
            
        Returns:
            处理结果
        """
        context = context or {}
        
        # 定义推理函数
        async def plan_func(h, user_input, context):
            """规划函数"""
            return {
                "steps": ["分析用户意图", "查询相关记忆", "生成响应"],
                "confidence": 0.5
            }
        
        async def memory_func(h, user_input, context):
            """记忆查询函数"""
            insights = []
            
            if self.memory_manager:
                # 使用正确的方法名 retrieve_relevant
                results = self.memory_manager.retrieve_relevant(user_input, top_k=5, min_score=0.1)
                for memory, score in results:
                    insights.append(f"[相关度:{score:.2f}] {memory.content}")
            
            return {
                "queries": [user_input],
                "insights": insights
            }
        
        async def tool_func(h, user_input, context):
            """工具执行函数"""
            return {"calls": []}
        
        async def persona_func(h, user_input, context):
            """人格适配函数"""
            return {"style": "balanced"}
        
        # 执行推理
        result = await self.reasoning_engine.reason(
            user_input=user_input,
            context=context,
            plan_func=plan_func,
            memory_func=memory_func,
            tool_func=tool_func,
            persona_func=persona_func
        )
        
        # 生成最终响应
        final_response = await self._generate_final_response(result, user_input, context)
        
        return {
            "response": final_response,
            "depth": result.depth_reached,
            "confidence": result.confidence,
            "plan": result.plan,
            "memories_used": result.memories_used,
            "tools_used": result.tools_used
        }
    
    async def _generate_final_response(
        self,
        reasoning_result: ReasoningResult,
        user_input: str,
        context: Dict[str, Any]
    ) -> str:
        """
        生成最终响应
        
        调用 LLM 生成响应
        """
        # 构建系统提示
        system_prompt = self._build_system_prompt(reasoning_result)
        
        # 构建消息
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        # 添加记忆上下文
        if reasoning_result.memories_used:
            memory_context = "\n\n相关记忆：\n" + "\n".join(f"- {m}" for m in reasoning_result.memories_used[:5])
            messages.append({"role": "system", "content": memory_context})
        
        # 添加规划步骤
        if reasoning_result.plan:
            plan_context = "\n\n我的思考步骤：\n" + "\n".join(f"{i+1}. {step}" for i, step in enumerate(reasoning_result.plan[:3]))
            messages.append({"role": "system", "content": plan_context})
        
        try:
            # 调用 LLM (异步)
            response = await self.llm_client.chat(messages)
            
            choices = response.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "我思考了这个问题。")
            
            return "我思考了这个问题。"
            
        except Exception as e:
            print(f"⚠️ LLM 调用失败: {e}")
            return self._fallback_response(reasoning_result)
    
    def _build_system_prompt(self, reasoning_result: ReasoningResult) -> str:
        """构建系统提示"""
        base_prompt = """你是 Omnia，一个自主的 AI 操作系统。
你拥有持久的记忆、推理能力和工具使用能力。
请根据用户的输入和你的思考，给出有帮助的回应。"""
        
        if reasoning_result.depth_reached <= 2:
            return base_prompt + "\n\n请简洁地回答。"
        elif reasoning_result.depth_reached >= 5:
            return base_prompt + "\n\n请深入思考，给出详细的分析。"
        else:
            return base_prompt
    
    def _fallback_response(self, reasoning_result: ReasoningResult) -> str:
        """降级响应"""
        parts = []
        
        if reasoning_result.plan:
            parts.append("我的思考：")
            for step in reasoning_result.plan[:3]:
                parts.append(f"- {step}")
        
        if reasoning_result.memories_used:
            parts.append(f"\n参考了 {len(reasoning_result.memories_used)} 条记忆。")
        
        return "\n".join(parts) if parts else "我思考了这个问题。"


def create_llm_reasoning_adapter(
    llm_client: Optional[LLMClient] = None,
    memory_manager: Optional[MemoryManagerV2] = None,
    max_loops: int = 8
) -> LLMReasoningAdapter:
    """创建 LLM 推理适配器实例"""
    return LLMReasoningAdapter(
        llm_client=llm_client,
        memory_manager=memory_manager,
        max_loops=max_loops
    )
