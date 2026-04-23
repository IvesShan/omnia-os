"""
ACT (Adaptive Computation Time) Planner

自适应计算时间规划器
- 根据任务复杂度决定推理深度
- 动态调整计算资源分配
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
import re


class ComplexityLevel(Enum):
    """任务复杂度等级"""
    QUICK = "quick"        # 1-2 轮，简单查询
    BALANCED = "balanced"  # 3-5 轮，中等任务
    DEEP = "deep"          # 6-8 轮，复杂推理


@dataclass
class TaskAnalysis:
    """任务分析结果"""
    complexity: ComplexityLevel
    estimated_depth: int
    requires_tools: bool
    requires_memory: bool
    keywords: List[str]
    confidence: float


class ACTPlanner:
    """自适应计算时间规划器"""
    
    # 复杂度关键词映射
    COMPLEXITY_KEYWORDS = {
        ComplexityLevel.QUICK: [
            "what is", "define", "简单", "查询", "是什么",
            "hello", "hi", "你好", "thanks", "谢谢"
        ],
        ComplexityLevel.BALANCED: [
            "explain", "how to", "为什么", "如何", "解释",
            "compare", "比较", "analyze", "分析", "建议"
        ],
        ComplexityLevel.DEEP: [
            "design", "architect", "设计", "架构", "优化",
            "refactor", "重构", "debug", "调试", "完整方案"
        ]
    }
    
    # 工具关键词
    TOOL_KEYWORDS = [
        "file", "read", "write", "execute", "shell",
        "文件", "读取", "写入", "执行", "命令"
    ]
    
    # 记忆关键词
    MEMORY_KEYWORDS = [
        "remember", "recall", "previous", "last time",
        "记得", "回忆", "上次", "之前", "历史"
    ]
    
    def __init__(self, max_depth: int = 8, min_depth: int = 1):
        self.max_depth = max_depth
        self.min_depth = min_depth
    
    def analyze(self, query: str, context: Optional[Dict] = None) -> TaskAnalysis:
        """分析任务复杂度
        
        Args:
            query: 用户查询
            context: 上下文信息
            
        Returns:
            TaskAnalysis: 任务分析结果
        """
        query_lower = query.lower()
        
        # 1. 关键词匹配
        keyword_scores = self._score_keywords(query_lower)
        
        # 2. 长度因素
        length_score = self._score_length(query)
        
        # 3. 上下文因素
        context_score = self._score_context(context) if context else 0.0
        
        # 4. 综合评估
        complexity = self._determine_complexity(
            keyword_scores, length_score, context_score
        )
        
        # 5. 估算深度
        estimated_depth = self._estimate_depth(complexity)
        
        # 6. 检测工具和记忆需求
        requires_tools = self._detect_tools(query_lower)
        requires_memory = self._detect_memory(query_lower)
        
        # 7. 提取关键词
        keywords = self._extract_keywords(query_lower)
        
        return TaskAnalysis(
            complexity=complexity,
            estimated_depth=estimated_depth,
            requires_tools=requires_tools,
            requires_memory=requires_memory,
            keywords=keywords,
            confidence=0.85  # 基础置信度
        )
    
    def estimate(self, query: str, context: Optional[Dict] = None) -> TaskAnalysis:
        """estimate 方法（别名）"""
        return self.analyze(query, context)
    
    def _score_keywords(self, query: str) -> Dict[ComplexityLevel, float]:
        """关键词评分"""
        scores = {}
        for level, keywords in self.COMPLEXITY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query) / len(keywords)
            scores[level] = score
        return scores
    
    def _score_length(self, query: str) -> float:
        """长度评分"""
        length = len(query)
        if length < 20:
            return 0.2  # 短查询
        elif length < 100:
            return 0.5  # 中等
        else:
            return 0.8  # 长查询
    
    def _score_context(self, context: Dict) -> float:
        """上下文评分"""
        if not context:
            return 0.0
        
        score = 0.0
        if context.get("history"):
            score += 0.3
        if context.get("active_files"):
            score += 0.2
        if context.get("active_project"):
            score += 0.2
        
        return min(score, 1.0)
    
    def _determine_complexity(
        self,
        keyword_scores: Dict[ComplexityLevel, float],
        length_score: float,
        context_score: float
    ) -> ComplexityLevel:
        """确定复杂度等级"""
        # 加权综合
        quick_score = keyword_scores.get(ComplexityLevel.QUICK, 0) * 0.5
        balanced_score = keyword_scores.get(ComplexityLevel.BALANCED, 0) * 0.3
        deep_score = keyword_scores.get(ComplexityLevel.DEEP, 0) * 0.2
        
        # 长度和上下文加成
        total_score = (quick_score + balanced_score + deep_score + 
                      length_score * 0.2 + context_score * 0.3)
        
        # 分级
        if total_score < 0.3:
            return ComplexityLevel.QUICK
        elif total_score < 0.6:
            return ComplexityLevel.BALANCED
        else:
            return ComplexityLevel.DEEP
    
    def _estimate_depth(self, complexity: ComplexityLevel) -> int:
        """估算推理深度"""
        depth_map = {
            ComplexityLevel.QUICK: 2,
            ComplexityLevel.BALANCED: 4,
            ComplexityLevel.DEEP: 6
        }
        return min(depth_map[complexity], self.max_depth)
    
    def _detect_tools(self, query: str) -> bool:
        """检测工具需求"""
        return any(kw in query for kw in self.TOOL_KEYWORDS)
    
    def _detect_memory(self, query: str) -> bool:
        """检测记忆需求"""
        return any(kw in query for kw in self.MEMORY_KEYWORDS)
    
    def _extract_keywords(self, query: str) -> List[str]:
        """提取关键词"""
        # 简单提取：去除停用词，保留实词
        words = re.findall(r'\b\w{2,}\b', query)
        return list(set(words))[:5]  # 最多5个关键词
