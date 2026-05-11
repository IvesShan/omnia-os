"""Vector Store API Routes.

Provides semantic search capabilities using ChromaDB.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

router = APIRouter(prefix="/api/vector", tags=["Vector Store"])

# Lazy import to avoid startup overhead
_vector_store = None


def _get_vector_store():
    """Get or create VectorStore instance."""
    global _vector_store
    if _vector_store is None:
        from core.neural_graph.vector_store import VectorStore
        _vector_store = VectorStore()
    return _vector_store


# Request/Response Models
class AddMemoryRequest(BaseModel):
    """Request to add a memory to vector store."""
    memory_id: str = Field(..., description="Unique identifier for the memory")
    text: str = Field(..., description="Text content to embed")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class SearchRequest(BaseModel):
    """Request to search memories."""
    query: str = Field(..., description="Search query text")
    n_results: int = Field(default=10, ge=1, le=100, description="Number of results")
    filter_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filters")


class SearchResult(BaseModel):
    """A single search result."""
    memory_id: str
    text: str
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0-1)")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Response from vector search."""
    query: str
    results: List[SearchResult]
    total: int
    elapsed_ms: float


class StatsResponse(BaseModel):
    """Vector store statistics."""
    total_memories: int
    collection_name: str
    embedding_model: str
    embedding_dim: int


# API Endpoints
@router.get("/status")
async def get_status():
    """Get vector store status."""
    try:
        store = _get_vector_store()
        return {
            "status": "ready",
            "collection_name": store.collection_name,
            "embedding_model": "all-MiniLM-L6-v2",
            "embedding_dim": 384
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.post("/add", response_model=Dict[str, Any])
async def add_memory(request: AddMemoryRequest):
    """Add a memory to the vector store."""
    try:
        store = _get_vector_store()
        success = store.add_memory(
            memory_id=request.memory_id,
            text=request.text,
            metadata=request.metadata or {}
        )
        return {
            "success": success,
            "memory_id": request.memory_id,
            "message": "Memory added successfully" if success else "Failed to add memory"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchResponse)
async def search_memories(request: SearchRequest):
    """Search memories using semantic similarity."""
    import time
    start_time = time.time()
    
    try:
        store = _get_vector_store()
        results = store.search(
            query=request.query,
            n_results=request.n_results,
            filter_metadata=request.filter_metadata
        )
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return SearchResponse(
            query=request.query,
            results=[
                SearchResult(
                    memory_id=r.memory_id,
                    text=r.text,
                    score=r.score,
                    metadata=r.metadata
                )
                for r in results
            ],
            total=len(results),
            elapsed_ms=elapsed_ms
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_memories_get(
    q: str = Query(..., description="Search query"),
    n: int = Query(10, ge=1, le=100, description="Number of results")
):
    """Search memories (GET method for convenience)."""
    try:
        store = _get_vector_store()
        results = store.search(query=q, n_results=n)
        
        return {
            "query": q,
            "results": [
                {
                    "memory_id": r.memory_id,
                    "text": r.text,
                    "score": r.score,
                    "metadata": r.metadata
                }
                for r in results
            ],
            "total": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/memory/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a memory from the vector store."""
    try:
        store = _get_vector_store()
        success = store.delete_memory(memory_id)
        return {
            "success": success,
            "memory_id": memory_id,
            "message": "Memory deleted" if success else "Memory not found"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-add")
async def batch_add_memories(memories: List[AddMemoryRequest]):
    """Add multiple memories at once."""
    try:
        store = _get_vector_store()
        results = []
        
        for memory in memories:
            success = store.add_memory(
                memory_id=memory.memory_id,
                text=memory.text,
                metadata=memory.metadata or {}
            )
            results.append({
                "memory_id": memory.memory_id,
                "success": success
            })
        
        successful = sum(1 for r in results if r["success"])
        return {
            "total": len(memories),
            "successful": successful,
            "failed": len(memories) - successful,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get vector store statistics."""
    try:
        store = _get_vector_store()
        count = store.collection.count()
        
        return StatsResponse(
            total_memories=count,
            collection_name=store.collection_name,
            embedding_model="all-MiniLM-L6-v2",
            embedding_dim=384
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_collection():
    """Clear all memories from the collection (dangerous!)."""
    try:
        store = _get_vector_store()
        # Delete and recreate collection
        store.client.delete_collection(store.collection_name)
        store.collection = store.client.get_or_create_collection(
            name=store.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        return {
            "success": True,
            "message": "Collection cleared"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
