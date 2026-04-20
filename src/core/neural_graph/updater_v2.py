"""Neural Graph Updater V2 - 使用改进的提取器"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from ..memory_palace import MemoryPalace
    from .graph import NeuralGraph

from .extractor_v2 import EntityExtractorV2, ExtractedRelation


@dataclass
class PendingMemory:
    memory_id: str
    text: str
    layer: str
    timestamp: float
    metadata: Dict[str, Any] = None


class NeuralGraphUpdaterV2:
    """使用 V2 提取器的图谱更新器"""
    
    BATCH_SIZE = 50
    QUEUE_THRESHOLD = 10
    IDLE_THRESHOLD = 300
    MAX_QUEUE_SIZE = 1000
    
    def __init__(self, graph: NeuralGraph = None, api_key: str = None, provider: str = None):
        if graph is None:
            from .graph import NeuralGraph
            graph = NeuralGraph()
        
        self.graph = graph
        self.extractor = EntityExtractorV2(api_key=api_key, provider=provider)
        
        self.pending_queue: deque[PendingMemory] = deque(maxlen=self.MAX_QUEUE_SIZE)
        self.last_activity = time.time()
        self.last_process_time = time.time()
        
        self.stats = {
            "total_collected": 0,
            "total_processed": 0,
            "total_entities": 0,
            "total_relations": 0,
            "errors": 0,
        }
        
        self._lock = threading.Lock()
        self._processing = False
    
    def on_memory_write(self, memory_id: str, text: str, layer: str, metadata: Dict = None):
        """Hook: 记忆写入时调用"""
        with self._lock:
            self.pending_queue.append(PendingMemory(
                memory_id=memory_id,
                text=text,
                layer=layer,
                timestamp=time.time(),
                metadata=metadata
            ))
            self.stats["total_collected"] += 1
            self.last_activity = time.time()
            
            # 队列满立即处理
            if len(self.pending_queue) >= self.QUEUE_THRESHOLD:
                self._process_batch()
    
    def process_all(self):
        """处理所有待处理记忆"""
        with self._lock:
            self._process_batch()
    
    def _process_batch(self):
        """批量处理"""
        if self._processing or not self.pending_queue:
            return
        
        self._processing = True
        
        try:
            batch = []
            while self.pending_queue and len(batch) < self.BATCH_SIZE:
                batch.append(self.pending_queue.popleft())
            
            if not batch:
                return
            
            for item in batch:
                try:
                    # 使用 V2 提取器
                    entities, relations = self.extractor.extract(item.text, use_llm=False)
                    
                    # 添加节点
                    for entity in entities:
                        self.graph.add_node(
                            entity_type=entity.type,
                            entity_name=entity.name,
                            canonical_name=entity.canonical_name,
                            properties=entity.properties
                        )
                    
                    # 添加关系
                    for rel in relations:
                        self.graph.add_edge(
                            source_name=rel.source,
                            target_name=rel.target,
                            relation_type=rel.relation,
                            evidence=item.memory_id
                        )
                    
                    self.stats["total_entities"] += len(entities)
                    self.stats["total_relations"] += len(relations)
                    self.stats["total_processed"] += 1
                    
                except Exception as e:
                    print(f"[UpdaterV2] Error processing {item.memory_id}: {e}")
                    self.stats["errors"] += 1
        
        finally:
            self._processing = False
            self.last_process_time = time.time()
    
    def get_stats(self) -> Dict:
        return {
            **self.stats,
            "queue_size": len(self.pending_queue),
            "last_activity": self.last_activity,
            "last_process": self.last_process_time,
        }
