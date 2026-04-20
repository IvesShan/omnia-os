"""Relation Inferencer - 关系推理器"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .graph import Entity, Relation


class RelationInferencer:
    """关系推理器"""
    
    # 关系模板
    RELATION_PATTERNS = {
        # 项目归属
        "BELONGS_TO": [
            ("项目", "人物", "开发"),
            ("文件", "项目", "属于"),
            ("概念", "项目", "相关"),
        ],
        # 协作关系
        "COLLABORATES_WITH": [
            ("人物", "人物", "协作"),
            ("项目", "项目", "集成"),
            ("人物", "项目", "参与"),
        ],
        # 依赖关系
        "DEPENDS_ON": [
            ("文件", "文件", "依赖"),
            ("项目", "项目", "依赖"),
            ("概念", "概念", "基于"),
        ],
        # 因果关系
        "CAUSED_BY": [
            ("事件", "事件", "导致"),
            ("事件", "文件", "修复"),
        ],
        # 工作关系
        "WORKED_ON": [
            ("人物", "项目", "开发"),
            ("人物", "文件", "修改"),
            ("人物", "概念", "研究"),
        ],
    }
    
    # 上下文关键词
    CONTEXT_KEYWORDS = {
        "BELONGS_TO": ["属于", "包含", "有", "包含"],
        "RELATED_TO": ["相关", "关联", "连接", "有关"],
        "DEPENDS_ON": ["依赖", "需要", "基于", "使用"],
        "CAUSED_BY": ["导致", "引起", "造成", "修复"],
        "WORKED_ON": ["开发", "修改", "创建", "更新", "部署"],
        "KNOWS_ABOUT": ["了解", "知道", "熟悉", "掌握"],
    }
    
    def infer(self, entity1: Entity, entity2: Entity, context: str) -> Optional[Relation]:
        """推理两个实体之间的关系"""
        
        # 1. 基于实体类型判断可能的关系
        possible_relations = self._get_possible_relations(entity1.type, entity2.type)
        
        if not possible_relations:
            return None
        
        # 2. 基于上下文确定关系类型
        relation_type = self._match_context(context, possible_relations)
        
        if not relation_type:
            # 默认为 RELATED_TO
            relation_type = "RELATED_TO"
        
        # 3. 计算关系强度
        weight = self._calculate_weight(entity1, entity2, context)
        
        return Relation(
            source=entity1.name,
            target=entity2.name,
            type=relation_type,
            weight=weight,
        )
    
    def infer_batch(self, entities: List[Entity], context: str) -> List[Relation]:
        """批量推理实体间的关系"""
        relations = []
        
        # 两两组合
        for i, e1 in enumerate(entities):
            for e2 in entities[i+1:]:
                relation = self.infer(e1, e2, context)
                if relation:
                    relations.append(relation)
        
        return relations
    
    def _get_possible_relations(self, type1: str, type2: str) -> List[str]:
        """基于实体类型获取可能的关系"""
        
        # 类型组合到关系的映射
        type_relations = {
            ("PERSON", "PROJECT"): ["WORKED_ON", "BELONGS_TO"],
            ("PERSON", "FILE"): ["WORKED_ON"],
            ("PERSON", "CONCEPT"): ["KNOWS_ABOUT"],
            ("PROJECT", "FILE"): ["BELONGS_TO", "DEPENDS_ON"],
            ("PROJECT", "CONCEPT"): ["RELATED_TO"],
            ("FILE", "FILE"): ["DEPENDS_ON", "RELATED_TO"],
            ("FILE", "CONCEPT"): ["RELATED_TO"],
            ("CONCEPT", "CONCEPT"): ["RELATED_TO", "DEPENDS_ON"],
            ("EVENT", "PROJECT"): ["RELATED_TO"],
            ("EVENT", "FILE"): ["CAUSED_BY"],
        }
        
        key = (type1, type2)
        reverse_key = (type2, type1)
        
        return type_relations.get(key, []) or type_relations.get(reverse_key, [])
    
    def _match_context(self, context: str, possible_relations: List[str]) -> Optional[str]:
        """匹配上下文确定关系类型"""
        context_lower = context.lower()
        
        for relation_type in possible_relations:
            keywords = self.CONTEXT_KEYWORDS.get(relation_type, [])
            if any(kw in context_lower for kw in keywords):
                return relation_type
        
        return None
    
    def _calculate_weight(self, entity1: Entity, entity2: Entity, context: str) -> float:
        """计算关系强度"""
        base_weight = 0.5
        
        # 1. 实体置信度影响
        confidence_factor = (entity1.confidence + entity2.confidence) / 2
        
        # 2. 上下文长度影响（更长的上下文可能有更多信息）
        length_factor = min(len(context) / 1000, 1.0) * 0.1
        
        # 3. 关键词密度
        keyword_count = sum(
            1 for keywords in self.CONTEXT_KEYWORDS.values()
            for kw in keywords
            if kw in context
        )
        keyword_factor = min(keyword_count * 0.1, 0.3)
        
        weight = base_weight + (confidence_factor - 0.5) * 0.2 + length_factor + keyword_factor
        
        return min(max(weight, 0.1), 1.0)
