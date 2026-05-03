"""Memory Updater — 智能更新机制.

当检测到冲突时：
1. 不重复新增
2. 更新旧记忆
3. 记录变更时间线
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ConflictResult:
    """冲突检测结果."""
    has_conflict: bool
    old_memory: Optional[Dict[str, Any]]
    action: str  # 'create', 'update', 'skip'
    reason: str


class MemoryUpdater:
    """智能记忆更新器."""
    
    # 相似度阈值（超过则认为是同一记忆）
    SIMILARITY_THRESHOLD = 0.85
    
    # 时间衰减因子（秒）
    TIME_DECAY_FACTOR = 7 * 24 * 3600  # 7天
    
    def __init__(self, memory_palace):
        """初始化更新器.
        
        Args:
            memory_palace: MemoryPalace 实例
        """
        self.mp = memory_palace
    
    def check_fact_conflict(self, category: str, key: str, 
                           new_value: str) -> ConflictResult:
        """检查事实冲突.
        
        Args:
            category: 分类
            key: 键
            new_value: 新值
        
        Returns:
            冲突检测结果
        """
        # 查找现有记忆
        existing = self.mp.recall_facts(category=category, key=key)
        
        if not existing:
            return ConflictResult(
                has_conflict=False,
                old_memory=None,
                action='create',
                reason='新记忆，无冲突'
            )
        
        # 找到最新版本
        latest = existing[0]
        old_value = latest.get('value', '')
        
        # 值相同，跳过
        if old_value == new_value:
            return ConflictResult(
                has_conflict=False,
                old_memory=latest,
                action='skip',
                reason='值相同，无需更新'
            )
        
        # 值不同，检测是否是更新信号
        # 例如：用户说"不再喜欢蓝色"，新值是"不喜欢蓝色"
        if self._is_update_signal(old_value, new_value):
            return ConflictResult(
                has_conflict=True,
                old_memory=latest,
                action='update',
                reason=f'检测到更新：{old_value} → {new_value}'
            )
        
        # 值不同但不是明确的更新，可能是新偏好
        # 检查时间间隔
        old_time = latest.get('updated_at') or latest.get('created_at')
        if old_time:
            try:
                if isinstance(old_time, str):
                    old_dt = datetime.fromisoformat(old_time.replace('Z', '+00:00'))
                else:
                    old_dt = old_time
                time_diff = (datetime.now(old_dt.tzinfo) - old_dt).total_seconds()
                
                # 超过衰减期，认为是偏好变更
                if time_diff > self.TIME_DECAY_FACTOR:
                    return ConflictResult(
                        has_conflict=True,
                        old_memory=latest,
                        action='update',
                        reason=f'偏好变更（间隔 {time_diff/86400:.1f} 天）'
                    )
            except Exception as e:
                logger.warning(f"时间解析失败: {e}")
        
        # 默认：创建新版本
        return ConflictResult(
            has_conflict=True,
            old_memory=latest,
            action='update',
            reason=f'值冲突：{old_value} vs {new_value}'
        )
    
    def _is_update_signal(self, old_value: str, new_value: str) -> bool:
        """检测是否是明确的更新信号.
        
        例如：
        - 旧：喜欢蓝色
        - 新：不喜欢蓝色
        → 返回 True
        """
        # 检测否定词
        negation_words = ['不', '不再', '没', '没有']
        
        old_positive = not any(neg in old_value for neg in negation_words)
        new_negative = any(neg in new_value for neg in negation_words)
        
        # 从正面变负面，或从负面变正面
        if old_positive != new_negative:
            return True
        
        # 检测"改"字
        if '改' in new_value or '换' in new_value:
            return True
        
        return False
    
    def update_or_create_fact(self, category: str, key: str, value: str,
                              source: str = "conversation",
                              confidence: float = 0.8) -> Dict[str, Any]:
        """智能更新或创建事实.
        
        Args:
            category: 分类
            key: 键
            value: 值
            source: 来源
            confidence: 置信度
        
        Returns:
            操作结果
        """
        conflict = self.check_fact_conflict(category, key, value)
        
        if conflict.action == 'skip':
            logger.info(f"[Updater] 跳过重复记忆: {category}:{key}")
            return {'action': 'skip', 'reason': conflict.reason}
        
        if conflict.action == 'update':
            # 使用 MemoryPalace 的版本化机制
            result = self.mp.remember_fact(
                category=category,
                key=key,
                value=value,
                source=source,
                strength=confidence
            )
            
            # 记录时间线事件
            if conflict.old_memory:
                self.mp.record_event(
                    event_date=datetime.now().date(),
                    event_type="memory_update",
                    title=f"记忆更新: {category}:{key}",
                    description=f"{conflict.old_memory.get('value', '')} → {value}",
                    tags="memory,update"
                )
            
            logger.info(f"[Updater] 更新记忆: {category}:{key} = {value}")
            return {'action': 'update', 'result': result, 'reason': conflict.reason}
        
        # 创建新记忆
        result = self.mp.remember_fact(
            category=category,
            key=key,
            value=value,
            source=source,
            strength=confidence
        )
        logger.info(f"[Updater] 创建记忆: {category}:{key} = {value}")
        return {'action': 'create', 'result': result, 'reason': conflict.reason}
    
    def update_or_create_habit(self, domain: str, pattern: str,
                               evidence: str = "",
                               certainty: float = 0.5) -> Dict[str, Any]:
        """智能更新或创建习惯."""
        # 查找现有习惯
        existing = self.mp.recall_habits(domain=domain)
        
        for habit in existing:
            if habit.get('pattern') == pattern:
                # 已存在，更新置信度
                old_certainty = habit.get('certainty', 0.5)
                new_certainty = min(1.0, old_certainty + 0.1)  # 每次观察增加 0.1
                
                result = self.mp.observe_habit(
                    domain=domain,
                    pattern=pattern,
                    evidence=evidence,
                    certainty=new_certainty
                )
                logger.info(f"[Updater] 增强习惯: {domain}:{pattern} (置信度: {new_certainty:.2f})")
                return {'action': 'update', 'result': result}
        
        # 创建新习惯
        result = self.mp.observe_habit(
            domain=domain,
            pattern=pattern,
            evidence=evidence,
            certainty=certainty
        )
        logger.info(f"[Updater] 创建习惯: {domain}:{pattern}")
        return {'action': 'create', 'result': result}
    
    def batch_update(self, extractions: List[Dict[str, Any]]) -> Dict[str, int]:
        """批量更新记忆.
        
        Args:
            extractions: 提取出的记忆列表
        
        Returns:
            统计结果
        """
        stats = {'created': 0, 'updated': 0, 'skipped': 0}
        
        for ext in extractions:
            mem_type = ext.get('memory_type')
            
            if mem_type == 'preference':
                result = self.update_or_create_fact(
                    category='preference',
                    key=ext.get('key', ''),
                    value=ext.get('value', ''),
                    confidence=ext.get('confidence', 0.7)
                )
                stats[result['action']] = stats.get(result['action'], 0) + 1
            
            elif mem_type == 'habit':
                result = self.update_or_create_habit(
                    domain='behavior',
                    pattern=ext.get('key', ''),
                    evidence=ext.get('evidence', ''),
                    certainty=ext.get('confidence', 0.6)
                )
                stats[result['action']] = stats.get(result['action'], 0) + 1
            
            elif mem_type == 'fact':
                result = self.update_or_create_fact(
                    category=ext.get('category', 'general'),
                    key=ext.get('key', ''),
                    value=ext.get('value', ''),
                    confidence=ext.get('confidence', 0.75)
                )
                stats[result['action']] = stats.get(result['action'], 0) + 1
        
        logger.info(f"[Updater] 批量更新完成: {stats}")
        return stats


if __name__ == "__main__":
    # 测试
    print("MemoryUpdater 测试")
    print("需要 MemoryPalace 实例才能运行完整测试")
