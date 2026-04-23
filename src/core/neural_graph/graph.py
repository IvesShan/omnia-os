"""Neural Graph - Memory Palace 的索引层"""

from __future__ import annotations

import json
import sqlite3
import time
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Import shared vector service
from core.vector_ipc import get_hybrid_vector_service

# 统一使用 config.py 中的路径配置
from core.config import NEURAL_GRAPH_DB, MEMORY_PALACE_DB


@dataclass
class Entity:
    """实体节点"""
    type: str          # PERSON/PROJECT/FILE/EVENT/CONCEPT/DATE/LOCATION
    name: str
    canonical_name: str = None
    confidence: float = 1.0
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.canonical_name is None:
            self.canonical_name = self.name
        if self.properties is None:
            self.properties = {}


@dataclass
class Relation:
    """关系边"""
    source: str
    target: str
    type: str          # BELONGS_TO/RELATED_TO/DEPENDS_ON/CAUSED_BY/WORKED_ON/...
    weight: float = 0.5
    evidence: str = None  # 来源记忆 ID


class NeuralGraph:
    """神经图谱 - Memory Palace 的索引层"""
    
    # 已知实体词典
    KNOWN_ENTITIES = {
        "PERSON": ["原点", "无限", "李先生", "建筑师", "原点 (Yuán diǎn)"],
        "PROJECT": ["喵修匠", "懂机帝", "Omnia", "Omnia OS", "njuosun.com", "miaoxiujiang"],
        "FILE": ["README.md", "config.json", "package.json", ".env", "openclaw.json"],
        "CONCEPT": ["协作", "记忆", "工具调用", "部署", "API", "MCP", "飞书"],
    }
    
    def __init__(self, db_path: str = None):
        # 统一使用 config.py 中的路径
        self.db_path = db_path or str(MEMORY_PALACE_DB)
        self._vector_service = None  # Lazy-loaded
        self._init_schema()
    
    @property
    def vector_service(self):
        """Lazy-load vector service (singleton)."""
        if self._vector_service is None:
            self._vector_service = get_vector_service()
        return self._vector_service

    def _init_schema(self):
        """初始化数据库 schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建节点表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS neural_nodes (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                entity_name TEXT NOT NULL,
                canonical_name TEXT,
                aliases TEXT,
                properties TEXT,
                embedding BLOB,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_accessed TEXT,
                access_count INTEGER DEFAULT 0
            )
        """)
        
        # 创建边表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS neural_edges (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                source_name TEXT,
                target_name TEXT,
                relation_type TEXT NOT NULL,
                weight REAL DEFAULT 0.5,
                evidence TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_accessed TEXT,
                access_count INTEGER DEFAULT 0,
                FOREIGN KEY (source_id) REFERENCES neural_nodes(id),
                FOREIGN KEY (target_id) REFERENCES neural_nodes(id)
            )
        """)
    
    def add_node(self, entity_type: str, entity_name: str, 
                 canonical_name: str = None, properties: Dict = None) -> str:
        """添加节点，返回节点ID"""
        import uuid
        node_id = f"entity_{uuid.uuid4().hex[:8]}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO neural_nodes 
            (id, entity_type, entity_name, canonical_name, properties, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (node_id, entity_type, entity_name, canonical_name or entity_name, 
              json.dumps(properties) if properties else None))
        
        conn.commit()
        conn.close()
        return node_id
    
    def add_edge(self, source_name: str, target_name: str, relation_type: str,
                 weight: float = 0.5, evidence: str = None) -> str:
        """添加边，返回边ID"""
        import uuid
        edge_id = f"edge_{uuid.uuid4().hex[:8]}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 查找或创建节点
        cursor.execute("SELECT id FROM neural_nodes WHERE entity_name = ?", (source_name,))
        source_row = cursor.fetchone()
        source_id = source_row[0] if source_row else self.add_node("ENTITY", source_name)
        
        cursor.execute("SELECT id FROM neural_nodes WHERE entity_name = ?", (target_name,))
        target_row = cursor.fetchone()
        target_id = target_row[0] if target_row else self.add_node("ENTITY", target_name)
        
        cursor.execute("""
            INSERT OR REPLACE INTO neural_edges
            (id, source_id, target_id, source_name, target_name, relation_type, weight, evidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (edge_id, source_id, target_id, source_name, target_name, 
              relation_type, weight, evidence))
        
        conn.commit()
        conn.close()
        return edge_id
    
    def get_stats(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM neural_nodes")
        nodes_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM neural_edges")
        edges_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT entity_type, COUNT(*) FROM neural_nodes GROUP BY entity_type")
        by_type = dict(cursor.fetchall())
        
        cursor.execute("SELECT relation_type, COUNT(*) FROM neural_edges GROUP BY relation_type")
        by_relation = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "nodes": nodes_count,
            "edges": edges_count,
            "nodes_by_type": by_type,
            "edges_by_relation": by_relation
        }
    
    def export_to_json(self, limit: int = 100, min_weight: float = 0.0) -> Dict[str, Any]:
        """导出图谱为 JSON 格式（用于前端可视化）
        
        改进：优先返回业务关系，去重，限制低价值关系
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 关系优先级：业务关系 > 其他关系
        priority_relations = [
            'WORKED_ON', 'created', 'owns', '经营', '开发', '推出', '运营',
            'KNOWS_ABOUT', 'is_a', '契合', '赋能', 'depends_on'
        ]
        
        # 低价值关系（限制数量）
        low_value_relations = ['DEPENDS_ON', 'RELATED_TO', 'BELONGS_TO']
        
        # 1. 优先获取业务关系的边
        priority_placeholders = ','.join('?' * len(priority_relations))
        cursor.execute(f"""
            SELECT source_name, target_name, relation_type, weight
            FROM neural_edges
            WHERE relation_type IN ({priority_placeholders})
               AND weight >= ?
            ORDER BY created_at DESC
        """, priority_relations + [min_weight])
        priority_edges = cursor.fetchall()
        
        # 2. 获取低价值关系（限制数量）
        low_value_placeholders = ','.join('?' * len(low_value_relations))
        cursor.execute(f"""
            SELECT source_name, target_name, relation_type, weight
            FROM neural_edges
            WHERE relation_type IN ({low_value_placeholders})
               AND weight >= ?
            ORDER BY created_at DESC
            LIMIT ?
        """, low_value_relations + [min_weight, limit])
        low_value_edges = cursor.fetchall()
        
        # 3. 合并边并去重（基于 source+target+relation）
        all_edges_raw = priority_edges + low_value_edges
        seen_edges = set()
        all_edges = []
        for e in all_edges_raw:
            edge_key = (e[0], e[1], e[2])  # source, target, relation
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                all_edges.append(e)
        
        # 4. 提取所有涉及的节点名称
        node_names = set()
        for e in all_edges:
            node_names.add(e[0])  # source_name
            node_names.add(e[1])  # target_name
        
        # 5. 获取这些节点的详细信息
        if not node_names:
            conn.close()
            return {"nodes": [], "edges": []}
            
        placeholders = ','.join('?' * len(node_names))
        cursor.execute(f"""
            SELECT id, entity_type, entity_name, canonical_name, properties, access_count
            FROM neural_nodes
            WHERE entity_name IN ({placeholders})
               OR canonical_name IN ({placeholders})
        """, list(node_names) + list(node_names))
        nodes_data = cursor.fetchall()
        
        # 6. 创建名称到节点的映射
        name_to_node = {}
        for n in nodes_data:
            name_to_node[n[2]] = n  # entity_name
            if n[3]:  # canonical_name
                name_to_node[n[3]] = n
        
        conn.close()
        
        # 7. 过滤边：只保留两端节点都存在的边
        edges = []
        seen_node_names = set()
        for e in all_edges:
            source, target = e[0], e[1]
            if source in name_to_node and target in name_to_node:
                edges.append(e)
                seen_node_names.add(source)
                seen_node_names.add(target)
            if len(edges) >= limit * 2:
                break
        
        # 8. 只返回实际参与边的节点
        nodes = [name_to_node[name] for name in seen_node_names if name in name_to_node]
        
        # 限制节点数量
        if len(nodes) > limit:
            nodes = sorted(nodes, key=lambda n: n[5] or 0, reverse=True)[:limit]
            node_names_final = set(n[2] for n in nodes)
            edges = [e for e in edges if e[0] in node_names_final and e[1] in node_names_final]
        
        return {
            "nodes": [
                {
                    "id": n[0],
                    "type": n[1],
                    "name": n[2],
                    "canonical_name": n[3],
                    "properties": json.loads(n[4]) if n[4] else {},
                    "access_count": n[5] or 0
                }
                for n in nodes
            ],
            "edges": [
                {
                    "source": e[0],
                    "target": e[1],
                    "relation": e[2],
                    "weight": e[3]
                }
                for e in edges
            ]
        }

    def search_nodes(self, query: str, limit: int = 10) -> List[Dict]:
        """搜索节点"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, entity_type, entity_name, canonical_name
            FROM neural_nodes
            WHERE entity_name LIKE ? OR canonical_name LIKE ?
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return [{"id": r[0], "type": r[1], "name": r[2]} for r in results]
    
    def get_connected_nodes(self, node_name: str, depth: int = 2) -> Dict:
        """获取与指定节点相连的所有节点（用于图谱展开）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 找到节点
        cursor.execute("SELECT id FROM neural_nodes WHERE entity_name = ?", (node_name,))
        row = cursor.fetchone()
        if not row:
            return {"nodes": [], "edges": []}
        
        node_id = row[0]
        visited_nodes = {node_id}
        visited_edges = set()
        result_nodes = []
        result_edges = []
        
        # BFS 遍历
        queue = [(node_id, 0)]
        while queue:
            current_id, current_depth = queue.pop(0)
            if current_depth > depth:
                break
            
            # 获取节点信息
            cursor.execute("""
                SELECT id, entity_type, entity_name, canonical_name
                FROM neural_nodes WHERE id = ?
            """, (current_id,))
            node = cursor.fetchone()
            if node:
                result_nodes.append({
                    "id": node[0],
                    "type": node[1],
                    "name": node[2]
                })
            
            # 获取相连的边和节点
            cursor.execute("""
                SELECT id, source_id, target_id, source_name, target_name, relation_type, weight
                FROM neural_edges
                WHERE source_id = ? OR target_id = ?
            """, (current_id, current_id))
            
            for edge in cursor.fetchall():
                edge_id = edge[0]
                if edge_id not in visited_edges:
                    visited_edges.add(edge_id)
                    result_edges.append({
                        "source": edge[3],
                        "target": edge[4],
                        "relation": edge[5],
                        "weight": edge[6]
                    })
                    
                    # 添加相邻节点到队列
                    neighbor_id = edge[2] if edge[1] == current_id else edge[1]
                    if neighbor_id not in visited_nodes and current_depth < depth:
                        visited_nodes.add(neighbor_id)
                        queue.append((neighbor_id, current_depth + 1))
        
        conn.close()
        return {"nodes": result_nodes, "edges": result_edges}
