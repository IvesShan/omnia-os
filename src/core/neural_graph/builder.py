"""Memory Palace to Neural Graph Builder - 从记忆宫殿构建神经图谱"""
from __future__ import annotations

from core.logging_config import get_logger

logger = get_logger(__name__)


import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .graph import NeuralGraph, Entity, Relation
from .extractor import EntityExtractor
from .inferencer import RelationInferencer
from core.config import MEMORY_PALACE_DB



class MemoryPalaceGraphBuilder:
    """从 Memory Palace 构建神经图谱"""
    
    def __init__(self, db_path: str = None, api_key: str = None, provider: str = None):
        self.db_path = db_path or str(MEMORY_PALACE_DB)
        self.graph = NeuralGraph(self.db_path)
        self.extractor = EntityExtractor(api_key, provider)
        self.inferencer = RelationInferencer()
        
        # 统计
        self.stats = {
            "processed": 0,
            "nodes_added": 0,
            "edges_added": 0,
            "errors": 0,
        }
    
    def build_all(self, batch_size: int = 100, use_llm: bool = False) -> Dict:
        """从 Memory Palace 构建完整图谱
        
        Args:
            batch_size: 每批处理数量
            use_llm: 是否使用 LLM 补充（空闲时为 True）
        
        Returns:
            构建统计
        """
        logger.info(f"[GraphBuilder] 开始从 Memory Palace 构建图谱...")
        
        # 处理各层
        self._process_facts(batch_size, use_llm)
        self._process_relations(batch_size)
        self._process_timeline(batch_size, use_llm)
        self._process_habits(batch_size, use_llm)
        
        logger.info(f"[GraphBuilder] 完成！")
        print(f"  - 处理记忆: {self.stats['processed']} 条")
        print(f"  - 添加节点: {self.stats['nodes_added']} 个")
        print(f"  - 添加边: {self.stats['edges_added']} 条")
        
        return self.stats
    
    def _process_facts(self, batch_size: int, use_llm: bool):
        """处理 facts 表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM facts")
            total = cursor.fetchone()[0]
            
            print(f"[GraphBuilder] 处理 facts: {total} 条")
            
            cursor.execute("""
                SELECT id, key, value, category
                FROM facts
            """)
            
            rows = cursor.fetchall()
        
        for i, row in enumerate(rows):
            if i % 50 == 0:
                print(f"  进度: {i}/{total}")
            
            self._process_memory(
                memory_id=str(row['id']),
                text=f"{row['key']} {row['value']}",
                layer="facts",
                use_llm=use_llm,
            )
    
    def _process_relations(self, batch_size: int):
        """处理 relations 表（已有关系，直接添加）"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM relations")
            total = cursor.fetchone()[0]
            
            print(f"[GraphBuilder] 处理 relations: {total} 条")
            
            cursor.execute("""
                SELECT id, subject, predicate, object, context, created_at
                FROM relations
                ORDER BY created_at DESC
            """)
            
            rows = cursor.fetchall()
        
        for row in rows:
            # 提取实体
            entities = self.extractor.extract(f"{row['subject']} {row['object']}")
            
            # 添加节点
            for entity in entities:
                self.graph.add_node(entity.type, entity.name, entity.canonical_name, entity.properties)
                self.stats['nodes_added'] += 1
            
            # 直接添加关系
            if row['subject'] and row['object']:
                relation = Relation(
                    source=row['subject'],
                    target=row['object'],
                    type=self._normalize_predicate(row['predicate']),
                    weight=0.8,  # 已有关系权重较高
                    evidence=json.dumps({"relation_id": row['id'], "layer": "relations"}),
                )
                self.graph.add_edge(relation.source, relation.target, relation.type, relation.weight, relation.evidence)
                self.stats['edges_added'] += 1
            
            self.stats['processed'] += 1
    
    def _process_timeline(self, batch_size: int, use_llm: bool):
        """处理 timeline 表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM timeline")
            total = cursor.fetchone()[0]
            
            print(f"[GraphBuilder] 处理 timeline: {total} 条")
            
            cursor.execute("""
                SELECT id, event_date, event_type, title, description, tags
                FROM timeline
                ORDER BY event_date DESC
            """)
            
            rows = cursor.fetchall()
        
        for i, row in enumerate(rows):
            if i % 50 == 0:
                print(f"  进度: {i}/{total}")
            
            text = f"{row['title']} {row['description'] or ''} {row['tags'] or ''}"
            self._process_memory(
                memory_id=str(row['id']),
                text=text,
                layer="timeline",
                use_llm=use_llm,
            )
    
    def _process_habits(self, batch_size: int, use_llm: bool):
        """处理 habits 表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM habits")
            total = cursor.fetchone()[0]
            
            print(f"[GraphBuilder] 处理 habits: {total} 条")
            
            # 使用 SELECT * 并动态获取列
            cursor.execute("SELECT * FROM habits")
            
            rows = cursor.fetchall()
        
        for i, row in enumerate(rows):
            if i % 50 == 0:
                print(f"  进度: {i}/{total}")
            
            # 动态获取字段
            pattern = row['pattern'] if 'pattern' in row.keys() else ''
            domain = row['domain'] if 'domain' in row.keys() else ''
            evidence = row['evidence'] if 'evidence' in row.keys() else ''
            
            text = f"{pattern} {domain} {evidence}"
            self._process_memory(
                memory_id=str(row['id']),
                text=text,
                layer="habits",
                use_llm=use_llm,
            )
    
    def _process_memory(self, memory_id: str, text: str, layer: str, use_llm: bool):
        """处理单条记忆"""
        try:
            # 提取实体
            entities = self.extractor.extract(text, use_llm=use_llm)
            
            if not entities:
                return
            
            # 添加节点
            for entity in entities:
                self.graph.add_node(entity.type, entity.name, entity.canonical_name, entity.properties)
                self.stats['nodes_added'] += 1
            
            # 推理关系
            if len(entities) >= 2:
                relations = self.inferencer.infer_batch(entities, text)
                for rel in relations:
                    rel.evidence = json.dumps({"memory_id": memory_id, "layer": layer})
                    self.graph.add_edge(rel.source, rel.target, rel.type, rel.weight, rel.evidence)
                    self.stats['edges_added'] += 1
            
            self.stats['processed'] += 1
            
        except (json.JSONDecodeError) as e:
            self.stats['errors'] += 1
            if self.stats['errors'] <= 5:
                print(f"  [Error] {e}")
    
    def _normalize_predicate(self, predicate: str) -> str:
        """规范化关系谓词"""
        mapping = {
            "属于": "BELONGS_TO",
            "相关": "RELATED_TO",
            "依赖": "DEPENDS_ON",
            "导致": "CAUSED_BY",
            "开发": "WORKED_ON",
            "参与": "WORKED_ON",
            "协作": "COLLABORATES_WITH",
        }
        
        return mapping.get(predicate, "RELATED_TO")
    
    def incremental_build(self, since: str = None):
        """增量构建（只处理新记忆）"""
        if since is None:
            # 获取最后处理时间
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT MAX(created_at) FROM neural_edges
                """)
                result = cursor.fetchone()
            
            if result and result[0]:
                since = result[0]
            else:
                # 首次构建
                return self.build_all()
        
        print(f"[GraphBuilder] 增量构建，从 {since}")
        
        # 只处理 created_at > since 的记忆
        # TODO: 实现增量逻辑
        
        return self.stats


class IdleGraphProcessor:
    """空闲时自动处理图谱"""
    
    IDLE_THRESHOLD = 5 * 60  # 5分钟无交互
    BATCH_SIZE = 50
    CPU_THRESHOLD = 0.5
    
    def __init__(self, db_path: str = None, api_key: str = None, provider: str = None):
        self.builder = MemoryPalaceGraphBuilder(db_path, api_key, provider)
        self.last_interaction = time.time()
        self.last_build = None
    
    def record_interaction(self):
        """记录用户交互"""
        self.last_interaction = time.time()
    
    def is_idle(self) -> bool:
        """是否空闲"""
        return (time.time() - self.last_interaction) > self.IDLE_THRESHOLD
    
    def should_process(self) -> bool:
        """是否应该处理"""
        if not self.is_idle():
            return False
        
        # 检查 CPU 负载
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=1) / 100
            if cpu > self.CPU_THRESHOLD:
                return False
        except Exception:
            pass
        
        # 检查是否有未处理的记忆
        # TODO: 实现检查逻辑
        
        return True
    
    def process_batch(self):
        """处理一批记忆"""
        logger.info(f"[IdleProcessor] 开始空闲处理...")
        
        try:
            stats = self.builder.build_all(
                batch_size=self.BATCH_SIZE,
                use_llm=True  # 空闲时使用 LLM
            )
            
            self.last_build = datetime.now().isoformat()
            
            print(f"[IdleProcessor] 处理完成: {stats}")
            return stats
            
        except (ValueError) as e:
            print(f"[IdleProcessor] 错误: {e}")
            return None
    
    def run_if_idle(self):
        """如果空闲则运行"""
        if self.should_process():
            return self.process_batch()
        return None


# 便捷函数
def build_neural_graph(api_key: str = None, provider: str = None) -> Dict:
    """构建神经图谱"""
    builder = MemoryPalaceGraphBuilder(api_key=api_key, provider=provider)
    return builder.build_all()
