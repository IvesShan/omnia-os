"""AgentSwarm 路由 - 多 Agent 并行执行

提供 Agent 集群编排能力，支持：
- 目标分解为并行子任务
- 多角色 Agent 协作
- 结果聚合与决策
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/swarm", tags=["AgentSwarm"])


# ========== 请求/响应模型 ==========

class DecomposeRequest(BaseModel):
    """目标分解请求"""
    goal: str
    context: str = ""
    max_subtasks: int = 3


class SubTaskModel(BaseModel):
    """子任务模型"""
    role: str
    goal: str
    context: str = ""


class ExecuteRequest(BaseModel):
    """并行执行请求"""
    goal: str
    context: str = ""
    subtasks: Optional[List[SubTaskModel]] = None
    parallel: bool = True


class SubAgentResultModel(BaseModel):
    """子 Agent 结果"""
    role: str
    goal: str
    status: str
    reply: str = ""
    steps: List[Dict[str, Any]] = []
    error: str = ""


class ExecuteResponse(BaseModel):
    """执行响应"""
    goal: str
    status: str
    results: List[SubAgentResultModel]
    synthesis: str = ""
    total_steps: int = 0


# ========== 路由端点 ==========

@router.post("/decompose")
async def decompose_goal(request: DecomposeRequest):
    """
    将高层目标分解为并行子任务
    
    使用 LLM 分析目标，生成 1-3 个可并行执行的子任务，
    每个子任务分配给专业角色（frontend/backend/devops/research）。
    """
    try:
        from src.core.actuator.agent_swarm import AgentSwarm, SubTask
        
        swarm = AgentSwarm()
        subtasks = swarm.decompose(request.goal, request.context or None)
        
        # 限制数量
        if len(subtasks) > request.max_subtasks:
            subtasks = subtasks[:request.max_subtasks]
        
        return {
            "ok": True,
            "goal": request.goal,
            "subtasks": [
                {
                    "role": st.role,
                    "goal": st.goal,
                    "context": st.context
                }
                for st in subtasks
            ],
            "count": len(subtasks)
        }
    except Exception as e:
        logger.error(f"Goal decomposition failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
async def execute_parallel(request: ExecuteRequest):
    """
    并行执行多 Agent 任务
    
    如果未提供子任务，会自动分解目标。
    各 Agent 并行执行，结果聚合后返回。
    """
    try:
        from src.core.actuator.agent_swarm import AgentSwarm, SubTask, SubAgentResult
        
        swarm = AgentSwarm()
        
        # 准备子任务
        subtasks = None
        if request.subtasks:
            subtasks = [
                SubTask(
                    role=st.role,
                    goal=st.goal,
                    context=st.context
                )
                for st in request.subtasks
            ]
        
        # 执行
        results = swarm.execute(
            request.goal,
            context=request.context or None,
            subtasks=subtasks,
            parallel=request.parallel
        )
        
        # 聚合结果
        synthesis = swarm.synthesize(results)
        
        return {
            "ok": True,
            "goal": request.goal,
            "status": "completed",
            "results": [
                {
                    "role": r.role,
                    "goal": r.goal,
                    "status": r.status,
                    "reply": r.reply,
                    "steps": r.steps,
                    "error": r.error
                }
                for r in results
            ],
            "synthesis": synthesis,
            "total_steps": sum(len(r.steps) for r in results)
        }
    except Exception as e:
        logger.error(f"Swarm execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roles")
async def get_available_roles():
    """获取可用的 Agent 角色"""
    return {
        "ok": True,
        "roles": [
            {
                "name": "frontend",
                "description": "UI/UX 专家，处理 HTML/CSS/JavaScript/SVG",
                "tools": ["read_file", "write_file", "execute_shell"]
            },
            {
                "name": "backend",
                "description": "Python/API 专家，处理后端逻辑和数据库",
                "tools": ["read_file", "write_file", "execute_shell"]
            },
            {
                "name": "devops",
                "description": "部署和自动化专家，处理系统配置和服务",
                "tools": ["execute_shell", "read_file", "write_file"]
            },
            {
                "name": "research",
                "description": "研究专家，使用 web_search 收集信息",
                "tools": ["web_search", "read_file"]
            },
            {
                "name": "general",
                "description": "通用执行 Agent，处理一般任务",
                "tools": ["read_file", "write_file", "execute_shell", "web_search"]
            }
        ]
    }


@router.post("/quick")
async def quick_execute(goal: str, context: str = ""):
    """
    快速执行 - 一键分解并执行
    
    简化接口，只需提供目标，自动完成分解和执行。
    """
    try:
        from src.core.actuator.agent_swarm import AgentSwarm
        
        swarm = AgentSwarm()
        results = swarm.execute(goal, context=context or None)
        synthesis = swarm.synthesize(results)
        
        return {
            "ok": True,
            "goal": goal,
            "synthesis": synthesis,
            "agent_count": len(results),
            "status": "completed"
        }
    except Exception as e:
        logger.error(f"Quick execute failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
