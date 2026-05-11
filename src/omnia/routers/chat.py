"""
聊天核心路由
负责：聊天、流式聊天、工具调用、会话管理
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
from src.omnia.services.agent_engine import agent_engine
from src.omnia.services.session_manager import (
    get_session_manager,
    load_recent_conversations,
    merge_histories,
)

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
    使用 Agent 引擎自动处理工具调用
    自动管理会话和记录对话历史
    """
    # 获取消息列表
    messages = req.get_messages()

    if not messages:
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 检测 Provider
    provider = req.provider or settings.current_provider or _detect_provider_from_env()

    # ===== 会话管理 =====
    session_manager = get_session_manager()
    session_id = session_manager.get_or_create_session(provider=provider)

    # NOTE: 已禁用自动合并数据库历史，避免会话污染
    # 前端负责管理历史消息，后端只处理当前请求的消息
    pass

    try:
        # ===== 使用 Agent 引擎处理工具调用（传入 session_id） =====
        result = await agent_engine.process_with_tools(
            llm_client=client,
            messages=messages,
            provider=provider,
            stream=False,
            session_id=session_id,  # 传入 session_id 用于自动记录
        )

        return ChatResponse(
            ok=True,
            content=result.get("content", ""),
            provider=provider,
            usage=result.get("usage"),
            tool_calls=result.get("tool_calls", 0),
            rounds=result.get("rounds", 0),
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
    使用 Agent 引擎自动处理工具调用
    自动管理会话和记录对话历史
    """
    # 获取消息列表
    messages = req.get_messages()

    if not messages:
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 检测 Provider
    provider = req.provider or settings.current_provider or _detect_provider_from_env()

    # ===== 会话管理 =====
    session_manager = get_session_manager()
    session_id = session_manager.get_or_create_session(provider=provider)

    # NOTE: 已禁用自动合并数据库历史，避免会话污染
    # 前端负责管理历史消息，后端只处理当前请求的消息
    pass

    async def generate():
        """生成 SSE 事件流"""
        try:
            # ===== 使用 Agent 引擎的流式处理（传入 session_id） =====
            async for event in agent_engine.process_stream_with_tools(
                llm_client=client,
                messages=messages,
                provider=provider,
                session_id=session_id,
            ):
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
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/chat/gateway")
async def chat_gateway(req: ChatRequest):
    """Gateway 模式聊天"""
    messages = req.get_messages()

    if not messages:
        raise HTTPException(status_code=400, detail="消息不能为空")

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
