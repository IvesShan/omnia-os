"""
神经图谱路由
负责：图谱构建、搜索、分析、可视化
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import asyncio

from src.omnia.config import settings
from src.omnia.dependencies import get_neural_graph

router = APIRouter()


class GraphStatsResponse(BaseModel):
    """图谱统计响应"""
    nodes: int
    edges: int
    density: float
    avg_degree: float


class EntityInfo(BaseModel):
    """实体信息"""
    type: str
    name: str
    confidence: float


class IntentResponse(BaseModel):
    """意图识别响应"""
    intent: str
    confidence: float
    entities: List[str]


# ========== Neural Graph API ==========

@router.get("/neural-graph/stats")
async def neural_graph_stats():
    """获取神经图谱统计信息"""
    try:
        graph = await get_neural_graph()
        stats = graph.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/neural-graph/related/{name}")
async def neural_graph_related(name: str):
    """获取相关节点"""
    try:
        graph = await get_neural_graph()
        related = graph.get_related(name)
        return {"name": name, "related": related}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/neural-graph/intent", response_model=IntentResponse)
async def neural_graph_intent(request: dict):
    """识别用户意图"""
    query = (request.get("query") or "").strip()
    
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    try:
        graph = await get_neural_graph()
        intent = graph.recognize_intent(query)
        return intent
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/neural-graph/extract")
async def neural_graph_extract(request: dict):
    """提取文本中的实体"""
    text = (request.get("text") or "").strip()
    use_llm = request.get("use_llm", False)
    
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    try:
        graph = await get_neural_graph()
        entities = graph.extract_entities(text)
        
        return {
            "text": text,
            "entities": [
                {"type": e.type, "name": e.name, "confidence": e.confidence}
                for e in entities
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/neural-graph/build")
async def neural_graph_build(request: dict):
    """从 Memory Palace 构建神经图谱"""
    use_llm = request.get("use_llm", False)
    batch_size = request.get("batch_size", 100)
    
    try:
        from src.core.neural_graph import build_neural_graph
        from src.omnia.services.llm_client import LLMClient
        
        # 获取 API key
        client = LLMClient()
        provider = settings.current_provider or "deepseek"
        api_key = client._load_api_key(provider)
        
        if not api_key:
            raise HTTPException(status_code=400, detail="No API key configured")
        
        # 构建图谱（CPU 密集，使用线程池）
        loop = asyncio.get_event_loop()
        stats = await loop.run_in_executor(
            None,
            lambda: build_neural_graph(api_key=api_key, provider=provider)
        )
        
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )


@router.post("/neural-graph/search")
async def neural_graph_search(request: dict):
    """在图谱中搜索"""
    query = (request.get("query") or "").strip()
    limit = request.get("limit", 10)
    
    if not query:
        return {"nodes": [], "related": []}
    
    try:
        graph = await get_neural_graph()
        
        # 搜索节点
        nodes = graph.search_nodes(query, limit)
        
        # 获取相关节点
        related = []
        if nodes:
            related = graph.get_related(nodes[0]["name"])
        
        return {
            "query": query,
            "nodes": nodes,
            "related": related[:limit]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/neural-graph/export")
async def neural_graph_export(limit: int = Query(100, ge=1, le=1000)):
    """导出图谱数据供前端可视化"""
    try:
        graph = await get_neural_graph()
        data = graph.export_to_json(limit=limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== Graph Visualization API ==========

@router.get("/graph")
async def graph_export(min_weight: float = Query(0.0, ge=0.0)):
    """导出图谱数据用于可视化"""
    try:
        graph = await get_neural_graph()
        data = graph.export_to_json(min_weight=min_weight)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/stats")
async def graph_stats():
    """图谱统计"""
    try:
        graph = await get_neural_graph()
        stats = graph.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/node/{name}")
async def graph_node_detail(name: str):
    """获取节点详情"""
    try:
        graph = await get_neural_graph()
        node = graph.get_node(name)
        
        if not node:
            raise HTTPException(status_code=404, detail=f"Node {name} not found")
        
        return node
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graph/path")
async def graph_find_path(request: dict):
    """查找两个节点之间的最短路径"""
    source = request.get("source")
    target = request.get("target")
    
    if not source or not target:
        raise HTTPException(status_code=400, detail="Source and target are required")
    
    try:
        graph = await get_neural_graph()
        path = graph.find_path(source, target)
        
        return {
            "source": source,
            "target": target,
            "path": path,
            "length": len(path) if path else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graph/paths")
async def graph_find_all_paths(request: dict):
    """查找两个节点之间的所有路径"""
    source = request.get("source")
    target = request.get("target")
    max_depth = request.get("max_depth", 5)
    
    if not source or not target:
        raise HTTPException(status_code=400, detail="Source and target are required")
    
    try:
        graph = await get_neural_graph()
        paths = graph.find_all_paths(source, target, max_depth=max_depth)
        
        return {
            "source": source,
            "target": target,
            "paths": paths,
            "count": len(paths)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/centrality/degree")
async def graph_degree_centrality():
    """计算度中心性"""
    try:
        graph = await get_neural_graph()
        centrality = graph.degree_centrality()
        
        # 排序并返回 top 20
        sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:20]
        
        return {
            "centrality": dict(sorted_nodes)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/centrality/pagerank")
async def graph_pagerank():
    """计算 PageRank"""
    try:
        graph = await get_neural_graph()
        pagerank = graph.pagerank()
        
        # 排序并返回 top 20
        sorted_nodes = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)[:20]
        
        return {
            "pagerank": dict(sorted_nodes)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/centrality/betweenness")
async def graph_betweenness_centrality():
    """计算介数中心性"""
    try:
        graph = await get_neural_graph()
        centrality = graph.betweenness_centrality()
        
        # 排序并返回 top 20
        sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:20]
        
        return {
            "centrality": dict(sorted_nodes)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/communities")
async def graph_find_communities():
    """发现社区结构"""
    try:
        graph = await get_neural_graph()
        communities = graph.find_communities()
        
        return {
            "communities": communities,
            "count": len(communities)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/neighbors/{node_id}")
async def graph_get_neighbors(node_id: str):
    """获取节点的邻居"""
    try:
        graph = await get_neural_graph()
        neighbors = graph.get_neighbors(node_id)
        
        return {
            "node": node_id,
            "neighbors": neighbors
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graph/search")
async def graph_search_nodes(request: dict):
    """搜索节点"""
    query = (request.get("query") or "").strip()
    limit = request.get("limit", 20)
    
    if not query:
        return {"nodes": []}
    
    try:
        graph = await get_neural_graph()
        nodes = graph.search_nodes(query, limit)
        
        return {
            "query": query,
            "nodes": nodes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
