"""
Integration Bridge for Omnia

Omnia 集成桥接
- 连接循环推理引擎与 Omnia 主流程
- 集成记忆系统
- 提供统一接口
"""

from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

from .act_planner import ACTPlanner, ComplexityLevel, TaskAnalysis
from .recurrent_engine import RecurrentReasoning, ReasoningResult
from .mla_compression import MLACompression


class IntegrationBridge:
    """Omnia 集成桥接"""
    
    def __init__(
        self,
        model_call: Callable,
        memory_palace=None,
        config: Optional[Dict] = None
    ):
        """
        Args:
            model_call: 模型调用函数
            memory_palace: 记忆宫殿实例
            config: 配置参数
        """
        self.config = config or {}
        
        # 初始化组件
        self.planner = ACTPlanner(
            max_depth=self.config.get('max_depth', 8),
            min_depth=self.config.get('min_depth', 1)
        )
        
        self.engine = RecurrentReasoning(
            model_call=model_call,
            max_iterations=self.config.get('max_iterations', 8),
            confidence_threshold=self.config.get('confidence_threshold', 0.85),
            min_iterations=self.config.get('min_iterations', 1)
        )
        
        self.compression = MLACompression()
        self.memory_palace = memory_palace
    
    def process(
        self,
        query: str,
        context: Optional[Dict] = None,
        on_step: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """处理用户查询
        
        Args:
            query: 用户查询
            context: 上下文
            on_step: 步骤回调
            
        Returns:
            处理结果
        """
        # 1. 任务分析
        analysis = self.planner.analyze(query, context)
        
        # 2. 检索相关记忆
        memories = self._retrieve_memories(query, analysis)
        
        # 3. 增强上下文
        enhanced_context = self._enhance_context(context, memories, analysis)
        
        # 4. 执行循环推理
        result = self.engine.reason(
            query=query,
            context=enhanced_context,
            on_step=on_step
        )
        
        # 5. 存储记忆
        self._store_memory(query, result)
        
        # 6. 返回结果
        return {
            'answer': result.final_answer,
            'confidence': result.final_confidence,
            'iterations': result.total_iterations,
            'complexity': analysis.complexity.value,
            'time_elapsed': result.time_elapsed,
            'stopped_early': result.stopped_early,
            'memories_used': len(memories)
        }
    
    def _retrieve_memories(
        self,
        query: str,
        analysis: TaskAnalysis
    ) -> List[Dict]:
        """检索相关记忆"""
        if not self.memory_palace:
            return []
        
        if not analysis.requires_memory:
            return []
        
        try:
            # 从记忆宫殿检索
            results = self.memory_palace.search_facts(query, limit=3)
            return results
        except Exception as e:
            print(f"[IntegrationBridge] Memory retrieval error: {e}")
            return []
    
    def _enhance_context(
        self,
        context: Optional[Dict],
        memories: List[Dict],
        analysis: TaskAnalysis
    ) -> Dict:
        """增强上下文"""
        enhanced = context.copy() if context else {}
        
        # 添加记忆
        if memories:
            enhanced['relevant_memories'] = memories
        
        # 添加任务分析
        enhanced['task_analysis'] = {
            'complexity': analysis.complexity.value,
            'estimated_depth': analysis.estimated_depth,
            'requires_tools': analysis.requires_tools,
            'keywords': analysis.keywords
        }
        
        return enhanced
    
    def _store_memory(self, query: str, result: ReasoningResult):
        """存储记忆"""
        if not self.memory_palace:
            return
        
        try:
            # 存储为事件
            self.memory_palace.store_event(
                event_type="reasoning",
                description=f"Query: {query[:50]}... | Answer: {result.final_answer[:50]}...",
                metadata={
                    'iterations': result.total_iterations,
                    'confidence': result.final_confidence,
                    'time_elapsed': result.time_elapsed
                }
            )
        except Exception as e:
            print(f"[IntegrationBridge] Memory storage error: {e}")
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'planner': {
                'max_depth': self.planner.max_depth,
                'min_depth': self.planner.min_depth
            },
            'engine': {
                'max_iterations': self.engine.max_iterations,
                'confidence_threshold': self.engine.confidence_threshold
            },
            'compression': self.compression.get_stats()
        }
