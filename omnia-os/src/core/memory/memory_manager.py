"""
Omnia Memory Manager - 记忆管理器

功能：
1. 存储对话历史
2. 检索相关记忆
3. 压缩记忆（可选）
4. 维护记忆索引

设计原则：
- 先实现基础功能，不依赖嵌入模型
- 使用关键词检索作为临时方案
- 支持后续升级到向量检索
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import re
import jieba
from collections import defaultdict


@dataclass
class Memory:
    """单条记忆"""
    id: str
    content: str
    role: str  # "user" or "assistant"
    timestamp: str
    keywords: List[str] = field(default_factory=list)
    importance: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class MemoryManager:
    """
    记忆管理器
    
    功能：
    1. 存储对话历史
    2. 检索相关记忆
    3. 压缩记忆（可选）
    """
    
    def __init__(
        self,
        max_memories: int = 1000,
        enable_compression: bool = False
    ):
        self.max_memories = max_memories
        self.enable_compression = enable_compression
        
        # 记忆存储
        self.memories: List[Memory] = []
        
        # 关键词索引（用于快速检索）
        self.keyword_index: Dict[str, List[str]] = defaultdict(list)
        
        # 统计信息
        self.stats = {
            "total_memories": 0,
            "total_retrievals": 0,
            "avg_retrieval_time": 0.0,
            "compression_ratio": 0.0
        }
    
    def add_memory(
        self,
        content: str,
        role: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Memory:
        """
        添加记忆
        
        Args:
            content: 记忆内容
            role: 角色（"user" 或 "assistant"）
            metadata: 元数据
        
        Returns:
            创建的记忆对象
        """
        # 生成记忆 ID
        memory_id = f"{role}_{datetime.now().isoformat()}_{len(self.memories)}"
        
        # 提取关键词
        keywords = self._extract_keywords(content)
        
        # 创建记忆对象
        memory = Memory(
            id=memory_id,
            content=content,
            role=role,
            timestamp=datetime.now().isoformat(),
            keywords=keywords,
            metadata=metadata or {}
        )
        
        # 添加到存储
        self.memories.append(memory)
        
        # 更新关键词索引
        for keyword in keywords:
            self.keyword_index[keyword].append(memory_id)
        
        # 更新统计
        self.stats["total_memories"] += 1
        
        # 检查是否需要清理旧记忆
        if len(self.memories) > self.max_memories:
            self._cleanup_old_memories()
        
        return memory
    
    def retrieve_relevant(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3
    ) -> List[Tuple[Memory, float]]:
        """
        检索相关记忆
        
        Args:
            query: 查询文本
            top_k: 返回 top-k 结果
            min_score: 最小相似度阈值
        
        Returns:
            (记忆, 相似度) 列表
        """
        import time
        start_time = time.time()
        
        # 提取查询关键词
        query_keywords = self._extract_keywords(query)
        
        # 计算每条记忆的相似度
        scores: List[Tuple[Memory, float]] = []
        
        for memory in self.memories:
            # 计算关键词重叠度
            overlap = len(set(memory.keywords) & set(query_keywords))
            total = len(set(memory.keywords) | set(query_keywords))
            
            if total > 0:
                similarity = overlap / total
            else:
                similarity = 0.0
            
            # 只保留相似度高于阈值的记忆
            if similarity >= min_score:
                scores.append((memory, similarity))
        
        # 按相似度排序
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # 更新统计
        elapsed = time.time() - start_time
        self.stats["total_retrievals"] += 1
        self.stats["avg_retrieval_time"] = (
            (self.stats["avg_retrieval_time"] * (self.stats["total_retrievals"] - 1) + elapsed)
            / self.stats["total_retrievals"]
        )
        
        return scores[:top_k]
    
    def get_recent_memories(self, n: int = 10) -> List[Memory]:
        """
        获取最近的 n 条记忆
        
        Args:
            n: 记忆数量
        
        Returns:
            记忆列表
        """
        return self.memories[-n:] if len(self.memories) >= n else self.memories
    
    def get_conversation_history(
        self,
        max_turns: int = 10
    ) -> List[Dict[str, str]]:
        """
        获取对话历史（用于 LLM API）
        
        Args:
            max_turns: 最大轮次
        
        Returns:
            消息列表 [{"role": "user", "content": "..."}]
        """
        recent = self.get_recent_memories(max_turns * 2)
        return [{"role": m.role, "content": m.content} for m in recent]
    
    def compress_old_memories(self) -> int:
        """
        压缩旧记忆
        
        Returns:
            压缩后的记忆数量
        """
        if not self.enable_compression:
            return len(self.memories)
        
        # TODO: 实现 MLA 压缩
        # 当前只是简单清理
        if len(self.memories) > self.max_memories * 0.8:
            # 保留最近 80% 的记忆
            keep_count = int(self.max_memories * 0.8)
            self.memories = self.memories[-keep_count:]
            
            # 重建索引
            self._rebuild_index()
        
        return len(self.memories)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        提取关键词
        
        使用 jieba 中文分词器进行智能分词
        
        Args:
            text: 文本
        
        Returns:
            关键词列表
        """
        # 中文停用词
        stop_words = {
            "的", "了", "是", "在", "我", "有", "和", "就",
            "不", "人", "都", "一", "一个", "上", "也", "很",
            "到", "说", "要", "去", "你", "会", "着", "没有",
            "看", "好", "自己", "这", "那", "什么", "怎么",
            "可以", "能", "吗", "呢", "吧", "啊", "嗯", "哦",
            "这个", "那个", "他", "她", "它", "我们", "你们",
            "他们", "她们", "它们", "但是", "因为", "所以",
            "如果", "虽然", "还是", "或者", "而且", "然后"
        }
        
        keywords = []
        
        try:
            # 使用 jieba 分词
            import jieba
            words = list(jieba.cut(text))
            
            # 过滤：停用词、单字、纯数字
            keywords = [
                word for word in words
                if len(word) >= 2 
                and word not in stop_words
                and not word.isdigit()
                and not word.isspace()
            ]
            
        except ImportError:
            # jieba 未安装，回退到正则
            words = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+|[0-9]+', text.lower())
            keywords = [
                word for word in words
                if len(word) >= 2 and word not in stop_words
            ]
        
        return list(set(keywords))

    def _cleanup_old_memories(self):
        """清理旧记忆"""
        # 保留最近 80% 的记忆
        keep_count = int(self.max_memories * 0.8)
        self.memories = self.memories[-keep_count:]
        
        # 重建索引
        self._rebuild_index()
    
    def _rebuild_index(self):
        """重建关键词索引"""
        self.keyword_index.clear()
        
        for memory in self.memories:
            for keyword in memory.keywords:
                self.keyword_index[keyword].append(memory.id)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "current_memories": len(self.memories),
            "unique_keywords": len(self.keyword_index),
            "max_memories": self.max_memories
        }
    
    def save_to_file(self, filepath: str):
        """保存记忆到文件"""
        data = {
            "memories": [
                {
                    "id": m.id,
                    "content": m.content,
                    "role": m.role,
                    "timestamp": m.timestamp,
                    "keywords": m.keywords,
                    "importance": m.importance,
                    "metadata": m.metadata
                }
                for m in self.memories
            ],
            "stats": self.stats
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_from_file(self, filepath: str):
        """从文件加载记忆"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.memories = [
            Memory(
                id=m["id"],
                content=m["content"],
                role=m["role"],
                timestamp=m["timestamp"],
                keywords=m["keywords"],
                importance=m.get("importance", 1.0),
                metadata=m.get("metadata", {})
            )
            for m in data.get("memories", [])
        ]
        
        self.stats = data.get("stats", self.stats)
        
        # 重建索引
        self._rebuild_index()
