"""
Memory Adapter - 适配 MemoryV3 到 Omnia 系统

提供兼容旧接口的适配层，让 Omnia 无缝使用 MemoryV3
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json
from pathlib import Path

from .memory_v3 import MemoryV3


class MemoryAdapter:
    """
    记忆适配器 - 将 MemoryV3 适配到 Omnia 系统
    
    功能：
    1. 提供与旧 MemoryManager 兼容的接口
    2. 内部使用 MemoryV3 的版本化存储
    3. 自动处理版本控制
    """
    
    def __init__(
        self,
        db_path: str = None,
        session_id: str = None
    ):
        """
        初始化记忆适配器
        
        Args:
            db_path: 数据库路径（默认 ~/.omnia/memory_v3.db）
            session_id: 当前会话 ID
        """
        self.memory_v3 = MemoryV3(db_path)
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.turn_number = 0
        
        # 统计信息
        self.stats = {
            "total_memories": 0,
            "total_retrievals": 0
        }
    
    # ========== 对话记忆（兼容旧接口） ==========
    
    def add_memory(
        self,
        content: str,
        role: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """
        添加对话记忆
        
        Args:
            content: 记忆内容
            role: 角色（"user" 或 "assistant"）
            metadata: 元数据
        
        Returns:
            创建的记忆对象
        """
        self.turn_number += 1
        
        # 使用 MemoryV3 的对话日志功能
        log_id = self.memory_v3.log_conversation(
            session_id=self.session_id,
            role=role,
            content=content,
            metadata=metadata,
            turn_number=self.turn_number
        )
        
        self.stats["total_memories"] += 1
        
        return {
            "id": log_id,
            "content": content,
            "role": role,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata
        }
    
    def retrieve_relevant(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3
    ) -> List[Tuple[Dict, float]]:
        """
        检索相关记忆
        
        Args:
            query: 查询文本
            top_k: 返回 top-k 结果
            min_score: 最小相似度阈值
        
        Returns:
            (记忆, 相似度) 列表
        """
        # 使用 MemoryV3 的搜索功能
        results = self.memory_v3.search_conversations_simple(
            query=query,
            limit=top_k
        )
        
        self.stats["total_retrievals"] += 1
        
        # 转换为兼容格式
        memories = []
        for result in results:
            memory = {
                "id": result["id"],
                "content": result["content"],
                "role": result["role"],
                "timestamp": result["created_at"],
                "metadata": result.get("metadata", {})
            }
            # 简单相似度计算（基于是否匹配）
            similarity = 1.0 if query.lower() in result["content"].lower() else 0.5
            memories.append((memory, similarity))
        
        return memories
    
    # ========== 事实记忆（新功能） ==========
    
    def remember_fact(
        self,
        key: str,
        value: Any,
        category: str = None,
        source: str = "user"
    ) -> int:
        """
        记住事实（自动版本控制）
        
        Args:
            key: 事实键
            value: 事实值
            category: 分类
            source: 来源
        
        Returns:
            记录 ID
        """
        return self.memory_v3.add_fact(
            key=key,
            value=value,
            category=category,
            source=source
        )
    
    def recall_fact(self, key: str) -> Optional[Any]:
        """
        回忆事实
        
        Args:
            key: 事实键
        
        Returns:
            事实值（最新 active 版本）
        """
        fact = self.memory_v3.get_fact(key)
        if fact:
            return fact.get("value")
        return None
    
    def recall_fact_history(self, key: str) -> List[Dict]:
        """
        回忆事实的所有版本历史
        
        Args:
            key: 事实键
        
        Returns:
            所有版本列表
        """
        return self.memory_v3.get_fact_history(key)
    
    # ========== 关系记忆 ==========
    
    def remember_relation(
        self,
        subject: str,
        predicate: str,
        object: str,
        context: str = None
    ) -> int:
        """
        记住关系
        
        Args:
            subject: 主体
            predicate: 谓词
            object: 客体
            context: 上下文
        
        Returns:
            记录 ID
        """
        return self.memory_v3.add_relation(
            subject=subject,
            predicate=predicate,
            object=object,
            context=context
        )
    
    def recall_relations(
        self,
        subject: str = None,
        predicate: str = None,
        object: str = None
    ) -> List[Dict]:
        """
        回忆关系
        
        Args:
            subject: 主体（可选）
            predicate: 谓词（可选）
            object: 客体（可选）
        
        Returns:
            关系列表
        """
        return self.memory_v3.get_relations(
            subject=subject,
            predicate=predicate,
            object=object
        )
    
    # ========== 习惯记忆 ==========
    
    def observe_habit(
        self,
        domain: str,
        pattern: str,
        evidence: str = None,
        certainty: float = 0.5
    ) -> int:
        """
        观察到习惯
        
        Args:
            domain: 领域
            pattern: 模式
            evidence: 证据
            certainty: 确定性
        
        Returns:
            记录 ID
        """
        return self.memory_v3.add_habit(
            domain=domain,
            pattern=pattern,
            evidence=evidence,
            certainty=certainty
        )
    
    # ========== 时间线 ==========
    
    def record_event(
        self,
        event_date: str,
        title: str,
        event_type: str = None,
        description: str = None,
        tags: List[str] = None
    ) -> int:
        """
        记录事件
        
        Args:
            event_date: 事件日期
            title: 标题
            event_type: 类型
            description: 描述
            tags: 标签
        
        Returns:
            记录 ID
        """
        return self.memory_v3.add_timeline_event(
            event_date=event_date,
            title=title,
            event_type=event_type,
            description=description,
            tags=tags
        )
    
    # ========== 统计和导出 ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        v3_stats = self.memory_v3.get_stats()
        return {
            **self.stats,
            **v3_stats
        }
    
    def export_memories(self, include_deprecated: bool = False) -> Dict[str, Any]:
        """
        导出所有记忆
        
        Args:
            include_deprecated: 是否包含已废弃的记忆
        
        Returns:
            记忆数据
        """
        return self.memory_v3.export_to_json(include_deprecated=include_deprecated)
    
    def search_all(self, query: str, limit: int = 10) -> Dict[str, List]:
        """
        搜索所有类型的记忆
        
        Args:
            query: 搜索关键词
            limit: 每类返回数量
        
        Returns:
            各类记忆的搜索结果
        """
        return {
            "facts": self.memory_v3.search_facts(query, limit=limit),
            "conversations": self.memory_v3.search_conversations_simple(query, limit=limit)
        }


# 兼容别名
MemoryManager = MemoryAdapter
