"""Gateway API Routes.

Manages channel adapters and message routing.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

router = APIRouter(prefix="/api/gateway", tags=["Gateway"])

# Lazy imports
_gateway_runner = None


def _get_gateway_runner():
    """Get or create GatewayRunner instance."""
    global _gateway_runner
    if _gateway_runner is None:
        from core.gateway.runner import GatewayRunner
        _gateway_runner = GatewayRunner()
    return _gateway_runner


# Request/Response Models
class AdapterInfo(BaseModel):
    """Adapter information."""
    channel_type: str
    status: str
    config: Dict[str, Any] = Field(default_factory=dict)


class SendMessageRequest(BaseModel):
    """Request to send a message."""
    channel: str = Field(..., description="Channel type (webchat, webhook, email, websocket)")
    target: str = Field(..., description="Target identifier (user_id, email, connection_id)")
    content: str = Field(..., description="Message content")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class WebhookReceiveRequest(BaseModel):
    """Request to receive webhook."""
    webhook_id: str = Field(..., description="Webhook identifier")
    payload: Dict[str, Any] = Field(..., description="Webhook payload")
    headers: Optional[Dict[str, str]] = Field(default=None, description="HTTP headers")


class WebSocketRegisterRequest(BaseModel):
    """Request to register WebSocket connection."""
    connection_id: str = Field(..., description="Connection ID")
    user_id: Optional[str] = Field(default=None, description="User ID")


# API Endpoints
@router.get("/status")
async def get_status():
    """Get gateway status."""
    try:
        runner = _get_gateway_runner()
        adapters = runner.list_adapters()
        
        return {
            "status": "running",
            "adapters": adapters,
            "total_adapters": len(adapters),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@router.get("/adapters")
async def list_adapters():
    """List all registered adapters."""
    try:
        runner = _get_gateway_runner()
        adapters = runner.list_adapters()
        
        return {
            "adapters": adapters,
            "total": len(adapters),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send")
async def send_message(request: SendMessageRequest):
    """Send a message through a specific channel."""
    try:
        from core.gateway.runner import ChannelType
        
        # 获取适配器
        runner = _get_gateway_runner()
        channel = ChannelType(request.channel)
        adapter = runner.get_adapter(channel)
        
        if not adapter:
            raise HTTPException(status_code=404, detail=f"Adapter not found: {request.channel}")
        
        # 发送消息
        success = await adapter.send(
            target=request.target,
            content=request.content,
            **(request.metadata or {})
        )
        
        return {
            "success": success,
            "channel": request.channel,
            "target": request.target,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/receive")
async def receive_webhook(request: WebhookReceiveRequest):
    """Receive a webhook message."""
    try:
        from gateway.webhook_adapter import WebhookAdapter
        
        runner = _get_gateway_runner()
        adapter = runner.get_adapter("webhook")
        
        if not adapter or not isinstance(adapter, WebhookAdapter):
            # 如果没有注册，创建临时实例
            adapter = WebhookAdapter()
            await adapter.start()
        
        result = await adapter.receive_webhook(
            webhook_id=request.webhook_id,
            payload=request.payload,
            headers=request.headers,
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/websocket/connections")
async def list_websocket_connections():
    """List active WebSocket connections."""
    try:
        from gateway.websocket_adapter import WebSocketAdapter
        
        runner = _get_gateway_runner()
        adapter = runner.get_adapter("websocket")
        
        if not adapter or not isinstance(adapter, WebSocketAdapter):
            return {
                "total_connections": 0,
                "connections": [],
            }
        
        return adapter.get_connections()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/websocket/register")
async def register_websocket(request: WebSocketRegisterRequest):
    """Register a WebSocket connection (for testing)."""
    try:
        from gateway.websocket_adapter import WebSocketAdapter
        
        runner = _get_gateway_runner()
        adapter = runner.get_adapter("websocket")
        
        if not adapter or not isinstance(adapter, WebSocketAdapter):
            raise HTTPException(status_code=404, detail="WebSocket adapter not found")
        
        # 注意：实际使用时，websocket 对象应该由 FastAPI 的 WebSocket 路由传入
        # 这里只是示例
        return {
            "success": True,
            "connection_id": request.connection_id,
            "user_id": request.user_id,
            "message": "Use FastAPI WebSocket route for actual connections"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/websocket/broadcast")
async def broadcast_message(content: str, message_type: str = "broadcast"):
    """Broadcast a message to all WebSocket connections."""
    try:
        from gateway.websocket_adapter import WebSocketAdapter
        
        runner = _get_gateway_runner()
        adapter = runner.get_adapter("websocket")
        
        if not adapter or not isinstance(adapter, WebSocketAdapter):
            raise HTTPException(status_code=404, detail="WebSocket adapter not found")
        
        count = await adapter.broadcast(content, message_type=message_type)
        
        return {
            "success": True,
            "sent_count": count,
            "message": f"Broadcast to {count} connections"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/channels")
async def list_channel_types():
    """List supported channel types."""
    from core.gateway.runner import ChannelType
    
    return {
        "channels": [
            {"type": "webchat", "name": "Web Chat", "description": "Omnia web interface"},
            {"type": "webhook", "name": "Webhook", "description": "HTTP webhook integration"},
            {"type": "email", "name": "Email", "description": "Email via SMTP/IMAP"},
            {"type": "websocket", "name": "WebSocket", "description": "Real-time bidirectional"},
            {"type": "feishu", "name": "Feishu", "description": "Feishu/Lark bot"},
        ]
    }


@router.post("/email/send")
async def send_email(
    to: str,
    subject: str,
    body: str,
    html: Optional[str] = None,
):
    """Send an email (requires SMTP configuration)."""
    try:
        from gateway.email_adapter import EmailAdapter
        import os
        
        runner = _get_gateway_runner()
        adapter = runner.get_adapter("email")
        
        if not adapter or not isinstance(adapter, EmailAdapter):
            # 从环境变量创建
            adapter = EmailAdapter(
                smtp_host=os.getenv("SMTP_HOST", "localhost"),
                smtp_port=int(os.getenv("SMTP_PORT", "25")),
                smtp_user=os.getenv("SMTP_USER"),
                smtp_password=os.getenv("SMTP_PASSWORD"),
                use_tls=os.getenv("SMTP_TLS", "true").lower() == "true",
            )
            await adapter.start()
        
        success = await adapter.send(
            target=to,
            content=body,
            subject=subject,
            html=html,
        )
        
        return {
            "success": success,
            "to": to,
            "subject": subject,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
