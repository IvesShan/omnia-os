"""
Omnia Neural Graph Algorithms - 神经图谱图算法

提供路径查找、中心度分析、社区发现等图算法
"""

import sqlite3
from typing import List, Dict, Any, Optional
from collections import defaultdict, deque
import random
import time
from pathlib import Path

# 使用统一配置
from core.config import MEMORY_PALACE_DB

DB_PATH = str(MEMORY_PALACE_DB)


class NeuralGraphAlgorithms:
    """神经图谱图算法引擎"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self._graph_cache = None
        self._cache_time = 0
    
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def load_graph(self, force_reload: bool = False) -> Dict[str, Any]:
        """加载图谱数据到内存"""
        current_time = time.time()
        
        # 缓存 60 秒
        if self._graph_cache and not force_reload and (current_time - self._cache_time) < 60:
            return self._graph_cache
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 加载节点
        cursor.execute("SELECT id, entity_type, entity_name, canonical_name FROM neural_nodes")
        nodes = {}
        for row in cursor.fetchall():
            nodes[row["id"]] = {
                "name": row["entity_name"] or row["canonical_name"] or row["id"],
                "type": row["entity_type"] or "DEFAULT"
            }
        
        # 加载边
        cursor.execute("SELECT source_id, target_id, relation_type, weight FROM neural_edges")
        edges = defaultdict(list)
        reverse_edges = defaultdict(list)
        
        for row in cursor.fetchall():
            source = row["source_id"]
            target = row["target_id"]
            rel_type = row["relation_type"] or "related_to"
            weight = row["weight"] or 1.0
            
            edges[source].append((target, rel_type, weight))
            reverse_edges[target].append((source, rel_type, weight))
        
        conn.close()
        
        self._graph_cache = {
            "nodes": nodes,
            "edges": dict(edges),
            "reverse_edges": dict(reverse_edges)
        }
        self._cache_time = current_time
        
        return self._graph_cache
    
    # ==================== 路径查找 ====================
    
    def find_path(self, start_id: str, end_id: str, max_depth: int = 4) -> Optional[List[Dict]]:
        """查找两个节点之间的最短路径（BFS）"""
        graph = self.load_graph()
        nodes = graph["nodes"]
        edges = graph["edges"]
        
        if start_id not in nodes or end_id not in nodes:
            return None
        
        queue = deque([(start_id, [start_id])])
        visited = {start_id}
        
        while queue:
            current, path = queue.popleft()
            
            if current == end_id:
                result = []
                for i, node_id in enumerate(path):
                    result.append({
                        "node": node_id,
                        "name": nodes[node_id]["name"],
                        "type": nodes[node_id]["type"]
                    })
                    
                    if i < len(path) - 1:
                        next_node = path[i + 1]
                        for target, rel_type, weight in edges.get(node_id, []):
                            if target == next_node:
                                result.append({"relation": rel_type, "weight": weight})
                                break
                return result
            
            if len(path) > max_depth:
                continue
            
            for neighbor, _, _ in edges.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None
    
    def find_all_paths(self, start_id: str, end_id: str, max_depth: int = 3, limit: int = 5) -> List[List[Dict]]:
        """查找两个节点之间的所有路径"""
        graph = self.load_graph()
        nodes = graph["nodes"]
        edges = graph["edges"]
        
        if start_id not in nodes or end_id not in nodes:
            return []
        
        results = []
        
        def dfs(current: str, path: List[str], visited: set):
            if len(results) >= limit:
                return
            
            if current == end_id:
                detailed_path = []
                for i, node_id in enumerate(path):
                    detailed_path.append({
                        "node": node_id,
                        "name": nodes[node_id]["name"],
                        "type": nodes[node_id]["type"]
                    })
                    
                    if i < len(path) - 1:
                        next_node = path[i + 1]
                        for target, rel_type, weight in edges.get(node_id, []):
                            if target == next_node:
                                detailed_path.append({"relation": rel_type, "weight": weight})
                                break
                
                results.append(detailed_path)
                return
            
            if len(path) > max_depth:
                return
            
            for neighbor, _, _ in edges.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    dfs(neighbor, path + [neighbor], visited)
                    visited.remove(neighbor)
        
        dfs(start_id, [start_id], {start_id})
        return results
    
    # ==================== 中心度分析 ====================
    
    def get_degree_centrality(self, top_k: int = 10) -> List[Dict]:
        """计算度中心性"""
        graph = self.load_graph()
        nodes = graph["nodes"]
        edges = graph["edges"]
        reverse_edges = graph["reverse_edges"]
        
        centrality = []
        for node_id, node_info in nodes.items():
            out_degree = len(edges.get(node_id, []))
            in_degree = len(reverse_edges.get(node_id, []))
            centrality.append({
                "node": node_id,
                "name": node_info["name"],
                "type": node_info["type"],
                "in_degree": in_degree,
                "out_degree": out_degree,
                "total": in_degree + out_degree
            })
        
        centrality.sort(key=lambda x: x["total"], reverse=True)
        return centrality[:top_k]
    
    def get_pagerank(self, top_k: int = 10, damping: float = 0.85, iterations: int = 20) -> List[Dict]:
        """计算 PageRank"""
        graph = self.load_graph()
        nodes = graph["nodes"]
        edges = graph["edges"]
        reverse_edges = graph["reverse_edges"]
        
        node_ids = list(nodes.keys())
        n = len(node_ids)
        
        if n == 0:
            return []
        
        pr = {node_id: 1.0 / n for node_id in node_ids}
        
        for _ in range(iterations):
            new_pr = {}
            for node_id in node_ids:
                incoming_sum = 0.0
                for source, _, _ in reverse_edges.get(node_id, []):
                    out_count = len(edges.get(source, []))
                    if out_count > 0:
                        incoming_sum += pr[source] / out_count
                
                new_pr[node_id] = (1 - damping) / n + damping * incoming_sum
            
            pr = new_pr
        
        results = []
        for node_id, score in pr.items():
            results.append({
                "node": node_id,
                "name": nodes[node_id]["name"],
                "type": nodes[node_id]["type"],
                "pagerank": round(score, 6)
            })
        
        results.sort(key=lambda x: x["pagerank"], reverse=True)
        return results[:top_k]
    
    def get_betweenness_centrality(self, top_k: int = 10, sample_size: int = 100) -> List[Dict]:
        """计算介数中心性"""
        graph = self.load_graph()
        nodes = graph["nodes"]
        edges = graph["edges"]
        
        node_ids = list(nodes.keys())
        betweenness = defaultdict(float)
        
        sample_nodes = random.sample(node_ids, min(sample_size, len(node_ids)))
        
        for start in sample_nodes:
            queue = deque([(start, [start])])
            visited = {start}
            
            while queue:
                current, path = queue.popleft()
                
                for node in path[1:-1]:
                    betweenness[node] += 1
                
                for neighbor, _, _ in edges.get(current, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, path + [neighbor]))
        
        max_val = max(betweenness.values()) if betweenness else 1
        
        results = []
        for node_id in node_ids:
            results.append({
                "node": node_id,
                "name": nodes[node_id]["name"],
                "type": nodes[node_id]["type"],
                "betweenness": round(betweenness.get(node_id, 0) / max_val, 4)
            })
        
        results.sort(key=lambda x: x["betweenness"], reverse=True)
        return results[:top_k]
    
    # ==================== 社区发现 ====================
    
    def find_communities(self) -> List[Dict]:
        """发现社区（标签传播算法）"""
        graph = self.load_graph()
        nodes = graph["nodes"]
        edges = graph["edges"]
        
        node_ids = list(nodes.keys())
        labels = {node_id: i for i, node_id in enumerate(node_ids)}
        
        for iteration in range(10):
            changed = False
            random.shuffle(node_ids)
            
            for node_id in node_ids:
                neighbor_labels = defaultdict(int)
                for neighbor, _, _ in edges.get(node_id, []):
                    neighbor_labels[labels[neighbor]] += 1
                
                for neighbor, _, _ in graph["reverse_edges"].get(node_id, []):
                    neighbor_labels[labels[neighbor]] += 1
                
                if neighbor_labels:
                    max_count = max(neighbor_labels.values())
                    candidates = [label for label, count in neighbor_labels.items() if count == max_count]
                    new_label = random.choice(candidates)
                    
                    if labels[node_id] != new_label:
                        labels[node_id] = new_label
                        changed = True
            
            if not changed:
                break
        
        # 按社区分组
        communities = defaultdict(list)
        for node_id, label in labels.items():
            communities[label].append({
                "node": node_id,
                "name": nodes[node_id]["name"],
                "type": nodes[node_id]["type"]
            })
        
        # 构建结果
        results = []
        for community_id, members in communities.items():
            type_counts = defaultdict(int)
            for member in members:
                type_counts[member["type"]] += 1
            
            dominant_type = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else "UNKNOWN"
            
            results.append({
                "community_id": community_id,
                "nodes": members,
                "size": len(members),
                "dominant_type": dominant_type
            })
        
        results.sort(key=lambda x: x["size"], reverse=True)
        return results
    
    # ==================== 邻居分析 ====================
    
    def get_neighbors(self, node_id: str, depth: int = 1) -> Dict[str, Any]:
        """获取节点的邻居"""
        graph = self.load_graph()
        nodes = graph["nodes"]
        edges = graph["edges"]
        reverse_edges = graph["reverse_edges"]
        
        if node_id not in nodes:
            return {"error": "Node not found"}
        
        result = {
            "node": node_id,
            "name": nodes[node_id]["name"],
            "type": nodes[node_id]["type"],
            "outgoing": [],
            "incoming": []
        }
        
        for target, rel_type, weight in edges.get(node_id, []):
            if target in nodes:
                result["outgoing"].append({
                    "target": target,
                    "target_name": nodes[target]["name"],
                    "relation": rel_type,
                    "weight": weight
                })
        
        for source, rel_type, weight in reverse_edges.get(node_id, []):
            if source in nodes:
                result["incoming"].append({
                    "source": source,
                    "source_name": nodes[source]["name"],
                    "relation": rel_type,
                    "weight": weight
                })
        
        return result
    
    def search_nodes(self, query: str, limit: int = 20) -> List[Dict]:
        """搜索节点"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, entity_type, entity_name, canonical_name 
            FROM neural_nodes 
            WHERE entity_name LIKE ? OR canonical_name LIKE ? OR id LIKE ?
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row["id"],
                "name": row["entity_name"] or row["canonical_name"] or row["id"],
                "type": row["entity_type"] or "DEFAULT"
            })
        
        conn.close()
        return results


# 全局实例
algorithms = NeuralGraphAlgorithms()
