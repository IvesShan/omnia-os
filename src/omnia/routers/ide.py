"""
IDE 集成路由
负责：IDE 上下文接收、IDE 状态查询、VS Code 扩展通信

从 Flask 版 web_server.py 完整移植，保持功能一致性。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.omnia.config import settings

router = APIRouter()

# ========== 请求/响应模型 ==========


class IDEContext(BaseModel):
    """
    IDE 上下文数据
    
    兼容 VSCode 扩展发送的格式：
    - file: 当前文件路径
    - language: 语言类型
    - line: 光标行号
    - column: 光标列号
    - selectedText: 选中的文本
    - timestamp: 时间戳（数字或字符串）
    - fullContent: 完整文件内容（可选）
    """
    file: Optional[str] = None
    language: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    selectedText: Optional[str] = None
    timestamp: Optional[Any] = None  # 支持数字或字符串
    fullContent: Optional[str] = None
    
    # 兼容旧格式（可选）
    selection: Optional[Dict[str, Any]] = None
    cursor: Optional[Dict[str, int]] = None
    project: Optional[str] = None
    branch: Optional[str] = None
    diagnostics: Optional[List[Any]] = None


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


def _normalize_context(context: IDEContext) -> Dict[str, Any]:
    """
    规范化上下文数据
    
    将 VSCode 扩展发送的格式转换为前端期望的格式
    """
    data = {}
    
    # 基本字段
    data["file"] = context.file
    data["language"] = context.language
    data["line"] = context.line
    data["column"] = context.column
    data["selectedText"] = context.selectedText or ""
    data["fullContent"] = context.fullContent
    
    # 处理时间戳（支持数字和字符串）
    if context.timestamp is not None:
        if isinstance(context.timestamp, (int, float)):
            # 数字时间戳转为 ISO 格式
            try:
                dt = datetime.fromtimestamp(context.timestamp / 1000.0)
                data["timestamp"] = dt.isoformat(timespec="seconds")
            except (ValueError, OSError):
                data["timestamp"] = str(context.timestamp)
        else:
            data["timestamp"] = str(context.timestamp)
    
    # 兼容旧格式字段
    if context.selection:
        data["selection"] = context.selection
    if context.cursor:
        data["cursor"] = context.cursor
    if context.project:
        data["project"] = context.project
    if context.branch:
        data["branch"] = context.branch
    if context.diagnostics:
        data["diagnostics"] = context.diagnostics
    
    # 移除 None 值
    return {k: v for k, v in data.items() if v is not None}


# ========== 路由 ==========


@router.post("/ide-context")
async def receive_ide_context(context: IDEContext):
    """
    接收 IDE 上下文

    VS Code 扩展通过此端点发送当前编辑器状态：
    - 当前打开的文件
    - 光标位置
    - 选中内容
    - 文件内容（可选）
    """
    data = _normalize_context(context)
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
