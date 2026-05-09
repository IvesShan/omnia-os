"""
Omnia FastAPI 主入口
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.omnia.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print(f"[Omnia] Starting FastAPI server on {settings.host}:{settings.port}")
    print(f"[Omnia] Debug mode: {settings.debug}")
    print(f"[Omnia] Current provider: {settings.current_provider or 'None'}")
    
    yield
    
    # 关闭时
    print("[Omnia] Shutting down...")


# 创建 FastAPI 应用
app = FastAPI(
    title="Omnia",
    description="AI Operating System - FastAPI Version",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 异常处理
class OmniaError(Exception):
    """Omnia 统一异常"""
    def __init__(self, code: str, message: str, status_code: int = 500):
        self.code = code
        self.message = message
        self.status_code = status_code


@app.exception_handler(OmniaError)
async def omnia_error_handler(request: Request, exc: OmniaError):
    """Omnia 异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "error": exc.message
        }
    )


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    import traceback
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_ERROR",
            "error": str(exc),
            "traceback": traceback.format_exc() if settings.debug else None
        }
    )


# 静态文件
static_dir = settings.project_root / "src" / "omnia" / "web" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# 健康检查
@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "version": "2.0.0"}


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "Omnia",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }


# API 状态
@app.get("/api/status")
async def api_status():
    """API 状态"""
    return {
        "status": "ok",
        "provider": settings.current_provider,
        "version": "2.0.0"
    }


# Provider 管理
@app.get("/api/providers")
async def list_providers():
    """列出可用的 Provider"""
    from src.omnia.dependencies import get_llm_client
    
    client = get_llm_client()
    providers = client.get_available_providers()
    
    return {
        "providers": providers,
        "current": settings.current_provider
    }


@app.post("/api/providers/switch")
async def switch_provider(provider: str):
    """切换 Provider"""
    from src.omnia.dependencies import get_llm_client
    
    client = get_llm_client()
    available = client.get_available_providers()
    
    if provider not in available:
        raise OmniaError(
            code="PROVIDER_NOT_AVAILABLE",
            message=f"Provider {provider} is not available. Available: {available}",
            status_code=400
        )
    
    settings.current_provider = provider
    return {"status": "ok", "provider": provider}


# 聊天接口（基础版本，后续由 Agent 1 完善）
@app.post("/api/chat")
async def chat(request: dict):
    """聊天接口"""
    from src.omnia.dependencies import get_llm_client, get_current_provider
    
    client = get_llm_client()
    provider = request.get("provider") or get_current_provider() or "local"
    
    messages = request.get("messages", [])
    tools = request.get("tools")
    
    try:
        result = await client.call(
            provider=provider,
            messages=messages,
            tools=tools,
            stream=False
        )
        return result
    except Exception as e:
        raise OmniaError(
            code="LLM_CALL_FAILED",
            message=str(e),
            status_code=500
        )


# 流式聊天（基础版本，后续由 Agent 1 完善）
@app.post("/api/chat/stream")
async def chat_stream(request: dict):
    """流式聊天接口"""
    from fastapi.responses import StreamingResponse
    from src.omnia.dependencies import get_llm_client, get_current_provider
    
    client = get_llm_client()
    provider = request.get("provider") or get_current_provider() or "local"
    
    messages = request.get("messages", [])
    tools = request.get("tools")
    
    async def generate():
        try:
            async for chunk in client.stream(
                provider=provider,
                messages=messages,
                tools=tools
            ):
                yield f"{chunk}\n\n"
        except Exception as e:
            yield f"data: {{'error': '{str(e)}'}}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


# 挂载路由（后续添加）
# from src.omnia.routers import chat, memory, graph, provider, workflow, feishu, status
# app.include_router(chat.router, prefix="/api", tags=["chat"])
# app.include_router(memory.router, prefix="/api", tags=["memory"])
# app.include_router(graph.router, prefix="/api", tags=["graph"])
# app.include_router(provider.router, prefix="/api", tags=["provider"])
# app.include_router(workflow.router, prefix="/api", tags=["workflow"])
# app.include_router(feishu.router, prefix="/webhook", tags=["feishu"])
# app.include_router(status.router, prefix="/api", tags=["status"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
