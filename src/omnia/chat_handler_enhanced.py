# Omnia Chat Handler - 增强版
# 支持 URL 自动检测和任务中断

import json
import uuid
from typing import Any, Optional
import re
from .url_detector import extract_urls, is_url_message, get_primary_url, get_url_type
from .interrupt_manager import check_interrupt, clear_interrupt, InterruptibleTask

# 导入原有的处理函数
from .chat_handler import handle_chat as original_handle_chat


def handle_chat_with_url(
    message: str,
    messages: list,
    model: str = "claude-3-5-sonnet-20241022",
    max_tokens: int = 4096,
    temperature: float = 0.7,
    system_prompt: Optional[str] = None,
    api_base: str = "http://localhost:5001",
    **kwargs
) -> dict:
    """
    增强版聊天处理，支持 URL 自动检测
    
    如果检测到用户发送的是 URL，会自动调用 web_search 工具查看网页内容
    """
    
    # 检查是否是中断指令
    if message.strip() == "/" or message.strip().startswith("/stop"):
        from .interrupt_manager import set_interrupt
        set_interrupt(reason="user_slash_command")
        return {
            "reply": "⏹️ 已收到中断信号，正在停止当前任务...",
            "steps": [{"action": "interrupt", "status": "success"}]
        }
    
    # 检查是否是 URL 消息
    if is_url_message(message):
        url = get_primary_url(message)
        url_type = get_url_type(url)
        
        # 构建提示，让 AI 知道用户想查看网页
        enhanced_message = f"""用户发送了一个 URL，请使用 web_search 工具查看这个网页的内容，然后总结给用户。

URL: {url}
类型: {url_type}

请：
1. 使用 web_search 工具查看网页内容
2. 总结网页的主要内容
3. 提取关键信息
"""
        
        # 调用原始处理函数
        return original_handle_chat(
            enhanced_message,
            messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt,
            api_base=api_base,
            **kwargs
        )
    
    # 普通消息，使用原始处理
    return original_handle_chat(
        message,
        messages,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system_prompt=system_prompt,
        api_base=api_base,
        **kwargs
    )


def handle_chat_interruptible(
    message: str,
    messages: list,
    task_name: str = "chat",
    **kwargs
) -> dict:
    """
    可中断的聊天处理
    
    在处理过程中会定期检查中断信号
    """
    with InterruptibleTask(task_name) as task:
        result = handle_chat_with_url(message, messages, **kwargs)
        
        if task.check():
            return {
                "reply": "⏹️ 任务已被用户中断",
                "steps": result.get("steps", []) + [{"action": "interrupted", "status": "success"}]
            }
        
        return result


# 为了向后兼容，提供默认的 handle_chat
def handle_chat(message: str, messages: list, **kwargs) -> dict:
    """
    默认聊天处理入口
    """
    return handle_chat_with_url(message, messages, **kwargs)
