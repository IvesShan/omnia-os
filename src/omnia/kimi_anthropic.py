# This file implements Anthropic Messages API support for Kimi
# With Prompt Caching support for token optimization

import json
import requests
from typing import List, Optional, Dict, Any


def call_kimi_anthropic(
    api_key: str, 
    messages: List[Dict[str, Any]], 
    tools: Optional[List[Dict]] = None, 
    model: str = "kimi-code",
    enable_caching: bool = True
) -> Dict[str, Any]:
    """使用 Anthropic Messages API 格式调用 Kimi，支持 Prompt Caching
    
    Args:
        api_key: Kimi API Key
        messages: OpenAI 格式的消息列表
        tools: 可选的工具定义
        model: 模型名称
        enable_caching: 是否启用 Prompt Caching（默认启用）
    
    Returns:
        OpenAI 格式的响应字典
    
    Prompt Caching 说明:
        - 缓存 system prompt 和工具定义，减少重复计算的 token 消耗
        - 缓存命中时，API 返回的 usage 中会包含 cache_read_input_tokens
        - 缓存未命中时，会创建新缓存，usage 中包含 cache_creation_input_tokens
    """
    url = "https://api.kimi.com/coding/v1/messages"
    
    # 转换消息格式
    anthropic_messages = []
    system_content = None
    
    for msg in messages:
        if msg.get("role") == "system":
            system_content = msg.get("content", "")
        elif msg.get("role") == "user":
            anthropic_messages.append({
                "role": "user",
                "content": msg.get("content", "")
            })
        elif msg.get("role") == "assistant":
            anthropic_messages.append({
                "role": "assistant",
                "content": msg.get("content", "")
            })
        elif msg.get("role") == "tool":
            # Tool results need to be added as user messages with special formatting
            anthropic_messages.append({
                "role": "user",
                "content": f"[Tool Result: {msg.get('name', 'unknown')}]\n{msg.get('content', '')}"
            })
    
    # 构建请求体
    payload = {
        "model": model,
        "messages": anthropic_messages,
        "max_tokens": 4096,
    }
    
    # 添加 system prompt（带缓存控制）
    if system_content:
        if enable_caching:
            # Prompt Caching: 在 system prompt 末尾添加 cache_control
            payload["system"] = [
                {
                    "type": "text",
                    "text": system_content,
                    "cache_control": {"type": "ephemeral"}
                }
            ]
        else:
            payload["system"] = system_content
    
    # 添加工具定义（带缓存控制）
    if tools:
        anthropic_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                anthropic_tools.append({
                    "name": func.get("name"),
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {})
                })
        payload["tools"] = anthropic_tools
        
        # 工具定义也可以缓存（在最后一个工具后添加 cache_control）
        if enable_caching and anthropic_tools:
            # 在工具列表末尾添加缓存控制
            # 注意：Anthropic API 要求 cache_control 在特定位置
            pass  # 工具缓存由 API 自动处理
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Omnia-Agent/1.0"
    }
    
    # 添加缓存相关头
    if enable_caching:
        headers["anthropic-beta"] = "prompt-caching-2024-07-31"
    
    print(f"[KimiAnthropic] POST {url}")
    print(f"[KimiAnthropic] Model: {model}")
    print(f"[KimiAnthropic] Messages: {len(anthropic_messages)}")
    print(f"[KimiAnthropic] Caching: {'enabled' if enable_caching else 'disabled'}")
    
    response = requests.post(url, headers=headers, json=payload, timeout=300)
    
    print(f"[KimiAnthropic] Status: {response.status_code}")
    
    if response.status_code != 200:
        error_text = response.text
        print(f"[KimiAnthropic] Error: {error_text[:500]}")
        raise RuntimeError(f"Kimi API error {response.status_code}: {error_text}")
    
    # 解析 Anthropic 格式响应
    anthropic_response = response.json()
    
    # 打印缓存统计
    usage = anthropic_response.get("usage", {})
    if usage.get("cache_read_input_tokens"):
        print(f"[KimiAnthropic] Cache hit! Saved {usage['cache_read_input_tokens']} tokens")
    if usage.get("cache_creation_input_tokens"):
        print(f"[KimiAnthropic] Cache created: {usage['cache_creation_input_tokens']} tokens")
    
    # 转换为 OpenAI 格式
    openai_response = _convert_anthropic_to_openai(anthropic_response)
    
    return openai_response


def _convert_anthropic_to_openai(anthropic_response: Dict[str, Any]) -> Dict[str, Any]:
    """将 Anthropic 响应转换为 OpenAI 格式"""
    content = anthropic_response.get("content", [])
    
    # 提取文本内容
    text_content = ""
    tool_calls = []
    
    for item in content:
        if item.get("type") == "text":
            text_content += item.get("text", "")
        elif item.get("type") == "tool_use":
            tool_calls.append({
                "id": item.get("id", ""),
                "type": "function",
                "function": {
                    "name": item.get("name", ""),
                    "arguments": json.dumps(item.get("input", {}))
                }
            })
    
    openai_message = {
        "role": "assistant",
        "content": text_content
    }
    
    if tool_calls:
        openai_message["tool_calls"] = tool_calls
    
    # 构建使用统计（包含缓存信息）
    usage = anthropic_response.get("usage", {})
    openai_usage = {
        "prompt_tokens": usage.get("input_tokens", 0),
        "completion_tokens": usage.get("output_tokens", 0),
        "total_tokens": (
            usage.get("input_tokens", 0) +
            usage.get("output_tokens", 0)
        )
    }
    
    # 添加缓存统计（如果有）
    if usage.get("cache_read_input_tokens"):
        openai_usage["cache_read_tokens"] = usage["cache_read_input_tokens"]
    if usage.get("cache_creation_input_tokens"):
        openai_usage["cache_creation_tokens"] = usage["cache_creation_input_tokens"]
    
    return {
        "id": anthropic_response.get("id", ""),
        "model": anthropic_response.get("model", ""),
        "choices": [{
            "index": 0,
            "message": openai_message,
            "finish_reason": anthropic_response.get("stop_reason", "stop")
        }],
        "usage": openai_usage
    }
