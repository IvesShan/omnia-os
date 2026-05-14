"""
Token Manager - 管理上下文 token 限制

根据不同模型的上下文窗口大小，动态管理消息历史。
"""

from typing import List, Dict, Tuple
import re


def estimate_tokens(text: str) -> int:
    """
    估算文本的 token 数量
    
    简单估算规则：
    - 英文：~4 字符 = 1 token
    - 中文：~2 字符 = 1 token
    - 代码：~3 字符 = 1 token
    
    这是一个粗略估算，实际值可能相差 10-20%
    """
    if not text:
        return 0
    
    # 统计中文字符
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    
    # 统计英文字符和数字
    english_chars = len(re.findall(r'[a-zA-Z0-9]', text))
    
    # 其他字符（包括空格、标点等）
    other_chars = len(text) - chinese_chars - english_chars
    
    # 估算 tokens
    # 中文：约 2 字符/token
    # 英文：约 4 字符/token
    # 其他：约 3 字符/token
    tokens = (
        chinese_chars // 2 +
        english_chars // 4 +
        other_chars // 3
    )
    
    return max(1, tokens)


def estimate_messages_tokens(messages: List[Dict[str, str]]) -> int:
    """
    估算消息列表的总 token 数量
    
    包括：
    - 消息内容
    - 角色标识（约 4 tokens/消息）
    - 格式开销（约 10%）
    """
    total = 0
    
    for msg in messages:
        # 角色开销
        total += 4
        
        # 内容
        content = msg.get("content", "")
        if isinstance(content, str):
            total += estimate_tokens(content)
        elif isinstance(content, list):
            # 多模态消息
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    total += estimate_tokens(item["text"])
        
        # 工具调用
        if "tool_calls" in msg:
            for tool_call in msg["tool_calls"]:
                total += estimate_tokens(str(tool_call))
    
    # 格式开销
    total = int(total * 1.1)
    
    return total


# 模型上下文窗口配置
MODEL_CONTEXT_WINDOWS = {
    # Kimi 模型
    "kimi": 128000,  # 128k
    "K2.6-code-preview": 128000,
    "moonshot-v1-8k": 8000,
    "moonshot-v1-32k": 32000,
    "moonshot-v1-128k": 128000,
    
    # Qianfan 模型
    "qianfan": 8000,
    "qianfan-code-latest": 8000,
    
    # OpenAI 模型
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-4-turbo": 128000,
    "gpt-3.5-turbo": 16000,
    
    # DeepSeek 模型
    "v4-pro": 128000,
    "deepseek-chat": 64000,
    "deepseek-v4-flash": 128000,
    "deepseek-coder": 16000,
    
    # 本地模型（默认）
    "local": 8192,
    
    # 默认值
    "default": 8000,
}


def get_model_context_window(model: str) -> int:
    """
    获取模型的上下文窗口大小
    
    Args:
        model: 模型名称
        
    Returns:
        上下文窗口大小（tokens）
    """
    # 精确匹配
    if model in MODEL_CONTEXT_WINDOWS:
        return MODEL_CONTEXT_WINDOWS[model]
    
    # 模糊匹配
    model_lower = model.lower()
    for key, value in MODEL_CONTEXT_WINDOWS.items():
        if key.lower() in model_lower or model_lower in key.lower():
            return value
    
    # 默认值
    return MODEL_CONTEXT_WINDOWS["default"]


def trim_messages_to_fit(
    messages: List[Dict[str, str]],
    model: str,
    max_output_tokens: int = 4096,
    system_prompt_tokens: int = 2000,
    safety_margin: float = 0.9,
    preserve_recent: int = 5,
) -> Tuple[List[Dict[str, str]], int]:
    """
    裁剪消息历史以适应模型的上下文窗口
    
    Args:
        messages: 消息列表
        model: 模型名称
        max_output_tokens: 预留的输出 token 数量
        system_prompt_tokens: 系统提示词的 token 数量
        safety_margin: 安全边际（0.9 表示使用 90% 的上下文窗口）
        preserve_recent: 保留最近的消息数量（不裁剪）
    
    Returns:
        (裁剪后的消息列表, 总 token 数量)
    """
    # 获取上下文窗口大小
    context_window = get_model_context_window(model)
    
    # 计算可用 token 预算
    available_tokens = int(
        (context_window - max_output_tokens - system_prompt_tokens) * safety_margin
    )
    
    # 估算当前 token 数量
    current_tokens = estimate_messages_tokens(messages)
    
    print(f"[TokenManager] Context window: {context_window}")
    print(f"[TokenManager] Available tokens: {available_tokens}")
    print(f"[TokenManager] Current tokens: {current_tokens}")
    
    if current_tokens <= available_tokens:
        # 不需要裁剪
        return messages, current_tokens
    
    # 需要裁剪
    print(f"[TokenManager] Trimming {len(messages)} messages...")
    
    # 策略：保留系统消息 + 最近的消息 + 压缩中间消息
    
    # 1. 分离系统消息
    system_messages = [m for m in messages if m.get("role") == "system"]
    non_system_messages = [m for m in messages if m.get("role") != "system"]
    
    # 2. 保留最近的消息
    preserved = non_system_messages[-preserve_recent:] if len(non_system_messages) > preserve_recent else non_system_messages
    to_compress = non_system_messages[:-preserve_recent] if len(non_system_messages) > preserve_recent else []
    
    # 3. 压缩中间消息（创建摘要）
    if to_compress:
        # 创建一个摘要消息
        summary = f"[Earlier conversation summary: {len(to_compress)} messages omitted to fit context window]"
        summary_msg = {
            "role": "system",
            "content": summary
        }
        
        # 重新组装
        trimmed = system_messages + [summary_msg] + preserved
        
        # 递归检查是否仍然超限
        new_tokens = estimate_messages_tokens(trimmed)
        if new_tokens > available_tokens:
            # 仍然超限，进一步裁剪
            # 移除更多中间消息
            preserve_recent = max(3, preserve_recent - 2)
            return trim_messages_to_fit(
                messages,
                model,
                max_output_tokens,
                system_prompt_tokens,
                safety_margin,
                preserve_recent
            )
        
        return trimmed, new_tokens
    
    # 没有中间消息需要压缩
    return system_messages + preserved, estimate_messages_tokens(system_messages + preserved)


def smart_compress_history(
    messages: List[Dict[str, str]],
    model: str,
    max_tokens: int = None,
) -> Tuple[List[Dict[str, str]], Dict]:
    """
    智能压缩消息历史
    
    策略：
    1. 保留系统消息
    2. 保留最近的消息
    3. 对中间消息进行摘要压缩
    4. 如果仍然超限，使用滑动窗口
    
    Args:
        messages: 消息列表
        model: 模型名称
        max_tokens: 最大 token 数量（可选，默认自动计算）
    
    Returns:
        (压缩后的消息列表, 统计信息)
    """
    if not max_tokens:
        max_tokens = get_model_context_window(model)
        # 预留输出空间
        max_tokens = int(max_tokens * 0.6)
    
    original_count = len(messages)
    original_tokens = estimate_messages_tokens(messages)
    
    trimmed, final_tokens = trim_messages_to_fit(
        messages,
        model,
        max_output_tokens=int(max_tokens * 0.3),
        system_prompt_tokens=int(max_tokens * 0.1),
    )
    
    stats = {
        "original_count": original_count,
        "final_count": len(trimmed),
        "original_tokens": original_tokens,
        "final_tokens": final_tokens,
        "compression_ratio": len(trimmed) / original_count if original_count > 0 else 1.0,
        "model": model,
        "context_window": get_model_context_window(model),
    }
    
    print(f"[TokenManager] Compression stats: {stats}")
    
    return trimmed, stats


# 便捷函数
def check_context_overflow(
    messages: List[Dict[str, str]],
    model: str = "kimi",
) -> Dict:
    """
    检查上下文是否溢出
    
    Returns:
        {
            "overflow": bool,
            "current_tokens": int,
            "max_tokens": int,
            "utilization": float,
        }
    """
    current = estimate_messages_tokens(messages)
    max_allowed = get_model_context_window(model)
    
    return {
        "overflow": current > max_allowed * 0.7,  # 超过 70% 视为溢出
        "current_tokens": current,
        "max_tokens": max_allowed,
        "utilization": current / max_allowed if max_allowed > 0 else 0,
    }
