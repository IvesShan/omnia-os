"""Evolution API — 自进化闭环接口

提供进化状态查询、手动触发、技能反馈等功能。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/evolution", tags=["evolution"])


class TriggerRequest(BaseModel):
    """手动触发进化请求"""
    force: bool = False  # 是否强制触发（忽略冷却时间）


class SkillFeedbackRequest(BaseModel):
    """技能使用反馈"""
    skill_id: str
    success: bool = True


@router.get("/status")
async def evolution_status():
    """获取自进化状态"""
    try:
        from src.core.skill_forge import get_evolution_bridge
        bridge = get_evolution_bridge()
        return bridge.status()
    except Exception as e:
        return {
            "running": False,
            "error": str(e),
        }


@router.post("/trigger")
async def trigger_evolution(request: TriggerRequest):
    """手动触发进化周期"""
    try:
        from src.core.orchestration.event_bus import EventBus
        bus = EventBus.get()
        
        bus.emit("evolution.trigger", {
            "force": request.force,
            "trigger": "manual_api",
        }, source="evolution_api")
        
        return {
            "ok": True,
            "message": "Evolution trigger emitted" + (" (forced)" if request.force else ""),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback")
async def submit_skill_feedback(request: SkillFeedbackRequest):
    """提交技能使用反馈"""
    try:
        from src.core.skill_forge import get_evolution_bridge
        bridge = get_evolution_bridge()
        
        bridge.record_skill_usage(
            skill_id=request.skill_id,
            success=request.success,
        )
        
        return {
            "ok": True,
            "skill_id": request.skill_id,
            "confidence": bridge.get_skill_confidence(request.skill_id),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def evolution_history():
    """获取进化历史"""
    try:
        from src.core.skill_forge import get_evolution_bridge
        bridge = get_evolution_bridge()
        
        return {
            "stats": bridge.stats,
            "feedback_count": len(bridge._feedback),
            "skills": [
                {
                    "skill_id": k,
                    "skill_name": v.skill_name,
                    "usage_count": v.usage_count,
                    "confidence": v.confidence,
                    "created_at": str(v.created_at),
                }
                for k, v in bridge._feedback.items()
            ],
        }
    except Exception as e:
        return {
            "stats": {},
            "error": str(e),
        }
