"""Memory Retriever — 时间衰减检索.

检索时考虑：
- 时间衰减（新记忆优先）
- 上下文相关性
- 记忆置信度
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ScoredMemory:
    """带分数的记忆."""
    memory: Dict[str, Any]
    semantic_score: float
    time_score: float
    final_score: float


class MemoryRetriever:
    """智能记忆检索器."""
    
    # 时间衰减参数
    HALF_LIFE_DAYS = 7.0  # 半衰期：7天
    
    # 权重配置
    SEMANTIC_WEIGHT = 0.6
    TIME_WEIGHT = 0.3
    CONFIDENCE_WEIGHT = 0.1
    
    def __init__(self, memory_palace):
        """初始化检索器.
        
        Args:
            memory_palace: MemoryPalace 实例
        """
        self.mp = memory_palace
    
    def time_decay_score(self, timestamp: Optional[str], 
                         reference_time: Optional[datetime] = None) -> float:
        """计算时间衰减分数.
        
        使用指数衰减：score = 0.5 ^ (age / half_life)
        
        Args:
            timestamp: 记忆时间戳
            reference_time: 参考时间（默认 now）
        
        Returns:
            时间分数 (0.0 - 1.0)
        """
        if not timestamp:
            return 0.5  # 无时间戳，给中等分数
        
        try:
            if isinstance(timestamp, str):
                # 处理各种时间格式
                timestamp = timestamp.replace('Z', '+00:00')
                mem_time = datetime.fromisoformat(timestamp)
            else:
                mem_time = timestamp
            
            if reference_time is None:
                reference_time = datetime.now(mem_time.tzinfo) if mem_time.tzinfo else datetime.now()
            
            age_seconds = (reference_time - mem_time).total_seconds()
            age_days = age_seconds / 86400.0
            
            # 指数衰减
            score = math.pow(0.5, age_days / self.HALF_LIFE_DAYS)
            return max(0.01, min(1.0, score))
        
        except Exception as e:
            logger.warning(f"时间解析失败: {e}")
            return 0.5
    
    def retrieve_facts(self, query: str, top_k: int = 10,
                       category: Optional[str] = None) -> List[ScoredMemory]:
        """检索事实（带时间衰减）.
        
        Args:
            query: 查询文本
            top_k: 返回数量
            category: 分类筛选
        
        Returns:
            带分数的记忆列表
        """
        # 语义搜索
        semantic_results = self.mp.search_facts_semantic(
            query, top_k=top_k * 2, active_only=True
        )
        
        if not semantic_results:
            return []
        
        # 计算综合分数
        scored = []
        for memory, sem_score in semantic_results:
            time_score = self.time_decay_score(memory.get('updated_at') or memory.get('created_at'))
            conf_score = memory.get('strength', 1.0)
            
            final_score = (
                self.SEMANTIC_WEIGHT * sem_score +
                self.TIME_WEIGHT * time_score +
                self.CONFIDENCE_WEIGHT * conf_score
            )
            
            scored.append(ScoredMemory(
                memory=memory,
                semantic_score=sem_score,
                time_score=time_score,
                final_score=final_score
            ))
        
        # 按综合分数排序
        scored.sort(key=lambda x: x.final_score, reverse=True)
        return scored[:top_k]
    
    def retrieve_habits(self, query: str, top_k: int = 10) -> List[ScoredMemory]:
        """检索习惯（带时间衰减）."""
        semantic_results = self.mp.search_habits_semantic(
            query, top_k=top_k * 2, active_only=True
        )
        
        if not semantic_results:
            return []
        
        scored = []
        for memory, sem_score in semantic_results:
            time_score = self.time_decay_score(memory.get('last_observed_at'))
            conf_score = memory.get('certainty', 0.5)
            
            final_score = (
                self.SEMANTIC_WEIGHT * sem_score +
                self.TIME_WEIGHT * time_score +
                self.CONFIDENCE_WEIGHT * conf_score
            )
            
            scored.append(ScoredMemory(
                memory=memory,
                semantic_score=sem_score,
                time_score=time_score,
                final_score=final_score
            ))
        
        scored.sort(key=lambda x: x.final_score, reverse=True)
        return scored[:top_k]
    
    def retrieve_timeline(self, query: str, top_k: int = 10) -> List[ScoredMemory]:
        """检索时间线事件（带时间衰减）."""
        semantic_results = self.mp.search_timeline_semantic(
            query, top_k=top_k * 2, active_only=True
        )
        
        if not semantic_results:
            return []
        
        scored = []
        for memory, sem_score in semantic_results:
            time_score = self.time_decay_score(memory.get('event_date'))
            conf_score = 1.0  # 时间线事件没有置信度字段
            
            final_score = (
                self.SEMANTIC_WEIGHT * sem_score +
                self.TIME_WEIGHT * time_score +
                self.CONFIDENCE_WEIGHT * conf_score
            )
            
            scored.append(ScoredMemory(
                memory=memory,
                semantic_score=sem_score,
                time_score=time_score,
                final_score=final_score
            ))
        
        scored.sort(key=lambda x: x.final_score, reverse=True)
        return scored[:top_k]
    
    def retrieve_all(self, query: str, top_k: int = 5) -> Dict[str, List[ScoredMemory]]:
        """跨层检索所有相关记忆.
        
        Args:
            query: 查询文本
            top_k: 每层返回数量
        
        Returns:
            各层的检索结果
        """
        return {
            'facts': self.retrieve_facts(query, top_k),
            'habits': self.retrieve_habits(query, top_k),
            'timeline': self.retrieve_timeline(query, top_k)
        }
    
    def get_recent_memories(self, days: int = 7, limit: int = 20) -> Dict[str, List[Dict]]:
        """获取最近 N 天的所有记忆.
        
        Args:
            days: 天数
            limit: 每层限制
        
        Returns:
            最近的记忆
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        facts = self.mp.recall_facts()
        recent_facts = [
            f for f in facts
            if self._is_after(f.get('updated_at') or f.get('created_at'), cutoff)
        ][:limit]
        
        habits = self.mp.recall_habits()
        recent_habits = [
            h for h in habits
            if self._is_after(h.get('last_observed_at'), cutoff)
        ][:limit]
        
        timeline = self.mp.recall_timeline(start_date=cutoff.date())
        recent_timeline = timeline[:limit]
        
        return {
            'facts': recent_facts,
            'habits': recent_habits,
            'timeline': recent_timeline
        }
    
    def _is_after(self, timestamp: Optional[str], cutoff: datetime) -> bool:
        """检查时间戳是否在截止时间之后."""
        if not timestamp:
            return False
        try:
            if isinstance(timestamp, str):
                timestamp = timestamp.replace('Z', '+00:00')
                ts = datetime.fromisoformat(timestamp)
            else:
                ts = timestamp
            return ts >= cutoff
        except:
            return False


if __name__ == "__main__":
    print("MemoryRetriever 测试")
    print("需要 MemoryPalace 实例才能运行完整测试")
