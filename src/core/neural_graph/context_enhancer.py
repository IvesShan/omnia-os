"""Neural Graph Context Enhancer - 为对话提供图谱上下文"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from core.config import MEMORY_PALACE_DB


@dataclass
class GraphContext:
    """图谱上下文"""
    entities: List[Dict]          # 相关实体
    relations: List[Dict]         # 相关关系
    subgraph_summary: str         # 子图摘要
    confidence: float = 0.0       # 置信度


class NeuralGraphContextEnhancer:
    """神经图谱上下文增强器
    
    从神经图谱中提取与当前对话相关的上下文，
    包括实体、关系、以及基于图遍历的相关信息。
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(
            str(MEMORY_PALACE_DB)
        )
    
    def enhance(
        self,
        message: str,
        max_entities: int = 5,      # Reduced from 10 for better precision
        max_relations: int = 8,     # Reduced from 15 for better precision
        max_depth: int = 2
    ) -> GraphContext:
        """增强消息上下文
        
        Args:
            message: 用户消息
            max_entities: 最大实体数
            max_relations: 最大关系数
            max_depth: 图遍历深度
            
        Returns:
            GraphContext: 图谱上下文
        """
        # 1. 从消息中提取潜在实体名
        potential_entities = self._extract_potential_entities(message)
        
        # 2. 在图谱中搜索匹配的实体
        matched_entities = []
        for name in potential_entities:
            nodes = self._search_nodes(name, limit=3)
            matched_entities.extend(nodes)
        
        # 3. 去重并限制数量
        seen_ids: Set[str] = set()
        entities = []
        for e in matched_entities:
            if e.get('id') not in seen_ids and len(entities) < max_entities:
                seen_ids.add(e['id'])
                entities.append(e)
        
        # 4. 获取相关关系
        relations = []
        for entity in entities:
            entity_relations = self._get_relations_for_entity(
                entity['entity_name'], 
                limit=max_relations // max(1, len(entities))
            )
            relations.extend(entity_relations)
        
        # 5. 去重关系
        seen_edge_ids: Set[str] = set()
        unique_relations = []
        for r in relations:
            if r.get('id') not in seen_edge_ids and len(unique_relations) < max_relations:
                seen_edge_ids.add(r['id'])
                unique_relations.append(r)
        
        # 6. 生成摘要
        summary = self._generate_summary(entities, unique_relations)
        
        # 7. 计算置信度
        confidence = min(1.0, len(entities) * 0.2 + len(unique_relations) * 0.1)
        
        return GraphContext(
            entities=entities,
            relations=unique_relations,
            subgraph_summary=summary,
            confidence=confidence
        )
    
    def _extract_potential_entities(self, text: str) -> List[str]:
        """从文本中提取潜在实体名
        
        使用简单的启发式规则：
        - 引号内的内容
        - 大写开头的词
        - 已知项目名/人名
        """
        entities = []
        
        # 已知实体词典
        known_entities = [
            "原点", "无限", "李先生", "建筑师",
            "喵修匠", "懂机帝", "Omnia", "Omnia OS", "omnia",
            "njuosun.com", "miaoxiujiang",
            "OpenClaw", "openclaw",
            "Memory Palace", "memory_palace",
            "Neural Graph", "neural_graph",
            "UltraPlan", "ultraplan",
            "MCP", "API", "飞书",
        ]
        
        # 检查已知实体
        text_lower = text.lower()
        for entity in known_entities:
            if entity.lower() in text_lower:
                entities.append(entity)
        
        # 提取引号内的内容
        import re
        quoted = re.findall(r'["\']([^"\']+)["\']', text)
        entities.extend(quoted[:3])
        
        # 提取反引号内的内容（代码/文件名）
        backtick = re.findall(r'`([^`]+)`', text)
        entities.extend(backtick[:3])
        
        return list(set(entities))
    
    def _search_nodes(self, query: str, limit: int = 5) -> List[Dict]:
        """搜索节点"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
            
                cursor.execute("""
                    SELECT id, entity_type, entity_name, canonical_name, access_count
                    FROM neural_nodes
                    WHERE entity_name LIKE ? OR canonical_name LIKE ?
                    ORDER BY access_count DESC
                    LIMIT ?
                """, (f"%{query}%", f"%{query}%", limit))
            
                rows = cursor.fetchall()
            
            return [dict(r) for r in rows]
        except Exception:
            return []
    
    def _get_relations_for_entity(self, entity_name: str, limit: int = 5) -> List[Dict]:
        """获取实体的相关关系"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
            
                cursor.execute("""
                    SELECT id, source_name, target_name, relation_type, weight
                    FROM neural_edges
                    WHERE source_name LIKE ? OR target_name LIKE ?
                    ORDER BY weight DESC
                    LIMIT ?
                """, (f"%{entity_name}%", f"%{entity_name}%", limit))
            
                rows = cursor.fetchall()
            
            return [dict(r) for r in rows]
        except Exception:
            return []
    
    def _generate_summary(self, entities: List[Dict], relations: List[Dict]) -> str:
        """生成图谱摘要"""
        if not entities and not relations:
            return "图谱中暂无相关信息"
        
        parts = []
        
        if entities:
            entity_types = {}
            for e in entities:
                t = e.get('entity_type', 'UNKNOWN')
                if t not in entity_types:
                    entity_types[t] = []
                entity_types[t].append(e.get('entity_name', ''))
            
            type_strs = []
            for t, names in entity_types.items():
                type_strs.append(f"{t}: {', '.join(names[:3])}")
            parts.append(f"相关实体 ({len(entities)}): " + "; ".join(type_strs))
        
        if relations:
            rel_strs = []
            for r in relations[:5]:
                rel_strs.append(
                    f"{r.get('source_name', '?')} --[{r.get('relation_type', '?')}]--> {r.get('target_name', '?')}"
                )
            parts.append(f"相关关系 ({len(relations)}): " + ", ".join(rel_strs))
        
        return "\n".join(parts)
    
    def get_hot_entities(self, limit: int = 10) -> List[Dict]:
        """获取热点实体（访问次数最高）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
            
                cursor.execute("""
                    SELECT entity_type, entity_name, access_count
                    FROM neural_nodes
                    ORDER BY access_count DESC
                    LIMIT ?
                """, (limit,))
            
                rows = cursor.fetchall()
            
            return [dict(r) for r in rows]
        except Exception:
            return []
    
    def get_context_prompt(self, message: str) -> str:
        """生成图谱上下文提示词
        
        Args:
            message: 用户消息
            
        Returns:
            str: 图谱上下文提示词（用于增强对话）
        """
        try:
            context = self.enhance(message)
            
            if not context.entities and not context.relations:
                return ""
            
            prompt_parts = ["\n【图谱上下文】"]
            
            if context.entities:
                entity_strs = []
                for e in context.entities[:5]:
                    entity_strs.append(f"{e.get('entity_name', '?')}({e.get('entity_type', '?')})")
                prompt_parts.append(f"相关实体: {', '.join(entity_strs)}")
            
            if context.relations:
                rel_strs = []
                for r in context.relations[:3]:
                    rel_strs.append(f"{r.get('source_name', '?')}→{r.get('target_name', '?')}")
                prompt_parts.append(f"相关关系: {', '.join(rel_strs)}")
            
            prompt_parts.append(f"(置信度: {context.confidence:.1%})")
            
            return "\n".join(prompt_parts)
            
        except Exception as e:
            print(f"[GraphEnhancer] Error generating context prompt: {e}")
            return ""


# 全局实例
_graph_enhancer_instance = None

def get_graph_enhancer() -> NeuralGraphContextEnhancer:
    """获取全局图增强器实例"""
    global _graph_enhancer_instance
    if _graph_enhancer_instance is None:
        _graph_enhancer_instance = NeuralGraphContextEnhancer()
    return _graph_enhancer_instance
