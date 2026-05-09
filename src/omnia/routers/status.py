"""
状态监控路由
负责：系统状态、健康检查、配置信息
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import os
import subprocess
import sqlite3
from pathlib import Path

from src.omnia.config import settings
from core.config import MEMORY_PALACE_DB, OMNIA_HOME

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
    timestamp: str


def _daemon_status() -> bool:
    """检查守护进程状态"""
    pid_file = OMNIA_HOME / "daemon.pid"
    if not pid_file.exists():
        return False
    
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False


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
        from core.notification import NotificationQueue
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
    """获取 IDE 上下文"""
    context_file = OMNIA_HOME / "ide_context.json"
    if not context_file.exists():
        return None
    
    try:
        import json
        return json.loads(context_file.read_text())
    except Exception:
        return None


def _git_snapshot() -> dict | None:
    """获取 Git 状态"""
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
        import platform
        shell = os.environ.get("SHELL", "unknown")
        return {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "shell": shell.split("/")[-1] if "/" in shell else shell,
            "provider": settings.current_provider or "auto",
        }
    except Exception:
        return {"error": "failed to get env info"}


def _cron_schedule() -> list:
    """获取 cron 计划"""
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


def _project_wings() -> list:
    """获取项目 wings（副项目）"""
    wings = []
    wings_dir = settings.project_root / "wings"
    if wings_dir.exists():
        for d in wings_dir.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                wings.append({"name": d.name})
    return wings


def _mcp_status() -> dict:
    """获取 MCP 状态"""
    return {
        "initialized": False,
        "tools_count": 0,
    }


def _current_provider() -> str | None:
    """获取当前 Provider"""
    if settings.current_provider:
        return settings.current_provider
    
    # 从 .env 检测
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
    
    return None


@router.get("/status")
async def get_status():
    """
    获取系统完整状态（兼容 Flask 前端格式）
    
    包括：
    - daemon_running, api_ready
    - memory, skills, notifications
    - ide_context, git
    - system, env, cron, wings, mcp
    - current_provider, timestamp
    """
    from src.omnia.services.llm_client import LLMClient
    
    # 检查 API 是否就绪
    client = LLMClient()
    provider = settings.current_provider or "deepseek"
    api_key = client._load_api_key(provider)
    api_ready = api_key is not None
    
    provider_val = _current_provider()
    
    return {
        "daemon_running": _daemon_status(),
        "api_ready": api_ready,
        "memory": _memory_counts(),
        "skills": _skills_summary(),
        "notifications": _notifications(),
        "ide_context": _ide_context(),
        "git": _git_snapshot(),
        "system": {
            "cpu_percent": _system_vitals().cpu_percent,
            "memory_percent": _system_vitals().memory_percent,
            "disk_percent": _system_vitals().disk_percent,
        },
        "env": _env_snapshot(),
        "cron": _cron_schedule(),
        "wings": _project_wings(),
        "mcp": _mcp_status(),
        "current_provider": provider_val,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


@router.get("/status/daemon")
async def daemon_status():
    """守护进程状态"""
    return {
        "running": _daemon_status(),
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
    """
    确认操作
    """
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
    """打开 IDE"""
    try:
        subprocess.Popen(
            ["code", str(settings.project_root)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/token/status")
async def token_status(request: dict):
    """
    Token 状态查询 - 返回模拟数据确保前端不报错
    """
    return {
        "total_tokens": 0,
        "utilization": 0,
        "status": "empty",
    }
