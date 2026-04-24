"""
Omnia Brain Backend API
融合 VowVector 架构 + porweb 视觉风格
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os

app = FastAPI(
    title="Omnia Brain API",
    description="全息知识图谱系统 API",
    version="0.1.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 数据模型
class KnowledgeNode(BaseModel):
    id: str
    label: str
    position: List[float]
    type: str  # core, module, database, persona
    content: Optional[str] = None
    embedding: Optional[List[float]] = None


class Connection(BaseModel):
    from_id: str
    to_id: str
    relationship: Optional[str] = None


class SearchResult(BaseModel):
    nodes: List[KnowledgeNode]
    score: float


# 演示数据
DEMO_NODES = [
    {"id": "1", "label": "Omnia", "position": [0, 0, 0], "type": "core"},
    {"id": "2", "label": "Memory Palace", "position": [2, 1, 0], "type": "module"},
    {"id": "3", "label": "Gateway", "position": [-2, 1, 0], "type": "module"},
    {"id": "4", "label": "Persona", "position": [0, 2, 1], "type": "module"},
    {"id": "5", "label": "Neo4j", "position": [3, -1, 0], "type": "database"},
    {"id": "6", "label": "Qdrant", "position": [-3, -1, 0], "type": "database"},
    {"id": "7", "label": "无限", "position": [0, -2, -1], "type": "persona"},
]

DEMO_CONNECTIONS = [
    {"from": "1", "to": "2"},
    {"from": "1", "to": "3"},
    {"from": "1", "to": "4"},
    {"from": "2", "to": "5"},
    {"from": "2", "to": "6"},
    {"from": "4", "to": "7"},
]


@app.get("/")
async def root():
    return {
        "message": "Omnia Brain API",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/api/knowledge-graph")
async def get_knowledge_graph():
    """获取知识图谱数据"""
    return {
        "nodes": DEMO_NODES,
        "connections": DEMO_CONNECTIONS
    }


@app.get("/api/nodes/{node_id}")
async def get_node(node_id: str):
    """获取单个节点详情"""
    for node in DEMO_NODES:
        if node["id"] == node_id:
            return node
    raise HTTPException(status_code=404, detail="Node not found")


@app.post("/api/nodes")
async def create_node(node: KnowledgeNode):
    """创建新节点"""
    # TODO: 保存到 Neo4j
    return {"message": "Node created", "node": node}


@app.get("/api/search")
async def search_nodes(query: str, limit: int = 10):
    """搜索知识节点"""
    # TODO: 使用 Qdrant 向量搜索
    results = []
    for node in DEMO_NODES:
        if query.lower() in node["label"].lower():
            results.append({
                "node": node,
                "score": 1.0
            })
    return {"results": results[:limit]}


@app.get("/api/stats")
async def get_stats():
    """获取系统统计信息"""
    return {
        "total_nodes": len(DEMO_NODES),
        "total_connections": len(DEMO_CONNECTIONS),
        "vector_dimension": 768,
        "databases": {
            "neo4j": "connected",
            "qdrant": "connected",
            "ollama": "connected"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
