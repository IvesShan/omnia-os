"""
Recurrent Reasoning Engine

循环推理引擎
- 多轮自我反思
- 置信度评估
- 动态停机
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any
import time


@dataclass
class ReasoningStep:
    """推理步骤"""
    iteration: int
    thought: str
    confidence: float
    action: Optional[str] = None
    result: Optional[str] = None


@dataclass
class ReasoningResult:
    """推理结果"""
    final_answer: str
    steps: List[ReasoningStep]
    total_iterations: int
    final_confidence: float
    stopped_early: bool
    time_elapsed: float


class RecurrentReasoning:
    """循环推理引擎"""
    
    def __init__(
        self,
        model_call: Callable,
        max_iterations: int = 8,
        confidence_threshold: float = 0.85,
        min_iterations: int = 1
    ):
        """
        Args:
            model_call: 模型调用函数
            max_iterations: 最大迭代次数
            confidence_threshold: 置信度阈值
            min_iterations: 最小迭代次数
        """
        self.model_call = model_call
        self.max_iterations = max_iterations
        self.confidence_threshold = confidence_threshold
        self.min_iterations = min_iterations
    
    def reason(
        self,
        query: str,
        context: Optional[Dict] = None,
        on_step: Optional[Callable[[ReasoningStep], None]] = None
    ) -> ReasoningResult:
        """执行循环推理
        
        Args:
            query: 用户查询
            context: 上下文
            on_step: 步骤回调
            
        Returns:
            ReasoningResult: 推理结果
        """
        start_time = time.time()
        steps = []
        
        # 初始推理
        current_thought = query
        current_confidence = 0.0
        
        for iteration in range(1, self.max_iterations + 1):
            # 构建提示
            prompt = self._build_prompt(query, current_thought, iteration)
            
            # 调用模型
            response = self.model_call(prompt, context)
            
            # 解析响应
            thought, confidence, action, result = self._parse_response(response)
            
            # 记录步骤
            step = ReasoningStep(
                iteration=iteration,
                thought=thought,
                confidence=confidence,
                action=action,
                result=result
            )
            steps.append(step)
            
            # 回调
            if on_step:
                on_step(step)
            
            # 更新状态
            current_thought = thought
            current_confidence = confidence
            
            # 检查停机条件
            if self._should_stop(iteration, confidence):
                break
        
        # 构建最终答案
        final_answer = self._synthesize_answer(steps)
        
        time_elapsed = time.time() - start_time
        
        return ReasoningResult(
            final_answer=final_answer,
            steps=steps,
            total_iterations=len(steps),
            final_confidence=current_confidence,
            stopped_early=len(steps) < self.max_iterations,
            time_elapsed=time_elapsed
        )
    
    def _build_prompt(
        self,
        query: str,
        current_thought: str,
        iteration: int
    ) -> str:
        """构建推理提示"""
        if iteration == 1:
            return f"""分析以下问题并提供初步思考：

问题：{query}

请提供：
1. 初步分析
2. 关键点识别
3. 置信度评估 (0.0-1.0)

格式：
思考：[你的分析]
置信度：[数值]
"""
        else:
            return f"""继续深入分析：

问题：{query}
当前思考：{current_thought}

请：
1. 反思之前的分析
2. 补充遗漏点
3. 更新置信度

格式：
思考：[深化分析]
置信度：[数值]
"""
    
    def _parse_response(self, response: str) -> tuple:
        """解析模型响应"""
        # 简单解析
        thought = response
        confidence = 0.7  # 默认置信度
        
        # 尝试提取置信度
        import re
        conf_match = re.search(r'置信度[：:]\s*([\d.]+)', response)
        if conf_match:
            confidence = float(conf_match.group(1))
        
        # 尝试提取思考部分
        thought_match = re.search(r'思考[：:]\s*(.+?)(?=置信度|$)', response, re.DOTALL)
        if thought_match:
            thought = thought_match.group(1).strip()
        
        return thought, confidence, None, None
    
    def _should_stop(self, iteration: int, confidence: float) -> bool:
        """判断是否应该停止"""
        # 必须达到最小迭代次数
        if iteration < self.min_iterations:
            return False
        
        # 置信度达标
        if confidence >= self.confidence_threshold:
            return True
        
        return False
    
    def _synthesize_answer(self, steps: List[ReasoningStep]) -> str:
        """综合最终答案"""
        if not steps:
            return "无法生成答案"
        
        # 取最后一步的思考作为基础
        final_thought = steps[-1].thought
        
        # 如果有多步，添加推理过程摘要
        if len(steps) > 1:
            summary = f"经过 {len(steps)} 轮推理：\n{final_thought}"
            return summary
        
        return final_thought
