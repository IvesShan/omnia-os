"""
增强向量检索器 - Vector Retriever Enhanced
支持多策略检索、重排序、缓存优化
"""

import sqlite3
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json
import hashlib


@dataclass
class RetrievalResult:
    """检索结果"""
    conversation_id: int
    content: str
    score: float
    timestamp: str
    channel: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return {
            'conversation_id': self.conversation_id,
            'content': self.content,
            'score': self.score,
            'timestamp': self.timestamp,
            'channel': self.channel,
            'metadata': self.metadata
        }


class VectorRetrieverEnhanced:
    """增强向量检索器"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Path.home() / ".omnia" / "conversations.db")
        self.cache_db = str(Path.home() / ".omnia" / "vector_cache.db")
        Path(self.cache_db).parent.mkdir(parents=True, exist_ok=True)
        self._init_cache_db()
        
        # 缓存配置
        self.cache_ttl = 3600  # 1小时
        self.cache_max_size = 1000
        
    def _init_cache_db(self):
        """初始化缓存数据库"""
        with sqlite3.connect(self.cache_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS query_cache (
                    query_hash TEXT PRIMARY KEY,
                    query_text TEXT NOT NULL,
                    results TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    hit_count INTEGER DEFAULT 0
                )
            ''')
    
    def search(
        self,
        query: str,
        query_vector: List[float],
        top_k: int = 10,
        strategy: str = 'hybrid',
        filters: Dict = None
    ) -> List[RetrievalResult]:
        """
        多策略检索
        
        Args:
            query: 查询文本
            query_vector: 查询向量
            top_k: 返回结果数
            strategy: 检索策略 (semantic, keyword, hybrid, time_weighted)
            filters: 过滤条件
        """
        # 检查缓存
        cached = self._check_cache(query)
        if cached:
            return cached
        
        # 根据策略检索
        if strategy == 'semantic':
            results = self._semantic_search(query_vector, top_k)
        elif strategy == 'keyword':
            results = self._keyword_search(query, top_k)
        elif strategy == 'hybrid':
            results = self._hybrid_search(query, query_vector, top_k)
        elif strategy == 'time_weighted':
            results = self._time_weighted_search(query_vector, top_k)
        else:
            results = self._hybrid_search(query, query_vector, top_k)
        
        # 应用过滤
        if filters:
            results = self._apply_filters(results, filters)
        
        # 重排序
        results = self._rerank(results, query)
        
        # 缓存结果
        self._cache_results(query, results)
        
        return results
    
    def _semantic_search(self, query_vector: List[float], top_k: int) -> List[RetrievalResult]:
        """纯语义检索"""
        query_vec = np.array(query_vector)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT id, content, vector, timestamp, channel, metadata
                FROM conversations
                WHERE vector IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (top_k * 3,))  # 取更多候选
            
            results = []
            for row in cursor.fetchall():
                conv_id, content, vec_str, timestamp, channel, metadata = row
                
                if vec_str:
                    try:
                        stored_vec = np.array(json.loads(vec_str))
                        # 计算余弦相似度
                        similarity = np.dot(query_vec, stored_vec) / (
                            np.linalg.norm(query_vec) * np.linalg.norm(stored_vec)
                        )
                        
                        results.append(RetrievalResult(
                            conversation_id=conv_id,
                            content=content,
                            score=float(similarity),
                            timestamp=timestamp,
                            channel=channel or 'unknown',
                            metadata=json.loads(metadata) if metadata else {}
                        ))
                    except (ValueError, json.JSONDecodeError) as e:
                        continue
            
            # 按相似度排序
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:top_k]
    
    def _keyword_search(self, query: str, top_k: int) -> List[RetrievalResult]:
        """关键词检索"""
        keywords = query.lower().split()
        
        with sqlite3.connect(self.db_path) as conn:
            # 构建SQL查询
            conditions = ' OR '.join([f'content LIKE ?' for _ in keywords])
            params = [f'%{kw}%' for kw in keywords]
            
            cursor = conn.execute(f'''
                SELECT id, content, timestamp, channel, metadata
                FROM conversations
                WHERE {conditions}
                ORDER BY timestamp DESC
                LIMIT ?
            ''', params + [top_k])
            
            results = []
            for row in cursor.fetchall():
                conv_id, content, timestamp, channel, metadata = row
                
                # 简单的关键词匹配分数
                score = sum(1 for kw in keywords if kw in content.lower()) / len(keywords)
                
                results.append(RetrievalResult(
                    conversation_id=conv_id,
                    content=content,
                    score=score,
                    timestamp=timestamp,
                    channel=channel or 'unknown',
                    metadata=json.loads(metadata) if metadata else {}
                ))
            
            return results
    
    def _hybrid_search(
        self, 
        query: str, 
        query_vector: List[float], 
        top_k: int
    ) -> List[RetrievalResult]:
        """混合检索（语义 + 关键词）"""
        # 语义检索
        semantic_results = self._semantic_search(query_vector, top_k)
        
        # 关键词检索
        keyword_results = self._keyword_search(query, top_k)
        
        # 合并结果
        combined = {}
        
        # 语义结果权重 0.7
        for r in semantic_results:
            combined[r.conversation_id] = r
            r.score *= 0.7
        
        # 关键词结果权重 0.3
        for r in keyword_results:
            if r.conversation_id in combined:
                combined[r.conversation_id].score += r.score * 0.3
            else:
                r.score *= 0.3
                combined[r.conversation_id] = r
        
        # 排序返回
        results = list(combined.values())
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def _time_weighted_search(
        self, 
        query_vector: List[float], 
        top_k: int
    ) -> List[RetrievalResult]:
        """时间加权检索（近期对话权重更高）"""
        results = self._semantic_search(query_vector, top_k * 2)
        
        now = datetime.now()
        for r in results:
            # 计算时间衰减
            conv_time = datetime.fromisoformat(r.timestamp)
            days_ago = (now - conv_time).days
            
            # 指数衰减：每天衰减 5%
            time_weight = np.exp(-0.05 * days_ago)
            r.score *= time_weight
        
        # 重新排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def _apply_filters(self, results: List[RetrievalResult], filters: Dict) -> List[RetrievalResult]:
        """应用过滤条件"""
        filtered = []
        
        for r in results:
            # 渠道过滤
            if 'channel' in filters and r.channel != filters['channel']:
                continue
            
            # 时间范围过滤
            if 'start_time' in filters:
                if r.timestamp < filters['start_time']:
                    continue
            
            if 'end_time' in filters:
                if r.timestamp > filters['end_time']:
                    continue
            
            # 元数据过滤
            if 'metadata' in filters:
                for key, value in filters['metadata'].items():
                    if r.metadata.get(key) != value:
                        continue
            
            filtered.append(r)
        
        return filtered
    
    def _rerank(self, results: List[RetrievalResult], query: str) -> List[RetrievalResult]:
        """重排序（基于查询相关性）"""
        # 简单的重排序：查询词出现次数
        query_words = set(query.lower().split())
        
        for r in results:
            content_words = set(r.content.lower().split())
            overlap = len(query_words & content_words)
            r.score += overlap * 0.01  # 小幅提升
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results
    
    def _check_cache(self, query: str) -> Optional[List[RetrievalResult]]:
        """检查缓存"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        
        with sqlite3.connect(self.cache_db) as conn:
            cursor = conn.execute('''
                SELECT results, created_at FROM query_cache
                WHERE query_hash = ?
            ''', (query_hash,))
            
            row = cursor.fetchone()
            if row:
                results_json, created_at = row
                
                # 检查是否过期
                created = datetime.fromisoformat(created_at)
                if (datetime.now() - created).seconds < self.cache_ttl:
                    # 更新命中计数
                    conn.execute('''
                        UPDATE query_cache 
                        SET hit_count = hit_count + 1
                        WHERE query_hash = ?
                    ''', (query_hash,))
                    
                    # 反序列化结果
                    results_data = json.loads(results_json)
                    return [RetrievalResult(**r) for r in results_data]
        
        return None
    
    def _cache_results(self, query: str, results: List[RetrievalResult]):
        """缓存结果"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        results_json = json.dumps([r.to_dict() for r in results])
        
        with sqlite3.connect(self.cache_db) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO query_cache
                (query_hash, query_text, results, created_at, hit_count)
                VALUES (?, ?, ?, ?, 0)
            ''', (query_hash, query, results_json, datetime.now().isoformat()))
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with sqlite3.connect(self.cache_db) as conn:
            total = conn.execute('SELECT COUNT(*) FROM query_cache').fetchone()[0]
            total_hits = conn.execute(
                'SELECT SUM(hit_count) FROM query_cache'
            ).fetchone()[0] or 0
            
            top_queries = conn.execute('''
                SELECT query_text, hit_count 
                FROM query_cache 
                ORDER BY hit_count DESC 
                LIMIT 10
            ''').fetchall()
            
            return {
                'total_cached': total,
                'total_hits': total_hits,
                'avg_hits': round(total_hits / total, 2) if total > 0 else 0,
                'top_queries': [
                    {'query': q, 'hits': h} for q, h in top_queries
                ]
            }
    
    def clear_cache(self):
        """清空缓存"""
        with sqlite3.connect(self.cache_db) as conn:
            conn.execute('DELETE FROM query_cache')


# 使用示例
if __name__ == "__main__":
    retriever = VectorRetrieverEnhanced()
    
    # 模拟查询向量
    query_vector = [0.1] * 384
    
    # 混合检索
    results = retriever.search(
        query="Omnia 优化",
        query_vector=query_vector,
        top_k=5,
        strategy='hybrid'
    )
    
    print(f"检索到 {len(results)} 条结果")
    for r in results:
        print(f"  [{r.score:.3f}] {r.content[:50]}...")
    
    # 缓存统计
    stats = retriever.get_cache_stats()
    print(f"\n缓存统计: {stats}")
