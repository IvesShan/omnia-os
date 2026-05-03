"""Memory System — 记忆系统集成层.

统一接口，协调：
- MemoryExtractor（提取）
- MemoryUpdater（更新）
- MemoryRetriever（检索）
- MemoryCompressor（压缩）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.memory_palace.memory_palace import MemoryPalace
from core.memory_palace.memory_extractor import MemoryExtractor, ExtractedMemory
from core.memory_palace.memory_updater import MemoryUpdater
from core.memory_palace.memory_retriever import MemoryRetriever, ScoredMemory
from core.memory_palace.memory_compressor import MemoryCompressor, CompressionResult

logger = logging.getLogger(__name__)


@dataclass
class MemorySystemConfig:
    """记忆系统配置."""
    # 提取配置
    min_extraction_confidence: float = 0.6
    
    # 更新配置
    conflict_threshold: float = 0.85
    time_decay_days: float = 7.0
    
    # 检索配置
    semantic_weight: float = 0.6
    time_weight: float = 0.3
    confidence_weight: float = 0.1
    
    # 压缩配置
    merge_threshold: float = 0.85
    expiry_days: int = 90
    compression_interval_hours: int = 24


class MemorySystem:
    """记忆系统统一接口."""
    
    def __init__(self, db_path: Optional[Path] = None, 
                 config: Optional[MemorySystemConfig] = None):
        """初始化记忆系统.
        
        Args:
            db_path: 数据库路径
            config: 配置对象
        """
        self.config = config or MemorySystemConfig()
        
        # 核心组件
        self.palace = MemoryPalace(db_path)
        self.extractor = MemoryExtractor(
            min_confidence=self.config.min_extraction_confidence
        )
        self.updater = MemoryUpdater(self.palace)
        self.retriever = MemoryRetriever(self.palace)
        self.compressor = MemoryCompressor(self.palace)
        
        # 设置检索器参数
        self.retriever.HALF_LIFE_DAYS = self.config.time_decay_days
        self.retriever.SEMANTIC_WEIGHT = self.config.semantic_weight
        self.retriever.TIME_WEIGHT = self.config.time_weight
        self.retriever.CONFIDENCE_WEIGHT = self.config.confidence_weight
        
        # 设置压缩器参数
        self.compressor.MERGE_THRESHOLD = self.config.merge_threshold
        self.compressor.EXPIRY_DAYS = self.config.expiry_days
        
        logger.info("[MemorySystem] 初始化完成")
    
    # ------------------------------------------------------------------
    # 提取 + 存储
    # ------------------------------------------------------------------
    def process_message(self, message: str, role: str = "user") -> Dict[str, Any]:
        """处理消息：提取 + 存储.
        
        Args:
            message: 用户消息
            role: 角色
        
        Returns:
            处理结果
        """
        # 提取
        extractions = self.extractor.extract(message, role)
        
        if not extractions:
            return {'extracted': 0, 'stored': 0}
        
        # 存储
        stats = {'extracted': len(extractions), 'stored': 0, 'skipped': 0}
        
        for ext in extractions:
            if ext.memory_type == 'preference':
                result = self.updater.update_or_create_fact(
                    category='preference',
                    key=ext.key,
                    value=ext.value,
                    confidence=ext.confidence
                )
            elif ext.memory_type == 'habit':
                result = self.updater.update_or_create_habit(
                    domain='behavior',
                    pattern=ext.key,
                    evidence=ext.evidence,
                    certainty=ext.confidence
                )
            elif ext.memory_type == 'fact':
                result = self.updater.update_or_create_fact(
                    category=ext.category,
                    key=ext.key,
                    value=ext.value,
                    confidence=ext.confidence
                )
            else:
                continue
            
            if result.get('action') in ['create', 'update']:
                stats['stored'] += 1
            elif result.get('action') == 'skip':
                stats['skipped'] += 1
        
        logger.info(f"[MemorySystem] 处理消息: 提取 {stats['extracted']}, 存储 {stats['stored']}")
        return stats
    
    # ------------------------------------------------------------------
    # 检索
    # ------------------------------------------------------------------
    def recall(self, query: str, top_k: int = 5) -> Dict[str, List[ScoredMemory]]:
        """检索相关记忆.
        
        Args:
            query: 查询文本
            top_k: 每层返回数量
        
        Returns:
            各层检索结果
        """
        return self.retriever.retrieve_all(query, top_k)
    
    def recall_facts(self, query: str, top_k: int = 10) -> List[ScoredMemory]:
        """检索事实."""
        return self.retriever.retrieve_facts(query, top_k)
    
    def recall_habits(self, query: str, top_k: int = 10) -> List[ScoredMemory]:
        """检索习惯."""
        return self.retriever.retrieve_habits(query, top_k)
    
    def get_recent(self, days: int = 7) -> Dict[str, List[Dict]]:
        """获取最近的记忆."""
        return self.retriever.get_recent_memories(days)
    
    # ------------------------------------------------------------------
    # 压缩
    # ------------------------------------------------------------------
    def compress(self, dry_run: bool = False) -> Dict[str, CompressionResult]:
        """压缩记忆."""
        return self.compressor.compress_all(dry_run)
    
    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------
    def get_stats(self) -> Dict[str, Any]:
        """获取记忆系统统计."""
        facts = self.palace.recall_facts()
        habits = self.palace.recall_habits()
        timeline = self.palace.recall_timeline()
        
        return {
            'total_facts': len(facts),
            'total_habits': len(habits),
            'total_timeline': len(timeline),
            'active_facts': len([f for f in facts if f.get('status') == 'active']),
            'active_habits': len([h for h in habits if h.get('status') == 'active']),
        }
    
    # ------------------------------------------------------------------
    # 便捷方法
    # ------------------------------------------------------------------
    def remember(self, key: str, value: str, category: str = "general",
                 confidence: float = 0.8) -> Dict[str, Any]:
        """便捷方法：记住一个事实."""
        return self.updater.update_or_create_fact(
            category=category,
            key=key,
            value=value,
            confidence=confidence
        )
    
    def forget(self, key: str, category: str = "general") -> bool:
        """便捷方法：忘记一个事实."""
        facts = self.palace.recall_facts(category=category, key=key)
        if facts:
            self.palace.forget_fact(facts[0]['id'])
            return True
        return False


# 单例
_memory_system: Optional[MemorySystem] = None


def get_memory_system(db_path: Optional[Path] = None,
                      config: Optional[MemorySystemConfig] = None) -> MemorySystem:
    """获取记忆系统单例."""
    global _memory_system
    if _memory_system is None:
        _memory_system = MemorySystem(db_path, config)
    return _memory_system


if __name__ == "__main__":
    # 测试
    print("MemorySystem 测试")
    
    # 创建测试实例
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_memory.db"
        system = MemorySystem(db_path)
        
        # 测试提取
        test_msg = "我喜欢绿色，每天早上都会喝咖啡"
        result = system.process_message(test_msg)
        print(f"提取结果: {result}")
        
        # 测试检索
        recalled = system.recall("绿色")
        print(f"检索结果: {len(recalled['facts'])} 条事实")
        
        # 测试统计
        stats = system.get_stats()
        print(f"统计: {stats}")
