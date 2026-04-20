"""Entity Extractor V2 - 业务优先的智能实体抽取

设计原则：
1. 业务实体优先：人物、项目、公司等核心实体
2. 文件路径严格过滤：避免代码片段、SVG 数据等垃圾
3. 关系提取：不仅提取实体，还提取关系
4. 质量 > 数量：宁可少提取，不要误提取
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from .graph import Entity


@dataclass
class ExtractedRelation:
    """提取的关系"""
    source: str
    source_type: str
    relation: str
    target: str
    target_type: str
    confidence: float = 0.8
    evidence: str = ""


class EntityExtractorV2:
    """业务优先的智能实体抽取器"""
    
    # 核心业务实体（高优先级）
    CORE_ENTITIES = {
        "PERSON": [
            "原点", "无限", "李先生", "建筑师", "王文浩", "王家祥", 
            "单爱桂", "许世尧", "Yuán diǎn", "Wúxiàn"
        ],
        "PROJECT": [
            "喵修匠", "懂机帝", "Omnia", "Omnia OS", "OpenClaw",
            "njuosun.com", "miaoxiujiang", "drone-repair"
        ],
        "COMPANY": [
            "物熵科技", "上海翎熵", "翎熵科技"
        ],
        "CONCEPT": [
            "无人机维修", "OPC", "一人公司", "知识图谱", "神经图谱",
            "记忆系统", "向量嵌入", "API", "MCP", "飞书"
        ],
    }
    
    # 业务关系模式（支持中英文）
    BUSINESS_RELATION_PATTERNS = [
        (r'([一-龥\w]+)\s*创建\s*了?\s*([一-龥\w]+)', 'created'),
        (r'([一-龥\w]+)\s*开发\s*了?\s*([一-龥\w]+)', 'developed'),
        (r'([一-龥\w]+)\s*设计\s*了?\s*([一-龥\w]+)', 'designed'),
        (r'([一-龥\w]+)\s*拥有\s*([一-龥\w]+)', 'owns'),
        (r'([一-龥\w]+)\s*参与\s*了?\s*([一-龥\w]+)', 'WORKED_ON'),
        (r'([一-龥\w]+)\s*负责\s*([一-龥\w]+)', 'responsible_for'),
        (r'([一-龥\w]+)\s*经营\s*([一-龥\w]+)', 'operates'),
        (r'([一-龥\w]+)\s*管理\s*([一-龥\w]+)', 'manages'),
        (r'([一-龥\w]+)\s*目标\s*是?\s*([一-龥\w]+)', 'targets'),
    ]
    
    VALID_FILE_EXTENSIONS = {
        '.md', '.txt', '.json', '.yaml', '.yml', '.toml',
        '.py', '.js', '.ts', '.rs', '.go', '.java',
        '.html', '.css', '.xml', '.sql',
        '.sh', '.bash', '.zsh',
        '.env', '.conf', '.cfg',
    }
    
    GARBAGE_PATTERNS = [
        r'^[\d\.\-\s]+$',
        r'^[\w\.\-]{1,3}$',
        r'^\d+\.\d+',
        r'^[\w]+\.warn',
        r'^console\.',
        r'^process\.',
        r'^window\.',
        r'^document\.',
        r'^Math\.',
        r'^JSON\.',
        r'^Array\.',
        r'^Object\.',
        r'^String\.',
        r'[\d\w]{32,}',
        r'^\d+\.\d+s$',
        r'^\d+\.\d+MB$',
        r'^\d+\.\d+KB$',
    ]
    
    def __init__(self, api_key: str = None, provider: str = None):
        self.api_key = api_key
        self.provider = provider
        self._garbage_re = [re.compile(p) for p in self.GARBAGE_PATTERNS]
    
    def extract(self, text: str, use_llm: bool = False) -> Tuple[List[Entity], List[ExtractedRelation]]:
        entities = []
        relations = []
        entities.extend(self._extract_core_entities(text))
        relations.extend(self._extract_business_relations(text))
        entities.extend(self._extract_dates(text))
        entities.extend(self._extract_files_strict(text))
        if use_llm:
            llm_entities, llm_relations = self._llm_extract(text)
            entities.extend(llm_entities)
            relations.extend(llm_relations)
        return self._deduplicate_entities(entities), self._deduplicate_relations(relations)
    
    def _extract_core_entities(self, text: str) -> List[Entity]:
        entities = []
        for entity_type, names in self.CORE_ENTITIES.items():
            for name in names:
                if name in text:
                    entities.append(Entity(type=entity_type, name=name, confidence=1.0))
        return entities
    
    def _extract_business_relations(self, text: str) -> List[ExtractedRelation]:
        relations = []
        for pattern, relation_type in self.BUSINESS_RELATION_PATTERNS:
            matches = re.findall(pattern, text)
            for source, target in matches:
                source_type = self._fuzzy_match_entity(source)
                target_type = self._fuzzy_match_entity(target)
                if source_type and target_type:
                    source_name = self._get_real_entity_name(source)
                    target_name = self._get_real_entity_name(target)
                    relations.append(ExtractedRelation(
                        source=source_name,
                        source_type=source_type,
                        relation=relation_type,
                        target=target_name,
                        target_type=target_type,
                        confidence=0.9,
                        evidence=text[:100]
                    ))
        return relations
    
    def _fuzzy_match_entity(self, text: str) -> Optional[str]:
        for entity_type, names in self.CORE_ENTITIES.items():
            for name in names:
                if name in text:
                    return entity_type
        return None
    
    def _get_real_entity_name(self, text: str) -> str:
        for entity_type, names in self.CORE_ENTITIES.items():
            for name in names:
                if name in text:
                    return name
        return text
    
    def _extract_dates(self, text: str) -> List[Entity]:
        patterns = [
            (r'\d{4}年\d{1,2}月\d{1,2}日', 'DATE'),
            (r'\d{4}-\d{2}-\d{2}', 'DATE'),
            (r'\d{4}/\d{2}/\d{2}', 'DATE'),
        ]
        entities = []
        for pattern, etype in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                entities.append(Entity(type=etype, name=match))
        return entities
    
    def _extract_files_strict(self, text: str) -> List[Entity]:
        entities = []
        patterns = [r'~?/[\w\-./]+\.\w{2,4}', r'[\w\-]+\.\w{2,4}']
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if self._is_valid_file(match):
                    entities.append(Entity(type='FILE', name=match))
        return entities
    
    def _is_valid_file(self, path: str) -> bool:
        if len(path) < 5 or len(path) > 200:
            return False
        for garbage_re in self._garbage_re:
            if garbage_re.match(path):
                return False
        ext = Path(path).suffix.lower()
        if ext and ext not in self.VALID_FILE_EXTENSIONS:
            return False
        if '.' not in Path(path).name:
            return False
        return True
    
    def _llm_extract(self, text: str) -> Tuple[List[Entity], List[ExtractedRelation]]:
        if not self.api_key:
            return [], []
        try:
            from omnia.chat import _call_model_messages
            prompt = f"""从以下文本中提取实体和关系，返回 JSON 格式：

文本：
{text[:2000]}

实体类型：PERSON, PROJECT, COMPANY, CONCEPT, DATE
关系类型：created, owns, WORKED_ON, operates, targets

返回格式：
{{"entities": [{{"type": "PERSON", "name": "xxx"}}], "relations": [{{"source": "xxx", "relation": "created", "target": "yyy"}}]}}"""
            response = _call_model_messages(
                api_key=self.api_key,
                provider=self.provider,
                messages=[{"role": "user", "content": prompt}],
                tools=None
            )
            content = response["choices"][0]["message"]["content"]
            import json
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                entities = [
                    Entity(type=e.get("type", "UNKNOWN"), name=e.get("name", ""), confidence=0.8)
                    for e in data.get("entities", [])
                    if e.get("name")
                ]
                relations = [
                    ExtractedRelation(
                        source=r.get("source", ""),
                        source_type=self._fuzzy_match_entity(r.get("source", "")) or "UNKNOWN",
                        relation=r.get("relation", "RELATED_TO"),
                        target=r.get("target", ""),
                        target_type=self._fuzzy_match_entity(r.get("target", "")) or "UNKNOWN",
                        confidence=0.8
                    )
                    for r in data.get("relations", [])
                    if r.get("source") and r.get("target")
                ]
                return entities, relations
        except Exception as e:
            print(f"[EntityExtractorV2] LLM failed: {e}")
        return [], []
    
    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        seen = set()
        unique = []
        for entity in entities:
            key = f"{entity.type}:{entity.name}"
            if key not in seen:
                seen.add(key)
                unique.append(entity)
        return unique
    
    def _deduplicate_relations(self, relations: List[ExtractedRelation]) -> List[ExtractedRelation]:
        seen = set()
        unique = []
        for rel in relations:
            key = f"{rel.source}:{rel.relation}:{rel.target}"
            if key not in seen:
                seen.add(key)
                unique.append(rel)
        return unique
