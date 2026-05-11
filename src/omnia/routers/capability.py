"""
渐进式能力解锁 API
Progressive Capability API

提供能力管理和进度追踪接口
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from core.capability.progressive import (
    ProgressiveCapabilitySystem,
    Capability,
    CapabilityLevel,
    CapabilityCategory
)

router = APIRouter(prefix="/api/capability", tags=["capability"])

# 全局实例
_capability_system: Optional[ProgressiveCapabilitySystem] = None


def get_capability_system() -> ProgressiveCapabilitySystem:
    """获取能力系统实例"""
    global _capability_system
    if _capability_system is None:
        _capability_system = ProgressiveCapabilitySystem()
    return _capability_system


# ==================== 请求模型 ====================

class RecordUsageRequest(BaseModel):
    """记录使用请求"""
    user_id: str = Field(..., description="用户 ID")
    capability_id: str = Field(..., description="能力 ID")


class UnlockRequest(BaseModel):
    """解锁请求"""
    user_id: str = Field(..., description="用户 ID")
    capability_id: str = Field(..., description="能力 ID")


class CreateCapabilityRequest(BaseModel):
    """创建能力请求"""
    id: str = Field(..., description="能力 ID")
    name: str = Field(..., description="能力名称")
    description: str = Field(..., description="能力描述")
    category: str = Field(..., description="能力类别")
    level: int = Field(..., ge=1, le=10, description="能力等级")
    prerequisites: List[str] = Field(default_factory=list, description="前置能力")
    auto_unlock: bool = Field(True, description="是否自动解锁")
    unlock_conditions: Dict[str, Any] = Field(default_factory=dict, description="解锁条件")


# ==================== 系统管理 ====================

@router.get("/status")
async def get_status():
    """获取能力系统状态"""
    system = get_capability_system()
    stats = system.get_stats()
    
    return {
        "status": "active",
        "stats": stats
    }


@router.get("/stats")
async def get_stats():
    """获取系统统计信息"""
    system = get_capability_system()
    return system.get_stats()


# ==================== 用户进度 ====================

@router.get("/progress/{user_id}")
async def get_progress(user_id: str):
    """获取用户进度"""
    system = get_capability_system()
    return system.get_progress_summary(user_id)


@router.get("/progress/{user_id}/summary")
async def get_progress_summary(user_id: str):
    """获取用户进度摘要"""
    system = get_capability_system()
    return system.get_progress_summary(user_id)


@router.post("/progress/{user_id}/reset")
async def reset_progress(user_id: str):
    """重置用户进度"""
    system = get_capability_system()
    system.reset_progress(user_id)
    
    return {
        "status": "success",
        "message": f"用户 {user_id} 进度已重置"
    }


@router.post("/progress/{user_id}/force-unlock-all")
async def force_unlock_all(user_id: str):
    """强制解锁所有能力（调试用）"""
    system = get_capability_system()
    system.force_unlock_all(user_id)
    
    return {
        "status": "success",
        "message": f"用户 {user_id} 已解锁所有能力"
    }


# ==================== 能力使用 ====================

@router.post("/usage/record")
async def record_usage(request: RecordUsageRequest):
    """记录能力使用"""
    system = get_capability_system()
    system.record_usage(request.user_id, request.capability_id)
    
    return {
        "status": "success",
        "message": f"已记录使用: {request.capability_id}"
    }


@router.get("/usage/{user_id}/top")
async def get_top_used_capabilities(
    user_id: str,
    limit: int = Query(10, ge=1, le=50, description="返回数量")
):
    """获取用户最常用的能力"""
    system = get_capability_system()
    user = system.get_or_create_user(user_id)
    
    # 按使用次数排序
    sorted_usage = sorted(
        user.capability_usage.items(),
        key=lambda x: x[1],
        reverse=True
    )[:limit]
    
    result = []
    for cap_id, count in sorted_usage:
        if cap_id in system.capabilities:
            cap = system.capabilities[cap_id]
            result.append({
                "capability_id": cap_id,
                "name": cap.name,
                "category": cap.category.value,
                "level": cap.level.name,
                "usage_count": count
            })
    
    return {
        "user_id": user_id,
        "top_capabilities": result
    }


# ==================== 能力解锁 ====================

@router.post("/unlock")
async def unlock_capability(request: UnlockRequest):
    """解锁能力"""
    system = get_capability_system()
    success = system.unlock_capability(request.user_id, request.capability_id)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"无法解锁能力: {request.capability_id}"
        )
    
    cap = system.capabilities.get(request.capability_id)
    
    return {
        "status": "success",
        "message": f"已解锁能力: {cap.name if cap else request.capability_id}",
        "capability": cap.to_dict() if cap else None
    }


@router.get("/{user_id}/available")
async def get_available_capabilities(user_id: str):
    """获取用户可用的能力"""
    system = get_capability_system()
    capabilities = system.get_available_capabilities(user_id)
    
    return {
        "user_id": user_id,
        "count": len(capabilities),
        "capabilities": [cap.to_dict() for cap in capabilities]
    }


@router.get("/{user_id}/locked")
async def get_locked_capabilities(user_id: str):
    """获取用户未解锁的能力"""
    system = get_capability_system()
    capabilities = system.get_locked_capabilities(user_id)
    
    return {
        "user_id": user_id,
        "count": len(capabilities),
        "capabilities": [cap.to_dict() for cap in capabilities]
    }


@router.get("/{user_id}/candidates")
async def get_unlock_candidates(user_id: str):
    """获取可以解锁的能力"""
    system = get_capability_system()
    capabilities = system.get_unlock_candidates(user_id)
    
    return {
        "user_id": user_id,
        "count": len(capabilities),
        "capabilities": [cap.to_dict() for cap in capabilities]
    }


# ==================== 能力推荐 ====================

@router.get("/{user_id}/recommendations")
async def get_recommendations(
    user_id: str,
    limit: int = Query(5, ge=1, le=20, description="推荐数量")
):
    """获取能力推荐"""
    system = get_capability_system()
    recommendations = system.get_capability_recommendations(user_id, limit)
    
    return {
        "user_id": user_id,
        "recommendations": recommendations
    }


# ==================== 能力管理 ====================

@router.get("/list")
async def list_all_capabilities():
    """列出所有能力"""
    system = get_capability_system()
    
    capabilities = [
        cap.to_dict() for cap in sorted(
            system.capabilities.values(),
            key=lambda c: (c.level.value, c.category.value, c.name)
        )
    ]
    
    return {
        "count": len(capabilities),
        "capabilities": capabilities
    }


@router.get("/capability/{capability_id}")
async def get_capability(capability_id: str):
    """获取能力详情"""
    system = get_capability_system()
    
    if capability_id not in system.capabilities:
        raise HTTPException(status_code=404, detail="能力不存在")
    
    return system.capabilities[capability_id].to_dict()


@router.post("/capability")
async def create_capability(request: CreateCapabilityRequest):
    """创建自定义能力"""
    system = get_capability_system()
    
    if request.id in system.capabilities:
        raise HTTPException(status_code=400, detail="能力 ID 已存在")
    
    try:
        category = CapabilityCategory(request.category)
        level = CapabilityLevel(request.level)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"无效的类别或等级: {e}")
    
    capability = Capability(
        id=request.id,
        name=request.name,
        description=request.description,
        category=category,
        level=level,
        prerequisites=request.prerequisites,
        auto_unlock=request.auto_unlock,
        unlock_conditions=request.unlock_conditions
    )
    
    system.add_custom_capability(capability)
    
    return {
        "status": "success",
        "message": f"已创建能力: {request.name}",
        "capability": capability.to_dict()
    }


@router.delete("/capability/{capability_id}")
async def delete_capability(capability_id: str):
    """删除能力"""
    system = get_capability_system()
    
    if capability_id not in system.capabilities:
        raise HTTPException(status_code=404, detail="能力不存在")
    
    system.remove_capability(capability_id)
    
    return {
        "status": "success",
        "message": f"已删除能力: {capability_id}"
    }


# ==================== 按类别/等级查询 ====================

@router.get("/category/{category}")
async def get_by_category(category: str):
    """按类别获取能力"""
    system = get_capability_system()
    
    try:
        cat = CapabilityCategory(category)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的类别: {category}")
    
    capabilities = [
        cap.to_dict() for cap in system.capabilities.values()
        if cap.category == cat
    ]
    
    return {
        "category": category,
        "count": len(capabilities),
        "capabilities": capabilities
    }


@router.get("/level/{level}")
async def get_by_level(level: int):
    """按等级获取能力"""
    system = get_capability_system()
    
    if level < 1 or level > 10:
        raise HTTPException(status_code=400, detail="等级必须在 1-10 之间")
    
    cap_level = CapabilityLevel(level)
    capabilities = [
        cap.to_dict() for cap in system.capabilities.values()
        if cap.level == cap_level
    ]
    
    return {
        "level": cap_level.name,
        "level_number": level,
        "count": len(capabilities),
        "capabilities": capabilities
    }


# ==================== 成就系统 ====================

@router.get("/{user_id}/achievements")
async def get_achievements(user_id: str):
    """获取用户成就"""
    system = get_capability_system()
    user = system.get_or_create_user(user_id)
    
    return {
        "user_id": user_id,
        "achievements_count": len(user.achievements),
        "achievements": user.achievements
    }


# ==================== 导出/导入 ====================

@router.get("/{user_id}/export")
async def export_progress(user_id: str):
    """导出用户进度"""
    system = get_capability_system()
    user = system.get_or_create_user(user_id)
    
    return {
        "user_id": user_id,
        "export_date": datetime.now().isoformat(),
        "progress": user.to_dict()
    }


@router.post("/{user_id}/import")
async def import_progress(user_id: str, progress_data: Dict[str, Any]):
    """导入用户进度"""
    system = get_capability_system()
    
    # 验证数据
    if "user_id" not in progress_data:
        raise HTTPException(status_code=400, detail="缺少 user_id")
    
    # 导入进度
    from core.capability.progressive import UserProgress
    user = UserProgress.from_dict(progress_data)
    system.user_progress[user_id] = user
    system._save_progress()
    
    return {
        "status": "success",
        "message": f"已导入用户 {user_id} 的进度"
    }
