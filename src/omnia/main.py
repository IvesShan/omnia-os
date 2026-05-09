"""
Omnia FastAPI 主入口
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from src.omnia.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print(f"[Omnia] Starting FastAPI server on {settings.host}:{settings.port}")
    print(f"[Omnia] Debug mode: {settings.debug}")
    print(f"[Omnia] Current provider: {settings.current_provider or 'auto'}")
    
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


# ========== 异常处理 ==========

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


# ========== 静态文件 ==========

# 前端文件目录
web_dir = settings.project_root / "web"
static_dir = web_dir / "static"

# 挂载静态文件
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ========== 基础路由 ==========

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "version": "2.0.0"}


# ========== 挂载路由模块（必须在静态文件路由之前）==========

from src.omnia.routers import provider, chat, memory, graph, status

# Provider 管理
app.include_router(provider.router, prefix="/api", tags=["provider"])

# 聊天核心
app.include_router(chat.router, prefix="/api", tags=["chat"])

# 记忆搜索
app.include_router(memory.router, prefix="/api", tags=["memory"])

# 神经图谱
app.include_router(graph.router, prefix="/api", tags=["graph"])

# 状态监控
app.include_router(status.router, prefix="/api", tags=["status"])

# 后续添加其他路由
# from src.omnia.routers import workflow, feishu
# app.include_router(workflow.router, prefix="/api", tags=["workflow"])
# app.include_router(feishu.router, prefix="/webhook", tags=["feishu"])


# ========== 前端路由（必须放在最后）==========

@app.get("/")
async def root():
    """根路径 - 返回前端页面"""
    index_path = web_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "name": "Omnia",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/{filename:path}")
async def serve_static(filename: str):
    """服务前端静态文件"""
    # 查找文件
    file_path = web_dir / filename
    if file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))
    
    return JSONResponse(
        status_code=404,
        content={"detail": "Not Found"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
