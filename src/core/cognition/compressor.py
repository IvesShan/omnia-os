"""
Context Compressor - Omnia 2.0

参考：Hermes 的 ContextEngine
目的：智能压缩上下文，在保持关键信息的同时减少 token 消耗

策略：
1. 滑动窗口：保留最近 N 条消息
2. 摘要压缩：对旧消息生成摘要
3. 实体提取：保留关键实体引用
4. 优先级队列：重要消息优先保留

Usage:
    from core.cognition.compressor import ContextCompressor
    
    compressor = ContextCompressor(max_tokens=4000)
    compressed = await compressor.compress(messages, preserve_recent=5)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable
import json
import re


@dataclass
class CompressionResult:
    """压缩结果"""
    messages: list[dict]
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    summary: str | None = None
    preserved_entities: dict = field(default_factory=dict)


@dataclass
class MessagePriority:
    """消息优先级"""
    message: dict
    priority: float  # 0.0 - 1.0
    reason: str


class ContextCompressor:
    """
    上下文压缩器
    
    工作流程：
    1. 分析消息重要性
    2. 提取关键实体
    3. 生成旧消息摘要
    4. 组装压缩后的上下文
    """
    
    # 重要关键词（提高优先级）
    IMPORTANT_KEYWORDS = [
        "重要", "关键", "必须", "确认", "决定", "决策",
        "错误", "失败", "问题", "bug", "error",
        "用户", "客户", "需求", "要求",
        "记住", "记住这个", "别忘了",
    ]
    
    # 可忽略的消息模式
    SKIP_PATTERNS = [
        r"^好的[，。！]?$",
        r"^嗯[，。！]?$",
        r"^收到[，。！]?$",
        r"^明白了[，。！]?$",
    ]
    
    def __init__(
        self,
        max_tokens: int = 4000,
        preserve_recent: int = 5,
        llm_summarizer: Callable | None = None
    ):
        """
        Args:
            max_tokens: 最大 token 数
            preserve_recent: 保留最近 N 条消息
            llm_summarizer: LLM 摘要函数
        """
        self.max_tokens = max_tokens
        self.preserve_recent = preserve_recent
        self.llm_summarizer = llm_summarizer
    
    async def compress(
        self,
        messages: list[dict],
        tools_used: list[str] | None = None
    ) -> CompressionResult:
        """
        压缩消息列表
        
        Args:
            messages: 消息列表
            tools_used: 使用过的工具（用于优先级判断）
        
        Returns:
            CompressionResult
        """
        if not messages:
            return CompressionResult(
                messages=[],
                original_tokens=0,
                compressed_tokens=0,
                compression_ratio=1.0
            )
        
        # 1. 计算原始 token 数
        original_tokens = self._estimate_tokens(messages)
        
        # 2. 如果已经在限制内，直接返回
        if original_tokens <= self.max_tokens:
            return CompressionResult(
                messages=messages,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compression_ratio=1.0
            )
        
        # 3. 分析消息优先级
        prioritized = self._analyze_priorities(messages, tools_used)
        
        # 4. 提取关键实体
        entities = self._extract_entities(messages)
        
        # 5. 分割消息：保留部分 + 压缩部分
        preserved_messages = messages[-self.preserve_recent:]
        to_compress = messages[:-self.preserve_recent]
        
        # 6. 生成摘要
        summary = None
        if to_compress and self.llm_summarizer:
            summary = await self._generate_summary(to_compress)
        
        # 7. 组装压缩后的消息
        compressed_messages = []
        
        # 添加摘要（如果有）
        if summary:
            compressed_messages.append({
                "role": "system",
                "content": f"[上下文摘要]\n{summary}"
            })
        
        # 添加关键实体（如果有重要实体）
        if entities:
            entity_text = "\n".join(f"- {k}: {v}" for k, v in entities.items()[:10])
            compressed_messages.append({
                "role": "system",
                "content": f"[关键信息]\n{entity_text}"
            })
        
        # 添加保留的最近消息
        compressed_messages.extend(preserved_messages)
        
        # 8. 计算压缩后 token 数
        compressed_tokens = self._estimate_tokens(compressed_messages)
        
        return CompressionResult(
            messages=compressed_messages,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compressed_tokens / original_tokens,
            summary=summary,
            preserved_entities=entities
        )
    
    def _estimate_tokens(self, messages: list[dict]) -> int:
        """估算 token 数（简化版：1 字 ≈ 0.5 token for Chinese）"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            # 中文约 0.5 token/字，英文约 0.25 token/字符
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
            other_chars = len(content) - chinese_chars
            tokens = chinese_chars * 2 + other_chars * 0.25
            total += int(tokens)
        return total
    
    def _analyze_priorities(
        self,
        messages: list[dict],
        tools_used: list[str] | None = None
    ) -> list[MessagePriority]:
        """分析消息优先级"""
        prioritized = []
        tools_set = set(tools_used or [])
        
        for i, msg in enumerate(messages):
            content = msg.get("content", "")
            role = msg.get("role", "")
            priority = 0.5  # 基础优先级
            reasons = []
            
            # 1. 角色权重
            if role == "system":
                priority += 0.3
                reasons.append("system message")
            elif role == "user":
                priority += 0.1
                reasons.append("user message")
            
            # 2. 位置权重（越近越重要）
            recency = i / len(messages)
            priority += recency * 0.3
            reasons.append(f"recency: {recency:.2f}")
            
            # 3. 关键词权重
            for keyword in self.IMPORTANT_KEYWORDS:
                if keyword in content:
                    priority += 0.15
                    reasons.append(f"keyword: {keyword}")
                    break
            
            # 4. 工具调用权重
            if msg.get("tool_calls"):
                priority += 0.1
                reasons.append("has tool calls")
            
            # 5. 长度惩罚（太长的消息可能需要压缩）
            if len(content) > 1000:
                priority -= 0.1
                reasons.append("long message")
            
            # 6. 可忽略模式检查
            for pattern in self.SKIP_PATTERNS:
                if re.match(pattern, content.strip()):
                    priority -= 0.4
                    reasons.append("skip pattern")
                    break
            
            priority = max(0.0, min(1.0, priority))
            
            prioritized.append(MessagePriority(
                message=msg,
                priority=priority,
                reason=", ".join(reasons)
            ))
        
        return prioritized
    
    def _extract_entities(self, messages: list[dict]) -> dict[str, str]:
        """提取关键实体"""
        entities = {}
        all_content = " ".join(m.get("content", "") for m in messages)
        
        # 提取文件路径
        file_pattern = r'[a-zA-Z0-9_\-/]+\.[a-zA-Z]{1,5}'
        files = set(re.findall(file_pattern, all_content))
        if files:
            entities["相关文件"] = ", ".join(list(files)[:5])
        
        # 提取项目名
        project_pattern = r'(omnia|喵修匠|懂机帝|OpenClaw)'
        projects = set(re.findall(project_pattern, all_content, re.IGNORECASE))
        if projects:
            entities["相关项目"] = ", ".join(projects)
        
        # 提取日期
        date_pattern = r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?'
        dates = set(re.findall(date_pattern, all_content))
        if dates:
            entities["相关日期"] = ", ".join(dates)
        
        # 提取人名/角色
        name_pattern = r'(原点|无限|Omnia|用户|客户)'
        names = set(re.findall(name_pattern, all_content))
        if names:
            entities["相关角色"] = ", ".join(names)
        
        return entities
    
    async def _generate_summary(self, messages: list[dict]) -> str:
        """生成摘要"""
        if not self.llm_summarizer:
            # 简化版：提取前几条消息的要点
            points = []
            for msg in messages[:5]:
                content = msg.get("content", "")[:100]
                role = msg.get("role", "unknown")
                points.append(f"[{role}] {content}...")
            return "\n".join(points)
        
        # 使用 LLM 生成摘要
        summary_prompt = f"""请总结以下对话的关键信息，用简洁的中文表达（不超过 200 字）：

{json.dumps([{"role": m["role"], "content": m["content"][:200]} for m in messages[:10]], ensure_ascii=False, indent=2)}

关键信息摘要："""
        
        try:
            summary = await self.llm_summarizer(summary_prompt)
            return summary[:500]  # 限制摘要长度
        except (json.JSONDecodeError) as e:
            print(f"[Compressor] Summary generation failed: {e}")
            return "（摘要生成失败）"


# ============================================================================
# Specialized Compressors
# ============================================================================

class ToolResultCompressor:
    """
    工具结果压缩器
    
    专门处理过长的工具返回结果
    """
    
    def __init__(self, max_length: int = 1500):
        self.max_length = max_length
    
    def compress(self, result: Any) -> str:
        """压缩工具结果"""
        if isinstance(result, str):
            text = result
        elif isinstance(result, dict):
            # 提取关键字段
            important_keys = ["error", "stdout", "stderr", "content", "path", "result"]
            parts = []
            for key in important_keys:
                if key in result:
                    parts.append(f"{key}: {str(result[key])[:500]}")
            text = "\n".join(parts) if parts else json.dumps(result, ensure_ascii=False)
        else:
            text = str(result)
        
        # 截断
        if len(text) > self.max_length:
            return text[:self.max_length] + "\n...[已截断]"
        
        return text


class ConversationSummarizer:
    """
    对话摘要器
    
    对完整对话生成摘要，用于跨会话记忆
    """
    
    def __init__(self, llm_caller: Callable):
        self.llm_caller = llm_caller
    
    async def summarize(
        self,
        messages: list[dict],
        focus: str | None = None
    ) -> str:
        """
        生成对话摘要
        
        Args:
            messages: 对话消息
            focus: 关注点（可选）
        
        Returns:
            摘要文本
        """
        focus_text = f"重点关注：{focus}\n\n" if focus else ""
        
        prompt = f"""{focus_text}请总结以下对话的核心内容，提取：
1. 主要话题
2. 关键决策
3. 待办事项
4. 重要实体（人名、项目、文件等）

对话内容：
{json.dumps([{"role": m["role"], "content": m["content"][:300]} for m in messages[-20:]], ensure_ascii=False, indent=2)}

请用简洁的中文总结："""
        
        summary = await self.llm_caller(prompt)
        return summary
