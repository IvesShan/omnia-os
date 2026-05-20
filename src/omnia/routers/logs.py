"""
日志管理路由
从 backend/main.py 合并
"""
import json
import asyncio
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

router = APIRouter()

# 日志路径
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_LOGS_PATH = _PROJECT_ROOT / "logs"
_OMNIA_HOME = Path.home() / ".omnia"
_BACKEND_LOG = _OMNIA_HOME / "logs" / "backend.log"


@router.get("/logs")
async def get_logs(lines: int = Query(100, description="返回的日志行数")):
    """获取日志"""
    # 优先查找 omnia-main.log
    log_file = _LOGS_PATH / "omnia-main.log"
    if not log_file.exists():
        log_file = _BACKEND_LOG

    if not log_file.exists():
        return {"logs": [], "message": "No log file found"}

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        return {"logs": [line.strip() for line in recent_lines], "total": len(all_lines)}
    except Exception as e:
        return {"logs": [], "error": str(e)}


@router.get("/logs/stream")
async def stream_logs():
    """实时日志流 (SSE)"""
    log_file = _LOGS_PATH / "omnia-main.log"
    if not log_file.exists():
        log_file = _BACKEND_LOG

    async def log_generator():
        last_size = 0
        while True:
            if log_file.exists():
                current_size = log_file.stat().st_size
                if current_size > last_size:
                    with open(log_file, "r", encoding="utf-8") as f:
                        f.seek(last_size)
                        new_content = f.read()
                        last_size = current_size
                        for line in new_content.strip().split("\n"):
                            if line:
                                yield f"data: {line}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(log_generator(), media_type="text/event-stream")
