"""Memory Compressor — 记忆压缩.

定期压缩相似记忆：
- 合并重复记忆
- 生成摘要记忆
- 清理过期记忆
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CompressionResult:
    """压缩结果."""
    merged_count: int
    archived_count: int
    summary_created: int
    details: List[str]


class MemoryCompressor:
    """记忆压缩器."""
    
    # 相似度阈值（超过则合并）
    MERGE_THRESHOLD = 0.85
    
    # 过期天数（超过则归档）
    EXPIRY_DAYS = 90
    
    # 每次压缩的最大数量
    MAX_COMPRESSION_BATCH = 100
    
    def __init__(self, memory_palace):
        """初始化压缩器.
        
        Args:
            memory_palace: MemoryPalace 实例
        """
        self.mp = memory_palace
    
    def compress_facts(self, dry_run: bool = False) -> CompressionResult:
        """压缩事实记忆.
        
        Args:
            dry_run: 仅模拟，不实际执行
        
        Returns:
            压缩结果
        """
        facts = self.mp.recall_facts(include_deprecated=False)
        details = []
        merged = 0
        archived = 0
        summaries = 0
        
        # 按分类分组
        by_category: Dict[str, List[Dict]] = {}
        for fact in facts:
            cat = fact.get('category', 'general')
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(fact)
        
        # 在每个分类内查找相似记忆
        for category, cat_facts in by_category.items():
            if len(cat_facts) < 2:
                continue
            
            # 查找相似对
            for i, fact1 in enumerate(cat_facts):
                for fact2 in cat_facts[i+1:]:
                    similarity = self._compute_similarity(
                        fact1.get('value', ''),
                        fact2.get('value', '')
                    )
                    
                    if similarity > self.MERGE_THRESHOLD:
                        # 合并
                        if not dry_run:
                            self._merge_facts(fact1, fact2)
                        merged += 1
                        details.append(f"合并: {fact1.get('key')} + {fact2.get('key')}")
        
        # 归档过期记忆
        cutoff = datetime.now() - timedelta(days=self.EXPIRY_DAYS)
        for fact in facts:
            updated = fact.get('updated_at') or fact.get('created_at')
            if updated and self._is_before(updated, cutoff):
                if not dry_run:
                    self._archive_fact(fact)
                archived += 1
                details.append(f"归档: {fact.get('key')} (过期)")
        
        # 为高频分类生成摘要
        for category, cat_facts in by_category.items():
            if len(cat_facts) >= 5:
                summary = self._generate_summary(cat_facts[:5])
                if summary and not dry_run:
                    self.mp.remember_fact(
                        category=category,
                        key=f"_summary_{datetime.now().strftime('%Y%m%d')}",
                        value=summary,
                        source="compressor",
                        strength=0.9
                    )
                    summaries += 1
                    details.append(f"摘要: {category}")
        
        logger.info(f"[Compressor] 压缩完成: 合并 {merged}, 归档 {archived}, 摘要 {summaries}")
        return CompressionResult(
            merged_count=merged,
            archived_count=archived,
            summary_created=summaries,
            details=details
        )
    
    def compress_habits(self, dry_run: bool = False) -> CompressionResult:
        """压缩习惯记忆."""
        habits = self.mp.recall_habits(include_deprecated=False)
        details = []
        merged = 0
        archived = 0
        summaries = 0
        
        # 按领域分组
        by_domain: Dict[str, List[Dict]] = {}
        for habit in habits:
            domain = habit.get('domain', 'general')
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(habit)
        
        # 查找相似习惯
        for domain, dom_habits in by_domain.items():
            if len(dom_habits) < 2:
                continue
            
            for i, habit1 in enumerate(dom_habits):
                for habit2 in dom_habits[i+1:]:
                    similarity = self._compute_similarity(
                        habit1.get('pattern', ''),
                        habit2.get('pattern', '')
                    )
                    
                    if similarity > self.MERGE_THRESHOLD:
                        if not dry_run:
                            self._merge_habits(habit1, habit2)
                        merged += 1
                        details.append(f"合并习惯: {habit1.get('pattern')[:30]}...")
        
        # 归档低置信度 + 长期未观察的习惯
        cutoff = datetime.now() - timedelta(days=self.EXPIRY_DAYS)
        for habit in habits:
            last_obs = habit.get('last_observed_at')
            certainty = habit.get('certainty', 0.5)
            
            if (last_obs and self._is_before(last_obs, cutoff)) or certainty < 0.3:
                if not dry_run:
                    self._archive_habit(habit)
                archived += 1
                details.append(f"归档习惯: {habit.get('pattern')[:30]}...")
        
        return CompressionResult(
            merged_count=merged,
            archived_count=archived,
            summary_created=summaries,
            details=details
        )
    
    def compress_all(self, dry_run: bool = False) -> Dict[str, CompressionResult]:
        """压缩所有记忆层.
        
        Args:
            dry_run: 仅模拟
        
        Returns:
            各层的压缩结果
        """
        logger.info(f"[Compressor] 开始压缩 (dry_run={dry_run})")
        
        return {
            'facts': self.compress_facts(dry_run),
            'habits': self.compress_habits(dry_run)
        }
    
    def _compute_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（简单版本）."""
        if not text1 or not text2:
            return 0.0
        
        # 使用 MemoryPalace 的向量服务
        try:
            vec1 = self.mp.vector_service.encode(text1)
            vec2 = self.mp.vector_service.encode(text2)
            return self.mp.vector_service.similarity(vec1, vec2)
        except Exception as e:
            logger.warning(f"相似度计算失败: {e}")
            # 回退到简单的字符重叠
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            if not words1 or not words2:
                return 0.0
            return len(words1 & words2) / max(len(words1), len(words2))
    
    def _merge_facts(self, fact1: Dict, fact2: Dict) -> None:
        """合并两个事实."""
        # 保留更新的那个
        time1 = fact1.get('updated_at') or fact1.get('created_at')
        time2 = fact2.get('updated_at') or fact2.get('created_at')
        
        if time1 and time2:
            if time1 > time2:
                # fact1 更新，标记 fact2 为 deprecated
                self.mp._connect().execute(
                    "UPDATE facts SET status = 'deprecated' WHERE id = ?",
                    (fact2['id'],)
                )
            else:
                self.mp._connect().execute(
                    "UPDATE facts SET status = 'deprecated' WHERE id = ?",
                    (fact1['id'],)
                )
            self.mp._connect().commit()
    
    def _merge_habits(self, habit1: Dict, habit2: Dict) -> None:
        """合并两个习惯."""
        # 合并观察次数和置信度
        obs1 = habit1.get('observation_count', 1)
        obs2 = habit2.get('observation_count', 1)
        cert1 = habit1.get('certainty', 0.5)
        cert2 = habit2.get('certainty', 0.5)
        
        # 加权平均
        total_obs = obs1 + obs2
        new_cert = (cert1 * obs1 + cert2 * obs2) / total_obs
        
        # 更新 habit1，标记 habit2
        conn = self.mp._connect()
        conn.execute(
            "UPDATE habits SET observation_count = ?, certainty = ? WHERE id = ?",
            (total_obs, new_cert, habit1['id'])
        )
        conn.execute(
            "UPDATE habits SET status = 'deprecated' WHERE id = ?",
            (habit2['id'],)
        )
        conn.commit()
    
    def _archive_fact(self, fact: Dict) -> None:
        """归档事实."""
        self.mp._connect().execute(
            "UPDATE facts SET status = 'archived' WHERE id = ?",
            (fact['id'],)
        )
        self.mp._connect().commit()
    
    def _archive_habit(self, habit: Dict) -> None:
        """归档习惯."""
        self.mp._connect().execute(
            "UPDATE habits SET status = 'archived' WHERE id = ?",
            (habit['id'],)
        )
        self.mp._connect().commit()
    
    def _generate_summary(self, facts: List[Dict]) -> Optional[str]:
        """生成摘要."""
        if not facts:
            return None
        
        # 简单拼接
        values = [f.get('value', '') for f in facts if f.get('value')]
        if not values:
            return None
        
        summary = " | ".join(values[:5])
        return f"[摘要] {summary[:200]}"
    
    def _is_before(self, timestamp: Optional[str], cutoff: datetime) -> bool:
        """检查时间戳是否在截止时间之前."""
        if not timestamp:
            return False
        try:
            if isinstance(timestamp, str):
                timestamp = timestamp.replace('Z', '+00:00')
                ts = datetime.fromisoformat(timestamp)
            else:
                ts = timestamp
            return ts < cutoff
        except:
            return False


if __name__ == "__main__":
    print("MemoryCompressor 测试")
    print("需要 MemoryPalace 实例才能运行完整测试")
