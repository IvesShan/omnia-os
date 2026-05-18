"""
工作流路由
负责：工作流执行、状态查询
集成 core.orchestration.WorkflowEngine
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio
import uuid

# 导入 WorkflowEngine
from src.core.orchestration import WorkflowEngine, WorkflowStep, WorkflowContext

router = APIRouter()

# 全局工作流引擎实例
_workflow_engine: Optional[WorkflowEngine] = None
_active_workflows: Dict[str, Dict[str, Any]] = {}  # 运行中的工作流


def get_workflow_engine() -> WorkflowEngine:
    """获取工作流引擎单例"""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
    return _workflow_engine


class WorkflowRequest(BaseModel):
    name: str
    args: Optional[Dict[str, Any]] = None


class WorkflowStatus(BaseModel):
    active: bool
    current: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None


# 内置工作流定义
async def _workflow_sync_memory(context: WorkflowContext) -> Dict[str, Any]:
    """同步记忆工作流"""
    from src.omnia.dependencies import get_memory_palace
    
    mp = await get_memory_palace()
    stats = {
        "facts": mp.count_facts() if hasattr(mp, 'count_facts') else 0,
        "habits": mp.count_habits() if hasattr(mp, 'count_habits') else 0,
    }
    
    return {"status": "synced", "stats": stats}


async def _workflow_backup(context: WorkflowContext) -> Dict[str, Any]:
    """备份工作流"""
    from pathlib import Path
    import shutil
    from src.omnia.config import settings
    
    backup_dir = settings.omnia_home / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"memory_backup_{timestamp}.db"
    
    if settings.memory_palace_db.exists():
        shutil.copy2(settings.memory_palace_db, backup_file)
        return {"status": "backed_up", "file": str(backup_file)}
    
    return {"status": "no_database", "message": "数据库不存在"}


async def _workflow_health_check(context: WorkflowContext) -> Dict[str, Any]:
    """健康检查工作流"""
    from src.omnia.dependencies import get_memory_palace
    
    results = {
        "memory_palace": "ok",
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        mp = await get_memory_palace()
        results["memory_palace"] = "connected"
    except Exception as e:
        results["memory_palace"] = f"error: {str(e)}"
    
    return results


# 工作流注册表
WORKFLOW_REGISTRY = {
    "sync": {
        "name": "同步记忆",
        "description": "同步和整理记忆数据库",
        "handler": _workflow_sync_memory,
    },
    "backup": {
        "name": "备份项目",
        "description": "备份记忆数据库到本地",
        "handler": _workflow_backup,
    },
    "health-check": {
        "name": "健康检查",
        "description": "检查系统各组件状态",
        "handler": _workflow_health_check,
    },
    # 保留原有的工作流名称（兼容前端）
    "sync-memory": {
        "name": "同步记忆",
        "description": "同步和整理记忆数据库",
        "handler": _workflow_sync_memory,
    },
}


@router.get("/workflow/status")
async def get_workflow_status() -> dict:
    """
    获取工作流引擎状态
    
    前端期望:
    {
        "active": false,
        "current": null
    }
    """
    active_count = len(_active_workflows)
    current_workflow = None
    
    if _active_workflows:
        # 获取第一个活跃的工作流
        wf_id, wf_info = next(iter(_active_workflows.items()))
        current_workflow = {
            "id": wf_id,
            "name": wf_info.get("name"),
            "started_at": wf_info.get("started_at"),
        }
    
    return {
        "active": active_count > 0,
        "current": current_workflow,
        "active_count": active_count,
        "available": list(WORKFLOW_REGISTRY.keys()),
    }


@router.post("/workflow")
async def run_workflow(req: WorkflowRequest, background_tasks: BackgroundTasks) -> dict:
    """
    运行工作流
    
    前端发送: {"name": "sync"}
    前端期望: {"ok": true, "message": "..."}
    """
    name = req.name
    
    if name not in WORKFLOW_REGISTRY:
        return {
            "ok": False,
            "error": f"工作流 '{name}' 不存在",
            "available_workflows": list(WORKFLOW_REGISTRY.keys()),
        }
    
    workflow_info = WORKFLOW_REGISTRY[name]
    workflow_id = str(uuid.uuid4())[:8]
    
    # 记录活跃工作流
    _active_workflows[workflow_id] = {
        "name": name,
        "display_name": workflow_info["name"],
        "started_at": datetime.now().isoformat(),
        "status": "running",
    }
    
    # 创建工作流步骤
    steps = [
        WorkflowStep(
            name=name,
            action=workflow_info["handler"],
            description=workflow_info["description"],
        )
    ]
    
    # 在后台执行工作流
    async def execute_workflow():
        try:
            engine = get_workflow_engine()
            context = WorkflowContext(
                workflow_id=workflow_id,
                inputs=req.args or {},
            )
            
            result = await engine.run(steps, context)
            
            # 更新状态
            _active_workflows[workflow_id]["status"] = "completed" if result.success else "failed"
            _active_workflows[workflow_id]["result"] = result.to_dict() if hasattr(result, 'to_dict') else str(result)
            _active_workflows[workflow_id]["finished_at"] = datetime.now().isoformat()
            
        except Exception as e:
            _active_workflows[workflow_id]["status"] = "failed"
            _active_workflows[workflow_id]["error"] = str(e)
        
        finally:
            # 5分钟后清理
            await asyncio.sleep(300)
            _active_workflows.pop(workflow_id, None)
    
    background_tasks.add_task(execute_workflow)
    
    return {
        "ok": True,
        "message": f"工作流 '{workflow_info['name']}' 已开始执行",
        "workflow_id": workflow_id,
        "workflow": name,
    }


@router.get("/workflow/{workflow_id}")
async def get_workflow_result(workflow_id: str) -> dict:
    """获取工作流执行结果"""
    if workflow_id not in _active_workflows:
        raise HTTPException(status_code=404, detail="工作流不存在或已过期")
    
    return _active_workflows[workflow_id]


@router.get("/workflows")
async def list_workflows() -> dict:
    """列出所有可用工作流"""
    return {
        "workflows": [
            {
                "id": wf_id,
                "name": wf_info["name"],
                "description": wf_info["description"],
            }
            for wf_id, wf_info in WORKFLOW_REGISTRY.items()
        ]
    }
