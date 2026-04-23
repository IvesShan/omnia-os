# This file implements Anthropic Messages API support for Kimi
# Save this as /home/shan//home/shan/omnia-os/omnia-os/src/omnia/kimi_anthropic.py

import json
import requests
from typing import List, Optional, Dict, Any

def call_kimi_anthropic(api_key: str, messages: List[Dict[str, Any]], tools: Optional[List[Dict]] = None, model: str = "kimi-code") -> Dict[str, Any]:
    """使用 Anthropic Messages API 格式调用 Kimi
    
    Args:
        api_key: Kimi API Key
        messages: OpenAI 格式的消息列表
        tools: 可选的工具定义
        model: 模型名称
    
    Returns:
        OpenAI 格式的响应字典
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
    
    if system_content:
        payload["system"] = system_content
    
    if tools:
        # 转换工具格式
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
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Omnia-Agent/1.0"
    }
    
    print(f"[KimiAnthropic] POST {url}")
    print(f"[KimiAnthropic] Model: {model}")
    print(f"[KimiAnthropic] Messages: {len(anthropic_messages)}")
    
    response = requests.post(url, headers=headers, json=payload, timeout=300)
    
    print(f"[KimiAnthropic] Status: {response.status_code}")
    
    if response.status_code != 200:
        error_text = response.text
        print(f"[KimiAnthropic] Error: {error_text[:500]}")
        raise RuntimeError(f"Kimi API error {response.status_code}: {error_text}")
    
    # 解析 Anthropic 格式响应
    anthropic_response = response.json()
    
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
    
    return {
        "id": anthropic_response.get("id", ""),
        "model": anthropic_response.get("model", ""),
        "choices": [{
            "index": 0,
            "message": openai_message,
            "finish_reason": anthropic_response.get("stop_reason", "stop")
        }],
        "usage": {
            "prompt_tokens": anthropic_response.get("usage", {}).get("input_tokens", 0),
            "completion_tokens": anthropic_response.get("usage", {}).get("output_tokens", 0),
            "total_tokens": (
                anthropic_response.get("usage", {}).get("input_tokens", 0) +
                anthropic_response.get("usage", {}).get("output_tokens", 0)
            )
        }
    }
