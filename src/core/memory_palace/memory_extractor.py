"""Memory Extractor — 自动从对话中提取关键信息.

识别用户消息中的：
- 偏好（我喜欢...）
- 习惯（我经常...）
- 事实（我是...）
- 关系（A 是 B 的...）
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple


@dataclass
class ExtractedMemory:
    """提取出的记忆单元."""
    memory_type: str  # preference, habit, fact, relation
    category: str
    key: str
    value: str
    confidence: float
    evidence: str
    context: Optional[str] = None


class MemoryExtractor:
    """从用户消息中自动提取关键信息."""
    
    # 偏好模式
    PREFERENCE_PATTERNS = [
        (r'我喜欢([^，。！？,\.]+)', 'positive'),
        (r'我不喜欢([^，。！？,\.]+)', 'negative'),
        (r'我爱([^，。！？,\.]+)', 'positive'),
        (r'我讨厌([^，。！？,\.]+)', 'negative'),
        (r'我偏好([^，。！？,\.]+)', 'positive'),
        (r'我更倾向于([^，。！？,\.]+)', 'positive'),
        (r'我prefer([^，。！？,\.]+)', 'positive'),
        (r'我的最爱是([^，。！？,\.]+)', 'positive'),
    ]
    
    # 习惯模式
    HABIT_PATTERNS = [
        (r'我经常([^，。！？,\.]+)', 'frequency'),
        (r'我总是([^，。！？,\.]+)', 'frequency'),
        (r'我习惯([^，。！？,\.]+)', 'frequency'),
        (r'我每天([^，。！？,\.]+)', 'daily'),
        (r'我每周([^，。！？,\.]+)', 'weekly'),
        (r'我通常在([^，。！？,\.]+)', 'pattern'),
        (r'我一般([^，。！？,\.]+)', 'pattern'),
    ]
    
    # 事实模式
    FACT_PATTERNS = [
        (r'我是([^，。！？,\.]+)', 'identity'),
        (r'我在([^，。！？,\.]+)工作', 'workplace'),
        (r'我在([^，。！？,\.]+)学习', 'school'),
        (r'我的职业是([^，。！？,\.]+)', 'profession'),
        (r'我的名字(叫|是)([^，。！？,\.]+)', 'name'),
        (r'我住在([^，。！？,\.]+)', 'location'),
        (r'我的项目(叫|是)([^，。！？,\.]+)', 'project'),
    ]
    
    # 关系模式
    RELATION_PATTERNS = [
        (r'([^，。！？,\.]+)是我的([^，。！？,\.]+)', 'belongs_to'),
        (r'([^，。！？,\.]+)是我的朋友', 'friend_of'),
        (r'([^，。！？,\.]+)是我的同事', 'colleague_of'),
        (r'([^，。！？,\.]+)是我的([^，。！？,\.]+)', 'relation'),
    ]
    
    # 否定模式（更新旧记忆）
    NEGATION_PATTERNS = [
        r'不再([^，。！？,\.]+)',
        r'不([^，。！？,\.]+)了',
        r'改([^，。！？,\.]+)了',
        r'换成([^，。！？,\.]+)',
        r'现在是([^，。！？,\.]+)',
    ]
    
    def __init__(self, min_confidence: float = 0.6):
        self.min_confidence = min_confidence
    
    def extract(self, message: str, role: str = "user") -> List[ExtractedMemory]:
        """从消息中提取所有可能的记忆.
        
        Args:
            message: 用户消息
            role: 角色（user/assistant）
        
        Returns:
            提取出的记忆列表
        """
        if role != "user":
            return []  # 只从用户消息中提取
        
        results = []
        
        # 提取偏好
        for pattern, sentiment in self.PREFERENCE_PATTERNS:
            matches = re.findall(pattern, message)
            for match in matches:
                memory = self._create_preference(match, sentiment, message)
                if memory and memory.confidence >= self.min_confidence:
                    results.append(memory)
        
        # 提取习惯
        for pattern, freq_type in self.HABIT_PATTERNS:
            matches = re.findall(pattern, message)
            for match in matches:
                memory = self._create_habit(match, freq_type, message)
                if memory and memory.confidence >= self.min_confidence:
                    results.append(memory)
        
        # 提取事实
        for pattern, fact_type in self.FACT_PATTERNS:
            matches = re.findall(pattern, message)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if len(match) == 1 else ' '.join(match)
                memory = self._create_fact(match, fact_type, message)
                if memory and memory.confidence >= self.min_confidence:
                    results.append(memory)
        
        # 提取关系
        for pattern, rel_type in self.RELATION_PATTERNS:
            matches = re.findall(pattern, message)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    memory = self._create_relation(match[0], match[1], rel_type, message)
                    if memory and memory.confidence >= self.min_confidence:
                        results.append(memory)
        
        # 检测否定（更新旧记忆的信号）
        for pattern in self.NEGATION_PATTERNS:
            if re.search(pattern, message):
                # 标记这条消息包含更新信号
                results.append(ExtractedMemory(
                    memory_type="update_signal",
                    category="meta",
                    key="has_update",
                    value="true",
                    confidence=0.9,
                    evidence=message,
                    context=message
                ))
                break
        
        return results
    
    def _create_preference(self, content: str, sentiment: str, 
                          original: str) -> Optional[ExtractedMemory]:
        """创建偏好记忆."""
        content = content.strip()
        if len(content) < 2:
            return None
        
        # 计算置信度
        confidence = 0.7
        if sentiment == 'positive':
            confidence = 0.8
        elif '很' in original or '非常' in original:
            confidence = 0.9
        
        value = '喜欢' if sentiment == 'positive' else '不喜欢'
        
        return ExtractedMemory(
            memory_type="preference",
            category="preference",
            key=content,
            value=value,
            confidence=confidence,
            evidence=original,
            context=original
        )
    
    def _create_habit(self, content: str, freq_type: str,
                     original: str) -> Optional[ExtractedMemory]:
        """创建习惯记忆."""
        content = content.strip()
        if len(content) < 2:
            return None
        
        # 计算置信度
        confidence = 0.6
        if freq_type in ['daily', 'always']:
            confidence = 0.8
        elif freq_type == 'weekly':
            confidence = 0.7
        
        return ExtractedMemory(
            memory_type="habit",
            category="behavior",
            key=content[:50],  # 习惯描述可能较长
            value=freq_type,
            confidence=confidence,
            evidence=original,
            context=original
        )
    
    def _create_fact(self, content: str, fact_type: str,
                    original: str) -> Optional[ExtractedMemory]:
        """创建事实记忆."""
        content = content.strip()
        if len(content) < 2:
            return None
        
        # 计算置信度
        confidence = 0.75
        
        return ExtractedMemory(
            memory_type="fact",
            category=fact_type,
            key=fact_type,
            value=content,
            confidence=confidence,
            evidence=original,
            context=original
        )
    
    def _create_relation(self, subject: str, obj: str, rel_type: str,
                        original: str) -> Optional[ExtractedMemory]:
        """创建关系记忆."""
        subject = subject.strip()
        obj = obj.strip()
        if len(subject) < 2 or len(obj) < 2:
            return None
        
        return ExtractedMemory(
            memory_type="relation",
            category="relation",
            key=f"{subject} -> {obj}",
            value=rel_type,
            confidence=0.7,
            evidence=original,
            context=original
        )
    
    def should_remember(self, message: str) -> Tuple[bool, float]:
        """判断消息是否值得记住.
        
        Returns:
            (是否值得记住, 置信度)
        """
        extractions = self.extract(message)
        if not extractions:
            return False, 0.0
        
        # 取最高置信度
        max_conf = max(e.confidence for e in extractions)
        return True, max_conf


# 便捷函数
def extract_memories(message: str) -> List[ExtractedMemory]:
    """便捷函数：从消息中提取记忆."""
    extractor = MemoryExtractor()
    return extractor.extract(message)


if __name__ == "__main__":
    # 测试
    test_messages = [
        "我喜欢蓝色",
        "我不再喜欢蓝色了，现在喜欢绿色",
        "我每天早上都会喝咖啡",
        "我是程序员，在字节跳动工作",
        "小明是我的朋友",
    ]
    
    extractor = MemoryExtractor()
    for msg in test_messages:
        results = extractor.extract(msg)
        print(f"\n消息: {msg}")
        for r in results:
            print(f"  → [{r.memory_type}] {r.key}: {r.value} (置信度: {r.confidence:.2f})")
