"""
Omnia FastAPI 主入口
"""
import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

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
    # ===== 启动时初始化 =====
    print(f"[Omnia] Starting FastAPI server on {settings.host}:{settings.port}")
    print(f"[Omnia] Debug mode: {settings.debug}")
    print(f"[Omnia] Current provider: {settings.current_provider or 'auto'}")

    # 初始化 MCP 工具（FastAPI 方式：用已有事件循环）
    try:
        from core.actuator.mcp_client import MCPClientManager
        mcp_manager = MCPClientManager()
        await mcp_manager.connect_all()
        mcp_tools = mcp_manager.get_all_tools_schema()
        app.state.mcp_manager = mcp_manager
        print(f"[Omnia] MCP connected: {len(mcp_tools)} tools")
        for tool in mcp_tools:
            print(f"  └─ {tool['function']['name']}")
    except Exception as e:
        print(f"[Omnia] MCP init skipped: {e}")
        import traceback
        traceback.print_exc()

    # 初始化工具系统（原生工具）
    try:
        from src.omnia.services.tool_registry import tool_registry
        tool_count = await tool_registry.initialize_default_tools()
        print(f"[Omnia] Native tools: {tool_count}")
        for name in tool_registry.get_tool_names():
            print(f"  └─ {name}")
    except Exception as e:
        print(f"[Omnia] Tool listing skipped: {e}")
        import traceback
        traceback.print_exc()

    # 初始化 Agent 引擎
    try:
        from src.omnia.services.agent_engine import agent_engine
        print(f"[Omnia] Agent engine ready (max {agent_engine.max_tool_rounds} rounds)")
    except Exception as e:
        print(f"[Omnia] Agent engine init skipped: {e}")

    # 初始化会话管理器
    try:
        from src.omnia.services.session_manager import get_session_manager
        sm = get_session_manager()
        info = sm.get_session_info()
        if info.get("status") == "active":
            print(f"[Omnia] Session resumed: {info['session_id']}, messages: {info['message_count']}")
        else:
            print(f"[Omnia] No active session to resume")
    except Exception as e:
        print(f"[Omnia] Session manager init skipped: {e}")

    # 初始化自动记忆
    try:
        from src.omnia.services.auto_memory import auto_memory
        print(f"[Omnia] Auto memory ready")
    except Exception as e:
        print(f"[Omnia] Auto memory init skipped: {e}")

    yield

    # ===== 关闭时 =====
    # 清理 MCP 子进程
    try:
        mcp_manager = getattr(app.state, "mcp_manager", None)
        if mcp_manager and hasattr(mcp_manager, "close"):
            await mcp_manager.close()
            print("[Omnia] MCP connections closed")
    except Exception as e:
        print(f"[Omnia] MCP cleanup error: {e}")

    # 关闭 LLM 客户端
    try:
        from src.omnia.services.llm_client import _client
        if _client:
            await _client.close()
            print("[Omnia] LLM client closed")
    except Exception:
        pass

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

web_dir = settings.project_root / "web"
static_dir = web_dir / "static"

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ========== 基础路由 ==========

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "version": "2.0.0"}


# ========== 挂载路由模块（必须在静态文件路由之前） ==========

from src.omnia.routers import provider, chat, memory, graph, status, workflow, feishu
from src.omnia.routers import swarm, scheduler, skills
from src.omnia.routers import computer, interrupt, wake
from src.omnia.routers import confirm, ide, model_status
from src.omnia.routers import discuss, long_task, fts
from src.omnia.routers import learner
from src.omnia.routers import vector, plan, gateway

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

# 工作流
app.include_router(workflow.router, prefix="/api", tags=["workflow"])

# 飞书集成
app.include_router(feishu.router, prefix="/api", tags=["feishu"])

# 多 Agent 讨论
app.include_router(discuss.router, prefix="/api", tags=["discuss"])

# 长任务处理
app.include_router(long_task.router, prefix="/api", tags=["task"])

# FTS 全文搜索
app.include_router(fts.router, prefix="/api", tags=["fts"])

# 确认操作
app.include_router(confirm.router, prefix="/api", tags=["confirm"])

# IDE 集成
app.include_router(ide.router, prefix="", tags=["ide"])

# 模型状态、Token、MCP、OpenAI 兼容
app.include_router(model_status.router, prefix="/api", tags=["model"])
# AgentSwarm 多 Agent 并行
app.include_router(swarm.router, tags=["swarm"])

# Scheduler 定时任务
app.include_router(scheduler.router, tags=["scheduler"])

# SkillForge 技能锻造
app.include_router(skills.router, tags=["skills"])

# AutoLearner 自动学习
app.include_router(learner.router, tags=["learner"])
app.include_router(vector.router, tags=["vector"])
app.include_router(plan.router, tags=["plan"])
app.include_router(gateway.router, tags=["gateway"])
# Computer Controller 电脑控制
app.include_router(computer.router, tags=["computer"])

# Interrupt Manager 中断管理
app.include_router(interrupt.router, tags=["interrupt"])

# Wake 唤醒功能
app.include_router(wake.router, tags=["wake"])






# ========== 工具管理路由 ==========

@app.get("/api/tools")
async def list_tools():
    """列出所有可用工具"""
    from src.omnia.services.tool_registry import tool_registry

    tools = tool_registry.get_tool_names()
    schemas = tool_registry.get_all_schemas()

    return {
        "total": len(tools),
        "tools": tools,
        "schemas": schemas,
    }


# ========== 会话管理路由 ==========

@app.get("/api/session")
async def get_session():
    """获取当前会话信息"""
    from src.omnia.services.session_manager import get_session_manager
    sm = get_session_manager()
    return sm.get_session_info()


@app.post("/api/session/new")
async def new_session():
    """强制创建新会话"""
    from src.omnia.services.session_manager import get_session_manager
    sm = get_session_manager()
    session_id = sm.force_new_session()
    return {"ok": True, "session_id": session_id}


# ========== 前端路由（必须放在最后） ==========

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
