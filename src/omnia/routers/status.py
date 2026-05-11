"""
状态监控路由
负责：系统状态、健康检查、配置信息

从 Flask 版 web_server.py 完整移植，保持功能一致性。
"""

from __future__ import annotations

import json
import os
import subprocess
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.omnia.config import settings

router = APIRouter()

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


def _memory_counts() -> dict:
    """获取记忆统计"""
    counts = {}
    if settings.memory_palace_db.exists():
        with sqlite3.connect(str(settings.memory_palace_db)) as conn:
            cursor = conn.cursor()
            for table in ["facts", "relations", "habits", "timeline", "conversation_logs"]:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    counts[table] = 0
    return counts


def _skills_summary() -> dict:
    """递归统计所有技能（包括子目录中的技能）"""
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
        from core.neuro_center.notification_queue import NotificationQueue
        q = NotificationQueue(settings.omnia_home / "notifications.jsonl")
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
    context_file = settings.omnia_home / "ide_context.json"
    if not context_file.exists():
        return None
    try:
        return json.loads(context_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def _git_snapshot() -> dict:
    """获取 Git 状态快照（完整版，与 Flask 一致）"""
    result = {"uncommitted_count": 0, "recent_commits_24h": 0, "branch": None}

    # 获取分支名
    try:
        branch_res = subprocess.run(
            ["git", "-C", str(settings.project_root), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if branch_res.returncode == 0:
            result["branch"] = branch_res.stdout.strip()
    except Exception:
        pass

    # 获取未提交文件数
    try:
        status_res = subprocess.run(
            ["git", "-C", str(settings.project_root), "status", "--short"],
            capture_output=True, text=True, timeout=10,
        )
        if status_res.returncode == 0:
            lines = [l for l in status_res.stdout.splitlines() if l.strip()]
            result["uncommitted_count"] = len(lines)
    except Exception:
        pass

    # 获取 24 小时内的提交数
    try:
        log_res = subprocess.run(
            ["git", "-C", str(settings.project_root), "log", "--since=24 hours ago", "--oneline", "--no-decorate"],
            capture_output=True, text=True, timeout=10,
        )
        if log_res.returncode == 0:
            commits = [l for l in log_res.stdout.splitlines() if l.strip()]
            result["recent_commits_24h"] = len(commits)
    except Exception:
        pass

    return result


def _system_vitals() -> dict:
    """获取系统状态（完整版，与 Flask 一致）"""
    vitals = {}
    try:
        import psutil
        vitals["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        vitals["memory_percent"] = mem.percent
        vitals["memory_used_gb"] = round(mem.used / (1024 ** 3), 2)
        vitals["memory_total_gb"] = round(mem.total / (1024 ** 3), 2)
        disk = psutil.disk_usage("/")
        vitals["disk_percent"] = disk.percent
        # CPU temperature (best effort)
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for key, entries in temps.items():
                    if entries:
                        vitals["cpu_temp_c"] = round(entries[0].current, 1)
                        break
        except Exception:
            vitals["cpu_temp_c"] = None
    except ImportError:
        pass
    return vitals


def _env_snapshot() -> dict:
    """获取环境快照（完整版，与 Flask 一致）"""
    import sys
    u = os.uname()

    # 确定当前使用的模型
    provider_models = {
        "deepseek": ("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        "qianfan": ("QIANFAN_MODEL", "qianfan-code-latest"),
        "kimi": ("MOONSHOT_MODEL", "K2.6-code-preview"),
        "openai": ("OPENAI_MODEL", "gpt-4o"),
        "xiaomi": ("MIMO_MODEL", "mimo-v2.5-pro"),
        "anthropic": ("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
    }

    model = "unknown"
    provider = settings.current_provider

    if provider:
        env_key, default = provider_models.get(provider, ("DEFAULT_MODEL", "unknown"))
        model = os.environ.get(env_key, default)
    else:
        # 自动检测
        env_file = settings.project_root / ".env"
        env_content = ""
        if env_file.exists():
            env_content = env_file.read_text(encoding="utf-8")

        api_key_env_map = {
            "deepseek": "DEEPSEEK_API_KEY",
            "qianfan": "QIANFAN_API_KEY",
            "kimi": "MOONSHOT_API_KEY",
            "openai": "OPENAI_API_KEY",
            "xiaomi": "MIMO_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }

        for pid, (env_key, default) in provider_models.items():
            key = api_key_env_map[pid]
            if os.environ.get(key) or f"{key}=" in env_content:
                provider = pid
                model = os.environ.get(env_key, default)
                if model == "unknown":
                    for line in env_content.splitlines():
                        if line.startswith(f"{env_key}="):
                            model = line.split("=", 1)[1].strip()
                            break
                if model == "unknown":
                    model = default
                break

    return {
        "hostname": u.nodename,
        "model": model,
        "provider": provider,
        "shell": os.environ.get("SHELL", "/bin/bash").split("/")[-1],
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "os": f"{u.sysname} {u.release}",
    }


def _cron_schedule() -> list:
    """获取 cron 计划（完整版，与 Flask 一致）"""
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
        jobs = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 6:
                schedule = " ".join(parts[:5])
                cmd = " ".join(parts[5:])
                # 提取简洁名称
                name = (cmd.split("/")[-1].split()[0] if "/" in cmd else (cmd.split()[0] if cmd.split() else "unknown"))
                if name.endswith(".py"):
                    name = name[:-3]
                jobs.append({"name": name, "schedule": schedule})
        return jobs
    except Exception:
        return []


def _project_wings() -> list:
    """获取项目 wings（完整版，与 Flask 一致）"""
    return [
        {"name": "喵修匠", "status": "active", "desc": "维修平台 · 商家工单系统"},
        {"name": "njuosun.com", "status": "active", "desc": "无人机维修站 · SEO 矩阵"},
        {"name": "Omnia", "status": "active", "desc": "Agent OS · 核心架构开发中"},
        {"name": "懂机帝", "status": "idle", "desc": "内容社区 · 暂时休眠"},
    ]


def _mcp_status(request_app=None) -> dict:
    """获取 MCP 状态"""
    try:
        # 优先检测 FastAPI 版的 mcp_manager
        if request_app and hasattr(request_app, "state") and hasattr(request_app.state, "mcp_manager"):
            mcp_manager = request_app.state.mcp_manager
            if hasattr(mcp_manager, "get_all_tools_schema"):
                tools = mcp_manager.get_all_tools_schema()
                return {
                    "initialized": True,
                    "tools_count": len(tools),
                }
        return {
            "initialized": False,
            "tools_count": 0,
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


# ========== 路由 ==========

@router.get("/status")
async def get_status(request: Request):
    """
    获取系统完整状态

    返回与 Flask 版完全一致的状态信息：
    - daemon_running: 守护进程状态
    - api_ready: API 就绪状态
    - memory: 记忆统计
    - skills: 技能统计
    - notifications: 通知列表
    - ide_context: IDE 上下文
    - git: Git 状态
    - system: 系统状态
    - env: 环境快照
    - cron: cron 计划
    - wings: 项目 wings
    - mcp: MCP 状态
    - tools: 工具摘要
    - timestamp: 时间戳
    """
    from src.omnia.services.llm_client import LLMClient

    client = LLMClient()
    provider = settings.current_provider or "deepseek"
    api_key = client._load_api_key(provider)
    api_ready = api_key is not None

    return {
        "daemon_running": _daemon_status(),
        "api_ready": api_ready,
        "memory": _memory_counts(),
        "skills": _skills_summary(),
        "notifications": _notifications(),
        "ide_context": _ide_context(),
        "git": _git_snapshot(),
        "system": _system_vitals(),
        "env": _env_snapshot(),
        "cron": _cron_schedule(),
        "wings": _project_wings(),
        "mcp": _mcp_status(request.app),
        "current_provider": _current_provider(),
        "tools": _tool_summary(),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


@router.get("/status/daemon")
async def daemon_status():
    """守护进程状态"""
    return {
        "running": _daemon_status(),
        "pid_file": str(settings.omnia_home / "daemon.pid"),
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
        "provider": provider,
    }


@router.get("/status/system")
async def system_status():
    """系统状态"""
    return _system_vitals()


@router.get("/status/git")
async def git_status():
    """Git 状态"""
    return _git_snapshot()


@router.get("/status/memory")
async def memory_status():
    """记忆状态"""
    return _memory_counts()


@router.get("/status/skills")
async def skills_status():
    """技能状态"""
    return _skills_summary()


@router.get("/status/env")
async def env_status():
    """环境快照"""
    return _env_snapshot()


@router.get("/status/cron")
async def cron_status():
    """Cron 计划"""
    return _cron_schedule()


@router.get("/status/wings")
async def wings_status():
    """项目 wings"""
    return _project_wings()
