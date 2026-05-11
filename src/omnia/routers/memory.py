"""
记忆搜索路由
负责：Memory Palace 搜索、统计
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import sqlite3

from src.omnia.config import settings
from src.omnia.dependencies import get_memory_palace
# 使用 settings.memory_palace_db

router = APIRouter()


class MemorySearchRequest(BaseModel):
    """记忆搜索请求"""
    query: str
    layer: str = "all"  # all, facts, habits, timeline
    top_k: int = 20


class MemorySearchResult(BaseModel):
    """记忆搜索结果"""
    layer: str
    id: int
    snippet: str
    score: float
    data: dict


class MemorySearchResponse(BaseModel):
    """记忆搜索响应"""
    results: List[MemorySearchResult]


class MemoryStatsResponse(BaseModel):
    """记忆统计响应"""
    facts: int
    habits: int
    timeline: int
    total: int


def _memory_counts() -> dict:
    """获取记忆统计（直接查询数据库）"""
    counts = {}
    if settings.memory_palace_db.exists():
        with sqlite3.connect(str(settings.memory_palace_db)) as conn:
            cursor = conn.cursor()
            for table in ["facts", "relations", "habits", "timeline", "conversation_logs"]:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    counts[table] = 0
    return counts


@router.post("/memory/search", response_model=MemorySearchResponse)
async def memory_search(req: MemorySearchRequest):
    """
    记忆搜索 - 语义搜索
    
    支持：
    - 多层搜索（facts, habits, timeline）
    - 语义相似度排序
    """
    if not req.query:
        return MemorySearchResponse(results=[])
    
    try:
        # 获取 MemoryPalace 实例
        mp = await get_memory_palace()
        
        # 执行语义搜索
        search_results = mp.search_all_semantic(req.query, top_k=req.top_k)
        
        # 扁平化结果
        results = []
        for layer_name, items in search_results.items():
            for item, score in items:
                # 提取内容（不同表字段名不同）
                content = ""
                if layer_name == "facts":
                    content = str(item.get("value", ""))
                elif layer_name == "habits":
                    content = str(item.get("pattern", ""))
                elif layer_name == "timeline":
                    content = str(item.get("title", "")) + " " + str(item.get("description", ""))
                else:
                    content = str(item.get("content", item.get("value", item.get("pattern", ""))))
                
                # 构建安全项（避免 bytes 类型）
                safe_item = {
                    "id": int(item.get("id", 0)),
                    "content": content[:500],
                    "created_at": str(item.get("created_at", "")),
                }
                
                results.append(MemorySearchResult(
                    layer=layer_name,
                    id=int(item.get("id", 0)),
                    snippet=content[:200],
                    score=float(score) if score else 0.0,
                    data=safe_item
                ))
        
        # 按分数排序并限制数量
        results.sort(key=lambda x: x.score, reverse=True)
        results = results[:req.top_k]
        
        return MemorySearchResponse(results=results)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/stats", response_model=MemoryStatsResponse)
async def memory_stats():
    """
    记忆统计
    返回各层的记忆数量
    """
    try:
        counts = _memory_counts()
        
        return MemoryStatsResponse(
            facts=counts.get("facts", 0),
            habits=counts.get("habits", 0),
            timeline=counts.get("timeline", 0),
            total=counts.get("facts", 0) + counts.get("habits", 0) + counts.get("timeline", 0)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/facts")
async def list_facts(limit: int = 20, offset: int = 0):
    """列出事实记忆"""
    try:
        mp = await get_memory_palace()
        facts = mp.recall_facts(limit=limit)
        
        return {
            "facts": [
                {
                    "id": f.get("id"),
                    "key": f.get("key"),
                    "value": f.get("value"),
                    "created_at": str(f.get("created_at", ""))
                }
                for f in facts
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/habits")
async def list_habits(limit: int = 20, offset: int = 0):
    """列出习惯记忆"""
    try:
        mp = await get_memory_palace()
        habits = mp.recall_habits(limit=limit)
        
        return {
            "habits": [
                {
                    "id": h.get("id"),
                    "pattern": h.get("pattern"),
                    "frequency": h.get("frequency"),
                    "last_seen": str(h.get("last_seen", ""))
                }
                for h in habits
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/timeline")
async def list_timeline(limit: int = 20, offset: int = 0):
    """列出时间线记忆"""
    try:
        mp = await get_memory_palace()
        events = mp.recall_timeline(limit=limit)
        
        return {
            "events": [
                {
                    "id": e.get("id"),
                    "title": e.get("title"),
                    "description": e.get("description"),
                    "timestamp": str(e.get("timestamp", ""))
                }
                for e in events
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
