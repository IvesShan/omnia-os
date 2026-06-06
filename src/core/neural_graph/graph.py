"""Neural Graph - Memory Palace 的索引层"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


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
        with sqlite3.connect(self.db_path) as conn:
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
            
            conn.commit()
    
    def add_node(self, entity_type: str, entity_name: str, 
                 canonical_name: str = None, properties: Dict = None) -> str:
        """添加节点，返回节点ID（自动去重：先检查是否已存在同名节点）"""
        import uuid
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 先检查是否已存在同名节点（按 canonical_name 去重）
            cursor.execute("""
                SELECT id FROM neural_nodes 
                WHERE canonical_name = ? OR entity_name = ?
                LIMIT 1
            """, (canonical_name or entity_name, entity_name))
            existing = cursor.fetchone()
            
            if existing:
                # 已存在，返回已有 ID
                return existing[0]
            
            # 不存在，创建新节点
            node_id = f"entity_{uuid.uuid4().hex[:8]}"
            
            cursor.execute("""
                INSERT OR REPLACE INTO neural_nodes 
                (id, entity_type, entity_name, canonical_name, properties, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (node_id, entity_type, entity_name, canonical_name or entity_name, 
                  json.dumps(properties) if properties else None))
            
            conn.commit()
        
        return node_id
    
    def add_edge(self, source_name: str, target_name: str, relation_type: str,
                 weight: float = 0.5, evidence: str = None) -> str:
        """添加边，返回边ID"""
        import uuid
        edge_id = f"edge_{uuid.uuid4().hex[:8]}"
        
        with sqlite3.connect(self.db_path) as conn:
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
        
        return edge_id
    
    def get_stats(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM neural_nodes")
            nodes_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM neural_edges")
            edges_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT entity_type, COUNT(*) FROM neural_nodes GROUP BY entity_type")
            by_type = dict(cursor.fetchall())
            
            cursor.execute("SELECT relation_type, COUNT(*) FROM neural_edges GROUP BY relation_type")
            by_relation = dict(cursor.fetchall())
        
        return {
            "nodes": nodes_count,
            "edges": edges_count,
            "nodes_by_type": by_type,
            "edges_by_relation": by_relation
        }
    
    def export_to_json(self, limit: int = 10000, min_weight: float = 0.0) -> Dict[str, Any]:
        """导出图谱为 JSON 格式（用于前端可视化）

        策略：返回所有节点（按 canonical_name 去重），以及 limit 条高质量边，确保图谱完整。
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 1. 获取所有节点（按 canonical_name 去重，保留每组第一条）
            cursor.execute("""
                SELECT id, entity_type, entity_name, canonical_name, properties, access_count
                FROM neural_nodes
                WHERE id IN (
                    SELECT MIN(id) FROM neural_nodes
                    GROUP BY COALESCE(canonical_name, entity_name)
                )
            """)
            all_nodes = cursor.fetchall()

            # 2. 获取所有有效边
            cursor.execute("""
                SELECT DISTINCT e.source_name, e.target_name, e.relation_type, e.weight
                FROM neural_edges e
                WHERE e.weight >= ?
                  AND e.source_name != e.target_name
                ORDER BY e.weight DESC
            """, (min_weight,))
            all_edges_raw = cursor.fetchall()

            # 3. 去重（基于 source+target+relation）
            seen_edges = set()
            all_edges = []
            for e in all_edges_raw:
                edge_key = (e[0], e[1], e[2])
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    all_edges.append(e)

            # 4. 截取边到 limit
            edges = all_edges[:limit]

            # 5. 构建节点映射
            name_to_node = {}
            for n in all_nodes:
                name_to_node[n[2]] = n  # entity_name
                if n[3]:  # canonical_name
                    name_to_node[n[3]] = n

            # 6. 收集边涉及的节点名称
            edge_node_names = set()
            for e in edges:
                edge_node_names.add(e[0])
                edge_node_names.add(e[1])

            # 7. 优先返回边涉及的节点，然后补充其他节点（直到全部）
            # 这样确保有连接关系的节点优先展示
            result_nodes = []
            seen_node_names = set()

            # 先添加边涉及的节点
            for name in edge_node_names:
                if name in name_to_node and name not in seen_node_names:
                    seen_node_names.add(name)
                    result_nodes.append(name_to_node[name])

            # 再添加其他节点（有访问记录的优先）
            other_nodes = []
            for n in all_nodes:
                if n[2] not in seen_node_names:
                    other_nodes.append(n)
            
            # 按访问次数排序
            other_nodes.sort(key=lambda x: x[5] or 0, reverse=True)
            result_nodes.extend(other_nodes)

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
                    for n in result_nodes
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
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, entity_type, entity_name, canonical_name
                FROM neural_nodes
                WHERE entity_name LIKE ? OR canonical_name LIKE ?
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit))
            
            results = cursor.fetchall()
        
        return [{"id": r[0], "type": r[1], "name": r[2]} for r in results]
    
    def get_connected_nodes(self, node_name: str, depth: int = 2) -> Dict:
        """获取与指定节点相连的所有节点（用于图谱展开）"""
        with sqlite3.connect(self.db_path) as conn:
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
        
        return {"nodes": result_nodes, "edges": result_edges}
    
    # ==================== 高级查询方法（供 Router 调用） ====================
    
    def get_node(self, name: str) -> Optional[Dict]:
        """获取单个节点详情"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 先尝试精确匹配
            cursor.execute("""
                SELECT id, entity_type, entity_name, canonical_name, properties, 
                       access_count, created_at, last_accessed
                FROM neural_nodes
                WHERE entity_name = ? OR canonical_name = ?
                LIMIT 1
            """, (name, name))
            row = cursor.fetchone()
            
            if not row:
                # 模糊匹配
                cursor.execute("""
                    SELECT id, entity_type, entity_name, canonical_name, properties,
                           access_count, created_at, last_accessed
                    FROM neural_nodes
                    WHERE entity_name LIKE ? OR canonical_name LIKE ?
                    LIMIT 1
                """, (f"%{name}%", f"%{name}%"))
                row = cursor.fetchone()
            
            if not row:
                return None
            
            node_id = row[0]
            
            # 获取相关边
            cursor.execute("""
                SELECT source_name, target_name, relation_type, weight
                FROM neural_edges
                WHERE source_id = ? OR target_id = ?
                ORDER BY weight DESC
                LIMIT 20
            """, (node_id, node_id))
            
            edges = []
            for edge in cursor.fetchall():
                edges.append({
                    "source": edge[0],
                    "target": edge[1],
                    "relation": edge[2],
                    "weight": edge[3]
                })
            
            return {
                "id": row[0],
                "type": row[1],
                "name": row[2],
                "canonical_name": row[3],
                "properties": json.loads(row[4]) if row[4] else {},
                "access_count": row[5] or 0,
                "created_at": row[6],
                "last_accessed": row[7],
                "connections": edges
            }
    
    def get_related(self, name: str, max_depth: int = 2) -> List[Dict]:
        """获取与指定节点相关的所有节点（BFS 1-2 层）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 找到节点
            cursor.execute("""
                SELECT id FROM neural_nodes 
                WHERE entity_name = ? OR canonical_name = ?
                LIMIT 1
            """, (name, name))
            row = cursor.fetchone()
            
            if not row:
                return []
            
            node_id = row[0]
            visited = {node_id}
            result = []
            
            queue = [(node_id, 0)]
            while queue:
                current_id, depth = queue.pop(0)
                if depth >= max_depth:
                    continue
                
                # 双向查找
                cursor.execute("""
                    SELECT id, source_id, target_id, source_name, target_name, 
                           relation_type, weight
                    FROM neural_edges
                    WHERE source_id = ? OR target_id = ?
                    ORDER BY weight DESC
                    LIMIT 10
                """, (current_id, current_id))
                
                for edge in cursor.fetchall():
                    edge_id = edge[0]
                    neighbor_id = edge[2] if edge[1] == current_id else edge[1]
                    neighbor_name = edge[4] if edge[1] == current_id else edge[3]
                    relation = edge[5]
                    weight = edge[6]
                    
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        
                        # 获取邻居节点详情
                        cursor.execute("""
                            SELECT entity_type, entity_name, canonical_name
                            FROM neural_nodes WHERE id = ?
                        """, (neighbor_id,))
                        node_info = cursor.fetchone()
                        
                        if node_info:
                            result.append({
                                "id": neighbor_id,
                                "type": node_info[0],
                                "name": node_info[1],
                                "canonical_name": node_info[2],
                                "relation": relation,
                                "weight": weight,
                                "depth": depth + 1
                            })
                            
                            if depth + 1 < max_depth:
                                queue.append((neighbor_id, depth + 1))
            
            # 按权重排序
            result.sort(key=lambda x: x["weight"], reverse=True)
            return result
    
    def find_path(self, source: str, target: str, max_depth: int = 4) -> Optional[List[Dict]]:
        """查找两个节点之间的最短路径（代理到 NeuralGraphAlgorithms）"""
        from src.core.neural_graph_algorithms import NeuralGraphAlgorithms
        
        # 先找到节点 ID
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id FROM neural_nodes 
                WHERE entity_name = ? OR canonical_name = ? LIMIT 1
            """, (source, source))
            source_row = cursor.fetchone()
            
            cursor.execute("""
                SELECT id FROM neural_nodes 
                WHERE entity_name = ? OR canonical_name = ? LIMIT 1
            """, (target, target))
            target_row = cursor.fetchone()
        
        if not source_row or not target_row:
            return None
        
        algo = NeuralGraphAlgorithms(db_path=self.db_path)
        return algo.find_path(source_row[0], target_row[0], max_depth=max_depth)
    
    def find_all_paths(self, source: str, target: str, max_depth: int = 3, limit: int = 5) -> List[List[Dict]]:
        """查找两个节点之间的所有路径（代理到 NeuralGraphAlgorithms）"""
        from src.core.neural_graph_algorithms import NeuralGraphAlgorithms
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id FROM neural_nodes 
                WHERE entity_name = ? OR canonical_name = ? LIMIT 1
            """, (source, source))
            source_row = cursor.fetchone()
            
            cursor.execute("""
                SELECT id FROM neural_nodes 
                WHERE entity_name = ? OR canonical_name = ? LIMIT 1
            """, (target, target))
            target_row = cursor.fetchone()
        
        if not source_row or not target_row:
            return []
        
        algo = NeuralGraphAlgorithms(db_path=self.db_path)
        return algo.find_all_paths(source_row[0], target_row[0], max_depth=max_depth, limit=limit)
    
    def degree_centrality(self, top_k: int = 20) -> Dict[str, float]:
        """计算度中心性（代理到 NeuralGraphAlgorithms）"""
        from src.core.neural_graph_algorithms import NeuralGraphAlgorithms
        
        algo = NeuralGraphAlgorithms(db_path=self.db_path)
        results = algo.get_degree_centrality(top_k=top_k)
        return {r["name"]: r["total"] for r in results}
    
    def pagerank(self, top_k: int = 20) -> Dict[str, float]:
        """计算 PageRank（代理到 NeuralGraphAlgorithms）"""
        from src.core.neural_graph_algorithms import NeuralGraphAlgorithms
        
        algo = NeuralGraphAlgorithms(db_path=self.db_path)
        results = algo.get_pagerank(top_k=top_k)
        return {r["name"]: r["pagerank"] for r in results}
    
    def betweenness_centrality(self, top_k: int = 20) -> Dict[str, float]:
        """计算介数中心性（代理到 NeuralGraphAlgorithms）"""
        from src.core.neural_graph_algorithms import NeuralGraphAlgorithms
        
        algo = NeuralGraphAlgorithms(db_path=self.db_path)
        results = algo.get_betweenness_centrality(top_k=top_k)
        return {r["name"]: r["betweenness"] for r in results}
    
    def find_communities(self) -> List[Dict]:
        """发现社区结构（代理到 NeuralGraphAlgorithms）"""
        from src.core.neural_graph_algorithms import NeuralGraphAlgorithms
        
        algo = NeuralGraphAlgorithms(db_path=self.db_path)
        return algo.find_communities()
    
    def get_neighbors(self, node_id_or_name: str, depth: int = 1) -> Dict:
        """获取节点邻居（代理到 NeuralGraphAlgorithms）"""
        from src.core.neural_graph_algorithms import NeuralGraphAlgorithms
        
        # 如果传入的是名称，先找到 ID
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM neural_nodes 
                WHERE entity_name = ? OR canonical_name = ? OR id = ?
                LIMIT 1
            """, (node_id_or_name, node_id_or_name, node_id_or_name))
            row = cursor.fetchone()
        
        if not row:
            return {"error": "Node not found"}
        
        algo = NeuralGraphAlgorithms(db_path=self.db_path)
        return algo.get_neighbors(row[0], depth=depth)
    
    def recognize_intent(self, query: str) -> Dict:
        """简单意图识别（基于关键词匹配）"""
        query_lower = query.lower()
        
        intent_patterns = {
            "search": ["搜索", "查找", "寻找", "找", "search", "find", "查询"],
            "build": ["构建", "建立", "创建图谱", "build", "create"],
            "analyze": ["分析", "统计", "分析图谱", "analyze", "stats"],
            "visualize": ["可视化", "展示", "显示图谱", "visualize", "show"],
            "navigate": ["导航", "路径", "关系", "navigate", "path", "related"],
            "memory": ["记忆", "回忆", "记住", "memory", "remember"],
        }
        
        detected_intent = "general"
        confidence = 0.0
        entities = []
        
        for intent, keywords in intent_patterns.items():
            for kw in keywords:
                if kw in query_lower:
                    detected_intent = intent
                    confidence = max(confidence, 0.7)
                    break
        
        # 提取已知实体
        for entity_type, names in self.KNOWN_ENTITIES.items():
            for name in names:
                if name.lower() in query_lower:
                    entities.append(name)
                    confidence = max(confidence, 0.9)
        
        if not entities:
            # 从图谱中搜索可能的实体
            words = query.split()
            for word in words:
                if len(word) > 2:
                    results = self.search_nodes(word, limit=1)
                    if results:
                        entities.append(results[0]["name"])
                        confidence = max(confidence, 0.5)
        
        return {
            "intent": detected_intent,
            "confidence": round(confidence or 0.3, 2),
            "entities": entities
        }
    
    def extract_entities(self, text: str) -> List[Entity]:
        """从文本中提取实体（基于规则匹配）"""
        entities = []
        seen = set()
        
        # 1. 匹配已知实体
        for entity_type, names in self.KNOWN_ENTITIES.items():
            for name in names:
                if name.lower() in text.lower() and name not in seen:
                    seen.add(name)
                    entities.append(Entity(
                        type=entity_type,
                        name=name,
                        canonical_name=name,
                        confidence=0.9
                    ))
        
        # 2. 基于规则提取
        import re
        
        # 提取文件名
        file_pattern = r'[\w\-]+\.(py|js|ts|json|md|yml|yaml|toml|sh|sql|html|css|vue)'
        for match in re.finditer(file_pattern, text):
            fname = match.group(0)
            if fname not in seen:
                seen.add(fname)
                entities.append(Entity(type="FILE", name=fname, confidence=0.7))
        
        # 提取 URL
        url_pattern = r'https?://[^\s\)\]]+'
        for match in re.finditer(url_pattern, text):
            url = match.group(0)
            if url not in seen:
                seen.add(url)
                entities.append(Entity(type="URL", name=url, confidence=0.8))
        
        # 提取日期
        date_pattern = r'\d{4}[-/]\d{1,2}[-/]\d{1,2}'
        for match in re.finditer(date_pattern, text):
            date = match.group(0)
            if date not in seen:
                seen.add(date)
                entities.append(Entity(type="DATE", name=date, confidence=0.8))
        
        # 提取项目名（大写开头的英文词组）
        project_pattern = r'\b[A-Z][a-zA-Z]{2,}(?:\s+[A-Z][a-zA-Z]+)*\b'
        for match in re.finditer(project_pattern, text):
            name = match.group(0)
            if name not in seen and len(name) > 3 and name not in ('This', 'That', 'What', 'When', 'Where', 'How', 'The'):
                seen.add(name)
                entities.append(Entity(type="PROJECT", name=name, confidence=0.5))
        
        return entities
