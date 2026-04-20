"""Entity Extractor - 规则 + LLM 混合实体抽取"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .graph import Entity


class EntityExtractor:
    """混合实体抽取器：规则 + LLM"""
    
    # 已知实体词典（可动态扩展）
    KNOWN_ENTITIES = {
        "PERSON": [
            "原点", "无限", "李先生", "建筑师", 
            "原点 (Yuán diǎn)", "Wúxiàn"
        ],
        "PROJECT": [
            "喵修匠", "懂机帝", "Omnia", "Omnia OS", 
            "njuosun.com", "miaoxiujiang", "drone-repair"
        ],
        "FILE": [
            "README.md", "config.json", "package.json", ".env", 
            "openclaw.json", "MEMORY.md", "SOUL.md"
        ],
        "CONCEPT": [
            "协作", "记忆", "工具调用", "部署", "API", "MCP", 
            "飞书", "知识图谱", "神经图谱", "向量", "嵌入"
        ],
        "LOCATION": [
            "本地", "云端", "本地项目", "服务器"
        ],
    }
    
    # 正则模式
    DATE_PATTERNS = [
        (r'\d{4}年\d{1,2}月\d{1,2}日', 'DATE'),
        (r'\d{4}-\d{2}-\d{2}', 'DATE'),
        (r'\d{4}/\d{2}/\d{2}', 'DATE'),
        (r'今天|昨天|前天|最近|刚刚|刚才', 'DATE'),
        (r'\d+天前|\d+小时前|\d+分钟前', 'DATE'),
    ]
    
    FILE_PATTERNS = [
        r'[\w\-./]+\.\w{2,4}(?![\w.])',  # 文件路径
        r'~\/[\w\-./]+',                    # 用户目录
        r'/[\w\-./]+',                      # 绝对路径
    ]
    
    def __init__(self, api_key: str = None, provider: str = None):
        self.api_key = api_key
        self.provider = provider
    
    def extract(self, text: str, use_llm: bool = False) -> List[Entity]:
        """提取实体
        
        Args:
            text: 输入文本
            use_llm: 是否使用 LLM 补充（空闲时为 True）
        
        Returns:
            实体列表
        """
        entities = []
        
        # 1. 规则快速匹配
        entities.extend(self._rule_based_extract(text))
        
        # 2. 日期提取
        entities.extend(self._extract_dates(text))
        
        # 3. 文件路径提取
        entities.extend(self._extract_files(text))
        
        # 4. LLM 补充（仅在空闲时）
        if use_llm and self._needs_llm(text):
            entities.extend(self._llm_extract(text))
        
        return self._deduplicate(entities)
    
    def _rule_based_extract(self, text: str) -> List[Entity]:
        """基于已知词典的快速匹配"""
        entities = []
        
        for entity_type, names in self.KNOWN_ENTITIES.items():
            for name in names:
                if name in text:
                    entities.append(Entity(
                        type=entity_type,
                        name=name,
                        confidence=1.0
                    ))
        
        return entities
    
    def _extract_dates(self, text: str) -> List[Entity]:
        """提取日期"""
        entities = []
        
        for pattern, etype in self.DATE_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                entities.append(Entity(type=etype, name=match))
        
        return entities
    
    def _extract_files(self, text: str) -> List[Entity]:
        """提取文件路径"""
        entities = []
        
        for pattern in self.FILE_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                # 过滤掉太长的（可能是误匹配）
                if len(match) < 100 and '.' in match.split('/')[-1]:
                    entities.append(Entity(type='FILE', name=match))
        
        return entities
    
    def _needs_llm(self, text: str) -> bool:
        """判断是否需要 LLM 补充"""
        # 文本较长或包含复杂结构
        complexity_indicators = [
            len(text) > 500,
            any(kw in text for kw in ["意味着", "导致", "因为", "所以", "关系", "影响"]),
            any(kw in text for kw in ["结合", "整合", "关联", "依赖"]),
        ]
        
        return any(complexity_indicators)
    
    def _llm_extract(self, text: str) -> List[Entity]:
        """LLM 实体抽取（空闲时调用）"""
        if not self.api_key:
            return []
        
        try:
            from omnia.chat import _call_model_messages
            
            prompt = f"""从以下文本中提取实体，返回 JSON 格式：

文本：
{text}

实体类型：
- PERSON: 人物
- PROJECT: 项目名称
- FILE: 文件名或路径
- EVENT: 事件
- CONCEPT: 概念或技术术语
- DATE: 日期
- LOCATION: 位置

返回格式（只返回 JSON，不要其他内容）：
{{"entities": [{{"type": "PERSON", "name": "xxx", "confidence": 0.9}}]}}
"""
            
            response = _call_model_messages(
                api_key=self.api_key,
                provider=self.provider,
                messages=[{"role": "user", "content": prompt}],
                tools=None
            )
            
            content = response["choices"][0]["message"]["content"]
            
            # 提取 JSON
            import json
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                return [
                    Entity(
                        type=e.get("type", "UNKNOWN"),
                        name=e.get("name", ""),
                        confidence=e.get("confidence", 0.8)
                    )
                    for e in data.get("entities", [])
                ]
        except Exception as e:
            print(f"[EntityExtractor] LLM extraction failed: {e}")
        
        return []
    
    def _deduplicate(self, entities: List[Entity]) -> List[Entity]:
        """去重"""
        seen = set()
        unique = []
        
        for entity in entities:
            key = f"{entity.type}:{entity.name}"
            if key not in seen:
                seen.add(key)
                unique.append(entity)
        
        return unique
    
    def update_known_entities(self, entity_type: str, names: List[str]):
        """更新已知实体词典（动态扩展）"""
        if entity_type in self.KNOWN_ENTITIES:
            self.KNOWN_ENTITIES[entity_type].extend(names)
        else:
            self.KNOWN_ENTITIES[entity_type] = names
