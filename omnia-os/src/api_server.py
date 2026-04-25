#!/usr/bin/env python3
"""
Omnia API Server - 对话 API 服务

提供 REST API 端点，集成循环推理引擎和记忆系统。
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from core.cognition.chat_integration import OmniaChatEngine
from core.memory.memory_manager_v2 import MemoryManagerV2

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="Omnia API",
    description="集成循环推理的 AI 系统API",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求模型
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    metadata: Dict[str, Any]


# 全局引擎实例
engine: Optional[OmniaChatEngine] = None
memory_manager: Optional[MemoryManagerV2] = None


@app.on_event("startup")
async def startup_event():
    """启动时初始化引擎"""
    global engine, memory_manager
    
    logger.info("🚀 启动 Omnia API Server...")
    
    # 初始化引擎
    engine = OmniaChatEngine(
        max_loops=8,
        halt_threshold=0.85,
        enable_mla=True  # 启用 MLA 压缩
    )
    
    # 初始化记忆管理器（修复：移除不支持的参数）
    memory_manager = MemoryManagerV2()
    
    logger.info("✅ 引擎初始化完成")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理"""
    logger.info("👋 关闭 Omnia API Server")


@app.get("/")
async def root():
    """健康检查"""
    return {
        "status": "ok",
        "name": "Omnia",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health():
    """详细健康检查"""
    return {
        "status": "healthy",
        "engine": "initialized" if engine else "not_initialized",
        "memory": "initialized" if memory_manager else "not_initialized",
        "stats": engine.get_stats() if engine else {}
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    处理对话请求
    
    集成循环推理引擎，根据任务复杂度自动调整推理深度。
    """
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        # 处理消息
        result = await engine.process_message(
            user_message=request.message,
            conversation_history=[],
            metadata=request.context or {}
        )
        
        # 存储到记忆
        if memory_manager:
            memory_manager.add_fact(
                key=f"chat_{datetime.now().isoformat()}",
                value={"user": request.message, "assistant": result['response']},
                source="chat"
            )
        
        return ChatResponse(
            response=result["response"],
            conversation_id=request.conversation_id or datetime.now().isoformat(),
            metadata=result["metadata"]
        )
        
    except Exception as e:
        logger.error(f"处理消息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def stats():
    """获取统计信息"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    return {
        "engine": engine.get_stats(),
        "memory": memory_manager.get_stats() if memory_manager else {}
    }


@app.get("/memory/search")
async def search_memory(query: str, layer: str = "facts"):
    """搜索记忆"""
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    
    results = memory_manager.retrieve_relevant(query, layer=layer)
    return {
        "query": query,
        "layer": layer,
        "results": results
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
