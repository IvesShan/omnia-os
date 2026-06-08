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
    在开发模式、GitHub Actions 和 Nuitka 打包后，需要把 core.xxx 映射到 src.core.xxx。
    """
    import importlib

    # 在 Nuitka onefile 模式下，standalone_main.py 已经设置了 OMNIA_ROOT 和 sys.path
    # 这里只需要确保 src.core 可导入，然后创建 core 的别名
    # 如果 src 在 sys.path 中，import src.core 应该能工作
    
    # 先尝试直接加载 src.core（如果 sys.path 中有项目根目录）
    try:
        src_core = importlib.import_module('src.core')
        if 'core' not in sys.modules:
            sys.modules['core'] = src_core
    except ImportError:
        # src.core 还找不到，可能是路径没配好
        # 尝试从当前文件推断项目根目录并加入 sys.path
        try:
            current_file = Path(__file__).resolve()
            # __file__ 可能是 .../src/omnia/main.py
            project_root = current_file.parent.parent.parent
            src_path = str(project_root / "src")
            if src_path not in sys.path:
                sys.path.insert(0, src_path)
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            # 再试一次
            src_core = importlib.import_module('src.core')
            if 'core' not in sys.modules:
                sys.modules['core'] = src_core
        except ImportError:
            pass  # 真的找不到，让后续导入报错

    # 设置导入钩子（拦截所有 core.xxx 导入）
    original_import = __builtins__['__import__']

    _THIRD_PARTY_CORE = ('certifi', 'httpcore', 'httpx', 'anyio', 'h11', 'h2', 'hpack', 'hyperframe', 'sniffio', 'idna')
    
    def _aliased_import(name, globals=None, locals=None, fromlist=(), level=0):
        # 不拦截相对导入 (level > 0)
        if level > 0:
            return original_import(name, globals, locals, fromlist, level)
        if name == 'core' or name.startswith('core.'):
            if name.startswith('core.') and name.split('.')[1] in _THIRD_PARTY_CORE:
                return original_import(name, globals, locals, fromlist, level)
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
from datetime import datetime
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

    # 传递 MCP 管理器给工具注册表，让 MCP 工具可执行
    try:
        if mcp_manager and hasattr(mcp_manager, 'call_tool'):
            tool_registry.set_mcp_manager(mcp_manager)
            # 将 MCP 工具注册到 tool_registry
            mcp_tools_list = mcp_manager.get_all_tools_schema()
            tool_registry.mcp_tools = mcp_tools_list
            # 重新初始化，确保 MCP 工具被注册到 _tools
            await tool_registry.initialize_default_tools()
            print(f"[Omnia] MCP tools registered: {len(mcp_tools_list)}")
    except Exception as e:
        print(f"[Omnia] MCP tool registration skipped: {e}")

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

    # 🧠 启动神经系统（EventBus + 自主行为引擎）
    try:
        from src.core.orchestration import start_nervous_system
        ns = start_nervous_system()
        print(f"[Omnia] Nervous system started — autonomous reflexes active")
    except Exception as e:
        print(f"[Omnia] Nervous system init skipped: {e}")
        import traceback
        traceback.print_exc()

    yield

    # ===== 关闭时 =====
    # 停止神经系统
    try:
        from src.core.orchestration import get_nervous_system
        ns = get_nervous_system()
        ns.stop()
        print("[Omnia] Nervous system stopped")
    except Exception:
        pass

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
    """根路径 - 检查是否首次运行，决定跳转到 Setup Wizard 还是主界面"""
    # 检查是否已完成初始配置
    setup_done_file = settings.project_root / ".omnia" / "config" / ".setup_done"
    if not setup_done_file.exists():
        # 首次运行，跳转到 Setup Wizard
        wizard_path = web_dir / "setup-wizard.html"
        if wizard_path.exists():
            return FileResponse(str(wizard_path))
    
    # 已完成配置，返回主界面
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


@app.get("/setup-wizard")
async def setup_wizard():
    """Setup Wizard 页面"""
    wizard_path = web_dir / "setup-wizard.html"
    if wizard_path.exists():
        return FileResponse(str(wizard_path))
    return JSONResponse(
        status_code=404,
        content={"detail": "Setup wizard not found"}
    )


@app.post("/api/setup/complete")
async def complete_setup():
    """标记初始配置完成"""
    setup_done_file = settings.project_root / ".omnia" / "config" / ".setup_done"
    setup_done_file.parent.mkdir(parents=True, exist_ok=True)
    setup_done_file.write_text(datetime.now().isoformat())
    return {"ok": True, "message": "Setup completed"}


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
