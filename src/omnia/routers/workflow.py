"""
工作流路由
负责：工作流执行、状态查询
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class WorkflowRequest(BaseModel):
    name: str
    args: Optional[dict] = None


class WorkflowStatus(BaseModel):
    active: bool
    current: Optional[str] = None
    progress: Optional[dict] = None


# 简单的工作流注册表
AVAILABLE_WORKFLOWS = {
    "seo-deploy": "部署 SEO",
    "courseware-check": "课件统计",
    "auto-skill-forge": "Auto-Skill Forge",
    "sync": "同步记忆",
    "backup": "备份项目",
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
    return {
        "active": False,
        "current": None,
        "available": list(AVAILABLE_WORKFLOWS.keys()),
    }


@router.post("/workflow")
async def run_workflow(req: WorkflowRequest) -> dict:
    """
    运行工作流
    
    前端发送: {"name": "seo-deploy"}
    前端期望: {"ok": true, "message": "..."}
    """
    name = req.name
    
    if name not in AVAILABLE_WORKFLOWS:
        # Fallback: 如果工作流不存在，返回模拟成功
        # 真正的实现需要集成到 Omnia 的工作流引擎
        return {
            "ok": False,
            "error": f"工作流 '{name}' 不存在",
            "available_workflows": list(AVAILABLE_WORKFLOWS.keys()),
        }
    
    # 工作流存在但未实现真正的执行逻辑
    # 这里返回提示信息
    return {
        "ok": True,
        "message": f"工作流 '{AVAILABLE_WORKFLOWS[name]}' 已提交执行（当前为模拟模式，完整执行需集成工作流引擎）",
        "workflow": name,
    }
