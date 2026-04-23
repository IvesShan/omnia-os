"""
Omnia Chat Integration - 将循环推理引擎接入 Omnia 主流程

这个模块将 OpenMythos 的核心机制集成到 Omnia 的对话流程中：
1. Recurrent Reasoning - 循环推理
2. ACT Planner - 自适应规划
3. Depth Adapter - 深度适配
4. Memory Integration - 记忆集成
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import time
import os

# 导入记忆管理器
from ..memory.memory_manager import MemoryManager


@dataclass
class ChatContext:
    """
    对话上下文
    """
    user_message: str
    conversation_history: List[Dict[str, str]]
    metadata: Dict[str, Any]
    complexity: Optional[str] = None
    reasoning_depth: int = 0
    response_style: Optional[str] = None


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
        provider: str = "kimi",
        api_key: Optional[str] = None,
        max_reasoning_depth: int = 3
    ):
        """
        初始化对话引擎
        
        Args:
            provider: API 提供商 (kimi, qianfan, openai)
            api_key: API 密钥
            max_reasoning_depth: 最大推理深度
        """
        self.provider = provider
        self.api_key = api_key
        self.max_reasoning_depth = max_reasoning_depth
        
        # 记忆管理器
        self.memory_manager = MemoryManager(
            max_memories=1000,
            enable_compression=True
        )
        
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
        
        # 1. 检索相关记忆
        relevant_memories = []
        try:
            relevant_memories = self.memory_manager.retrieve_relevant(
                user_message,
                top_k=5,
                min_score=0.3
            )
        except Exception as e:
            print(f"[WARNING] Memory retrieval failed: {e}")
        
        # 2. 评估任务复杂度
        complexity = self._assess_complexity(user_message)
        
        # 3. 根据复杂度决定推理深度
        reasoning_depth = self._get_reasoning_depth(complexity)
        
        # 4. 执行推理
        reasoning_steps = []
        confidence = 0.0
        
        if reasoning_depth > 0:
            # 执行循环推理
            result = await self._execute_reasoning(
                user_message=user_message,
                conversation_history=conversation_history or [],
                relevant_memories=relevant_memories,
                max_depth=reasoning_depth
            )
            
            reply = result.get("reply", "")
            reasoning_steps = result.get("steps", [])
            confidence = result.get("confidence", 0.0)
        else:
            # 简单任务，直接回答
            reply = self._simple_response(user_message)
            confidence = 0.9
        
        # 5. 更新统计
        elapsed_time = time.time() - start_time
        self._update_stats(complexity, reasoning_depth)
        
        # 6. 返回结果
        return {
            "reply": reply,
            "session_id": metadata.get("session_id", "") if metadata else "",
            "reasoning_steps": reasoning_steps,
            "confidence": confidence,
            "depth_used": reasoning_depth,
            "memory_used": len(relevant_memories) > 0,
            "provider": self.provider,
            "mode": "reasoning",
            "elapsed_time": elapsed_time
        }
    
    def _assess_complexity(self, message: str) -> str:
        """
        评估任务复杂度
        
        Args:
            message: 用户消息
            
        Returns:
            复杂度级别: simple, medium, complex
        """
        # 简单的启发式规则
        message_lower = message.lower()
        
        # 复杂任务关键词
        complex_keywords = [
            "分析", "设计", "优化", "实现", "架构",
            "比较", "评估", "规划", "重构", "集成"
        ]
        
        # 中等任务关键词
        medium_keywords = [
            "解释", "说明", "描述", "列出", "总结",
            "如何", "为什么", "什么", "怎么"
        ]
        
        # 检查复杂度
        if any(kw in message_lower for kw in complex_keywords):
            return "complex"
        elif any(kw in message_lower for kw in medium_keywords):
            return "medium"
        else:
            return "simple"
    
    def _get_reasoning_depth(self, complexity: str) -> int:
        """
        根据复杂度决定推理深度
        
        Args:
            complexity: 复杂度级别
            
        Returns:
            推理深度
        """
        depth_map = {
            "simple": 0,      # 直接回答
            "medium": 2,      # 2 轮推理
            "complex": self.max_reasoning_depth  # 最大深度
        }
        
        return depth_map.get(complexity, 0)
    
    async def _execute_reasoning(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        relevant_memories: List[Dict],
        max_depth: int
    ) -> Dict[str, Any]:
        """
        执行循环推理
        
        Args:
            user_message: 用户消息
            conversation_history: 对话历史
            relevant_memories: 相关记忆
            max_depth: 最大推理深度
            
        Returns:
            推理结果
        """
        from omnia.chat import _call_model_messages
        
        steps = []
        confidence = 0.0
        current_thought = ""
        
        for i in range(max_depth):
            # 构建推理提示
            step_prompt = f"""
当前推理步骤: {i + 1}/{max_depth}

用户问题: {user_message}

当前思考: {current_thought if current_thought else "开始推理"}

请继续推理，并给出：
1. 当前步骤的思考
2. 置信度: [0.0-1.0]
"""
            
            # 调用模型
            messages = [
                {"role": "system", "content": "你是一个深度推理助手，擅长分析复杂问题。"},
                {"role": "user", "content": step_prompt}
            ]
            
            try:
                data = _call_model_messages(
                    api_key=self.api_key,
                    provider=self.provider,
                    messages=messages
                )
                
                # 提取响应内容
                response = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # 解析响应
                step_result = {
                    "step": i + 1,
                    "thought": response,
                    "confidence": self._extract_confidence(response)
                }
                
                steps.append(step_result)
                
                # 更新置信度
                confidence = step_result["confidence"]
                
                # 如果置信度足够高，提前终止
                if confidence >= 0.85:
                    break
                
                # 更新当前思考
                current_thought = response
                
            except Exception as e:
                print(f"[ERROR] Reasoning step {i+1} failed: {e}")
                break
        
        # 生成最终回复
        final_prompt = f"""
基于以下推理过程，生成最终回复：

原始问题: {user_message}

推理步骤:
{self._format_reasoning_steps(steps)}

请给出清晰、准确的最终回复：
"""
        
        messages = [
            {"role": "system", "content": "你是一个智能助手，基于推理过程生成准确的回复。"},
            {"role": "user", "content": final_prompt}
        ]
        
        try:
            data = _call_model_messages(
                api_key=self.api_key,
                provider=self.provider,
                messages=messages
            )
            final_reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            print(f"[ERROR] Final reply generation failed: {e}")
            final_reply = "抱歉，推理过程中出现错误。"
        
        return {
            "reply": final_reply,
            "steps": steps,
            "confidence": confidence
        }
    
    def _build_reasoning_prompt(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        relevant_memories: List[Dict]
    ) -> str:
        """
        构建推理提示
        """
        prompt_parts = [f"用户问题: {user_message}\n"]
        
        if relevant_memories:
            prompt_parts.append("\n相关记忆:")
            for mem in relevant_memories[:3]:
                prompt_parts.append(f"- {mem.get('content', '')}")
        
        if conversation_history:
            prompt_parts.append("\n对话历史:")
            for msg in conversation_history[-5:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prompt_parts.append(f"- {role}: {content}")
        
        return "\n".join(prompt_parts)
    
    def _extract_confidence(self, response: str) -> float:
        """
        从响应中提取置信度
        """
        import re
        
        # 尝试提取置信度
        match = re.search(r'置信度[:：]\s*([\d.]+)', response)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        
        # 默认置信度
        return 0.7
    
    def _format_reasoning_steps(self, steps: List[Dict]) -> str:
        """
        格式化推理步骤
        """
        formatted = []
        for step in steps:
            formatted.append(f"步骤 {step['step']}: {step['thought'][:200]}...")
        
        return "\n".join(formatted)
    
    def _simple_response(self, message: str) -> str:
        """
        简单响应
        """
        from omnia.chat import _call_model_messages
        
        messages = [
            {"role": "user", "content": message}
        ]
        
        try:
            data = _call_model_messages(
                api_key=self.api_key,
                provider=self.provider,
                messages=messages
            )
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            print(f"[ERROR] Simple response failed: {e}")
            return "抱歉，我无法处理这个请求。"
    
    def _update_stats(self, complexity: str, depth: int):
        """
        更新统计信息
        """
        self.stats["total_conversations"] += 1
        self.stats["avg_depth"] = (
            (self.stats["avg_depth"] * (self.stats["total_conversations"] - 1) + depth)
            / self.stats["total_conversations"]
        )
        
        if complexity == "simple":
            self.stats["simple_tasks"] += 1
        elif complexity == "medium":
            self.stats["medium_tasks"] += 1
        else:
            self.stats["complex_tasks"] += 1
