"""
ACT Planner - 自适应计算规划器

借鉴 OpenMythos 的 ACT (Adaptive Computation Time) 机制：
- 简单任务：单步规划，快速响应
- 复杂任务：多步规划，深度思考
- 根据任务复杂度自适应调整规划深度

核心思想：
- 评估任务复杂度
- 根据复杂度决定规划步骤数
- 支持动态调整规划策略
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import re


class TaskComplexity(Enum):
    """任务复杂度级别"""
    SIMPLE = "simple"      # 简单：单步规划
    MEDIUM = "medium"      # 中等：2-3 步规划
    COMPLEX = "complex"    # 复杂：4-5 步规划
    CRITICAL = "critical"  # 关键：多步深度规划


@dataclass
class PlanStep:
    """规划步骤"""
    step_id: int
    description: str
    tools_needed: List[str] = field(default_factory=list)
    estimated_time: float = 1.0
    dependencies: List[int] = field(default_factory=list)


@dataclass
class AdaptivePlan:
    """自适应规划结果"""
    complexity: TaskComplexity
    steps: List[PlanStep]
    total_estimated_time: float
    reasoning: str
    confidence: float


class ComplexityEstimator:
    """
    任务复杂度评估器
    
    评估维度：
    1. 输入长度
    2. 意图类型
    3. 涉及的工具数量
    4. 上下文复杂度
    5. 关键词匹配
    """
    
    def __init__(self):
        # 复杂度阈值
        self.thresholds = {
            "simple": 0.3,
            "medium": 0.6,
            "complex": 0.8,
            "critical": 0.95
        }
        
        # 高复杂度关键词
        self.complex_keywords = [
            "分析", "设计", "架构", "重构", "优化",
            "比较", "评估", "研究", "深入", "详细",
            "多角度", "全面", "系统性", "完整"
        ]
        
        # 简单关键词
        self.simple_keywords = [
            "是什么", "怎么样", "多少", "哪里",
            "简单", "快速", "直接", "告诉我"
        ]
    
    def estimate(
        self,
        user_input: str,
        context: Optional[Dict] = None
    ) -> TaskComplexity:
        """
        评估任务复杂度
        
        Args:
            user_input: 用户输入
            context: 上下文信息
        
        Returns:
            TaskComplexity: 复杂度级别
        """
        score = 0.0
        
        # 1. 输入长度
        input_length = len(user_input)
        if input_length > 300:
            score += 0.3
        elif input_length > 100:
            score += 0.15
        
        # 2. 关键词匹配
        complex_matches = sum(
            1 for kw in self.complex_keywords
            if kw in user_input
        )
        simple_matches = sum(
            1 for kw in self.simple_keywords
            if kw in user_input
        )
        
        score += min(0.3, complex_matches * 0.1)
        score -= min(0.2, simple_matches * 0.05)
        
        # 3. 意图类型
        intent = self._detect_intent(user_input)
        if intent in ["code_task", "creative_work", "analysis"]:
            score += 0.25
        elif intent in ["memory_query", "system_status"]:
            score += 0.05
        
        # 4. 涉及的工具数量
        tools_needed = self._estimate_tools(user_input)
        score += min(0.2, len(tools_needed) * 0.05)
        
        # 5. 上下文复杂度
        if context:
            if len(context) > 5:
                score += 0.1
            if "files" in context and len(context["files"]) > 2:
                score += 0.1
        
        # 归一化到 0-1
        score = max(0.0, min(1.0, score))
        
        # 根据阈值分类
        if score < self.thresholds["simple"]:
            return TaskComplexity.SIMPLE
        elif score < self.thresholds["medium"]:
            return TaskComplexity.MEDIUM
        elif score < self.thresholds["complex"]:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.CRITICAL
    
    def _detect_intent(self, user_input: str) -> str:
        """检测意图类型"""
        # 代码相关
        if any(kw in user_input for kw in ["代码", "函数", "bug", "修复", "实现"]):
            return "code_task"
        
        # 创意相关
        if any(kw in user_input for kw in ["设计", "创意", "想法", "建议"]):
            return "creative_work"
        
        # 分析相关
        if any(kw in user_input for kw in ["分析", "比较", "评估", "研究"]):
            return "analysis"
        
        # 记忆查询
        if any(kw in user_input for kw in ["记得", "上次", "之前", "历史"]):
            return "memory_query"
        
        # 系统状态
        if any(kw in user_input for kw in ["状态", "运行", "检查", "监控"]):
            return "system_status"
        
        return "general"
    
    def _estimate_tools(self, user_input: str) -> List[str]:
        """估计需要的工具"""
        tools = []
        
        # 文件操作
        if any(kw in user_input for kw in ["文件", "读取", "写入", "修改"]):
            tools.append("file_ops")
        
        # 网络搜索
        if any(kw in user_input for kw in ["搜索", "查找", "最新", "新闻"]):
            tools.append("web_search")
        
        # 代码执行
        if any(kw in user_input for kw in ["运行", "执行", "测试", "调试"]):
            tools.append("code_exec")
        
        # 记忆查询
        if any(kw in user_input for kw in ["记得", "上次", "历史"]):
            tools.append("memory_query")
        
        return tools


class ACTPlanner:
    """
    自适应计算规划器
    
    借鉴 OpenMythos 的 ACT 机制，根据任务复杂度调整规划深度：
    
    - 简单任务 (complexity < 0.3): 单步规划
    - 中等任务 (0.3 ≤ complexity < 0.6): 2-3 步规划
    - 复杂任务 (complexity ≥ 0.6): 4-5 步规划
    
    核心优势：
    - 简单问题快速响应
    - 复杂问题深度思考
    - 自适应计算资源分配
    """
    
    def __init__(
        self,
        max_planning_steps: int = 5,
        enable_adaptive: bool = True
    ):
        self.max_steps = max_planning_steps
        self.enable_adaptive = enable_adaptive
        self.complexity_estimator = ComplexityEstimator()
        
        # 规划模板
        self.plan_templates = {
            TaskComplexity.SIMPLE: [
                "直接回答用户问题"
            ],
            TaskComplexity.MEDIUM: [
                "理解用户需求",
                "收集相关信息",
                "生成响应"
            ],
            TaskComplexity.COMPLEX: [
                "深入理解用户需求",
                "分析问题背景",
                "收集相关信息",
                "综合分析和推理",
                "生成详细响应"
            ],
            TaskComplexity.CRITICAL: [
                "全面分析用户需求",
                "深度问题背景研究",
                "收集所有相关信息",
                "多角度综合分析",
                "推理和验证",
                "生成全面响应",
                "质量检查"
            ]
        }
    

    def estimate_complexity(
        self,
        user_input: str,
        context: Optional[Dict] = None
    ) -> TaskComplexity:
        """
        评估任务复杂度（便捷方法）
        
        Args:
            user_input: 用户输入
            context: 上下文信息
        
        Returns:
            TaskComplexity: 复杂度级别
        """
        return self.complexity_estimator.estimate(user_input, context)

    async def plan(
        self,
        user_input: str,
        context: Optional[Dict] = None
    ) -> AdaptivePlan:
        """
        执行自适应规划
        
        Args:
            user_input: 用户输入
            context: 上下文信息
        
        Returns:
            AdaptivePlan: 规划结果
        """
        # 评估复杂度
        complexity = self.complexity_estimator.estimate(user_input, context)
        
        # 根据复杂度选择规划策略
        if not self.enable_adaptive:
            complexity = TaskComplexity.MEDIUM  # 默认中等复杂度
        
        # 生成规划步骤
        steps = self._generate_steps(user_input, complexity, context)
        
        # 计算总估计时间
        total_time = sum(step.estimated_time for step in steps)
        
        # 生成规划推理
        reasoning = self._generate_reasoning(complexity, steps)
        
        return AdaptivePlan(
            complexity=complexity,
            steps=steps,
            total_estimated_time=total_time,
            reasoning=reasoning,
            confidence=self._calculate_confidence(complexity, steps)
        )
    
    def _generate_steps(
        self,
        user_input: str,
        complexity: TaskComplexity,
        context: Optional[Dict]
    ) -> List[PlanStep]:
        """
        生成规划步骤
        
        Args:
            user_input: 用户输入
            complexity: 复杂度级别
            context: 上下文信息
        
        Returns:
            List[PlanStep]: 规划步骤列表
        """
        # 获取模板
        template = self.plan_templates[complexity]
        
        # 创建步骤
        steps = []
        for i, desc in enumerate(template):
            step = PlanStep(
                step_id=i + 1,
                description=desc,
                tools_needed=self._estimate_tools_for_step(desc, user_input),
                estimated_time=self._estimate_time_for_step(desc, complexity),
                dependencies=[i] if i > 0 else []
            )
            steps.append(step)
        
        return steps
    
    def _estimate_tools_for_step(
        self,
        step_desc: str,
        user_input: str
    ) -> List[str]:
        """估计步骤需要的工具"""
        tools = []
        
        if "收集" in step_desc or "查找" in step_desc:
            tools.append("memory_query")
            if "搜索" in user_input:
                tools.append("web_search")
        
        if "分析" in step_desc:
            tools.append("reasoning")
        
        if "生成" in step_desc:
            tools.append("llm_generate")
        
        return tools
    
    def _estimate_time_for_step(
        self,
        step_desc: str,
        complexity: TaskComplexity
    ) -> float:
        """估计步骤耗时"""
        base_times = {
            TaskComplexity.SIMPLE: 0.5,
            TaskComplexity.MEDIUM: 1.0,
            TaskComplexity.COMPLEX: 1.5
        }
        
        base_time = base_times[complexity]
        
        # 根据步骤类型调整
        if "分析" in step_desc:
            base_time *= 1.5
        elif "收集" in step_desc:
            base_time *= 1.2
        
        return base_time
    
    def _generate_reasoning(
        self,
        complexity: TaskComplexity,
        steps: List[PlanStep]
    ) -> str:
        """生成规划推理"""
        complexity_desc = {
            TaskComplexity.SIMPLE: "简单任务",
            TaskComplexity.MEDIUM: "中等复杂度任务",
            TaskComplexity.COMPLEX: "复杂任务"
        }
        
        return (
            f"评估为{complexity_desc[complexity]}，"
            f"规划 {len(steps)} 个步骤，"
            f"预计耗时 {sum(s.estimated_time for s in steps):.1f}s"
        )
    
    def _calculate_confidence(
        self,
        complexity: TaskComplexity,
        steps: List[PlanStep]
    ) -> float:
        """计算规划置信度"""
        # 基础置信度
        base_confidence = {
            TaskComplexity.SIMPLE: 0.9,
            TaskComplexity.MEDIUM: 0.75,
            TaskComplexity.COMPLEX: 0.6
        }
        
        return base_confidence[complexity]
    
    def get_planning_stats(self) -> Dict[str, Any]:
        """获取规划统计信息"""
        return {
            "max_steps": self.max_steps,
            "adaptive_enabled": self.enable_adaptive,
            "complexity_thresholds": self.complexity_estimator.thresholds
        }


# 便捷函数
def create_act_planner(
    max_planning_steps: int = 5,
    enable_adaptive: bool = True
) -> ACTPlanner:
    """创建 ACT 规划器实例"""
    return ACTPlanner(
        max_planning_steps=max_planning_steps,
        enable_adaptive=enable_adaptive
    )
