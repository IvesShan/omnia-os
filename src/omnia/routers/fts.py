"""
FTS5 全文搜索路由
负责：跨会话消息搜索、BM25 排序
集成 core.memory.fts_search
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from src.omnia.config import settings

router = APIRouter()


class FTSSearchRequest(BaseModel):
    """FTS 搜索请求"""
    query: str
    limit: int = 10
    session_id: Optional[str] = None
    role: Optional[str] = None  # user, assistant, system


class FTSSearchResult(BaseModel):
    """FTS 搜索结果"""
    id: int
    session_id: str
    role: str
    content: str
    timestamp: str
    rank: float
    highlights: List[str]


class FTSSearchResponse(BaseModel):
    """FTS 搜索响应"""
    query: str
    total: int
    results: List[FTSSearchResult]


def _get_fts_client():
    """获取 FTS 客户端"""
    from src.core.memory.fts_search import FTSClient
    return FTSClient(settings.omnia_home / "fts.db")


@router.post("/fts/search", response_model=FTSSearchResponse)
async def fts_search(req: FTSSearchRequest) -> dict:
    """
    全文搜索
    
    使用 FTS5 进行高效全文搜索，支持 BM25 排序
    """
    if not req.query:
        raise HTTPException(status_code=400, detail="搜索关键词不能为空")
    
    try:
        fts = _get_fts_client()
        
        # 执行搜索
        results = fts.search(
            query=req.query,
            limit=req.limit,
            session_id=req.session_id,
            role=req.role,
        )
        
        # 转换结果
        search_results = [
            FTSSearchResult(
                id=r.id,
                session_id=r.session_id,
                role=r.role,
                content=r.content,
                timestamp=r.timestamp.isoformat() if hasattr(r.timestamp, 'isoformat') else str(r.timestamp),
                rank=r.rank,
                highlights=r.highlights,
            )
            for r in results
        ]
        
        return FTSSearchResponse(
            query=req.query,
            total=len(search_results),
            results=search_results,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/fts/search")
async def fts_search_get(
    q: str = Query(..., description="搜索关键词"),
    limit: int = Query(10, ge=1, le=100),
    session_id: Optional[str] = None,
) -> dict:
    """
    全文搜索 (GET 方式)
    
    快速搜索接口，适合简单查询
    """
    req = FTSSearchRequest(query=q, limit=limit, session_id=session_id)
    return await fts_search(req)


@router.post("/fts/index")
async def fts_index_message(
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[dict] = None,
) -> dict:
    """
    索引消息
    
    将消息存入 FTS 索引，供后续搜索
    """
    try:
        fts = _get_fts_client()
        
        from src.core.memory.fts_search import MessageRecord
        
        record = MessageRecord(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata or {},
        )
        
        fts.store_message(record)
        
        return {
            "ok": True,
            "message": "消息已索引",
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"索引失败: {str(e)}")


@router.get("/fts/stats")
async def fts_stats() -> dict:
    """
    FTS 统计信息
    
    返回索引的消息数量、会话数量等
    """
    try:
        fts = _get_fts_client()
        stats = fts.get_stats()
        
        return {
            "ok": True,
            "stats": stats,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@router.delete("/fts/session/{session_id}")
async def fts_delete_session(session_id: str) -> dict:
    """
    删除会话的所有消息索引
    """
    try:
        fts = _get_fts_client()
        deleted = fts.delete_session(session_id)
        
        return {
            "ok": True,
            "deleted_count": deleted,
            "message": f"已删除会话 {session_id} 的 {deleted} 条消息",
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
