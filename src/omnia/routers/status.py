"""
状态监控路由
负责：系统状态、健康检查、配置信息
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import os
import subprocess
import asyncio
import sqlite3
from pathlib import Path

from src.omnia.config import settings
from src.core.config import MEMORY_PALACE_DB, OMNIA_HOME

router = APIRouter()


class SystemVitals(BaseModel):
    """系统状态"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float


class StatusResponse(BaseModel):
    """状态响应"""
    daemon_running: bool
    api_ready: bool
    memory: Dict[str, int]
    skills: Dict[str, int]
    notifications: list
    ide_context: Optional[Dict[str, Any]]
    git: Optional[Dict[str, Any]]
    system: SystemVitals
    env: Dict[str, Any]
    cron: list
    wings: list
    mcp: Dict[str, Any]
    current_provider: Optional[str]
    tools: Dict[str, Any]
    timestamp: str


async def _daemon_status_async() -> bool:
    """检查 API 服务状态（已改为直接检测，避免自调用死锁）"""
    import socket
    def _check_port():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        try:
            # 连接 127.0.0.1:8765 看是否通
            result = sock.connect_ex(('127.0.0.1', 8765))
            return result == 0
        except Exception:
            return False
        finally:
            sock.close()
    return await asyncio.to_thread(_check_port)


def _memory_counts() -> dict:
    """获取记忆统计"""
    counts = {}
    if MEMORY_PALACE_DB.exists():
        with sqlite3.connect(str(MEMORY_PALACE_DB)) as conn:
            cursor = conn.cursor()
            for table in ["facts", "relations", "habits", "timeline", "conversation_logs"]:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    counts[table] = 0
    return counts


def _skills_summary() -> dict:
    """递归统计所有技能"""
    total = 0
    auto_forged = 0
    
    for base_dir in [settings.project_root / "skills", settings.project_root / ".tmp_skills"]:
        if base_dir.exists():
            for skill_md in base_dir.rglob("SKILL.md"):
                skill_dir = skill_md.parent
                total += 1
                if "auto-forge" in skill_dir.name or skill_dir.name.startswith("auto-forge"):
                    auto_forged += 1
    
    return {"total": total, "auto_forged": auto_forged}


def _notifications() -> list:
    """获取通知列表"""
    try:
        from src.core.notification import NotificationQueue
        q = NotificationQueue(OMNIA_HOME / "notifications.jsonl")
        notes = q.pop_pending(limit=5, mark_popped=False)
        return [
            {
                "id": n.id,
                "level": n.level,
                "source": n.source,
                "title": n.title,
                "body": n.body,
                "created_at": n.created_at,
            }
            for n in notes
        ]
    except Exception:
        return []


def _ide_context() -> dict | None:
    """获取 IDE 上下文（5 分钟超时视为断开）"""
    import time
    context_file = OMNIA_HOME / "ide_context.json"
    if not context_file.exists():
        return None
    
    try:
        import json
        data = json.loads(context_file.read_text())
        # 检查是否过期（5 分钟无更新视为断开）
        received_at = data.get("received_at", "")
        if received_at:
            try:
                from datetime import datetime
                last_update = datetime.fromisoformat(received_at)
                elapsed = (datetime.now() - last_update).total_seconds()
                if elapsed > 300:  # 5 分钟超时
                    return None
            except (ValueError, TypeError):
                pass
        return data
    except Exception:
        return None


def _git_snapshot() -> dict | None:
    """获取 Git 状态（在线程池中执行，避免阻塞事件循环）"""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=settings.project_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return None
        
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=settings.project_root,
            capture_output=True,
            text=True,
            timeout=5
        ).stdout.strip()
        
        return {
            "branch": branch,
            "modified": len([l for l in lines if l.startswith(" M") or l.startswith("M ")]),
            "untracked": len([l for l in lines if l.startswith("??")]),
            "staged": len([l for l in lines if l.startswith("A ") or l.startswith("M ")]),
        }
    except Exception:
        return None




async def _git_snapshot_async() -> dict | None:
    """异步获取 Git 状态"""
    return await asyncio.to_thread(_git_snapshot)

def _system_vitals() -> SystemVitals:
    """获取系统状态"""
    try:
        import psutil
        return SystemVitals(
            cpu_percent=psutil.cpu_percent(interval=0.1),
            memory_percent=psutil.virtual_memory().percent,
            disk_percent=psutil.disk_usage('/').percent
        )
    except ImportError:
        return SystemVitals(
            cpu_percent=0.0,
            memory_percent=0.0,
            disk_percent=0.0
        )


def _env_snapshot() -> dict:
    """获取环境快照"""
    try:
        import platform as pfm
        shell = os.environ.get("SHELL", "unknown")
        return {
            "hostname": pfm.node(),
            "os": pfm.platform(),
            "python": pfm.python_version(),
            "shell": shell.split("/")[-1] if "/" in shell else shell,
            "model": settings.current_provider or "auto",
        }
    except Exception:
        return {"error": "failed to get env info"}


def _cron_schedule_sync() -> list:
    """获取 cron 计划（同步版本）"""
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip() and not l.startswith("#")]
            return [{"line": l} for l in lines[:10]]
        return []
    except Exception:
        return []




async def _cron_schedule() -> list:
    """获取 cron 计划（异步版本）"""
    return await asyncio.to_thread(_cron_schedule_sync)

def _project_wings() -> list:
    """获取项目 wings（副项目）"""
    wings = []
    wings_dir = settings.project_root / "wings"
    if wings_dir.exists():
        for d in wings_dir.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                wings.append({"name": d.name})
    return wings


def _mcp_status(app=None) -> dict:
    """获取 MCP 状态（FastAPI 版支持 app.state.mcp_manager）"""
    try:
        # 优先检测 FastAPI 版的 mcp_manager
        if app and hasattr(app, "state") and hasattr(app.state, "mcp_manager"):
            mcp_manager = app.state.mcp_manager
            if hasattr(mcp_manager, "get_all_tools_schema"):
                tools = mcp_manager.get_all_tools_schema()
                return {
                    "initialized": True,
                    "tools_count": len(tools),
                }
        # Fallback：尝试旧版检测
        from src.omnia.services.mcp_bridge import mcp_bridge
        return {
            "initialized": mcp_bridge.connected,
            "tools_count": mcp_bridge.tools_count,
        }
    except Exception:
        return {
            "initialized": False,
            "tools_count": 0,
        }


def _tool_summary() -> dict:
    """获取工具系统摘要"""
    try:
        from src.omnia.services.tool_registry import tool_registry
        return {
            "total": tool_registry.get_tool_count(),
            "names": tool_registry.get_tool_names(),
        }
    except Exception:
        return {"total": 0, "names": []}


def _current_provider() -> str | None:
    """获取当前 Provider"""
    if settings.current_provider:
        return settings.current_provider
    
    env_file = settings.project_root / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("OMNIA_PROVIDER="):
                return line.split("=", 1)[1].strip()
    
    if os.environ.get("DEEPSEEK_API_KEY"):
        return "deepseek"
    elif os.environ.get("MOONSHOT_API_KEY"):
        return "kimi"
    
    return None


@router.get("/status")
async def get_status(request: Request):
    """获取系统完整状态"""
    from src.omnia.services.llm_client import LLMClient
    
    client = LLMClient()
    provider = settings.current_provider or "deepseek"
    api_key = client._load_api_key(provider)
    api_ready = api_key is not None
    
    provider_val = _current_provider()
    
    return {
        "daemon_running": await _daemon_status_async(),
        "api_ready": api_ready,
        "memory": _memory_counts(),
        "skills": _skills_summary(),
        "notifications": _notifications(),
        "ide_context": _ide_context(),
        "git": await _git_snapshot_async(),
        "system": {
            "cpu_percent": _system_vitals().cpu_percent,
            "memory_percent": _system_vitals().memory_percent,
            "disk_percent": _system_vitals().disk_percent,
        },
        "env": _env_snapshot(),
        "cron": await _cron_schedule(),
        "wings": _project_wings(),
        "mcp": _mcp_status(request.app),
        "current_provider": provider_val,
        "tools": _tool_summary(),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


@router.get("/status/daemon")
async def daemon_status():
    """守护进程状态"""
    return {
        "running": await _daemon_status_async(),
        "pid_file": str(OMNIA_HOME / "daemon.pid")
    }


@router.get("/status/api")
async def api_status():
    """API 就绪状态"""
    from src.omnia.services.llm_client import LLMClient
    client = LLMClient()
    provider = settings.current_provider or "deepseek"
    api_key = client._load_api_key(provider)
    
    return {
        "ready": api_key is not None,
        "provider": provider
    }


@router.get("/status/system")
async def system_status():
    """系统状态"""
    return _system_vitals()


@router.get("/status/git")
async def git_status():
    """Git 状态"""
    return _git_snapshot() or {"error": "Not a git repository"}


@router.get("/status/memory")
async def memory_status():
    """记忆状态"""
    return _memory_counts()


@router.post("/confirm")
async def confirm_action(request: dict):
    """确认操作"""
    cid = (request.get("confirm_id") or "").strip()
    approved = bool(request.get("approved"))
    
    return {
        "confirm_id": cid,
        "approved": approved,
        "status": "processed",
        "steps": [],
        "reply": "操作已确认" if approved else "操作已取消",
    }


@router.post("/open-ide")
async def open_ide():
    """打开 IDE（复用已打开的 VS Code 窗口）"""
    try:
        # 使用 --reuse-window 参数复用已打开的 VS Code 窗口
        subprocess.Popen(
            ["code", "--reuse-window", str(settings.project_root)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/token/status")
async def token_status(request: dict):
    """Token 状态查询"""
    return {
        "total_tokens": 0,
        "utilization": 0,
        "status": "empty",
    }
