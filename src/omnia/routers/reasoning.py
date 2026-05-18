"""
Reasoning Engine API Routes
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime

from src.core.cognition.reasoning_engine import (
    get_reasoning_engine,
    ReasoningType,
    ReasoningStatus
)

router = APIRouter(prefix="/api/reasoning", tags=["reasoning"])


# Request/Response Models
class ReasonRequest(BaseModel):
    query: str = Field(..., description="推理问题")
    reasoning_type: str = Field("deductive", description="推理类型: deductive, inductive, abductive, analogical, causal")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")


class CompareAlternativesRequest(BaseModel):
    query: str = Field(..., description="比较问题")
    alternatives: List[str] = Field(..., description="备选方案列表")


class ReasoningResponse(BaseModel):
    chain_id: str
    query: str
    reasoning_type: str
    status: str
    conclusion: Optional[str] = None
    confidence: Optional[float] = None
    premises_count: int
    created_at: str


class ChainDetailResponse(BaseModel):
    id: str
    query: str
    reasoning_type: str
    status: str
    premises: List[Dict[str, Any]]
    conclusions: List[Dict[str, Any]]
    final_conclusion: Optional[Dict[str, Any]]
    created_at: str
    completed_at: Optional[str]


# Routes
@router.post("/reason", response_model=ReasoningResponse)
async def execute_reasoning(request: ReasonRequest):
    """执行推理"""
    try:
        engine = get_reasoning_engine()
        
        # 解析推理类型
        reasoning_type_map = {
            "deductive": ReasoningType.DEDUCTIVE,
            "inductive": ReasoningType.INDUCTIVE,
            "abductive": ReasoningType.ABDUCTIVE,
            "analogical": ReasoningType.ANALOGICAL,
            "causal": ReasoningType.CAUSAL
        }
        
        reasoning_type = reasoning_type_map.get(
            request.reasoning_type.lower(),
            ReasoningType.DEDUCTIVE
        )
        
        chain = await engine.reason(
            query=request.query,
            reasoning_type=reasoning_type,
            context=request.context
        )
        
        return ReasoningResponse(
            chain_id=chain.id,
            query=chain.query,
            reasoning_type=chain.reasoning_type.value,
            status=chain.status.value,
            conclusion=chain.final_conclusion.content if chain.final_conclusion else None,
            confidence=chain.final_conclusion.confidence if chain.final_conclusion else None,
            premises_count=len(chain.premises),
            created_at=chain.created_at.isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare", response_model=Dict[str, float])
async def compare_alternatives(request: CompareAlternativesRequest):
    """比较备选方案"""
    try:
        engine = get_reasoning_engine()
        results = await engine.compare_alternatives(
            query=request.query,
            alternatives=request.alternatives
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chain/{chain_id}", response_model=ChainDetailResponse)
async def get_chain_detail(chain_id: str):
    """获取推理链详情"""
    engine = get_reasoning_engine()
    chain = engine.get_chain(chain_id)
    
    if not chain:
        raise HTTPException(status_code=404, detail="推理链不存在")
    
    return ChainDetailResponse(
        id=chain.id,
        query=chain.query,
        reasoning_type=chain.reasoning_type.value,
        status=chain.status.value,
        premises=[
            {
                "id": p.id,
                "content": p.content,
                "confidence": p.confidence,
                "source": p.source
            }
            for p in chain.premises
        ],
        conclusions=[
            {
                "id": c.id,
                "content": c.content,
                "confidence": c.confidence,
                "steps": c.steps
            }
            for c in chain.conclusions
        ],
        final_conclusion={
            "id": chain.final_conclusion.id,
            "content": chain.final_conclusion.content,
            "confidence": chain.final_conclusion.confidence,
            "steps": chain.final_conclusion.steps
        } if chain.final_conclusion else None,
        created_at=chain.created_at.isoformat(),
        completed_at=chain.completed_at.isoformat() if chain.completed_at else None
    )


@router.get("/chain/{chain_id}/explain")
async def explain_reasoning(chain_id: str):
    """解释推理过程"""
    engine = get_reasoning_engine()
    explanation = await engine.explain_reasoning(chain_id)
    return {"explanation": explanation}


@router.get("/chains")
async def list_chains():
    """列出所有推理链"""
    engine = get_reasoning_engine()
    chains = engine.get_all_chains()
    
    return {
        "total": len(chains),
        "chains": [
            {
                "id": c.id,
                "query": c.query,
                "type": c.reasoning_type.value,
                "status": c.status.value,
                "created_at": c.created_at.isoformat()
            }
            for c in chains
        ]
    }


@router.delete("/chains")
async def clear_chains():
    """清空推理链"""
    engine = get_reasoning_engine()
    engine.clear_chains()
    return {"message": "已清空所有推理链"}


@router.get("/types")
async def get_reasoning_types():
    """获取支持的推理类型"""
    return {
        "types": [
            {
                "value": "deductive",
                "name": "演绎推理",
                "description": "从一般到特殊，根据已知规则推导结论"
            },
            {
                "value": "inductive",
                "name": "归纳推理",
                "description": "从特殊到一般，根据观察总结规律"
            },
            {
                "value": "abductive",
                "name": "溯因推理",
                "description": "根据观察推断最可能的解释"
            },
            {
                "value": "analogical",
                "name": "类比推理",
                "description": "根据相似性推断结论"
            },
            {
                "value": "causal",
                "name": "因果推理",
                "description": "分析因果关系得出结论"
            }
        ]
    }
