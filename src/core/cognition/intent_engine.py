"""
Intent Engine - Omnia 2.0

创新点：意图驱动架构
目的：在工具调用前理解用户意图，更准确地响应用户需求

Intent Types:
- query: 查询信息
- action: 执行动作
- create: 创建内容
- modify: 修改内容
- delete: 删除内容
- analyze: 分析数据
- learn: 学习新技能
- reflect: 反思总结
- chat: 普通对话

Usage:
    from core.cognition.intent_engine import IntentEngine
    
    engine = IntentEngine()
    intent = await engine.recognize("帮我删除 test.txt 文件", context)
    # Intent(type="delete", confidence=0.95, entities={"file": "test.txt"})
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
import re


class IntentType(Enum):
    """意图类型"""
    QUERY = "query"           # 查询信息
    ACTION = "action"         # 执行动作
    CREATE = "create"         # 创建内容
    MODIFY = "modify"         # 修改内容
    DELETE = "delete"         # 删除内容
    ANALYZE = "analyze"       # 分析数据
    LEARN = "learn"           # 学习新技能
    REFLECT = "reflect"       # 反思总结
    CHAT = "chat"             # 普通对话
    UNKNOWN = "unknown"       # 未知意图


@dataclass
class Entity:
    """提取的实体"""
    name: str
    value: str
    confidence: float = 1.0


@dataclass
class Intent:
    """用户意图"""
    type: IntentType
    confidence: float
    entities: dict[str, Entity] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    sub_intents: list[Intent] = field(default_factory=list)
    raw_text: str = ""
    normalized_text: str = ""


@dataclass
class IntentContext:
    """意图识别上下文"""
    session_id: str
    user_id: str
    recent_messages: list[dict] = field(default_factory=list)
    user_preferences: dict = field(default_factory=dict)
    available_tools: list[str] = field(default_factory=list)


# ============================================================================
# Rule-based Intent Matcher
# ============================================================================

class RuleMatcher:
    """
    基于规则的意图匹配器
    
    使用关键词和模式匹配快速识别意图
    """
    
    # 意图关键词映射
    INTENT_PATTERNS: dict[IntentType, list[tuple[str, float]]] = {
        IntentType.QUERY: [
            (r"(什么|怎么样|如何|怎么|哪|是否|有没有|查询|查看|看看|检查)", 0.7),
            (r"(?:(?:帮)?我(?:想)?(?:看看|查查|确认|了解))", 0.8),
            (r"(?:状态|情况|信息|数据)", 0.5),
        ],
        IntentType.ACTION: [
            (r"(帮我|请|麻烦|执行|运行|启动|停止|重启|打开|关闭)", 0.7),
            (r"(?:执行|运行|启动)(.+?)(?:命令|脚本|程序)", 0.9),
        ],
        IntentType.CREATE: [
            (r"(创建|新建|生成|写一个|做一个|制作|添加)", 0.8),
            (r"(?:创建|新建)(?:文件|目录|项目|文档)", 0.9),
        ],
        IntentType.MODIFY: [
            (r"(修改|编辑|更新|更改|改变|调整)", 0.8),
            (r"(?:修改|编辑|更新)(?:文件|配置|设置)", 0.9),
        ],
        IntentType.DELETE: [
            (r"(删除|移除|清除|卸载|干掉)", 0.9),
            (r"(?:删除|移除)(?:文件|目录|记录)", 0.95),
        ],
        IntentType.ANALYZE: [
            (r"(分析|统计|比较|对比|评估|研究)", 0.8),
            (r"(?:分析|统计)(?:数据|日志|性能)", 0.9),
        ],
        IntentType.LEARN: [
            (r"(学习|记住|记录|保存|存储)", 0.7),
            (r"(?:学习|记住)(?:技能|知识|偏好)", 0.9),
        ],
        IntentType.REFLECT: [
            (r"(总结|回顾|反思|梳理|复盘)", 0.8),
            (r"(?:总结|回顾|梳理)(?:一下|状态|进展)", 0.9),
        ],
        IntentType.CHAT: [
            (r"(你好|嗨|哈喽|早上好|晚上好)", 0.9),
            (r"(?:聊聊|谈谈|说说)", 0.7),
        ],
    }
    
    # 实体提取模式
    ENTITY_PATTERNS = {
        "file": [
            r"([a-zA-Z0-9_\-/]+\.py)",
            r"([a-zA-Z0-9_\-/]+\.js)",
            r"([a-zA-Z0-9_\-/]+\.md)",
            r"([a-zA-Z0-9_\-/]+\.txt)",
            r"([a-zA-Z0-9_\-/]+\.json)",
            r"文件\s*[：:]*\s*([a-zA-Z0-9_\-/\.]+)",
        ],
        "directory": [
            r"目录\s*[：:]*\s*([a-zA-Z0-9_\-/]+)",
            r"文件夹\s*[：:]*\s*([a-zA-Z0-9_\-/]+)",
        ],
        "command": [
            r"命令\s*[：:]*\s*(.+?)(?:\s|$)",
            r"执行\s+(.+?)(?:\s|$)",
        ],
        "project": [
            r"(omnia|喵修匠|懂机帝)",
        ],
    }
    
    def match(self, text: str) -> Intent | None:
        """
        快速匹配意图
        
        Returns:
            Intent if high confidence match, None otherwise
        """
        text_lower = text.lower()
        scores: dict[IntentType, float] = {}
        
        # 计算每个意图的分数
        for intent_type, patterns in self.INTENT_PATTERNS.items():
            max_score = 0.0
            for pattern, base_score in patterns:
                if re.search(pattern, text_lower):
                    max_score = max(max_score, base_score)
            if max_score > 0:
                scores[intent_type] = max_score
        
        if not scores:
            return None
        
        # 取最高分
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        
        # 高置信度才返回
        if best_score >= 0.8:
            entities = self._extract_entities(text)
            return Intent(
                type=best_type,
                confidence=best_score,
                entities=entities,
                raw_text=text,
                normalized_text=text_lower,
            )
        
        return None
    
    def _extract_entities(self, text: str) -> dict[str, Entity]:
        """提取实体"""
        entities = {}
        
        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    entities[entity_type] = Entity(
                        name=entity_type,
                        value=match.group(1),
                        confidence=0.9
                    )
                    break
        
        return entities


# ============================================================================
# LLM-based Intent Recognizer
# ============================================================================

class LLMIntentRecognizer:
    """
    基于大模型的意图识别器
    
    当规则匹配不够准确时，使用 LLM 进行深度理解
    """
    
    INTENT_PROMPT = """分析用户消息的意图，返回 JSON 格式结果。

用户消息：{message}

上下文：
- 最近话题：{recent_topics}
- 可用工具：{tools}

意图类型：
- query: 查询信息
- action: 执行动作
- create: 创建内容
- modify: 修改内容
- delete: 删除内容
- analyze: 分析数据
- learn: 学习新技能
- reflect: 反思总结
- chat: 普通对话

返回格式：
{
  "intent_type": "query",
  "confidence": 0.95,
  "entities": {
    "file": "test.py",
    "operation": "read"
  },
  "constraints": ["需要确认"],
  "reasoning": "用户想查看文件内容"
}

只返回 JSON，不要其他内容。"""

    def __init__(self, call_model: Callable):
        """
        Args:
            call_model: 模型调用函数 (prompt: str) -> str
        """
        self.call_model = call_model
    
    async def recognize(
        self,
        message: str,
        context: IntentContext
    ) -> Intent:
        """使用 LLM 识别意图"""
        import json
        
        # 构建提示
        recent_topics = [m.get("content", "")[:50] for m in context.recent_messages[-3:]]
        tools = ", ".join(context.available_tools[:10])
        
        prompt = self.INTENT_PROMPT.format(
            message=message,
            recent_topics=recent_topics,
            tools=tools
        )
        
        try:
            response = await self.call_model(prompt)
            
            # 解析 JSON
            # 提取 JSON 块
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                
                intent_type = IntentType(data.get("intent_type", "unknown"))
                confidence = data.get("confidence", 0.5)
                
                entities = {}
                for k, v in data.get("entities", {}).items():
                    entities[k] = Entity(name=k, value=str(v))
                
                return Intent(
                    type=intent_type,
                    confidence=confidence,
                    entities=entities,
                    constraints=data.get("constraints", []),
                    raw_text=message,
                    normalized_text=message.lower(),
                )
        except Exception as e:
            print(f"[IntentEngine] LLM recognition failed: {e}")
        
        # 失败时返回未知意图
        return Intent(
            type=IntentType.UNKNOWN,
            confidence=0.0,
            raw_text=message,
            normalized_text=message.lower(),
        )


# ============================================================================
# Intent Engine
# ============================================================================

class IntentEngine:
    """
    意图引擎
    
    工作流程：
    1. 规则快速匹配（高置信度直接返回）
    2. LLM 深度理解（规则不确定时）
    3. 上下文修正（根据历史调整）
    """
    
    def __init__(self, llm_caller: Callable | None = None):
        self.rule_matcher = RuleMatcher()
        self.llm_recognizer = LLMIntentRecognizer(llm_caller) if llm_caller else None
    
    async def recognize(
        self,
        message: str,
        context: IntentContext
    ) -> Intent:
        """
        识别用户意图
        
        Args:
            message: 用户消息
            context: 上下文
        
        Returns:
            识别出的意图
        """
        # 1. 规则快速匹配
        rule_intent = self.rule_matcher.match(message)
        if rule_intent and rule_intent.confidence >= 0.9:
            return rule_intent
        
        # 2. LLM 深度理解
        if self.llm_recognizer:
            llm_intent = await self.llm_recognizer.recognize(message, context)
            
            # 如果规则匹配有结果，合并
            if rule_intent:
                llm_intent.entities.update(rule_intent.entities)
            
            return llm_intent
        
        # 3. 返回规则结果或未知
        return rule_intent or Intent(
            type=IntentType.UNKNOWN,
            confidence=0.0,
            raw_text=message,
            normalized_text=message.lower(),
        )
    
    def decompose(self, intent: Intent) -> list[Intent]:
        """
        分解复杂意图
        
        例如："帮我整理项目并部署到服务器"
        → Intent 1: "整理项目"
        → Intent 2: "部署到服务器"
        """
        # 检测连接词
        connectors = ["并", "然后", "接着", "之后", "再", "同时"]
        
        text = intent.raw_text
        for conn in connectors:
            if conn in text:
                parts = text.split(conn, 1)
                if len(parts) == 2:
                    sub_intents = []
                    for part in parts:
                        part = part.strip()
                        if part:
                            sub_intent = Intent(
                                type=intent.type,
                                confidence=intent.confidence * 0.9,
                                raw_text=part,
                                normalized_text=part.lower(),
                            )
                            sub_intents.append(sub_intent)
                    if sub_intents:
                        return sub_intents
        
        return [intent]
    
    def to_tool_hints(self, intent: Intent) -> list[str]:
        """
        根据意图推荐工具
        
        Returns:
            推荐的工具名称列表
        """
        hints = {
            IntentType.QUERY: ["read_file", "list_directory", "web_search", "query_memory"],
            IntentType.ACTION: ["execute_shell", "read_file"],
            IntentType.CREATE: ["write_file", "execute_shell"],
            IntentType.MODIFY: ["write_file", "execute_shell"],
            IntentType.DELETE: ["execute_shell"],
            IntentType.ANALYZE: ["read_file", "execute_shell", "web_search"],
            IntentType.LEARN: ["query_memory"],
            IntentType.REFLECT: ["query_memory"],
            IntentType.CHAT: [],
            IntentType.UNKNOWN: [],
        }
        return hints.get(intent.type, [])


# ============================================================================
# Convenience Functions
# ============================================================================

def create_intent_engine(llm_caller: Callable | None = None) -> IntentEngine:
    """创建意图引擎实例"""
    return IntentEngine(llm_caller)
