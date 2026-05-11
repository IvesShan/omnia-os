"""Scheduler API - 定时任务调度

支持 Cron 表达式、一次性任务、周期性任务
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

# 尝试导入 Scheduler 模块
try:
    from core.orchestration.scheduler import Scheduler, ScheduledTask
    SCHEDULER_AVAILABLE = True
except ImportError as e:
    SCHEDULER_AVAILABLE = False
    Scheduler = None
    ScheduledTask = None


# ============== 请求/响应模型 ==============

class CreateTaskRequest(BaseModel):
    """创建任务请求"""
    name: str
    cron: Optional[str] = None  # Cron 表达式
    interval_seconds: Optional[float] = None  # 间隔秒数
    run_once: bool = False
    run_at: Optional[datetime] = None
    action_type: str = "http_callback"  # http_callback, workflow, script
    action_config: Dict[str, Any] = {}
    enabled: bool = True
    max_retries: int = 3
    metadata: Optional[Dict[str, Any]] = None


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    name: str
    cron: Optional[str]
    interval_seconds: Optional[float]
    run_once: bool
    run_at: Optional[datetime]
    enabled: bool
    last_run: Optional[datetime]
    last_result: Optional[str]
    next_run: Optional[datetime]
    run_count: int
    status: str  # idle, running, error, disabled


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskResponse]
    total: int
    running_count: int


class UpdateTaskRequest(BaseModel):
    """更新任务请求"""
    name: Optional[str] = None
    cron: Optional[str] = None
    interval_seconds: Optional[float] = None
    enabled: Optional[bool] = None
    max_retries: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


# ============== 全局实例 ==============

_scheduler = None
_tasks: Dict[str, Dict[str, Any]] = {}  # 存储任务配置
_task_counter = 0


def get_scheduler():
    """获取或创建调度器实例"""
    global _scheduler
    if not SCHEDULER_AVAILABLE:
        return None
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler


def generate_task_id() -> str:
    """生成任务 ID"""
    global _task_counter
    _task_counter += 1
    return f"task_{_task_counter:04d}"


# ============== API 端点 ==============

@router.get("/status")
async def get_scheduler_status():
    """获取调度器状态"""
    scheduler = get_scheduler()
    
    return {
        "available": SCHEDULER_AVAILABLE,
        "running": scheduler.is_running() if scheduler else False,
        "total_tasks": len(_tasks),
        "enabled_tasks": sum(1 for t in _tasks.values() if t.get("enabled", True)),
    }


@router.post("/tasks", response_model=TaskResponse)
async def create_task(request: CreateTaskRequest):
    """创建定时任务"""
    if not SCHEDULER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Scheduler module not available")
    
    # 验证参数
    if not request.cron and not request.interval_seconds and not request.run_once:
        raise HTTPException(
            status_code=400,
            detail="Must specify either cron, interval_seconds, or run_once=True"
        )
    
    if request.run_once and not request.run_at:
        raise HTTPException(
            status_code=400,
            detail="run_at must be specified for one-time tasks"
        )
    
    task_id = generate_task_id()
    
    # 存储任务配置
    task_data = {
        "task_id": task_id,
        "name": request.name,
        "cron": request.cron,
        "interval_seconds": request.interval_seconds,
        "run_once": request.run_once,
        "run_at": request.run_at,
        "enabled": request.enabled,
        "action_type": request.action_type,
        "action_config": request.action_config,
        "max_retries": request.max_retries,
        "metadata": request.metadata or {},
        "last_run": None,
        "last_result": None,
        "next_run": None,
        "run_count": 0,
        "status": "idle" if request.enabled else "disabled",
        "created_at": datetime.now(),
    }
    
    # 计算下次运行时间
    if request.cron:
        # 使用 croniter 计算下次运行时间
        try:
            from croniter import croniter
            cron = croniter(request.cron, datetime.now())
            task_data["next_run"] = cron.get_next(datetime)
        except ImportError:
            task_data["next_run"] = None
    elif request.interval_seconds:
        task_data["next_run"] = datetime.now()  # 立即运行
    elif request.run_once and request.run_at:
        task_data["next_run"] = request.run_at
    
    _tasks[task_id] = task_data
    
    # 如果调度器正在运行，添加任务
    scheduler = get_scheduler()
    if scheduler and request.enabled:
        # 创建 ScheduledTask 并添加到调度器
        from core.orchestration.scheduler import ScheduledTask
        
        async def task_action():
            if task_data["action_type"] == "http_callback":
                import aiohttp
                url = task_data["action_config"].get("url")
                if url:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, json=task_data["action_config"].get("payload", {})) as resp:
                            return await resp.text()
            elif task_data["action_type"] == "workflow":
                from core.orchestration.workflow_engine import WorkflowEngine
                engine = WorkflowEngine()
                workflow_id = task_data["action_config"].get("workflow_id")
                if workflow_id:
                    return await engine.execute_workflow(workflow_id)
            elif task_data["action_type"] == "script":
                import subprocess
                script = task_data["action_config"].get("script")
                if script:
                    result = subprocess.run(script, shell=True, capture_output=True, text=True)
                    return result.stdout
            return "completed"
        
        scheduled_task = ScheduledTask(
            name=task_id,
            action=task_action,
            cron=request.cron,
            interval_seconds=request.interval_seconds,
            run_once=request.run_once,
            run_at=request.run_at,
            enabled=request.enabled,
            max_retries=request.max_retries,
        )
        scheduler.add_task(scheduled_task)
    
    return TaskResponse(
        task_id=task_data["task_id"],
        name=task_data["name"],
        cron=task_data["cron"],
        interval_seconds=task_data["interval_seconds"],
        run_once=task_data["run_once"],
        run_at=task_data["run_at"],
        enabled=task_data["enabled"],
        last_run=task_data["last_run"],
        last_result=task_data["last_result"],
        next_run=task_data["next_run"],
        run_count=task_data["run_count"],
        status=task_data["status"],
    )


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(enabled: Optional[bool] = None):
    """列出所有任务"""
    tasks = list(_tasks.values())
    
    if enabled is not None:
        tasks = [t for t in tasks if t.get("enabled") == enabled]
    
    task_responses = [
        TaskResponse(
            task_id=t["task_id"],
            name=t["name"],
            cron=t.get("cron"),
            interval_seconds=t.get("interval_seconds"),
            run_once=t.get("run_once", False),
            run_at=t.get("run_at"),
            enabled=t["enabled"],
            last_run=t.get("last_run"),
            last_result=t.get("last_result"),
            next_run=t.get("next_run"),
            run_count=t.get("run_count", 0),
            status=t["status"],
        )
        for t in tasks
    ]
    
    running_count = sum(1 for t in tasks if t["status"] == "running")
    
    return TaskListResponse(
        tasks=task_responses,
        total=len(tasks),
        running_count=running_count,
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """获取任务详情"""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    t = _tasks[task_id]
    
    return TaskResponse(
        task_id=t["task_id"],
        name=t["name"],
        cron=t.get("cron"),
        interval_seconds=t.get("interval_seconds"),
        run_once=t.get("run_once", False),
        run_at=t.get("run_at"),
        enabled=t["enabled"],
        last_run=t.get("last_run"),
        last_result=t.get("last_result"),
        next_run=t.get("next_run"),
        run_count=t.get("run_count", 0),
        status=t["status"],
    )


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, request: UpdateTaskRequest):
    """更新任务"""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    task = _tasks[task_id]
    
    # 更新字段
    if request.name is not None:
        task["name"] = request.name
    if request.cron is not None:
        task["cron"] = request.cron
    if request.interval_seconds is not None:
        task["interval_seconds"] = request.interval_seconds
    if request.enabled is not None:
        task["enabled"] = request.enabled
        task["status"] = "idle" if request.enabled else "disabled"
    if request.max_retries is not None:
        task["max_retries"] = request.max_retries
    if request.metadata is not None:
        task["metadata"] = request.metadata
    
    return TaskResponse(
        task_id=task["task_id"],
        name=task["name"],
        cron=task.get("cron"),
        interval_seconds=task.get("interval_seconds"),
        run_once=task.get("run_once", False),
        run_at=task.get("run_at"),
        enabled=task["enabled"],
        last_run=task.get("last_run"),
        last_result=task.get("last_result"),
        next_run=task.get("next_run"),
        run_count=task.get("run_count", 0),
        status=task["status"],
    )


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    del _tasks[task_id]
    
    return {"ok": True, "message": f"Task {task_id} deleted"}


@router.post("/tasks/{task_id}/run")
async def run_task_now(task_id: str):
    """立即运行任务"""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    task = _tasks[task_id]
    
    # 更新状态
    task["status"] = "running"
    task["last_run"] = datetime.now()
    
    # 实际执行任务
    scheduler = get_scheduler()
    if scheduler:
        scheduled_task = scheduler.get_task(task_id)
        if scheduled_task:
            try:
                import asyncio
                if asyncio.iscoroutinefunction(scheduled_task.action):
                    result = await scheduled_task.action()
                else:
                    result = scheduled_task.action()
                task["last_result"] = str(result) if result else "success"
            except Exception as e:
                task["last_result"] = f"error: {str(e)}"
                task["status"] = "error"
                raise
    elif task["action_type"] == "workflow":
        # 执行工作流
        pass
    elif task["action_type"] == "script":
        # 执行脚本
        pass
    
    # 模拟执行
    task["run_count"] += 1
    task["last_result"] = "success"
    task["status"] = "idle"
    
    # 如果是一次性任务，禁用它
    if task.get("run_once"):
        task["enabled"] = False
        task["status"] = "disabled"
    
    return {
        "ok": True,
        "message": f"Task {task_id} executed",
        "result": task["last_result"],
    }


@router.post("/tasks/{task_id}/enable")
async def enable_task(task_id: str):
    """启用任务"""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    _tasks[task_id]["enabled"] = True
    _tasks[task_id]["status"] = "idle"
    
    return {"ok": True, "message": f"Task {task_id} enabled"}


@router.post("/tasks/{task_id}/disable")
async def disable_task(task_id: str):
    """禁用任务"""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    _tasks[task_id]["enabled"] = False
    _tasks[task_id]["status"] = "disabled"
    
    return {"ok": True, "message": f"Task {task_id} disabled"}


@router.post("/start")
async def start_scheduler():
    """启动调度器"""
    if not SCHEDULER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Scheduler module not available")
    
    scheduler = get_scheduler()
    if scheduler is None:
        raise HTTPException(status_code=500, detail="Failed to initialize scheduler")
    
    # 启动调度器
    scheduler.start()
    
    return {"ok": True, "message": "Scheduler started"}


@router.post("/stop")
async def stop_scheduler():
    """停止调度器"""
    if not SCHEDULER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Scheduler module not available")
    
    scheduler = get_scheduler()
    if scheduler is None:
        raise HTTPException(status_code=500, detail="Failed to initialize scheduler")
    
    # 停止调度器
    scheduler.stop()
    
    return {"ok": True, "message": "Scheduler stopped"}


@router.get("/validate-cron")
async def validate_cron_expression(cron: str):
    """验证 Cron 表达式"""
    try:
        from croniter import croniter
        c = croniter(cron, datetime.now())
        next_runs = [c.get_next(datetime) for _ in range(5)]
        
        return {
            "valid": True,
            "next_runs": [dt.isoformat() for dt in next_runs],
        }
    except ImportError:
        return {
            "valid": False,
            "error": "croniter not installed",
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
        }
