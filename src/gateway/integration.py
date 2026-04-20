"""Gateway Integration - OpenClaw Gateway 适配层

连接 Omnia 到 OpenClaw Gateway，实现：
- 统一聊天接口
- 跨平台消息同步
- 集成 OpenClaw 生态
"""

from __future__ import annotations

import json
import requests
from typing import Dict, Generator, Any

# Gateway 配置
GATEWAY_URL = "http://127.0.0.1:8080"


def handle_chat_unified(
    message: str,
    history: list = None,
    provider: str = None,
    **kwargs
) -> Generator[str, None, None]:
    """通过 Gateway 处理聊天请求
    
    Args:
        message: 用户消息
        history: 对话历史
        provider: AI 提供商
        
    Yields:
        SSE 事件流
    """
    # 构造请求
    payload = {
        "message": message,
        "history": history or [],
        "provider": provider,
        **kwargs
    }
    
    try:
        # 调用 Gateway API
        response = requests.post(
            f"{GATEWAY_URL}/api/chat/stream",
            json=payload,
            stream=True,
            timeout=300
        )
        
        # 流式返回
        for line in response.iter_lines():
            if line:
                yield f"{line.decode('utf-8')}\n\n"
                
    except requests.exceptions.RequestException as e:
        yield f"data: {json.dumps({'type': 'error', 'message': f'Gateway 连接失败: {str(e)}'})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'full_content': f'错误: {str(e)}'})}\n\n"


def check_gateway_health() -> Dict[str, Any]:
    """检查 Gateway 健康状态"""
    try:
        response = requests.get(f"{GATEWAY_URL}/health", timeout=5)
        return {
            "status": "online" if response.status_code == 200 else "error",
            "url": GATEWAY_URL,
            "code": response.status_code
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "offline",
            "url": GATEWAY_URL,
            "error": str(e)
        }


def send_to_gateway(
    endpoint: str,
    data: dict,
    method: str = "POST"
) -> Dict[str, Any]:
    """通用 Gateway API 调用
    
    Args:
        endpoint: API 端点（如 "/api/chat"）
        data: 请求数据
        method: HTTP 方法
        
    Returns:
        响应数据
    """
    url = f"{GATEWAY_URL}{endpoint}"
    
    try:
        if method == "POST":
            response = requests.post(url, json=data, timeout=60)
        elif method == "GET":
            response = requests.get(url, params=data, timeout=60)
        else:
            raise ValueError(f"Unsupported method: {method}")
            
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


# 便捷函数
def is_gateway_available() -> bool:
    """检查 Gateway 是否可用"""
    return check_gateway_health().get("status") == "online"
