"""
MLA (Memory Latent Attention) Compression

记忆压缩模块
- 向量压缩
- 潜在注意力
- 高效检索
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass
class CompressionConfig:
    """压缩配置"""
    input_dim: int = 768      # 输入维度
    latent_dim: int = 64      # 潜在维度
    compression_ratio: int = 12  # 压缩比


class MLACompression:
    """MLA 压缩模块"""
    
    def __init__(self, config: Optional[CompressionConfig] = None):
        self.config = config or CompressionConfig()
        
        # 初始化压缩矩阵（简化版，实际应使用训练好的权重）
        np.random.seed(42)
        self.compress_matrix = np.random.randn(
            self.config.input_dim, 
            self.config.latent_dim
        ) / np.sqrt(self.config.input_dim)
        
        self.decompress_matrix = self.compress_matrix.T
    
    def compress(self, vectors: np.ndarray) -> np.ndarray:
        """压缩向量
        
        Args:
            vectors: 输入向量 [N, input_dim]
            
        Returns:
            压缩后的向量 [N, latent_dim]
        """
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        
        # 简单线性投影
        compressed = np.dot(vectors, self.compress_matrix)
        
        return compressed
    
    def decompress(self, compressed: np.ndarray) -> np.ndarray:
        """解压向量
        
        Args:
            compressed: 压缩向量 [N, latent_dim]
            
        Returns:
            解压后的向量 [N, input_dim]
        """
        if compressed.ndim == 1:
            compressed = compressed.reshape(1, -1)
        
        # 简单线性投影
        decompressed = np.dot(compressed, self.decompress_matrix)
        
        return decompressed
    
    def compress_memory(
        self,
        memories: List[Dict],
        embedding_fn: Optional[callable] = None
    ) -> Tuple[np.ndarray, List[Dict]]:
        """压缩记忆集合
        
        Args:
            memories: 记忆列表
            embedding_fn: 嵌入函数
            
        Returns:
            (压缩向量, 记忆元数据)
        """
        if not memories:
            return np.array([]), []
        
        # 提取向量
        vectors = []
        metadata = []
        
        for mem in memories:
            if 'embedding' in mem:
                vectors.append(mem['embedding'])
            elif embedding_fn:
                vec = embedding_fn(mem.get('content', ''))
                vectors.append(vec)
            else:
                # 使用随机向量作为占位符
                vectors.append(np.random.randn(self.config.input_dim))
            
            # 保存元数据
            metadata.append({
                'id': mem.get('id'),
                'category': mem.get('category'),
                'timestamp': mem.get('timestamp'),
                'importance': mem.get('importance', 1.0)
            })
        
        # 批量压缩
        vectors_array = np.array(vectors)
        compressed = self.compress(vectors_array)
        
        return compressed, metadata
    
    def retrieve(
        self,
        query_vector: np.ndarray,
        compressed_memories: np.ndarray,
        metadata: List[Dict],
        top_k: int = 5
    ) -> List[Dict]:
        """检索相关记忆
        
        Args:
            query_vector: 查询向量
            compressed_memories: 压缩的记忆向量
            metadata: 记忆元数据
            top_k: 返回数量
            
        Returns:
            最相关的记忆列表
        """
        if len(compressed_memories) == 0:
            return []
        
        # 压缩查询向量
        query_compressed = self.compress(query_vector)
        
        # 计算相似度
        similarities = np.dot(compressed_memories, query_compressed.T).flatten()
        
        # 排序
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # 返回结果
        results = []
        for idx in top_indices:
            result = metadata[idx].copy()
            result['similarity'] = float(similarities[idx])
            results.append(result)
        
        return results
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'input_dim': self.config.input_dim,
            'latent_dim': self.config.latent_dim,
            'compression_ratio': self.config.compression_ratio,
            'memory_saved': f"{self.config.compression_ratio}x"
        }
