"""
长任务处理路由
负责：复杂任务分解、执行、进度追踪
集成 LongTaskHandler
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio
import json
import uuid

from src.omnia.config import settings

router = APIRouter()

# 任务存储
TASK_DIR = settings.omnia_home / "tasks"


def _ensure_task_dir():
    """确保任务目录存在"""
    TASK_DIR.mkdir(parents=True, exist_ok=True)


class TaskCreateRequest(BaseModel):
    """创建任务请求"""
    goal: str
    auto_decompose: bool = True
    max_steps: int = 10


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    goal: str
    status: str  # pending, running, paused, completed, failed
    total_steps: int
    completed_steps: int
    current_step: Optional[str]
    percentage: float
    created_at: str
    updated_at: str


class TaskStep(BaseModel):
    """任务步骤"""
    id: str
    description: str
    tool_name: Optional[str]
    tool_args: Optional[Dict[str, Any]]
    status: str  # pending, running, completed, failed
    result: Optional[str]
    observation: Optional[str]


def _load_task(task_id: str) -> dict:
    """加载任务"""
    import json
    _ensure_task_dir()
    file = TASK_DIR / f"{task_id}.json"
    if file.exists():
        try:
            return json.loads(file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _save_task(task_id: str, data: dict):
    """保存任务"""
    import json
    _ensure_task_dir()
    file = TASK_DIR / f"{task_id}.json"
    file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _analyze_complexity(goal: str) -> Dict[str, Any]:
    """分析任务复杂度"""
    import re
    
    # 统计任务步骤数
    numbered_steps = len(re.findall(r'\d[)\.]\s*', goal))
    separator_steps = goal.count("和") + goal.count("然后") + goal.count("接着")
    
    # 动词检测
    action_verbs = ["读取", "列出", "执行", "显示", "查看", "检查", "分析", "生成", "创建", "删除"]
    action_count = sum(1 for verb in action_verbs if verb in goal)
    
    estimated_steps = max(numbered_steps, separator_steps + 1, action_count)
    
    # 复杂关键词
    complex_keywords = ["同时", "然后", "接着", "批量", "多个", "一系列", "逐步", "依次"]
    is_complex = any(kw in goal for kw in complex_keywords) or estimated_steps > 3
    
    return {
        "is_complex": is_complex,
        "estimated_steps": estimated_steps,
        "should_decompose": estimated_steps > 5 or is_complex,
    }


@router.post("/task/analyze")
async def analyze_task(goal: str) -> dict:
    """
    分析任务复杂度
    
    返回任务是否需要分解、预估步骤数等信息
    """
    analysis = _analyze_complexity(goal)
    
    return {
        "ok": True,
        "goal": goal,
        "analysis": analysis,
        "recommendation": "建议使用长任务处理器" if analysis["should_decompose"] else "可以直接执行",
    }


@router.post("/task", response_model=Dict[str, Any])
async def create_task(req: TaskCreateRequest, background_tasks: BackgroundTasks) -> dict:
    """
    创建长任务
    
    自动分析复杂度，必要时分解为多个步骤
    """
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    
    # 分析复杂度
    analysis = _analyze_complexity(req.goal)
    
    # 创建任务记录
    task = {
        "task_id": task_id,
        "goal": req.goal,
        "status": "pending",
        "auto_decompose": req.auto_decompose,
        "analysis": analysis,
        "steps": [],
        "total_steps": 0,
        "completed_steps": 0,
        "current_step_index": 0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    
    # 如果需要自动分解
    if req.auto_decompose and analysis["should_decompose"]:
        # 这里应该调用 LLM 进行任务分解
        # 简化版：创建占位步骤
        task["steps"] = [
            {
                "id": f"step_{i}",
                "description": f"步骤 {i+1}",
                "status": "pending",
                "result": None,
            }
            for i in range(min(analysis["estimated_steps"], req.max_steps))
        ]
        task["total_steps"] = len(task["steps"])
    
    _save_task(task_id, task)
    
    return {
        "ok": True,
        "task_id": task_id,
        "status": "pending",
        "analysis": analysis,
        "total_steps": task["total_steps"],
        "message": "任务已创建，等待执行",
    }


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> dict:
    """获取任务状态"""
    task = _load_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    percentage = (task["completed_steps"] / task["total_steps"] * 100) if task["total_steps"] > 0 else 0
    
    return TaskStatusResponse(
        task_id=task["task_id"],
        goal=task["goal"],
        status=task["status"],
        total_steps=task["total_steps"],
        completed_steps=task["completed_steps"],
        current_step=task["steps"][task["current_step_index"]]["description"] if task["steps"] and task["current_step_index"] < len(task["steps"]) else None,
        percentage=round(percentage, 1),
        created_at=task["created_at"],
        updated_at=task["updated_at"],
    )


@router.post("/task/{task_id}/start")
async def start_task(task_id: str, background_tasks: BackgroundTasks) -> dict:
    """开始执行任务"""
    task = _load_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task["status"] == "running":
        raise HTTPException(status_code=400, detail="任务已在运行中")
    
    # 更新状态
    task["status"] = "running"
    task["updated_at"] = datetime.now().isoformat()
    _save_task(task_id, task)
    
    # 在后台执行任务
    try:
        import asyncio
        asyncio.create_task(_execute_task_async(task_id))
    except Exception as bg_err:
        task["status"] = "failed"
        task["error"] = str(bg_err)
        _save_task(task_id, task)
    
    return {
        "ok": True,
        "task_id": task_id,
        "status": "running",
        "message": "任务已开始执行",
    }


@router.post("/task/{task_id}/pause")
async def pause_task(task_id: str) -> dict:
    """暂停任务"""
    task = _load_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task["status"] != "running":
        raise HTTPException(status_code=400, detail="只能暂停运行中的任务")
    
    task["status"] = "paused"
    task["updated_at"] = datetime.now().isoformat()
    _save_task(task_id, task)
    
    return {
        "ok": True,
        "task_id": task_id,
        "status": "paused",
        "message": "任务已暂停",
    }


@router.post("/task/{task_id}/resume")
async def resume_task(task_id: str) -> dict:
    """恢复暂停的任务"""
    task = _load_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task["status"] != "paused":
        raise HTTPException(status_code=400, detail="只能恢复暂停的任务")
    
    task["status"] = "running"
    task["updated_at"] = datetime.now().isoformat()
    _save_task(task_id, task)
    
    return {
        "ok": True,
        "task_id": task_id,
        "status": "running",
        "message": "任务已恢复",
    }


@router.post("/task/{task_id}/cancel")
async def cancel_task(task_id: str) -> dict:
    """取消任务"""
    task = _load_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task["status"] in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="任务已结束，无法取消")
    
    task["status"] = "cancelled"
    task["updated_at"] = datetime.now().isoformat()
    _save_task(task_id, task)
    
    return {
        "ok": True,
        "task_id": task_id,
        "status": "cancelled",
        "message": "任务已取消",
    }


@router.get("/task/{task_id}/steps")
async def get_task_steps(task_id: str) -> dict:
    """获取任务的所有步骤"""
    task = _load_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return {
        "task_id": task_id,
        "total_steps": task["total_steps"],
        "completed_steps": task["completed_steps"],
        "steps": task["steps"],
    }


@router.get("/tasks")
async def list_tasks(status: Optional[str] = None) -> dict:
    """列出所有任务"""
    import json
    
    _ensure_task_dir()
    tasks = []
    
    for file in TASK_DIR.glob("task_*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            if status is None or data["status"] == status:
                tasks.append({
                    "task_id": data["task_id"],
                    "goal": data["goal"][:100],
                    "status": data["status"],
                    "total_steps": data["total_steps"],
                    "completed_steps": data["completed_steps"],
                    "created_at": data["created_at"],
                })
        except (json.JSONDecodeError, OSError, KeyError):
            continue
    
    return {
        "total": len(tasks),
        "tasks": sorted(tasks, key=lambda x: x["created_at"], reverse=True),
    }


@router.delete("/task/{task_id}")
async def delete_task(task_id: str) -> dict:
    """删除任务"""
    file = TASK_DIR / f"{task_id}.json"
    
    if not file.exists():
        raise HTTPException(status_code=404, detail="任务不存在")
    
    file.unlink()
    
    return {
        "ok": True,
        "message": f"任务 {task_id} 已删除",
    }
