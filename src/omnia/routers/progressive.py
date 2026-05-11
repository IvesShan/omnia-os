"""
Progressive Capability API Routes
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime

from core.capability.progressive import (
    get_progressive_capability,
    CapabilityStatus
)

router = APIRouter(prefix="/api/progressive", tags=["progressive"])


# Request/Response Models
class RecordUsageRequest(BaseModel):
    user_id: str = Field(..., description="用户ID")
    capability_id: str = Field(..., description="能力ID")
    success: bool = Field(True, description="是否成功")


class UnlockRequest(BaseModel):
    user_id: str = Field(..., description="用户ID")
    capability_id: str = Field(..., description="能力ID")


class ActivateRequest(BaseModel):
    user_id: str = Field(..., description="用户ID")
    capability_id: str = Field(..., description="能力ID")


# Routes
@router.get("/status")
async def get_system_status():
    """获取系统状态"""
    system = get_progressive_capability()
    return {
        "status": "active",
        "total_capabilities": len(system.capability_registry),
        "users_count": len(system.users)
    }


@router.get("/capabilities")
async def list_all_capabilities():
    """列出所有能力"""
    system = get_progressive_capability()
    
    return {
        "total": len(system.capability_registry),
        "capabilities": [
            {
                "id": cap.id,
                "name": cap.name,
                "description": cap.description,
                "level": cap.level.value,
                "level_name": cap.level.name,
                "dependencies": cap.dependencies,
                "unlock_conditions": cap.unlock_conditions
            }
            for cap in system.capability_registry.values()
        ]
    }


@router.get("/user/{user_id}/stats")
async def get_user_stats(user_id: str):
    """获取用户统计"""
    system = get_progressive_capability()
    stats = system.get_user_stats(user_id)
    return stats


@router.get("/user/{user_id}/capabilities")
async def get_user_capabilities(user_id: str):
    """获取用户能力"""
    system = get_progressive_capability()
    capabilities = system.get_user_capabilities(user_id)
    
    return {
        "user_id": user_id,
        "total": len(capabilities),
        "capabilities": [
            {
                "id": cap.id,
                "name": cap.name,
                "description": cap.description,
                "level": cap.level.value,
                "status": cap.status.value,
                "usage_count": cap.usage_count,
                "success_count": cap.success_count,
                "success_rate": cap.success_count / cap.usage_count if cap.usage_count > 0 else 0,
                "last_used": cap.last_used.isoformat() if cap.last_used else None,
                "unlocked_at": cap.unlocked_at.isoformat() if cap.unlocked_at else None
            }
            for cap in capabilities.values()
        ]
    }


@router.get("/user/{user_id}/available")
async def get_available_capabilities(user_id: str):
    """获取可解锁的能力"""
    system = get_progressive_capability()
    capabilities = system.get_available_capabilities(user_id)
    
    return {
        "user_id": user_id,
        "total": len(capabilities),
        "capabilities": [
            {
                "id": cap.id,
                "name": cap.name,
                "description": cap.description,
                "level": cap.level.value,
                "dependencies": cap.dependencies,
                "unlock_conditions": cap.unlock_conditions
            }
            for cap in capabilities
        ]
    }


@router.get("/user/{user_id}/capability/{capability_id}/progress")
async def get_capability_progress(user_id: str, capability_id: str):
    """获取能力进度"""
    system = get_progressive_capability()
    progress = system.get_capability_progress(user_id, capability_id)
    return progress


@router.post("/unlock")
async def unlock_capability(request: UnlockRequest):
    """解锁能力"""
    system = get_progressive_capability()
    success, message = await system.unlock_capability(
        user_id=request.user_id,
        capability_id=request.capability_id
    )
    
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)


@router.post("/activate")
async def activate_capability(request: ActivateRequest):
    """激活能力"""
    system = get_progressive_capability()
    success, message = await system.activate_capability(
        user_id=request.user_id,
        capability_id=request.capability_id
    )
    
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)


@router.post("/usage")
async def record_usage(request: RecordUsageRequest):
    """记录使用情况"""
    system = get_progressive_capability()
    await system.record_usage(
        user_id=request.user_id,
        capability_id=request.capability_id,
        success=request.success
    )
    
    return {"success": True, "message": "已记录使用情况"}


@router.get("/levels")
async def get_capability_levels():
    """获取能力等级"""
    from core.capability.progressive import CapabilityLevel
    
    return {
        "levels": [
            {
                "value": level.value,
                "name": level.name,
                "description": {
                    1: "新手 - 基础功能",
                    2: "初学者 - 简单工具",
                    3: "中级 - 复杂任务",
                    4: "高级 - 技能创建",
                    5: "专家 - 工作流设计",
                    6: "大师 - 系统优化"
                }.get(level.value, "")
            }
            for level in CapabilityLevel
        ]
    }
