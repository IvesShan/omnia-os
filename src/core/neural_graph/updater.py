"""Neural Graph Updater - 混合更新机制（Hook + 心跳）

设计原则：
1. Hook 收集：记忆写入时不阻塞，只入队列
2. 心跳处理：空闲时批量处理队列
3. 双重触发：队列满立即处理，空闲时也处理
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from ..memory_palace import MemoryPalace
    from .graph import NeuralGraph
    from .extractor import EntityExtractor
    from .inferencer import RelationInferencer


@dataclass
class PendingMemory:
    """待处理的记忆项"""
    memory_id: str
    text: str
    layer: str
    timestamp: float
    metadata: Dict[str, Any] = None


class NeuralGraphUpdater:
    """神经图谱更新器 - 混合机制"""
    
    # 配置
    BATCH_SIZE = 50           # 批处理大小
    QUEUE_THRESHOLD = 10      # 队列阈值（超过立即处理）
    IDLE_THRESHOLD = 300      # 空闲阈值（秒）
    MAX_QUEUE_SIZE = 1000     # 最大队列大小
    
    def __init__(
        self,
        graph: NeuralGraph = None,
        extractor: EntityExtractor = None,
        inferencer: RelationInferencer = None,
    ):
        # 自动初始化依赖
        if graph is None:
            from .graph import NeuralGraph
            graph = NeuralGraph()
        if extractor is None:
            from .extractor import EntityExtractor
            extractor = EntityExtractor()
        if inferencer is None:
            from .inferencer import RelationInferencer
            inferencer = RelationInferencer()
        
        self.graph = graph
        self.extractor = extractor
        self.inferencer = inferencer
        
        # 待处理队列
        self.pending_queue: deque[PendingMemory] = deque(maxlen=self.MAX_QUEUE_SIZE)
        
        # 活动追踪
        self.last_activity = time.time()
        self.last_process_time = time.time()
        
        # 统计
        self.stats = {
            "total_collected": 0,
            "total_processed": 0,
            "total_entities": 0,
            "total_relations": 0,
            "errors": 0,
        }
        
        # 锁（线程安全）
        self._lock = threading.Lock()
        self._processing = False
    
    # ------------------------------------------------------------------
    # Hook: 记忆写入时触发
    # ------------------------------------------------------------------
    
    def on_memory_write(
        self,
        memory_id: str,
        text: str,
        layer: str,
        metadata: Dict[str, Any] = None,
    ) -> None:
        """Hook: 记忆写入时调用（不阻塞）
        
        Args:
            memory_id: 记忆 ID
            text: 记忆文本
            layer: 记忆层（facts/relations/timeline/habits）
            metadata: 额外元数据
        """
        with self._lock:
            # 入队列
            self.pending_queue.append(PendingMemory(
                memory_id=memory_id,
                text=text,
                layer=layer,
                timestamp=time.time(),
                metadata=metadata or {},
            ))
            
            self.last_activity = time.time()
            self.stats["total_collected"] += 1
            
            # 队列超过阈值，异步处理
            if len(self.pending_queue) >= self.QUEUE_THRESHOLD:
                threading.Thread(
                    target=self._process_batch_async,
                    daemon=True,
                ).start()
    
    # ------------------------------------------------------------------
    # 心跳: 定期检查
    # ------------------------------------------------------------------
    
    def on_heartbeat(self, force: bool = False) -> Dict[str, Any]:
        """心跳: 检查是否需要处理
        
        Args:
            force: 强制处理（忽略空闲检查）
        
        Returns:
            处理结果统计
        """
        idle_time = time.time() - self.last_activity
        queue_size = len(self.pending_queue)
        
        # 判断是否需要处理
        should_process = force or (
            idle_time >= self.IDLE_THRESHOLD and queue_size > 0
        )
        
        if should_process:
            result = self._process_batch()
            return {
                "trigger": "heartbeat",
                "idle_time": idle_time,
                "processed": result.get("processed", 0),
                "entities": result.get("entities", 0),
                "relations": result.get("relations", 0),
                "error": result.get("error"),
            }
        
        return {
            "trigger": "heartbeat",
            "idle_time": idle_time,
            "queue_size": queue_size,
            "processed": 0,
            "skipped": True,
        }
    
    # ------------------------------------------------------------------
    # 批处理
    # ------------------------------------------------------------------
    
    def _process_batch_async(self) -> None:
        """异步批处理（不阻塞主流程）"""
        self._process_batch()
    
    def _process_batch(self) -> Dict[str, Any]:
        """批量处理待处理记忆
        
        Returns:
            处理结果统计
        """
        # 避免重复处理
        if self._processing:
            return {"processed": 0, "reason": "already_processing"}
        
        with self._lock:
            if not self.pending_queue:
                return {"processed": 0, "reason": "empty_queue"}
            
            self._processing = True
            
            try:
                # 取出一批
                batch = []
                for _ in range(min(self.BATCH_SIZE, len(self.pending_queue))):
                    if self.pending_queue:
                        batch.append(self.pending_queue.popleft())
                
                # 处理
                result = self._process_memories(batch)
                
                # 更新统计
                self.stats["total_processed"] += result.get("processed", 0)
                self.stats["total_entities"] += result.get("entities", 0)
                self.stats["total_relations"] += result.get("relations", 0)
                self.last_process_time = time.time()
                
                return result
                
            except Exception as e:
                self.stats["errors"] += 1
                print(f"[NeuralGraphUpdater] Error processing batch: {e}")
                return {"processed": 0, "error": str(e)}
                
            finally:
                self._processing = False
    
    def _process_memories(self, memories: List[PendingMemory]) -> Dict[str, Any]:
        """处理一批记忆
        
        Args:
            memories: 待处理记忆列表
        
        Returns:
            处理结果
        """
        if not self.graph or not self.extractor:
            return {"processed": 0, "reason": "no_graph_or_extractor"}
        
        total_entities = 0
        total_relations = 0
        
        for memory in memories:
            try:
                # 1. 提取实体
                entities = self.extractor.extract(
                    memory.text,
                    use_llm=False,  # Hook 时不使用 LLM（快速）
                )
                
                # 2. 添加节点
                for entity in entities:
                    node_id = self.graph.add_node(entity)
                    if node_id:
                        total_entities += 1
                
                # 3. 推断关系
                if self.inferencer and len(entities) >= 2:
                    relations = self.inferencer.infer_batch(
                        entities,
                        context=memory.layer,
                    )
                    
                    for relation in relations:
                        edge_id = self.graph.add_edge(relation)
                        if edge_id:
                            total_relations += 1
                
            except Exception as e:
                print(f"[NeuralGraphUpdater] Error processing memory {memory.memory_id}: {e}")
        
        return {
            "processed": len(memories),
            "entities": total_entities,
            "relations": total_relations,
        }
    
    # ------------------------------------------------------------------
    # 状态查询
    # ------------------------------------------------------------------
    
    def get_status(self) -> Dict[str, Any]:
        """获取更新器状态"""
        return {
            "queue_size": len(self.pending_queue),
            "is_processing": self._processing,
            "last_activity": self.last_activity,
            "last_process_time": self.last_process_time,
            "idle_time": time.time() - self.last_activity,
            "stats": self.stats.copy(),
        }
    
    def get_pending_count(self) -> int:
        """获取待处理数量"""
        return len(self.pending_queue)
    
    def clear_queue(self) -> int:
        """清空队列（返回清空的数量）"""
        with self._lock:
            count = len(self.pending_queue)
            self.pending_queue.clear()
            return count
