"""
Omnia FastAPI 主入口
"""
import os
import sys
from pathlib import Path

# ========== 模块别名注册（解决 core.xxx -> src.core.xxx）==========
# 必须在任何 core.xxx 导入之前执行
def _setup_core_aliases():
    """
    代码库中大量使用了 `from core.xxx` 导入，但项目结构是 src/core/xxx.py。
    在开发模式和 GitHub Actions 中，需要把 core.xxx 映射到 src.core.xxx。
    Nuitka 打包后 standalone_main.py 也会做同样的映射。
    """
    import importlib

    # 如果 src.core 可导入但 core 不可导入，创建别名
    try:
        src_core = importlib.import_module('src.core')
        if 'core' not in sys.modules:
            sys.modules['core'] = src_core
    except ImportError:
        pass  # src.core 不存在，不处理

    # 设置导入钩子
    original_import = __builtins__['__import__']

    def _aliased_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'core' or name.startswith('core.'):
            src_name = 'src.' + name
            try:
                # 如果 src.core.xxx 还没加载，先加载它
                if src_name not in sys.modules:
                    original_import(src_name, globals, locals, fromlist, level)
                # 创建 core.xxx 的别名指向 src.core.xxx
                if src_name in sys.modules:
                    sys.modules[name] = sys.modules[src_name]
                    return sys.modules[src_name]
            except ImportError:
                pass  # src.core.xxx 也不存在，回退到原始导入
        return original_import(name, globals, locals, fromlist, level)

    __builtins__['__import__'] = _aliased_import


_setup_core_aliases()
# ========== 别名注册结束 ==========


# 打包模式：通过环境变量获取路径，避免 __file__ 指向错误位置
_root = os.environ.get("OMNIA_ROOT")
if _root:
    _PROJECT_ROOT = Path(_root)
    # Nuitka --standalone 会把 src 子包编译进可执行文件
    # 但需要确保临时解压目录也在 sys.path 中
    # standalone_main.py 已经处理了，这里不再重复添加
else:
    # 开发模式：通过 __file__ 推断
    _PROJECT_ROOT = Path(__file__).parent.parent.parent
    # 确保 src 目录在 sys.path 中（仅开发模式需要）
    _src_path = str(_PROJECT_ROOT / "src")
    if _src_path not in sys.path:
        sys.path.insert(0, _src_path)

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
    print(f"[Omnia] Project root: {settings.project_root}")
    print(f"[Omnia] Debug mode: {settings.debug}")
    print(f"[Omnia] Current provider: {settings.current_provider or 'auto'}")

    # 初始化 MCP 工具（FastAPI 方式：用已有事件循环）
    try:
        from src.core.actuator.mcp_client import MCPClientManager
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


# ========== 健康检查（最高优先级，不经过其他路由） ==========

@app.get("/health")
async def health():
    """健康检查 - 轻量级，不触发任何重操作"""
    return {"status": "ok", "version": "2.0.0"}


# ========== 静态文件 ==========

web_dir = settings.project_root / "web"
static_dir = web_dir / "static"

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ========== 挂载路由模块 ==========

from src.omnia.routers import provider, chat, memory, graph, status, workflow, feishu
from src.omnia.routers import swarm, scheduler, skills
from src.omnia.routers import computer, interrupt, wake
from src.omnia.routers import confirm, ide, model_status
from src.omnia.routers import discuss, long_task, fts
from src.omnia.routers import learner
from src.omnia.routers import summary
from src.omnia.routers import vector, plan, gateway
from src.omnia.routers import reasoning, capability, reflection, progressive
from src.omnia.routers import performance
from src.omnia.routers import license

# Progressive Capability 渐进式能力
# Reflection 反思模块
app.include_router(reflection.router, tags=["reflection"])
app.include_router(capability.router, tags=["capability"])

# Reasoning Engine 推理引擎
app.include_router(reasoning.router, tags=["reasoning"])
# Progressive Capability 渐进式能力
app.include_router(progressive.router, tags=["progressive"])
app.include_router(performance.router, tags=["performance"])
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

# Summary 总结模块
app.include_router(summary.router, prefix="/api", tags=["summary"])

# License 授权管理
app.include_router(license.router, tags=["license"])


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
