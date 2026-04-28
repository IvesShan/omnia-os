"""Vector Integration - 将真正的向量嵌入集成到神经图谱

from core.logging_config import get_logger

logger = get_logger(__name__)

这个模块将 VectorStore 与 NeuralGraph 连接起来：
1. 为每个节点生成真正的语义向量
2. 支持语义相似度搜索
3. 自动同步节点和向量

Usage:
    from core.neural_graph import NeuralGraph
    from core.neural_graph.vector_integration import VectorIntegration
    
    graph = NeuralGraph()
    vi = VectorIntegration(graph)
    
    # 为所有节点生成向量
    vi.embed_all_nodes()
    
    # 语义搜索
    results = vi.semantic_search("用户偏好", top_k=5)
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# 使用 SharedVectorService（与 Memory Palace 共享）
from core.vector_ipc import get_hybrid_vector_service


class VectorIntegration:
    """
    将真正的向量嵌入集成到神经图谱
    
    Features:
    - 使用 SharedVectorService 生成语义向量（与 Memory Palace 共享）
    - 更新 NeuralGraph 中的 embedding 字段
    - 支持语义相似度搜索
    - 增量更新（只处理新节点）
    """
    
    def __init__(
        self,
        graph,  # NeuralGraph 实例
        model_name: str = "all-MiniLM-L6-v2",  # 保留参数用于兼容，实际使用 SharedVectorService
    ):
        self.graph = graph
        self.db_path = graph.db_path
        
        # 使用共享向量服务（单例）
        self._vector_service = get_vector_service()
        print(f"[VectorIntegration] Using SharedVectorService (fallback={self._vector_service._use_fallback})")
    
    def embed_text(self, text: str) -> np.ndarray:
        """生成文本的向量嵌入"""
        return self._vector_service.encode(text)
    
    def embed_node(self, entity_type: str, entity_name: str, properties: Dict = None) -> np.ndarray:
        """
        为节点生成向量
        
        策略：组合类型、名称、属性来生成语义向量
        """
        # 构建描述文本
        parts = [f"{entity_type}: {entity_name}"]
        
        if properties:
            # 提取关键属性
            for key in ["description", "role", "project", "context"]:
                if key in properties:
                    parts.append(f"{key}: {properties[key]}")
        
        text = " | ".join(parts)
        return self.embed_text(text)
    
    def update_node_embedding(self, node_id: str, embedding: np.ndarray) -> bool:
        """更新节点的向量"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE neural_nodes SET embedding = ? WHERE id = ?",
                    (embedding.tobytes(), node_id)
                )
                conn.commit()
            return True
        except (sqlite3.Error) as e:
            print(f"[VectorIntegration] Error updating embedding: {e}")
            return False
    
    def embed_all_nodes(self, batch_size: int = 100, force: bool = False) -> Dict:
        """
        为所有节点生成向量
        
        Args:
            batch_size: 批量处理大小
            force: 是否强制重新生成（即使已有向量）
        
        Returns:
            统计信息
        """
        logger.info(f"[VectorIntegration] 开始为节点生成向量...")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
        
        # 查询需要处理的节点
            if force:
                cursor.execute("""
                    SELECT id, entity_type, entity_name, properties
                    FROM neural_nodes
                """)
            else:
                cursor.execute("""
                    SELECT id, entity_type, entity_name, properties
                    FROM neural_nodes
                    WHERE embedding IS NULL
                """)
        
            nodes = cursor.fetchall()
        
        total = len(nodes)
        print(f"[VectorIntegration] 需要处理 {total} 个节点")
        
        if total == 0:
            return {"total": 0, "processed": 0, "errors": 0}
        
        processed = 0
        errors = 0
        
        for i, node in enumerate(nodes):
            try:
                # 解析属性
                properties = None
                if node["properties"]:
                    try:
                        properties = json.loads(node["properties"]) if isinstance(node["properties"], str) else node["properties"]
                    except (json.JSONDecodeError) as e:
                        properties = None
                
                # 生成向量
                embedding = self.embed_node(
                    node["entity_type"],
                    node["entity_name"],
                    properties
                )
                
                # 更新数据库
                self.update_node_embedding(node["id"], embedding)
                processed += 1
                
                # 进度报告
                if (i + 1) % 10 == 0 or (i + 1) == total:
                    print(f"  进度: {i + 1}/{total}")
                
            except (ValueError) as e:
                print(f"  [Error] Node {node['id']}: {e}")
                errors += 1
        
        print(f"[VectorIntegration] 完成！处理: {processed}, 错误: {errors}")
        return {"total": total, "processed": processed, "errors": errors}
    
    def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        entity_types: List[str] = None,
        min_similarity: float = 0.0
    ) -> List[Dict]:
        """
        语义相似度搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            entity_types: 过滤实体类型
            min_similarity: 最小相似度阈值
        
        Returns:
            [{"id", "type", "name", "similarity"}, ...]
        """
        # 生成查询向量
        query_embedding = self.embed_text(query)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
        
        # 查询所有有向量的节点
            if entity_types:
                placeholders = ",".join("?" * len(entity_types))
                cursor.execute(f"""
                    SELECT id, entity_type, entity_name, canonical_name, embedding
                    FROM neural_nodes
                    WHERE embedding IS NOT NULL
                    AND entity_type IN ({placeholders})
                """, entity_types)
            else:
                cursor.execute("""
                    SELECT id, entity_type, entity_name, canonical_name, embedding
                    FROM neural_nodes
                    WHERE embedding IS NOT NULL
                """)
        
            nodes = cursor.fetchall()
        
        # 计算相似度
        results = []
        for node in nodes:
            try:
                # 反序列化向量
                node_embedding = np.frombuffer(node["embedding"], dtype=np.float32)
                
                # 余弦相似度
                similarity = np.dot(query_embedding, node_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(node_embedding)
                )
                
                if similarity >= min_similarity:
                    results.append({
                        "id": node["id"],
                        "type": node["entity_type"],
                        "name": node["entity_name"],
                        "canonical_name": node["canonical_name"],
                        "similarity": float(similarity)
                    })
            except (ValueError) as e:
                continue
        
        # 排序并返回 top_k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]
    
    def find_similar_nodes(self, node_id: str, top_k: int = 10) -> List[Dict]:
        """
        查找与指定节点最相似的节点
        
        Args:
            node_id: 节点ID
            top_k: 返回结果数量
        
        Returns:
            [{"id", "type", "name", "similarity"}, ...]
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
        
        # 获取目标节点的向量
            cursor.execute(
                "SELECT embedding FROM neural_nodes WHERE id = ?",
                (node_id,)
            )
            result = cursor.fetchone()
        
            if not result or not result[0]:
                return []
        
        target_embedding = np.frombuffer(result[0], dtype=np.float32)
        
        # 查询其他节点
        cursor.execute("""
            SELECT id, entity_type, entity_name, canonical_name, embedding
            FROM neural_nodes
            WHERE embedding IS NOT NULL
            AND id != ?
        """, (node_id,))
        
        nodes = cursor.fetchall()
        conn.close()
        
        # 计算相似度
        results = []
        for node in nodes:
            try:
                node_embedding = np.frombuffer(node["embedding"], dtype=np.float32)
                
                similarity = np.dot(target_embedding, node_embedding) / (
                    np.linalg.norm(target_embedding) * np.linalg.norm(node_embedding)
                )
                
                results.append({
                    "id": node["id"],
                    "type": node["entity_type"],
                    "name": node["entity_name"],
                    "canonical_name": node["canonical_name"],
                    "similarity": float(similarity)
                })
            except (ValueError) as e:
                continue
        
        # 排序并返回
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]


def integrate_vectors(graph, force: bool = False) -> Dict:
    """便捷函数：为图谱的所有节点生成向量"""
    vi = VectorIntegration(graph)
    return vi.embed_all_nodes(force=force)


def semantic_node_search(graph, query: str, top_k: int = 10) -> List[Dict]:
    """便捷函数：语义搜索节点"""
    vi = VectorIntegration(graph)
    return vi.semantic_search(query, top_k=top_k)
