"""
聊天核心路由
负责：聊天、流式聊天、工具调用
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
import os

from src.omnia.models.chat import ChatRequest, ChatResponse
from src.omnia.services.llm_client import LLMClient
from src.omnia.config import settings
from src.omnia.dependencies import get_llm_client

router = APIRouter()


def _detect_provider_from_env() -> str:
    """从环境变量检测 Provider"""
    model_mode = os.environ.get("OMNIA_MODEL_MODE", "cloud")
    
    if model_mode == "local":
        return "local"
    
    # 检查 .env 文件
    env_file = settings.project_root / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("OMNIA_PROVIDER="):
                return line.split("=", 1)[1].strip()
    
    # 自动检测
    if os.environ.get("DEEPSEEK_API_KEY"):
        return "deepseek"
    elif os.environ.get("MOONSHOT_API_KEY"):
        return "kimi"
    elif os.environ.get("MIMO_API_KEY"):
        return "xiaomi"
    elif os.environ.get("OPENAI_API_KEY"):
        return "openai"
    elif os.environ.get("QIANFAN_API_KEY"):
        return "qianfan"
    
    return "deepseek"  # 默认


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    client: LLMClient = Depends(get_llm_client)
):
    """
    聊天接口 - 非流式
    返回完整的回复内容
    
    支持两种格式：
    1. 简单格式：{"message": "你好"}
    2. 完整格式：{"messages": [{"role": "user", "content": "你好"}]}
    """
    # 获取消息列表
    messages = req.get_messages()
    
    if not messages:
        raise HTTPException(status_code=400, detail="消息不能为空")
    
    # 检测 Provider
    provider = req.provider or settings.current_provider or _detect_provider_from_env()
    
    try:
        # 调用 LLM
        result = await client.chat(
            messages=messages,
            provider=provider,
            tools=req.tools,
            stream=False
        )
        
        return ChatResponse(
            ok=True,
            content=result.get("content", ""),
            provider=provider,
            usage=result.get("usage")
        )
    except Exception as e:
        return ChatResponse(
            ok=False,
            error=str(e)
        )


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    client: LLMClient = Depends(get_llm_client)
):
    """
    流式聊天接口 - SSE
    返回 Server-Sent Events 流
    """
    # 获取消息列表
    messages = req.get_messages()
    
    if not messages:
        raise HTTPException(status_code=400, detail="消息不能为空")
    
    # 检测 Provider
    provider = req.provider or settings.current_provider or _detect_provider_from_env()
    
    async def generate():
        """生成 SSE 事件流"""
        try:
            async for event in client.stream_chat(
                messages=messages,
                provider=provider,
                tools=req.tools
            ):
                # 格式化为 SSE
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            error_event = {
                "type": "error",
                "message": f"Stream error: {str(e)}"
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
            
            done_event = {"type": "done", "full_content": ""}
            yield f"data: {json.dumps(done_event, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        }
    )


@router.post("/chat/gateway")
async def chat_gateway(req: ChatRequest):
    """
    Gateway 模式聊天
    通过 OpenClaw Gateway 处理
    """
    messages = req.get_messages()
    
    if not messages:
        raise HTTPException(status_code=400, detail="消息不能为空")
    
    # 检查是否启用 Gateway 模式
    use_gateway = os.environ.get("OMNIA_USE_GATEWAY", "false").lower() == "true"
    
    if not use_gateway:
        raise HTTPException(status_code=400, detail="Gateway mode is not enabled")
    
    try:
        from gateway.integration import handle_chat_unified
        
        async def generate():
            for event in handle_chat_unified(
                req.message,
                req.history or [],
                req.provider
            ):
                yield event
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="Gateway module not found")
