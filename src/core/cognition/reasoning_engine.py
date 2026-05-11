"""
Reasoning Engine - 推理引擎
提供逻辑推理和决策支持能力
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class ReasoningType(Enum):
    """推理类型"""
    DEDUCTIVE = "deductive"  # 演绎推理
    INDUCTIVE = "inductive"  # 归纳推理
    ABDUCTIVE = "abductive"  # 溯因推理
    ANALOGICAL = "analogical"  # 类比推理
    CAUSAL = "causal"  # 因果推理


class ReasoningStatus(Enum):
    """推理状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Premise:
    """前提"""
    id: str
    content: str
    confidence: float = 1.0  # 0.0 - 1.0
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conclusion:
    """结论"""
    id: str
    content: str
    confidence: float = 0.0
    reasoning_type: ReasoningType = ReasoningType.DEDUCTIVE
    premises: List[str] = field(default_factory=list)  # premise IDs
    steps: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningChain:
    """推理链"""
    id: str
    query: str
    reasoning_type: ReasoningType
    status: ReasoningStatus = ReasoningStatus.PENDING
    premises: List[Premise] = field(default_factory=list)
    conclusions: List[Conclusion] = field(default_factory=list)
    final_conclusion: Optional[Conclusion] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReasoningEngine:
    """推理引擎"""
    
    def __init__(self, llm_client=None, memory_client=None):
        self.llm_client = llm_client
        self.memory_client = memory_client
        self.chains: Dict[str, ReasoningChain] = {}
        self.max_premises = 10
        self.min_confidence = 0.3
    
    async def reason(
        self,
        query: str,
        reasoning_type: ReasoningType = ReasoningType.DEDUCTIVE,
        context: Optional[Dict[str, Any]] = None
    ) -> ReasoningChain:
        """
        执行推理
        
        Args:
            query: 推理问题
            reasoning_type: 推理类型
            context: 上下文信息
        
        Returns:
            推理链
        """
        chain_id = f"reason_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        chain = ReasoningChain(
            id=chain_id,
            query=query,
            reasoning_type=reasoning_type,
            metadata=context or {}
        )
        
        self.chains[chain_id] = chain
        
        try:
            chain.status = ReasoningStatus.IN_PROGRESS
            
            # 1. 收集前提
            premises = await self._gather_premises(query, context)
            chain.premises = premises
            
            # 2. 执行推理
            conclusion = await self._execute_reasoning(chain)
            
            if conclusion:
                chain.conclusions.append(conclusion)
                chain.final_conclusion = conclusion
                chain.status = ReasoningStatus.COMPLETED
            else:
                chain.status = ReasoningStatus.FAILED
            
            chain.completed_at = datetime.now()
            
        except Exception as e:
            logger.error(f"推理失败: {e}")
            chain.status = ReasoningStatus.FAILED
            chain.metadata["error"] = str(e)
        
        return chain
    
    async def _gather_premises(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Premise]:
        """收集前提"""
        premises = []
        
        # 从上下文中提取前提
        if context and "facts" in context:
            for i, fact in enumerate(context["facts"][:self.max_premises]):
                premise = Premise(
                    id=f"premise_{i}",
                    content=fact.get("content", ""),
                    confidence=fact.get("confidence", 1.0),
                    source=fact.get("source", "context")
                )
                premises.append(premise)
        
        # 从记忆中搜索相关前提
        if self.memory_client:
            try:
                memories = await self._search_relevant_memories(query)
                for i, memory in enumerate(memories[:5]):
                    premise = Premise(
                        id=f"memory_{i}",
                        content=memory.get("content", ""),
                        confidence=memory.get("confidence", 0.8),
                        source="memory"
                    )
                    premises.append(premise)
            except Exception as e:
                logger.warning(f"搜索记忆失败: {e}")
        
        # 使用 LLM 生成前提
        if self.llm_client and len(premises) < 3:
            llm_premises = await self._generate_premises_with_llm(query)
            premises.extend(llm_premises)
        
        return premises
    
    async def _search_relevant_memories(self, query: str) -> List[Dict[str, Any]]:
        """搜索相关记忆"""
        # 简化实现，实际应调用 memory_client
        return []
    
    async def _generate_premises_with_llm(self, query: str) -> List[Premise]:
        """使用 LLM 生成前提"""
        if not self.llm_client:
            return []
        
        prompt = f"""分析以下问题，列出3-5个相关的前提条件或已知事实：

问题：{query}

请以JSON格式返回前提列表：
{{"premises": ["前提1", "前提2", ...]}}
"""
        
        try:
            # 调用 LLM
            response = await self._call_llm(prompt)
            result = json.loads(response)
            
            premises = []
            for i, content in enumerate(result.get("premises", [])):
                premise = Premise(
                    id=f"llm_{i}",
                    content=content,
                    confidence=0.7,
                    source="llm_generated"
                )
                premises.append(premise)
            
            return premises
        except Exception as e:
            logger.error(f"LLM 生成前提失败: {e}")
            return []
    
    async def _execute_reasoning(self, chain: ReasoningChain) -> Optional[Conclusion]:
        """执行推理过程"""
        if not self.llm_client:
            return None
        
        # 构建推理提示
        prompt = self._build_reasoning_prompt(chain)
        
        try:
            response = await self._call_llm(prompt)
            conclusion = self._parse_conclusion(response, chain)
            return conclusion
        except Exception as e:
            logger.error(f"推理执行失败: {e}")
            return None
    
    def _build_reasoning_prompt(self, chain: ReasoningChain) -> str:
        """构建推理提示"""
        reasoning_type_desc = {
            ReasoningType.DEDUCTIVE: "演绎推理：从一般到特殊，根据已知规则推导结论",
            ReasoningType.INDUCTIVE: "归纳推理：从特殊到一般，根据观察总结规律",
            ReasoningType.ABDUCTIVE: "溯因推理：根据观察推断最可能的解释",
            ReasoningType.ANALOGICAL: "类比推理：根据相似性推断结论",
            ReasoningType.CAUSAL: "因果推理：分析因果关系得出结论"
        }
        
        premises_text = "\n".join([
            f"{i+1}. {p.content} (置信度: {p.confidence:.2f})"
            for i, p in enumerate(chain.premises)
        ])
        
        prompt = f"""请使用{reasoning_type_desc[chain.reasoning_type]}来回答以下问题。

问题：{chain.query}

已知前提：
{premises_text}

请进行推理并给出结论。以JSON格式返回：
{{
  "reasoning_steps": [
    {{"step": 1, "description": "推理步骤描述", "type": "deduction/induction/etc"}},
    ...
  ],
  "conclusion": "最终结论",
  "confidence": 0.85,
  "explanation": "推理过程说明"
}}
"""
        return prompt
    
    def _parse_conclusion(self, response: str, chain: ReasoningChain) -> Conclusion:
        """解析结论"""
        try:
            result = json.loads(response)
            
            conclusion = Conclusion(
                id=f"conclusion_{chain.id}",
                content=result.get("conclusion", ""),
                confidence=result.get("confidence", 0.5),
                reasoning_type=chain.reasoning_type,
                premises=[p.id for p in chain.premises],
                steps=result.get("reasoning_steps", []),
                metadata={
                    "explanation": result.get("explanation", "")
                }
            )
            
            return conclusion
        except Exception as e:
            logger.error(f"解析结论失败: {e}")
            return Conclusion(
                id=f"conclusion_{chain.id}",
                content=response,
                confidence=0.3,
                reasoning_type=chain.reasoning_type
            )
    
    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        if not self.llm_client:
            raise ValueError("LLM client not configured")
        
        # 实际实现应调用 llm_client
        # 这里是简化版本
        if hasattr(self.llm_client, 'chat'):
            response = await self.llm_client.chat(prompt)
            return response
        else:
            raise ValueError("LLM client does not support chat method")
    
    async def evaluate_conclusion(self, conclusion: Conclusion) -> float:
        """评估结论的可靠性"""
        # 基于多个因素评估
        scores = []
        
        # 1. 前提置信度
        if conclusion.premises:
            avg_premise_conf = sum(
                p.confidence for p in self._get_premises(conclusion.premises)
            ) / len(conclusion.premises)
            scores.append(avg_premise_conf * 0.3)
        
        # 2. 推理步骤完整性
        if conclusion.steps:
            step_score = min(len(conclusion.steps) / 5.0, 1.0) * 0.3
            scores.append(step_score)
        
        # 3. 结论置信度
        scores.append(conclusion.confidence * 0.4)
        
        return sum(scores)
    
    def _get_premises(self, premise_ids: List[str]) -> List[Premise]:
        """获取前提列表"""
        premises = []
        for chain in self.chains.values():
            for premise in chain.premises:
                if premise.id in premise_ids:
                    premises.append(premise)
        return premises
    
    async def compare_alternatives(
        self,
        query: str,
        alternatives: List[str]
    ) -> Dict[str, float]:
        """比较多个备选方案"""
        results = {}
        
        for alt in alternatives:
            chain = await self.reason(
                query=f"{query} 备选方案：{alt}",
                reasoning_type=ReasoningType.DEDUCTIVE
            )
            
            if chain.final_conclusion:
                score = await self.evaluate_conclusion(chain.final_conclusion)
                results[alt] = score
            else:
                results[alt] = 0.0
        
        return results
    
    def get_chain(self, chain_id: str) -> Optional[ReasoningChain]:
        """获取推理链"""
        return self.chains.get(chain_id)
    
    def get_all_chains(self) -> List[ReasoningChain]:
        """获取所有推理链"""
        return list(self.chains.values())
    
    def clear_chains(self):
        """清空推理链"""
        self.chains.clear()
    
    async def explain_reasoning(self, chain_id: str) -> str:
        """解释推理过程"""
        chain = self.get_chain(chain_id)
        if not chain:
            return "推理链不存在"
        
        explanation = f"推理问题：{chain.query}\n\n"
        explanation += f"推理类型：{chain.reasoning_type.value}\n\n"
        
        explanation += "前提：\n"
        for i, premise in enumerate(chain.premises, 1):
            explanation += f"{i}. {premise.content} (置信度: {premise.confidence:.2f})\n"
        
        if chain.final_conclusion:
            explanation += f"\n推理步骤：\n"
            for step in chain.final_conclusion.steps:
                explanation += f"- {step.get('description', '')}\n"
            
            explanation += f"\n结论：{chain.final_conclusion.content}\n"
            explanation += f"置信度：{chain.final_conclusion.confidence:.2f}\n"
            
            if "explanation" in chain.final_conclusion.metadata:
                explanation += f"\n说明：{chain.final_conclusion.metadata['explanation']}\n"
        
        return explanation


# 全局实例
_reasoning_engine: Optional[ReasoningEngine] = None


def get_reasoning_engine() -> ReasoningEngine:
    """获取推理引擎实例"""
    global _reasoning_engine
    if _reasoning_engine is None:
        _reasoning_engine = ReasoningEngine()
    return _reasoning_engine
