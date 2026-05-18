"""
模型状态路由
负责：模型在线状态、Token 使用量、MCP 状态、OpenAI 兼容接口

从 Flask 版 web_server.py 完整移植，保持功能一致性。
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.omnia.config import settings

router = APIRouter()

# ========== Provider 配置 ==========

PROVIDER_MODELS = {
    "deepseek": ("DEEPSEEK_MODEL", "deepseek-v4-flash"),
    "qianfan": ("QIANFAN_MODEL", "qianfan-code-latest"),
    "kimi": ("MOONSHOT_MODEL", "K2.6-code-preview"),
    "openai": ("OPENAI_MODEL", "gpt-4o"),
    "xiaomi": ("MIMO_MODEL", "mimo-v2.5-pro"),
    "anthropic": ("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
}

API_KEY_ENV_MAP = {
    "deepseek": ("DEEPSEEK_API_KEY", "DEEPSEEK_ACCESS_KEY"),
    "qianfan": ("QIANFAN_API_KEY", "QIANFAN_ACCESS_KEY"),
    "kimi": ("MOONSHOT_API_KEY", "MOONSHOT_API_KEY"),
    "openai": ("OPENAI_API_KEY", "OPENAI_API_KEY"),
    "xiaomi": ("MIMO_API_KEY", "MIMO_API_KEY"),
    "anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"),
}

MODEL_CONTEXT_LIMITS = {
    "kimi": 128000,
    "openai": 128000,
    "anthropic": 200000,
    "qianfan": 128000,
    "deepseek": 64000,
    "xiaomi": 128000,
    "local": 32000,
}


# ========== 请求/响应模型 ==========

class ModelStatusResponse(BaseModel):
    """模型状态响应"""
    local_online: bool
    cloud_online: bool
    current_mode: str
    current_model: Optional[str] = None
    provider: Optional[str] = None


class TokenStatusRequest(BaseModel):
    """Token 状态请求"""
    messages: List[Dict[str, Any]] = []
    model: str = "kimi"


class TokenStatusResponse(BaseModel):
    """Token 状态响应"""
    total_tokens: int
    limit: int
    utilization: float
    status: str
    model: str


class MCPStatusResponse(BaseModel):
    """MCP 状态响应"""
    available: bool
    initialized: bool
    native_tools: int
    mcp_tools: int
    total_tools: int
    tools: List[Dict[str, Any]]
    config_path: Optional[str] = None
    error: Optional[str] = None


class OpenAICompatRequest(BaseModel):
    """OpenAI 兼容请求"""
    model: str = "gpt-4"
    messages: List[Dict[str, Any]]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str] = None


# ========== 辅助函数 ==========

def _daemon_status() -> bool:
    """检查守护进程状态"""
    pid_file = settings.omnia_home / "daemon.pid"
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False


def _check_provider_configured(env_key: str) -> bool:
    """检查 Provider 是否已配置"""
    if os.environ.get(env_key):
        return True
    env_file = settings.project_root / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(f"{env_key}="):
                return True
    return False


def _load_local_models() -> List[Dict[str, Any]]:
    """加载本地模型配置"""
    local_models = []
    local_llm_config = settings.local_llm_config

    if not local_llm_config.exists():
        return local_models

    try:
        import yaml
        with open(local_llm_config, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        for model_id, model_info in config.get('models', {}).items():
            local_models.append({
                "id": f"local-{model_id}",
                "name": model_info.get('display_name', model_id),
                "configured": True,
                "model": model_id,
                "type": "local",
                "supports_tools": model_info.get('supports_tools', False),
                "supports_thinking": model_info.get('supports_thinking', False),
            })
    except Exception as e:
        print(f"[model_status] Failed to load local_llm.yaml: {e}")

    return local_models


def _get_current_model_info() -> Dict[str, str]:
    """获取当前使用的模型信息"""
    provider = settings.current_provider

    # 如果用户手动选择了 provider
    if provider:
        env_key, default = PROVIDER_MODELS.get(provider, ("DEFAULT_MODEL", "unknown"))
        model = os.environ.get(env_key, default)
        return {"provider": provider, "model": model}

    # 自动检测：检查 .env 文件
    env_file = settings.project_root / ".env"
    env_content = ""
    if env_file.exists():
        env_content = env_file.read_text(encoding="utf-8")

    # 按优先级检测
    for pid, (env_key, default) in PROVIDER_MODELS.items():
        key1, key2 = API_KEY_ENV_MAP[pid]
        # 检查环境变量
        if os.environ.get(key1) or os.environ.get(key2):
            model = os.environ.get(env_key, default)
            return {"provider": pid, "model": model}
        # 检查 .env 文件
        if f"{key1}=" in env_content or f"{key2}=" in env_content:
            model = default
            for line in env_content.splitlines():
                if line.startswith(f"{env_key}="):
                    model = line.split("=", 1)[1].strip()
                    break
            return {"provider": pid, "model": model}

    return {"provider": "unknown", "model": "unknown"}


# ========== 路由 ==========

@router.get("/model/status", response_model=ModelStatusResponse)
async def model_status():
    """
    模型服务状态

    返回：
    - local_online: 本地模型是否在线
    - cloud_online: 云端模型是否在线
    - current_mode: 当前使用的模式
    - current_model: 当前使用的模型名称
    - provider: 当前 Provider
    """
    # 检查守护进程状态
    daemon_running = _daemon_status()

    # 检查云端 Provider 是否配置
    cloud_online = False
    for pid, (env_key, _) in API_KEY_ENV_MAP.items():
        if _check_provider_configured(env_key):
            cloud_online = True
            break

    # 获取当前模型信息
    model_info = _get_current_model_info()

    return ModelStatusResponse(
        local_online=daemon_running,
        cloud_online=cloud_online,
        current_mode=model_info["provider"] or "auto",
        current_model=model_info["model"],
        provider=model_info["provider"],
    )


@router.post("/token/status", response_model=TokenStatusResponse)
async def token_status(req: TokenStatusRequest):
    """
    Token 使用量估算

    前端调用此接口显示 Token 利用率。
    基于消息内容长度进行估算。
    """
    # 估算 Token 数量
    total_chars = 0
    for msg in req.messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)

    # 粗略估算：1 token ≈ 4 字符（中英混合平均）
    estimated_tokens = total_chars // 4

    # 获取模型上下文限制
    limit = MODEL_CONTEXT_LIMITS.get(req.model, 128000)
    utilization = min(estimated_tokens / limit * 100, 100) if limit > 0 else 0

    # 确定状态
    if utilization < 80:
        status = "ok"
    elif utilization < 95:
        status = "warning"
    else:
        status = "critical"

    return TokenStatusResponse(
        total_tokens=estimated_tokens,
        limit=limit,
        utilization=round(utilization, 1),
        status=status,
        model=req.model,
    )


@router.get("/mcp/status", response_model=MCPStatusResponse)
async def mcp_status(request: Request):
    """
    MCP 连接状态和可用工具

    返回：
    - available: MCP SDK 是否安装
    - initialized: MCP 是否已初始化
    - native_tools: 原生工具数量
    - mcp_tools: MCP 工具数量
    - tools: MCP 工具列表
    """
    try:
        from src.core.actuator.mcp_client import MCP_AVAILABLE
    except ImportError:
        MCP_AVAILABLE = False

    if not MCP_AVAILABLE:
        return MCPStatusResponse(
            available=False,
            initialized=False,
            native_tools=0,
            mcp_tools=0,
            total_tools=0,
            tools=[],
            message="MCP SDK not installed. Run: pip install mcp"
        )

    # 获取 MCP 管理器
    mcp_manager = getattr(request.app.state, "mcp_manager", None)
    initialized = mcp_manager is not None

    try:
        from src.omnia.services.tool_registry import tool_registry
        native_count = len(tool_registry._tools)

        if initialized and hasattr(mcp_manager, "get_all_tools_schema"):
            all_mcp_tools = mcp_manager.get_all_tools_schema()
            mcp_count = len(all_mcp_tools)

            # 提取工具信息
            tool_names = []
            for tool in all_mcp_tools[:20]:  # 限制前 20 个
                func = tool.get("function", {})
                tool_names.append({
                    "name": func.get("name", "unknown"),
                    "description": func.get("description", "")[:50],
                })
        else:
            mcp_count = 0
            tool_names = []

        return MCPStatusResponse(
            available=True,
            initialized=initialized,
            native_tools=native_count,
            mcp_tools=mcp_count,
            total_tools=native_count + mcp_count,
            tools=tool_names,
            config_path=str(settings.project_root / "config" / "mcp_servers.json"),
        )
    except Exception as e:
        return MCPStatusResponse(
            available=True,
            initialized=initialized,
            native_tools=0,
            mcp_tools=0,
            total_tools=0,
            tools=[],
            error=str(e),
        )


@router.post("/chat/completions")
async def openai_chat_completions(req: OpenAICompatRequest):
    """
    OpenAI 兼容的聊天接口

    兼容 OpenAI API 格式，支持：
    - 非流式响应
    - 流式响应（SSE）
    - 工具调用

    用途：第三方集成、自定义前端
    """
    from src.omnia.services.llm_client import LLMClient
    from src.omnia.services.agent_engine import agent_engine

    client = LLMClient()
    provider = settings.current_provider or "deepseek"

    messages = req.messages

    if req.stream:
        # 流式响应
        async def generate():
            try:
                async for event in agent_engine.process_stream_with_tools(
                    llm_client=client,
                    messages=messages,
                    provider=provider,
                ):
                    if event.get("type") == "token":
                        chunk = {
                            "id": "chatcmpl-omnia",
                            "object": "chat.completion.chunk",
                            "choices": [{
                                "index": 0,
                                "delta": {"content": event.get("content", "")},
                                "finish_reason": None,
                            }]
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
                    elif event.get("type") == "done":
                        chunk = {
                            "id": "chatcmpl-omnia",
                            "object": "chat.completion.chunk",
                            "choices": [{
                                "index": 0,
                                "delta": {},
                                "finish_reason": "stop",
                            }]
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
                        yield "data: [DONE]\n\n"
            except Exception as e:
                error_chunk = {
                    "error": {"message": str(e), "type": "server_error"}
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"}
        )
    else:
        # 非流式响应
        try:
            result = await agent_engine.process_with_tools(
                llm_client=client,
                messages=messages,
                provider=provider,
                stream=False,
            )

            return {
                "id": "chatcmpl-omnia",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": req.model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result.get("content", ""),
                    },
                    "finish_reason": "stop",
                }],
                "usage": result.get("usage", {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                }),
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
