"""
IDE 集成路由
负责：IDE 上下文接收、IDE 状态查询、VS Code 扩展通信

从 Flask 版 web_server.py 完整移植，保持功能一致性。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.omnia.config import settings
from src.omnia.config import settings

router = APIRouter()

# ========== 请求/响应模型 ==========

class IDEContext(BaseModel):
    """IDE 上下文数据"""
    file: Optional[str] = None
    language: Optional[str] = None
    selection: Optional[Dict[str, Any]] = None
    cursor: Optional[Dict[str, int]] = None
    project: Optional[str] = None
    branch: Optional[str] = None
    diagnostics: Optional[list] = None
    timestamp: Optional[str] = None


class IDEStatusResponse(BaseModel):
    """IDE 状态响应"""
    connected: bool
    context: Optional[Dict[str, Any]] = None
    last_update: Optional[str] = None


# ========== 辅助函数 ==========

def _get_ide_context_path() -> Path:
    """获取 IDE 上下文文件路径"""
    return settings.omnia_home / "ide_context.json"


def _load_ide_context() -> Optional[Dict[str, Any]]:
    """加载 IDE 上下文"""
    context_file = _get_ide_context_path()
    if not context_file.exists():
        return None
    try:
        return json.loads(context_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _save_ide_context(data: Dict[str, Any]) -> None:
    """保存 IDE 上下文"""
    context_file = _get_ide_context_path()
    context_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        context_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except OSError as e:
        print(f"[IDE] Failed to save context: {e}")
        raise


# ========== 路由 ==========

@router.post("/ide-context")
async def receive_ide_context(context: IDEContext):
    """
    接收 IDE 上下文

    VS Code 扩展通过此端点发送当前编辑器状态：
    - 当前打开的文件
    - 光标位置
    - 选中内容
    - 诊断信息（错误、警告）
    - 项目信息
    """
    data = context.model_dump(exclude_none=True)
    data["received_at"] = datetime.now().isoformat(timespec="seconds")

    try:
        _save_ide_context(data)
        return {
            "status": "ok",
            "file": data.get("file"),
            "received_at": data["received_at"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ide-context")
async def get_ide_context():
    """
    获取当前 IDE 上下文

    返回 VS Code 扩展最近发送的编辑器状态。
    供 Agent 在处理请求时参考。
    """
    context = _load_ide_context()
    if not context:
        return {
            "connected": False,
            "context": None,
            "message": "No IDE context available"
        }

    return {
        "connected": True,
        "context": context,
        "last_update": context.get("received_at"),
    }


@router.get("/ide/status", response_model=IDEStatusResponse)
async def ide_status():
    """
    IDE 连接状态

    检查 VS Code 扩展是否在线（基于最近一次上下文更新时间）。
    """
    context = _load_ide_context()
    if not context:
        return IDEStatusResponse(connected=False)

    # 检查是否在 5 分钟内有更新
    received_at = context.get("received_at", "")
    if received_at:
        try:
            last_update = datetime.fromisoformat(received_at)
            elapsed = (datetime.now() - last_update).total_seconds()
            connected = elapsed < 300  # 5 分钟内视为在线
        except ValueError:
            connected = False
    else:
        connected = False

    return IDEStatusResponse(
        connected=connected,
        context=context if connected else None,
        last_update=received_at if connected else None,
    )


@router.delete("/ide-context")
async def clear_ide_context():
    """清除 IDE 上下文"""
    context_file = _get_ide_context_path()
    if context_file.exists():
        context_file.unlink()
    return {"ok": True, "message": "IDE context cleared"}
