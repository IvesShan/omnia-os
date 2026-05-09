"""
状态监控路由
负责：系统状态、健康检查、配置信息
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import os
import subprocess
import sqlite3
from pathlib import Path

from src.omnia.config import settings
from src.omnia.dependencies import get_memory_palace
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
    ide_context: Optional[Dict[str, Any]]
    git: Optional[Dict[str, Any]]
    system: SystemVitals
    timestamp: str


def _daemon_status() -> bool:
    """检查守护进程状态"""
    pid_file = OMNIA_HOME / "daemon.pid"
    if not pid_file.exists():
        return False
    
    try:
        pid = int(pid_file.read_text().strip())
        # 检查进程是否存在
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
        
        return {
            "branch": subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=settings.project_root,
                capture_output=True,
                text=True,
                timeout=5
            ).stdout.strip(),
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


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """
    获取系统完整状态
    
    包括：
    - 守护进程状态
    - API 就绪状态
    - 记忆统计
    - IDE 上下文
    - Git 状态
    - 系统状态
    """
    from src.omnia.services.llm_client import LLMClient
    
    # 检查 API 是否就绪
    client = LLMClient()
    provider = settings.current_provider or "deepseek"
    api_key = client._load_api_key(provider)
    api_ready = api_key is not None
    
    return StatusResponse(
        daemon_running=_daemon_status(),
        api_ready=api_ready,
        memory=_memory_counts(),
        ide_context=_ide_context(),
        git=_git_snapshot(),
        system=_system_vitals(),
        timestamp=datetime.now().isoformat(timespec="seconds")
    )


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
    
    用于敏感操作的确认机制
    """
    cid = (request.get("confirm_id") or "").strip()
    approved = bool(request.get("approved"))
    
    # TODO: 实现确认机制
    # 这需要与 Flask 版本的确认系统集成
    
    return {
        "confirm_id": cid,
        "approved": approved,
        "status": "processed"
    }


@router.post("/open-ide")
async def open_ide():
    """打开 IDE"""
    try:
        import subprocess
        subprocess.Popen(
            ["code", str(settings.project_root)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
