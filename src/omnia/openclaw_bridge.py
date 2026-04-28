# Omnia OpenClaw Bridge
# 使用 OpenClaw 的 Gateway 调用 Kimi API

import requests
from typing import List, Dict, Any, Optional

def call_via_openclaw(message: str, history: List[Dict] = None, tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """通过 OpenClaw Gateway 调用 Kimi API
    
    使用 OpenClaw 内部已经配置好的 Kimi 连接
    """
    # OpenClaw Gateway 地址
    gateway_url = "http://127.0.0.1:18789/v1/chat/completions"
    
    # 构建消息
    messages = history or []
    messages.append({"role": "user", "content": message})
    
    payload = {
        "model": "kimi/kimi-code",
        "messages": messages,
        "max_tokens": 4096,
        "temperature": 0.7,
    }
    
    if tools:
        payload["tools"] = tools
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer openclaw-local",  # OpenClaw 本地模式不需要真实 token
    }
    
    print(f"[OpenClawBridge] Calling {gateway_url}")
    response = requests.post(gateway_url, headers=headers, json=payload, timeout=300)
    
    if response.status_code != 200:
        error = response.text
        print(f"[OpenClawBridge] Error: {error[:500]}")
        raise RuntimeError(f"OpenClaw error {response.status_code}: {error}")
    
    return response.json()
