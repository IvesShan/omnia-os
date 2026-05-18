"""Plan Generator API Routes.

Exposes the Plan Generator cognitive module.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

router = APIRouter(prefix="/api/plan", tags=["Plan Generator"])

# Lazy import
_plan_generator = None


def _get_plan_generator():
    """Get or create PlanGenerator instance."""
    global _plan_generator
    if _plan_generator is None:
        from src.core.cognition.plan_generator import PlanGenerator
        _plan_generator = PlanGenerator()
    return _plan_generator


# Request/Response Models
class AnalyzeRequest(BaseModel):
    """Request to analyze task complexity."""
    task: str = Field(..., description="Task description")


class AnalyzeResponse(BaseModel):
    """Response from complexity analysis."""
    complexity: str
    estimated_steps: int
    requires_planning: bool
    suggested_approach: str
    indicators: Dict[str, int]


class GeneratePlanRequest(BaseModel):
    """Request to generate execution plan."""
    task: str = Field(..., description="Task description")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class PlanStepResponse(BaseModel):
    """A step in the plan."""
    step_id: int
    description: str
    step_type: str
    action: Dict[str, Any]
    dependencies: List[int]
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None


class PlanResponse(BaseModel):
    """Response with execution plan."""
    plan_id: str
    goal: str
    steps: List[PlanStepResponse]
    created_at: str
    current_step: int
    status: str
    progress: Dict[str, Any]
    estimated_time: float


class OptimizeRequest(BaseModel):
    """Request to optimize a plan."""
    plan: Dict[str, Any] = Field(..., description="Plan to optimize")


# API Endpoints
@router.get("/status")
async def get_status():
    """Get plan generator status."""
    return {
        "status": "ready",
        "module": "PlanGenerator",
        "layer": "Cognitive Layer (Layer 4)",
        "features": [
            "task_complexity_analysis",
            "step_decomposition",
            "dependency_management",
            "parallel_optimization"
        ]
    }


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_complexity(request: AnalyzeRequest):
    """Analyze task complexity."""
    try:
        generator = _get_plan_generator()
        result = generator.analyze_complexity(request.task)
        
        return AnalyzeResponse(
            complexity=result["complexity"],
            estimated_steps=result["estimated_steps"],
            requires_planning=result["requires_planning"],
            suggested_approach=result["suggested_approach"],
            indicators=result["indicators"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", response_model=PlanResponse)
async def generate_plan(request: GeneratePlanRequest):
    """Generate an execution plan for a task."""
    try:
        generator = _get_plan_generator()
        plan = await generator.generate_plan(request.task, request.context)
        
        completed, total, percentage = plan.get_progress()
        estimated_time = generator.estimate_execution_time(plan)
        
        return PlanResponse(
            plan_id=plan.plan_id,
            goal=plan.goal,
            steps=[
                PlanStepResponse(
                    step_id=s.step_id,
                    description=s.description,
                    step_type=s.step_type.value,
                    action=s.action,
                    dependencies=s.dependencies,
                    status=s.status.value,
                    result=s.result,
                    error=s.error
                )
                for s in plan.steps
            ],
            created_at=plan.created_at.isoformat(),
            current_step=plan.current_step,
            status=plan.status,
            progress={
                "completed": completed,
                "total": total,
                "percentage": percentage
            },
            estimated_time=estimated_time
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize")
async def optimize_plan(request: OptimizeRequest):
    """Optimize a plan for parallel execution."""
    try:
        from src.core.cognition.plan_generator import ExecutionPlan, PlanStep, StepType, StepStatus
        
        # Reconstruct plan from dict
        steps = [
            PlanStep(
                step_id=s["step_id"],
                description=s["description"],
                step_type=StepType(s["step_type"]),
                action=s["action"],
                dependencies=s.get("dependencies", []),
                status=StepStatus(s.get("status", "pending")),
                result=s.get("result"),
                error=s.get("error")
            )
            for s in request.plan["steps"]
        ]
        
        plan = ExecutionPlan(
            plan_id=request.plan["plan_id"],
            goal=request.plan["goal"],
            steps=steps,
            created_at=datetime.fromisoformat(request.plan["created_at"]),
            current_step=request.plan.get("current_step", 0),
            status=request.plan.get("status", "created")
        )
        
        generator = _get_plan_generator()
        optimized = generator.optimize_plan(plan)
        
        return {
            "success": True,
            "plan": optimized.to_dict(),
            "message": "Plan optimized for parallel execution"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/examples")
async def get_examples():
    """Get example tasks for each complexity level."""
    return {
        "simple": [
            "读取 config.json 文件",
            "显示当前时间",
            "列出当前目录的文件"
        ],
        "medium": [
            "读取文件内容并发送邮件",
            "分析日志文件找出错误",
            "下载图片并保存到本地"
        ],
        "complex": [
            "分析项目代码结构，生成文档，并创建 README",
            "比较两个数据库的表结构差异，并生成迁移脚本",
            "根据用户需求设计并实现一个新功能模块"
        ]
    }
