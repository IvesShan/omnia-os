"""
反思模块 API
Reflection API

提供自我评估和改进建议接口
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from core.cognition.reflection import (
    ReflectionEngine,
    ReflectionInsight,
    ReflectionType,
    Severity
)

router = APIRouter(prefix="/api/reflection", tags=["reflection"])

# 全局实例
_reflection_engine: Optional[ReflectionEngine] = None


def get_reflection_engine() -> ReflectionEngine:
    """获取反思引擎实例"""
    global _reflection_engine
    if _reflection_engine is None:
        _reflection_engine = ReflectionEngine()
    return _reflection_engine


# ==================== 请求模型 ====================

class RecordToolCallRequest(BaseModel):
    """记录工具调用请求"""
    session_id: str
    success: bool


class RecordErrorRequest(BaseModel):
    """记录错误请求"""
    session_id: str


class ResolveInsightRequest(BaseModel):
    """解决洞察请求"""
    insight_id: str


# ==================== 系统管理 ====================

@router.get("/status")
async def get_status():
    """获取反思系统状态"""
    engine = get_reflection_engine()
    stats = engine.get_stats()
    
    return {
        "status": "active",
        "stats": stats
    }


@router.get("/stats")
async def get_stats():
    """获取系统统计信息"""
    engine = get_reflection_engine()
    return engine.get_stats()


# ==================== 会话追踪 ====================

@router.post("/session/{session_id}/start")
async def start_session_tracking(session_id: str):
    """开始会话追踪"""
    engine = get_reflection_engine()
    engine.start_session_tracking(session_id)
    
    return {
        "status": "success",
        "message": f"已开始追踪会话: {session_id}"
    }


@router.post("/session/{session_id}/end")
async def end_session_tracking(session_id: str):
    """结束会话追踪"""
    engine = get_reflection_engine()
    engine.end_session_tracking(session_id)
    
    return {
        "status": "success",
        "message": f"已结束追踪会话: {session_id}"
    }


@router.post("/session/{session_id}/message")
async def record_message(session_id: str):
    """记录消息"""
    engine = get_reflection_engine()
    engine.record_message(session_id)
    
    return {"status": "success"}


@router.post("/tool-call")
async def record_tool_call(request: RecordToolCallRequest):
    """记录工具调用"""
    engine = get_reflection_engine()
    engine.record_tool_call(request.session_id, request.success)
    
    return {"status": "success"}


@router.post("/error")
async def record_error(request: RecordErrorRequest):
    """记录错误"""
    engine = get_reflection_engine()
    engine.record_error(request.session_id)
    
    return {"status": "success"}


@router.get("/session/{session_id}/metrics")
async def get_session_metrics(session_id: str):
    """获取会话指标"""
    engine = get_reflection_engine()
    
    if session_id not in engine.session_metrics:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return engine.session_metrics[session_id].to_dict()


# ==================== 分析功能 ====================

@router.post("/analyze/quality/{session_id}")
async def analyze_conversation_quality(session_id: str):
    """分析对话质量"""
    engine = get_reflection_engine()
    insight = engine.analyze_conversation_quality(session_id)
    
    if insight is None:
        return {
            "status": "good",
            "message": "对话质量良好，无需改进"
        }
    
    return {
        "status": "needs_improvement",
        "insight": insight.to_dict()
    }


@router.post("/analyze/tools")
async def analyze_tool_usage():
    """分析工具使用模式"""
    engine = get_reflection_engine()
    insight = engine.analyze_tool_usage_patterns()
    
    if insight is None:
        return {
            "status": "good",
            "message": "工具使用效率良好"
        }
    
    return {
        "status": "analyzed",
        "insight": insight.to_dict()
    }


@router.post("/analyze/knowledge-gaps")
async def identify_knowledge_gaps():
    """识别知识缺口"""
    engine = get_reflection_engine()
    gaps = engine.identify_knowledge_gaps()
    
    return {
        "status": "analyzed",
        "gaps_found": len(gaps),
        "gaps": [g.to_dict() for g in gaps]
    }


# ==================== 改进报告 ====================

@router.get("/report")
async def generate_improvement_report():
    """生成改进报告"""
    engine = get_reflection_engine()
    report = engine.generate_improvement_report()
    
    return report


@router.get("/recommendations")
async def get_recommendations(
    limit: int = Query(10, ge=1, le=50, description="返回数量")
):
    """获取改进建议"""
    engine = get_reflection_engine()
    report = engine.generate_improvement_report()
    
    return {
        "recommendations": report["recommendations"][:limit]
    }


# ==================== 洞察管理 ====================

@router.get("/insights")
async def get_recent_insights(
    limit: int = Query(20, ge=1, le=100, description="返回数量")
):
    """获取最近的洞察"""
    engine = get_reflection_engine()
    insights = engine.get_recent_insights(limit)
    
    return {
        "count": len(insights),
        "insights": [i.to_dict() for i in insights]
    }


@router.get("/insights/type/{insight_type}")
async def get_insights_by_type(insight_type: str):
    """按类型获取洞察"""
    engine = get_reflection_engine()
    
    try:
        rtype = ReflectionType(insight_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"无效的洞察类型: {insight_type}"
        )
    
    insights = engine.get_insights_by_type(rtype)
    
    return {
        "type": insight_type,
        "count": len(insights),
        "insights": [i.to_dict() for i in insights]
    }


@router.get("/insights/severity/{severity}")
async def get_insights_by_severity(severity: str):
    """按严重程度获取洞察"""
    engine = get_reflection_engine()
    
    try:
        sev = Severity(severity)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"无效的严重程度: {severity}"
        )
    
    insights = engine.get_insights_by_severity(sev)
    
    return {
        "severity": severity,
        "count": len(insights),
        "insights": [i.to_dict() for i in insights]
    }


@router.post("/insights/resolve")
async def resolve_insight(request: ResolveInsightRequest):
    """标记洞察为已解决"""
    engine = get_reflection_engine()
    success = engine.resolve_insight(request.insight_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"洞察不存在: {request.insight_id}"
        )
    
    return {
        "status": "success",
        "message": f"已解决洞察: {request.insight_id}"
    }


@router.get("/insight/{insight_id}")
async def get_insight(insight_id: str):
    """获取洞察详情"""
    engine = get_reflection_engine()
    
    for insight in engine.insights:
        if insight.id == insight_id:
            return insight.to_dict()
    
    raise HTTPException(status_code=404, detail="洞察不存在")


# ==================== 维护操作 ====================

@router.post("/cleanup")
async def cleanup_old_insights(
    days: int = Query(30, ge=1, le=365, description="保留天数")
):
    """清理旧洞察"""
    engine = get_reflection_engine()
    engine.cleanup_old_insights(days)
    
    return {
        "status": "success",
        "message": f"已清理 {days} 天前的已解决洞察"
    }


# ==================== 类型枚举 ====================

@router.get("/types")
async def get_insight_types():
    """获取所有洞察类型"""
    return {
        "types": [
            {"value": t.value, "name": t.name}
            for t in ReflectionType
        ]
    }


@router.get("/severities")
async def get_severities():
    """获取所有严重程度"""
    return {
        "severities": [
            {"value": s.value, "name": s.name}
            for s in Severity
        ]
    }
