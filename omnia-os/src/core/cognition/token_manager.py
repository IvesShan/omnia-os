"""
Token Manager - Token 计数和上下文管理

功能：
- 估算消息的 token 数量
- 检测上下文溢出
- 智能压缩历史消息
- 支持多种模型的上下文窗口配置
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import re


@dataclass
class ModelContextWindow:
    """模型上下文窗口配置"""
    name: str
    context_window: int  # 总上下文窗口
    max_output: int  # 最大输出 tokens
    recommended_utilization: float  # 推荐利用率 (0.0-1.0)


# 常见模型的上下文窗口配置
MODEL_CONTEXT_WINDOWS: Dict[str, ModelContextWindow] = {
    # Kimi
    "kimi": ModelContextWindow("kimi", 128000, 4096, 0.7),
    "moonshot-v1-8k": ModelContextWindow("moonshot-v1-8k", 8192, 4096, 0.7),
    "moonshot-v1-32k": ModelContextWindow("moonshot-v1-32k", 32768, 4096, 0.7),
    "moonshot-v1-128k": ModelContextWindow("moonshot-v1-128k", 131072, 4096, 0.7),
    
    # 智谱 GLM 系列
    "glm-5": ModelContextWindow("glm-5", 128000, 4096, 0.7),
    "glm-5-plus": ModelContextWindow("glm-5-plus", 128000, 4096, 0.7),
    "glm-4": ModelContextWindow("glm-4", 128000, 4096, 0.7),
    "glm-4-plus": ModelContextWindow("glm-4-plus", 128000, 4096, 0.7),
    "glm-4-air": ModelContextWindow("glm-4-air", 128000, 4096, 0.7),
    "glm-4-airx": ModelContextWindow("glm-4-airx", 8192, 4096, 0.7),
    "glm-4-flash": ModelContextWindow("glm-4-flash", 128000, 4096, 0.7),
    "chatglm-turbo": ModelContextWindow("chatglm-turbo", 32768, 4096, 0.7),
    "chatglm_turbo": ModelContextWindow("chatglm_turbo", 32768, 4096, 0.7),
    
    # Qianfan (百度千帆平台 - 多模型接口)
    "qianfan": ModelContextWindow("qianfan", 128000, 4096, 0.7),  # 默认值，实际取决于后端模型
    "qianfan-code-latest": ModelContextWindow("qianfan-code-latest", 8000, 2048, 0.6),
    "ERNIE-Bot-4": ModelContextWindow("ERNIE-Bot-4", 8000, 2048, 0.6),
    
    # DeepSeek
    "deepseek": ModelContextWindow("deepseek", 64000, 4096, 0.7),
    "deepseek-chat": ModelContextWindow("deepseek-chat", 64000, 4096, 0.7),
    "deepseek-coder": ModelContextWindow("deepseek-coder", 16000, 4096, 0.7),
    
    # OpenAI
    "gpt-4o": ModelContextWindow("gpt-4o", 128000, 4096, 0.7),
    "gpt-4o-mini": ModelContextWindow("gpt-4o-mini", 128000, 4096, 0.7),
    "gpt-4-turbo": ModelContextWindow("gpt-4-turbo", 128000, 4096, 0.7),
    "gpt-3.5-turbo": ModelContextWindow("gpt-3.5-turbo", 16385, 4096, 0.7),
    
    # Local LLM (默认)
    "local": ModelContextWindow("local", 8192, 2048, 0.6),
}


def estimate_text_tokens(text: str) -> int:
    """
    估算文本的 token 数量
    
    使用简单的启发式方法：
    - 英文：约 4 字符 = 1 token
    - 中文：约 1.5 字符 = 1 token
    - 代码：约 3 字符 = 1 token
    
    Args:
        text: 要估算的文本
        
    Returns:
        估算的 token 数量
    """
    if not text:
        return 0
    
    # 统计中文字符
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    
    # 统计英文字符（包括数字和标点）
    english_chars = len(text) - chinese_chars
    
    # 估算 tokens
    # 中文：约 1.5 字符/token
    # 英文：约 4 字符/token
    chinese_tokens = chinese_chars / 1.5
    english_tokens = english_chars / 4
    
    # 加上一些额外开销（格式化、特殊 token 等）
    overhead = 5
    
    return int(chinese_tokens + english_tokens + overhead)


def estimate_messages_tokens(messages: List[Dict[str, Any]]) -> int:
    """
    估算消息列表的 token 数量
    
    Args:
        messages: 消息列表，每条消息包含 role 和 content
        
    Returns:
        估算的总 token 数量
    """
    total_tokens = 0
    
    for msg in messages:
        # 每条消息的格式化开销
        total_tokens += 4  # <im_start>{role}\n{content}<im_end>\n
        
        # role 的 tokens
        role = msg.get("role", "")
        total_tokens += estimate_text_tokens(role)
        
        # content 的 tokens
        content = msg.get("content", "")
        if isinstance(content, str):
            total_tokens += estimate_text_tokens(content)
        elif isinstance(content, list):
            # 多模态消息
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    total_tokens += estimate_text_tokens(part.get("text", ""))
                elif isinstance(part, str):
                    total_tokens += estimate_text_tokens(part)
        
        # metadata 的 tokens（如果有）
        metadata = msg.get("metadata", {})
        if metadata:
            total_tokens += estimate_text_tokens(str(metadata))
    
    # 添加系统提示的开销
    total_tokens += 20
    
    return total_tokens


def get_model_context_window(model_name: str) -> ModelContextWindow:
    """
    获取模型的上下文窗口配置
    
    Args:
        model_name: 模型名称
        
    Returns:
        模型上下文窗口配置
    """
    # 1. 直接匹配（原始名称）
    if model_name in MODEL_CONTEXT_WINDOWS:
        return MODEL_CONTEXT_WINDOWS[model_name]
    
    # 2. 标准化后匹配
    model_key = model_name.lower().replace("-", "_").replace(".", "_")
    if model_key in MODEL_CONTEXT_WINDOWS:
        return MODEL_CONTEXT_WINDOWS[model_key]
    
    # 3. 模糊匹配（避免误匹配到短名称）
    for key, config in MODEL_CONTEXT_WINDOWS.items():
        # 只匹配包含关系，但排除太短的键（如 "qianfan" 不应匹配 "qianfan-code-latest"）
        if len(key) > 5 and (key in model_key or model_key in key):
            return config
    
    # 4. 默认返回 local 配置
    return MODEL_CONTEXT_WINDOWS["local"]


def check_context_overflow(
    messages: List[Dict[str, Any]],
    model_name: str = "kimi",
    reserved_for_output: int = 2000
) -> Dict[str, Any]:
    """
    检查上下文是否溢出
    
    Args:
        messages: 消息列表
        model_name: 模型名称
        reserved_for_output: 为输出预留的 tokens
        
    Returns:
        包含溢出信息的字典：
        - overflow: 是否溢出
        - current_tokens: 当前 tokens
        - max_tokens: 最大可用 tokens
        - utilization: 利用率
        - recommended_tokens: 推荐的 tokens 上限
    """
    model_config = get_model_context_window(model_name)
    current_tokens = estimate_messages_tokens(messages)
    
    # 可用于输入的 tokens
    available_for_input = model_config.context_window - reserved_for_output
    
    # 推荐的上限
    recommended_limit = int(available_for_input * model_config.recommended_utilization)
    
    return {
        "overflow": current_tokens > available_for_input,
        "warning": current_tokens > recommended_limit,
        "current_tokens": current_tokens,
        "max_tokens": available_for_input,
        "recommended_tokens": recommended_limit,
        "utilization": current_tokens / available_for_input,
        "model": model_config.name,
        "context_window": model_config.context_window
    }


def smart_compress_history(
    messages: List[Dict[str, Any]],
    model_name: str = "kimi",
    preserve_recent: int = 10,
    reserved_for_output: int = 2000
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    智能压缩历史消息
    
    策略：
    1. 保留最近的消息
    2. 压缩中间的消息（摘要）
    3. 保留系统消息
    
    Args:
        messages: 消息列表
        model_name: 模型名称
        preserve_recent: 保留最近的消息数量
        reserved_for_output: 为输出预留的 tokens
        
    Returns:
        (压缩后的消息列表, 压缩统计信息)
    """
    if not messages:
        return [], {"compressed": False, "reason": "empty_messages"}
    
    # 检查是否需要压缩
    overflow_info = check_context_overflow(messages, model_name, reserved_for_output)
    
    if not overflow_info["overflow"] and not overflow_info["warning"]:
        return messages, {
            "compressed": False,
            "reason": "no_overflow",
            "tokens": overflow_info["current_tokens"]
        }
    
    # 分离系统消息和普通消息
    system_messages = [m for m in messages if m.get("role") == "system"]
    regular_messages = [m for m in messages if m.get("role") != "system"]
    
    # 如果消息太少，直接返回
    if len(regular_messages) <= preserve_recent:
        return messages, {
            "compressed": False,
            "reason": "too_few_messages",
            "count": len(regular_messages)
        }
    
    # 保留最近的消息
    recent_messages = regular_messages[-preserve_recent:]
    old_messages = regular_messages[:-preserve_recent]
    
    # 创建摘要消息
    summary_content = _create_summary(old_messages)
    
    summary_message = {
        "role": "system",
        "content": f"[历史摘要]\n{summary_content}",
        "metadata": {
            "type": "compressed_summary",
            "original_count": len(old_messages),
            "compression_ratio": 0.1
        }
    }
    
    # 合并消息
    compressed_messages = system_messages + [summary_message] + recent_messages
    
    # 计算压缩效果
    original_tokens = overflow_info["current_tokens"]
    compressed_tokens = estimate_messages_tokens(compressed_messages)
    
    stats = {
        "compressed": True,
        "original_count": len(messages),
        "compressed_count": len(compressed_messages),
        "original_tokens": original_tokens,
        "compressed_tokens": compressed_tokens,
        "tokens_saved": original_tokens - compressed_tokens,
        "compression_ratio": compressed_tokens / original_tokens if original_tokens > 0 else 0,
        "model": model_name
    }
    
    return compressed_messages, stats


def _create_summary(messages: List[Dict[str, Any]]) -> str:
    """
    创建消息摘要
    
    Args:
        messages: 要摘要的消息列表
        
    Returns:
        摘要文本
    """
    # 统计关键信息
    user_messages = [m for m in messages if m.get("role") == "user"]
    assistant_messages = [m for m in messages if m.get("role") == "assistant"]
    
    # 提取关键内容（简化版）
    topics = []
    for msg in user_messages[:5]:  # 只看前 5 条用户消息
        content = msg.get("content", "")
        if isinstance(content, str) and len(content) > 50:
            # 提取前 100 个字符作为主题
            topics.append(content[:100] + "..." if len(content) > 100 else content)
    
    # 构建摘要
    summary_parts = [
        f"共 {len(messages)} 条历史消息",
        f"用户消息: {len(user_messages)} 条",
        f"助手回复: {len(assistant_messages)} 条",
    ]
    
    if topics:
        summary_parts.append("\n主要话题:")
        for i, topic in enumerate(topics[:3], 1):
            summary_parts.append(f"  {i}. {topic}")
    
    return "\n".join(summary_parts)


def get_token_stats(messages: List[Dict[str, Any]], model_name: str = "kimi") -> Dict[str, Any]:
    """
    获取 token 统计信息
    
    Args:
        messages: 消息列表
        model_name: 模型名称
        
    Returns:
        统计信息字典
    """
    model_config = get_model_context_window(model_name)
    total_tokens = estimate_messages_tokens(messages)
    
    # 按角色统计
    role_stats = {}
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        tokens = estimate_text_tokens(content) if isinstance(content, str) else 0
        
        if role not in role_stats:
            role_stats[role] = {"count": 0, "tokens": 0}
        
        role_stats[role]["count"] += 1
        role_stats[role]["tokens"] += tokens
    
    return {
        "total_tokens": total_tokens,
        "message_count": len(messages),
        "model": model_config.name,
        "context_window": model_config.context_window,
        "utilization": total_tokens / model_config.context_window,
        "remaining_tokens": model_config.context_window - total_tokens,
        "role_breakdown": role_stats
    }


# 便捷函数
def count_tokens(text: str) -> int:
    """快速计算文本的 token 数量"""
    return estimate_text_tokens(text)


def count_message_tokens(message: Dict[str, Any]) -> int:
    """快速计算单条消息的 token 数量"""
    return estimate_messages_tokens([message])
