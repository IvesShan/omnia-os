#!/usr/bin/env python3
"""
Omnia API Server V2 - 集成向量搜索和自动备份

新增功能：
1. 向量相似度搜索（混合检索）
2. 本地意图分类
3. 自动备份记忆
4. 增强的统计信息
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from core.cognition.chat_integration import OmniaChatEngine
from core.memory.memory_manager_v2 import MemoryManagerV2
from core.embedding.local_embedding import LocalEmbedding, IntentClassifier

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="Omnia API V2",
    description="集成向量搜索和自动备份的 AI 系统 API",
    version="2.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 请求模型 ====================

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    use_vector_search: bool = True  # 是否使用向量搜索


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    metadata: Dict[str, Any]
    intent: Optional[str] = None
    relevant_memories: Optional[List[Dict[str, Any]]] = None


class MemorySearchRequest(BaseModel):
    query: str
    top_k: int = 5
    use_vector: bool = True


class MemorySearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    query: str
    search_type: str
    total: int


# ==================== 全局实例 ====================

engine: Optional[OmniaChatEngine] = None
memory_manager: Optional[MemoryManagerV2] = None
intent_classifier: Optional[IntentClassifier] = None
embedding_engine: Optional[LocalEmbedding] = None

# 自动备份配置
BACKUP_INTERVAL = 3600  # 1小时
last_backup_time: Optional[datetime] = None


# ==================== 启动/关闭 ====================

@app.on_event("startup")
async def startup_event():
    """启动时初始化所有组件"""
    global engine, memory_manager, intent_classifier, embedding_engine
    
    logger.info("🚀 启动 Omnia API Server V2...")
    
    try:
        # 1. 初始化记忆管理器
        logger.info("  📚 初始化记忆管理器...")
        memory_manager = MemoryManagerV2()
        
        # 2. 初始化嵌入引擎
        logger.info("  🧠 初始化嵌入引擎...")
        embedding_engine = LocalEmbedding()
        
        # 3. 初始化意图分类器
        logger.info("  🎯 初始化意图分类器...")
        intent_classifier = IntentClassifier()
        
        # 4. 初始化对话引擎
        logger.info("  💬 初始化对话引擎...")
        engine = OmniaChatEngine(
            max_loops=8,
            halt_threshold=0.85,
            enable_mla=True
        )
        
        # 5. 启动自动备份任务
        logger.info("  💾 启动自动备份...")
        asyncio.create_task(auto_backup_task())
        
        logger.info("✅ 所有组件初始化完成")
        
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理"""
    logger.info("👋 关闭 Omnia API Server V2")
    
    # 最后一次备份
    if memory_manager:
        try:
            backup_path = memory_manager.backup()
            logger.info(f"💾 最终备份完成: {backup_path}")
        except Exception as e:
            logger.error(f"备份失败: {e}")


# ==================== 自动备份任务 ====================

async def auto_backup_task():
    """自动备份任务"""
    global last_backup_time
    
    while True:
        await asyncio.sleep(BACKUP_INTERVAL)
        
        if memory_manager:
            try:
                backup_path = memory_manager.backup()
                last_backup_time = datetime.now()
                logger.info(f"💾 自动备份完成: {backup_path}")
            except Exception as e:
                logger.error(f"自动备份失败: {e}")


# ==================== API 端点 ====================

@app.get("/")
async def root():
    """健康检查"""
    return {
        "status": "ok",
        "name": "Omnia",
        "version": "2.0.0",
        "features": ["vector_search", "auto_backup", "intent_classification"],
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health():
    """详细健康检查"""
    stats = {}
    
    if memory_manager:
        stats = memory_manager.get_stats()
    
    return {
        "status": "healthy",
        "engine": "initialized" if engine else "not_initialized",
        "memory": "initialized" if memory_manager else "not_initialized",
        "embedding": "initialized" if embedding_engine else "not_initialized",
        "intent_classifier": "initialized" if intent_classifier else "not_initialized",
        "stats": stats,
        "last_backup": last_backup_time.isoformat() if last_backup_time else None
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    处理对话请求（增强版）
    
    新增功能：
    - 意图分类
    - 向量相似度检索
    - 混合搜索
    """
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        # 1. 意图分类
        intent = None
        if intent_classifier:
            intent_result = intent_classifier.classify(request.message)
            intent = intent_result[0] if isinstance(intent_result, tuple) else intent_result
        
        # 2. 向量相似度检索
        relevant_memories = []
        if request.use_vector_search and memory_manager:
            # 使用混合搜索（关键词 + 向量）
            results = memory_manager.query_vector(
                query=request.message,
                limit=5,
                # min_similarity=0.3
            )
            
            relevant_memories = [
                {
                    "content": r.get("entry", {}).get("value", r.get("key", "")),
                    "layer": r.get("layer", "unknown"),
                    "relevance": r.get("relevance", 0.0),
                    "source": r.get("source", "unknown")
                }
                for r in results
            ]
        
        # 3. 处理消息
        result = await engine.process_message(
            user_message=request.message,
            conversation_history=[],
            metadata={
                **(request.context or {}),
                "intent": intent,
                "relevant_memories_count": len(relevant_memories)
            }
        )
        
        # 4. 存储到记忆
        if memory_manager:
            memory_manager.add_memory(
                content=f"User: {request.message}",
                role="user",
                metadata={"intent": intent}
            )
            memory_manager.add_memory(
                content=f"Assistant: {result['response']}",
                role="assistant",
                metadata={"intent": intent}
            )
        
        return ChatResponse(
            response=result["response"],
            conversation_id=request.conversation_id or datetime.now().isoformat(),
            metadata=result["metadata"],
            intent=intent,
            relevant_memories=relevant_memories if relevant_memories else None
        )
        
    except Exception as e:
        logger.error(f"处理消息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/search", response_model=MemorySearchResponse)
async def search_memory(request: MemorySearchRequest):
    """
    记忆搜索（支持向量搜索）
    
    - use_vector=True: 混合搜索（关键词 + 向量）
    - use_vector=False: 仅关键词搜索
    """
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    
    try:
        if request.use_vector:
            # 混合搜索
            results = memory_manager.query_vector(
                query=request.query,
                limit=request.top_k,
                # min_similarity=0.2
            )
            search_type = "hybrid"
        else:
            # 关键词搜索
            results = memory_manager.query(
                query=request.query,
                limit=request.top_k
            )
            search_type = "keyword"
        
        return MemorySearchResponse(
            results=results,
            query=request.query,
            search_type=search_type,
            total=len(results)
        )
        
    except Exception as e:
        logger.error(f"记忆搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def stats():
    """获取统计信息"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    result = {
        "engine": engine.get_stats(),
        "memory": memory_manager.get_stats() if memory_manager else {},
        "last_backup": last_backup_time.isoformat() if last_backup_time else None
    }
    
    return result


@app.post("/memory/backup")
async def manual_backup():
    """手动触发备份"""
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    
    try:
        backup_path = memory_manager.backup()
        global last_backup_time
        last_backup_time = datetime.now()
        
        return {
            "status": "success",
            "backup_path": backup_path,
            "timestamp": last_backup_time.isoformat()
        }
        
    except Exception as e:
        logger.error(f"手动备份失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/stats")
async def memory_stats():
    """获取记忆统计"""
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    
    return memory_manager.get_stats()


# ==================== 主入口 ====================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api_server_v2:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
