"""Omnia Gateway - 统一消息入口。

Omnia 的独立网关，支持多种消息通道：
- WebChat
- Feishu
- CLI
- API
- 更多...

使用方法：
    from gateway import GatewayRunner, WebChatAdapter
    
    runner = GatewayRunner()
    adapter = WebChatAdapter()
    await runner.register_adapter(adapter)
    await runner.start()
"""

from __future__ import annotations

# Core Gateway
from src.core.gateway.runner import GatewayRunner, MessageEvent, ChannelType

# Adapters
from gateway.webchat_adapter import WebChatAdapter
from gateway.integration import (
    handle_chat_unified,
    check_gateway_health,
    send_to_gateway,
    is_gateway_available,
)
from gateway.chat_handler_wrapper import ChatHandlerWrapper

__all__ = [
    # Core
    "GatewayRunner",
    "MessageEvent",
    "ChannelType",
    # Adapters
    "WebChatAdapter",
    # Integration
    "handle_chat_unified",
    "check_gateway_health",
    "send_to_gateway",
    "is_gateway_available",
    # Handler
    "ChatHandlerWrapper",
]
