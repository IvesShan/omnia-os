"""feishu.py — 飞书集成路由

提供：飞书机器人 Webhook 接收、消息处理、事件订阅
集成 AgentEngine 实现智能回复
"""

import json
import hashlib
import time
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from src.omnia.config import settings

router = APIRouter()


class FeishuWebhookRequest(BaseModel):
    """飞书 Webhook 请求体"""
    challenge: Optional[str] = None
    token: Optional[str] = None
    type: Optional[str] = None
    event: Optional[Dict[str, Any]] = None
    header: Optional[Dict[str, Any]] = None
    encrypt: Optional[str] = None


def _verify_token(token: str) -> bool:
    """验证飞书 token"""
    if not settings.feishu_verify_token:
        return True  # 未配置时不验证
    return token == settings.feishu_verify_token


def _decrypt_payload(encrypt: str) -> Dict:
    """解密飞书加密消息"""
    try:
        import base64
        from cryptography.fernet import Fernet

        # 使用 app_secret 的前32位作为 key
        key = base64.urlsafe_b64encode(
            settings.feishu_app_secret[:32].encode().ljust(32, b"\0")[:32]
        )
        f = Fernet(key)
        decrypted = f.decrypt(encrypt.encode())
        return json.loads(decrypted)
    except Exception as e:
        print(f"[Feishu] Decrypt error: {e}")
        return {}


async def _get_agent_engine():
    """获取 AgentEngine 实例"""
    from src.omnia.services.agent_engine import AgentEngine
    from src.omnia.services.tool_registry import ToolRegistry
    from src.omnia.services.session_manager import SessionManager
    from src.omnia.services.llm_client import LLMClient
    
    # 创建必要的组件
    tool_registry = ToolRegistry()
    session_manager = SessionManager()
    llm_client = LLMClient()
    
    return AgentEngine(
        llm_client=llm_client,
        tool_registry=tool_registry,
        session_manager=session_manager,
    )


async def _handle_message(event: Dict) -> str:
    """处理飞书消息事件 - 接入 AgentEngine"""
    message = event.get("message", {})
    content_str = message.get("content", "{}")
    sender = event.get("sender", {})
    sender_id = sender.get("sender_id", {})
    open_id = sender_id.get("open_id", "unknown")
    message_id = message.get("message_id", "")
    
    # 解析消息内容
    try:
        content = json.loads(content_str) if isinstance(content_str, str) else content_str
        text = content.get("text", "") if isinstance(content, dict) else str(content)
    except (json.JSONDecodeError, AttributeError):
        text = str(content_str)
    
    print(f"[Feishu] Received message from {open_id}: {text[:100]}")
    
    # 如果消息为空，返回提示
    if not text.strip():
        return "请输入您的问题，我会尽力帮助您。"
    
    try:
        # 获取 AgentEngine
        engine = await _get_agent_engine()
        
        # 构建会话 ID（使用 open_id 作为会话标识）
        session_id = f"feishu_{open_id}"
        
        # 处理消息
        response_text = ""
        async for chunk in engine.process_stream_with_tools(
            message=text,
            session_id=session_id,
        ):
            if isinstance(chunk, dict):
                # 处理字典类型的 chunk
                if chunk.get("type") == "text":
                    response_text += chunk.get("content", "")
                elif chunk.get("type") == "tool_use":
                    # 工具调用信息，可以选择性显示
                    tool_name = chunk.get("name", "unknown")
                    print(f"[Feishu] Tool called: {tool_name}")
            elif isinstance(chunk, str):
                response_text += chunk
        
        # 如果没有响应，使用默认回复
        if not response_text.strip():
            response_text = "我收到了您的消息，但暂时无法生成回复。请稍后再试。"
        
        # 飞书消息长度限制
        if len(response_text) > 2000:
            response_text = response_text[:1997] + "..."
        
        return response_text
        
    except Exception as e:
        print(f"[Feishu] AgentEngine error: {e}")
        import traceback
        traceback.print_exc()
        
        # 降级处理：返回简单回复
        return f"抱歉，处理您的消息时遇到问题。错误: {str(e)[:100]}"


def _handle_event_callback(event: Dict) -> str:
    """处理飞书事件回调"""
    event_type = event.get("type", "unknown")
    print(f"[Feishu] Event callback: {event_type}")

    if event_type == "message":
        # 使用 asyncio 运行异步函数
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            # 如果在异步上下文中，创建任务
            return asyncio.create_task(_handle_message(event))
        else:
            # 同步上下文，直接运行
            return loop.run_until_complete(_handle_message(event))

    return f"事件已接收: {event_type}"


# ========== 飞书事件回调路由 ==========

@router.post("/feishu/webhook")
async def feishu_webhook(request: Request):
    """
    飞书 Webhook 回调入口
    
    支持：
    - URL Challenge 验证
    - 事件回调
    - 加密消息
    """
    try:
        body = await request.json()
    except Exception:
        return PlainTextResponse("Invalid JSON", status_code=400)

    # URL Challenge 验证
    challenge = body.get("challenge")
    if challenge:
        token = body.get("token", "")
        if settings.feishu_verify_token and not _verify_token(token):
            raise HTTPException(status_code=403, detail="Token verification failed")
        return {"challenge": challenge}

    # 处理加密消息
    encrypt = body.get("encrypt")
    if encrypt:
        decrypted = _decrypt_payload(encrypt)
        body = decrypted

    event = body.get("event", {})
    if event:
        # 异步处理消息
        reply = await _handle_message(event)
        return {"msg": "ok", "reply": reply}

    return {"msg": "ok"}


@router.post("/feishu/card")
async def feishu_card_action(request: Request):
    """
    飞书卡片交互回调
    """
    try:
        body = await request.json()
    except Exception:
        return PlainTextResponse("Invalid JSON", status_code=400)

    action = body.get("action", {})
    tag = action.get("tag", "")
    value = action.get("value", {})
    open_id = body.get("open_id", "")

    print(f"[Feishu] Card action: tag={tag}, value={value}, user={open_id}")

    return {"msg": "ok", "action": tag}


@router.get("/feishu/status")
async def feishu_status():
    """飞书集成配置状态"""
    return {
        "configured": bool(settings.feishu_app_id and settings.feishu_app_secret),
        "app_id": settings.feishu_app_id[:8] + "..." if settings.feishu_app_id else None,
        "has_verify_token": bool(settings.feishu_verify_token),
    }


@router.post("/feishu/send")
async def send_feishu_message(request: Request):
    """
    主动发送飞书消息（需要配置 app_id 和 app_secret）
    
    请求体:
    {
        "open_id": "用户的 open_id",
        "message": "要发送的消息"
    }
    """
    try:
        body = await request.json()
        open_id = body.get("open_id")
        message = body.get("message")
        
        if not open_id or not message:
            raise HTTPException(status_code=400, detail="缺少 open_id 或 message")
        
        # 获取 tenant_access_token
        import httpx
        
        if not settings.feishu_app_id or not settings.feishu_app_secret:
            return {"ok": False, "message": "飞书 app_id 或 app_secret 未配置"}
        
        # 获取 tenant_access_token
        token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(token_url, json={
                "app_id": settings.feishu_app_id,
                "app_secret": settings.feishu_app_secret,
            })
            token_data = token_resp.json()
            tenant_token = token_data.get("tenant_access_token")
            
            if not tenant_token:
                return {"ok": False, "message": f"获取 tenant_access_token 失败: {token_data}"}
            
            # 发送消息
            send_url = "https://open.feishu.cn/open-apis/im/v1/messages"
            headers = {
                "Authorization": f"Bearer {tenant_token}",
                "Content-Type": "application/json; charset=utf-8",
            }
            import json as _json
            payload = {
                "receive_id": open_id,
                "msg_type": "text",
                "content": _json.dumps({"text": message}),
            }
            send_resp = await client.post(
                send_url,
                headers=headers,
                params={"receive_id_type": "open_id"},
                json=payload,
            )
            send_data = send_resp.json()
            
            if send_data.get("code") == 0:
                return {"ok": True, "message": "消息发送成功", "message_id": send_data.get("data", {}).get("message_id")}
            else:
                return {"ok": False, "message": f"发送失败: {send_data.get('msg', '未知错误')}", "detail": send_data}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
