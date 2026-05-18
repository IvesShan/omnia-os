"""
Omnia Simple Engine - 无 LLM 的降级引擎

当 LLM 不可用时，提供基于规则和检索的响应能力。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.omnia.config import settings


class TaskComplexity(Enum):
    """任务复杂度级别"""
    SIMPLE = "simple"       # 简单问答、指令
    MEDIUM = "medium"       # 需要检索、推理
    COMPLEX = "complex"     # 需要深度推理
    CRITICAL = "critical"   # 必须使用 LLM


@dataclass
class SimpleResponse:
    """简单引擎响应"""
    reply: str
    confidence: float
    complexity: TaskComplexity
    needs_llm: bool = False
    source: str = "simple_engine"
    metadata: Dict[str, Any] = None


class ComplexityEstimator:
    """任务复杂度评估器"""
    
    # 简单模式关键词
    SIMPLE_PATTERNS = [
        r'^(你好|hi|hello|hey)',
        r'^(谢谢|thanks|thank you)',
        r'^(再见|bye|goodbye)',
        r'^(是|否|yes|no)$',
        r'(时间|几点|现在时间)',
        r'(日期|今天|今天是)',
        r'(状态|status)',
        r'(你是谁|自我介绍)',
        r'(帮助|help|你能做什么)',
    ]
    
    # 中等复杂度关键词
    MEDIUM_PATTERNS = [
        r'(解释|explain|什么是|what is)',
        r'(如何|how to|怎么)',
        r'(比较|compare|区别)',
        r'(列表|list|列出)',
        r'(记忆|memory|回忆)',
    ]
    
    # 高复杂度关键词
    COMPLEX_PATTERNS = [
        r'(分析|analyze|深度|deep)',
        r'(推理|reasoning|逻辑|logic)',
        r'(创作|create|生成|generate)',
        r'(代码|code|编程|program)',
        r'(优化|optimize|改进|improve)',
    ]
    
    def estimate(self, user_input: str) -> TaskComplexity:
        """评估任务复杂度"""
        user_input_lower = user_input.lower().strip()
        
        # 检查高复杂度
        for pattern in self.COMPLEX_PATTERNS:
            if re.search(pattern, user_input_lower):
                return TaskComplexity.COMPLEX
        
        # 检查中等复杂度
        for pattern in self.MEDIUM_PATTERNS:
            if re.search(pattern, user_input_lower):
                return TaskComplexity.MEDIUM
        
        # 检查简单模式
        for pattern in self.SIMPLE_PATTERNS:
            if re.search(pattern, user_input_lower):
                return TaskComplexity.SIMPLE
        
        # 默认中等
        return TaskComplexity.MEDIUM


class RuleEngine:
    """基于规则的响应引擎"""
    
    def __init__(self):
        self.rules = self._build_rules()
    
    def _build_rules(self) -> List[Dict[str, Any]]:
        """构建规则库"""
        return [
            # 问候
            {
                "patterns": [r'^(你好|hi|hello|hey)', r'^(您好)'],
                "responses": [
                    "你好！我是 Omnia，很高兴为你服务。",
                    "Hi! 我是 Omnia，有什么可以帮你的吗？",
                ],
                "confidence": 0.95,
            },
            # 感谢
            {
                "patterns": [r'^(谢谢|thanks|thank you)'],
                "responses": [
                    "不客气！",
                    "很高兴能帮到你！",
                    "随时为你服务！",
                ],
                "confidence": 0.95,
            },
            # 告别
            {
                "patterns": [r'^(再见|bye|goodbye)'],
                "responses": [
                    "再见！期待下次见面。",
                    "Bye! 有需要随时找我。",
                ],
                "confidence": 0.95,
            },
            # 时间查询
            {
                "patterns": [r'(时间|几点|现在时间)'],
                "action": "get_time",
                "confidence": 0.90,
            },
            # 日期查询
            {
                "patterns": [r'(日期|今天|今天是)'],
                "action": "get_date",
                "confidence": 0.90,
            },
            # 状态查询
            {
                "patterns": [r'(状态|status|系统状态)'],
                "action": "get_status",
                "confidence": 0.90,
            },
            # 帮助
            {
                "patterns": [r'(帮助|help|你能做什么)'],
                "responses": [
                    "我可以帮你：\n"
                    "1. 回答问题和提供建议\n"
                    "2. 查询和管理记忆\n"
                    "3. 执行系统操作\n"
                    "4. 协助编程和开发任务\n\n"
                    "有什么需要帮助的吗？",
                ],
                "confidence": 0.85,
            },
            # 自我介绍
            {
                "patterns": [r'(你是谁|自我介绍|introduce)'],
                "responses": [
                    "我是 Omnia，一个持续进化的 AI 操作系统。\n\n"
                    "我的特点：\n"
                    "• 拥有持久记忆，能记住我们的每次对话\n"
                    "• 可以执行各种工具和脚本\n"
                    "• 支持多轮推理和复杂任务规划\n"
                    "• 在 LLM 不可用时也能提供基础服务\n\n"
                    "我由 原点 和 无限 共同创造。",
                ],
                "confidence": 0.90,
            },
        ]
    
    def match(self, user_input: str) -> Optional[Dict[str, Any]]:
        """匹配规则"""
        user_input_lower = user_input.lower().strip()
        
        for rule in self.rules:
            for pattern in rule.get("patterns", []):
                if re.search(pattern, user_input_lower):
                    return rule
        
        return None
    
    def execute_action(self, action: str) -> str:
        """执行动作"""
        from datetime import datetime
        
        if action == "get_time":
            now = datetime.now()
            return f"现在是 {now.strftime('%H:%M:%S')}"
        
        elif action == "get_date":
            now = datetime.now()
            return f"今天是 {now.strftime('%Y年%m月%d日')}，星期{['一','二','三','四','五','六','日'][now.weekday()]}"
        
        elif action == "get_status":
            return (
                "系统状态：\n"
                "• 简单引擎：✅ 运行中\n"
                "• 记忆系统：✅ 可用\n"
                "• LLM 模式：⚠️ 降级模式\n\n"
                "系统运行正常，但建议启用 LLM 以获得更好的体验。"
            )
        
        return "动作执行完成"


class KnowledgeRetriever:
    """知识检索引擎"""
    
    def __init__(self, memory_palace):
        self.memory = memory_palace
    
    def search(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """搜索相关知识"""
        results = []
        
        # 从记忆宫殿搜索
        if self.memory:
            try:
                facts = self.memory.query_facts(query, limit=limit)
                for fact in facts:
                    results.append({
                        "content": fact.get("content", ""),
                        "source": "memory_palace",
                        "layer": "facts",
                        "confidence": 0.8,
                    })
            except Exception as e:
                print(f"[KnowledgeRetriever] Error searching facts: {e}")
        
        return results


class SimpleEngine:
    """Omnia 简单引擎 - 无 LLM 降级模式"""
    
    def __init__(self, workspace_root: Path = None):
        self.workspace_root = workspace_root or Path.home()
        self.complexity_estimator = ComplexityEstimator()
        self.rule_engine = RuleEngine()
        
        # 初始化记忆系统
        self.memory = None
        self.knowledge_retriever = None
        
        try:
            from src.core.memory_palace.memory_palace import MemoryPalace
            self.memory = MemoryPalace(self.workspace_root)
            self.knowledge_retriever = KnowledgeRetriever(self.memory)
        except Exception as e:
            print(f"[SimpleEngine] Warning: Memory system unavailable: {e}")
    
    def process(self, user_input: str, conversation_history: List[Dict] = None) -> SimpleResponse:
        """处理用户输入"""
        
        # 1. 评估复杂度
        complexity = self.complexity_estimator.estimate(user_input)
        
        # 2. 简单任务 - 规则引擎
        if complexity == TaskComplexity.SIMPLE:
            rule = self.rule_engine.match(user_input)
            
            if rule:
                # 执行动作
                if "action" in rule:
                    reply = self.rule_engine.execute_action(rule["action"])
                    return SimpleResponse(
                        reply=reply,
                        confidence=rule.get("confidence", 0.8),
                        complexity=complexity,
                        source="rule_engine_action",
                    )
                
                # 返回预设响应
                elif "responses" in rule:
                    import random
                    reply = random.choice(rule["responses"])
                    return SimpleResponse(
                        reply=reply,
                        confidence=rule.get("confidence", 0.8),
                        complexity=complexity,
                        source="rule_engine",
                    )
        
        # 3. 中等任务 - 知识检索
        if complexity in [TaskComplexity.MEDIUM, TaskComplexity.SIMPLE]:
            if self.knowledge_retriever:
                results = self.knowledge_retriever.search(user_input)
                
                if results:
                    # 构建响应
                    context = "\n\n".join([
                        f"• {r['content']}" 
                        for r in results[:2]
                    ])
                    
                    reply = f"根据我的记忆，找到了相关信息：\n\n{context}\n\n（注：这是简化模式响应，建议启用 LLM 获得更好的回答）"
                    
                    return SimpleResponse(
                        reply=reply,
                        confidence=0.6,
                        complexity=complexity,
                        source="knowledge_retrieval",
                        metadata={"results_count": len(results)},
                    )
        
        # 4. 复杂任务 - 需要 LLM
        if complexity in [TaskComplexity.COMPLEX, TaskComplexity.CRITICAL]:
            return SimpleResponse(
                reply="这个问题需要深度推理能力。当前运行在简化模式，建议启用 LLM 以获得更好的回答。\n\n或者，你可以尝试简化你的问题，我会尽力基于现有知识回答。",
                confidence=0.3,
                complexity=complexity,
                needs_llm=True,
                source="fallback",
            )
        
        # 5. 默认响应
        return SimpleResponse(
            reply="我理解了你的问题。当前运行在简化模式，能力有限。\n\n建议启用 LLM 模式以获得更好的体验。或者你可以换个方式提问，我会尽力帮助你。",
            confidence=0.5,
            complexity=complexity,
            needs_llm=True,
            source="default",
        )
    
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        return True  # 简单引擎总是可用


# 测试代码
if __name__ == "__main__":
    engine = SimpleEngine()
    
    test_cases = [
        "你好",
        "现在几点了",
        "今天是几号",
        "你能做什么",
        "你是谁",
        "解释一下什么是记忆系统",
        "帮我写一个 Python 脚本",
    ]
    
    print("=" * 60)
    print("Omnia Simple Engine 测试")
    print("=" * 60)
    
    for test in test_cases:
        print(f"\n用户: {test}")
        result = engine.process(test)
        print(f"回复: {result.reply}")
        print(f"置信度: {result.confidence}")
        print(f"复杂度: {result.complexity.value}")
        print(f"需要 LLM: {result.needs_llm}")
        print("-" * 60)
