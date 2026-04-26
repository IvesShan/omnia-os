#!/usr/bin/env python3
"""
Omnia API Server (Optimized) - 对话 API 服务

新增功能：
- Token 管理和监控
- 上下文状态 API
- 自动压缩历史消息
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

# 使用优化版本的引擎
from core.cognition.chat_integration_optimized import OmniaChatEngineOptimized
from core.memory.memory_adapter import MemoryAdapter as MemoryManagerV2
from core.cognition.token_manager import (
    estimate_messages_tokens,
    check_context_overflow,
    get_model_context_window,
    get_token_stats
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="Omnia API (Optimized)",
    description="集成 Token 管理的 AI 系统API",
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


# 请求模型
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = None  # 新增：对话历史
    context: Optional[Dict[str, Any]] = None
    model: Optional[str] = "kimi"  # 新增：模型选择


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    metadata: Dict[str, Any]


class TokenStatusResponse(BaseModel):
    """Token 状态响应"""
    model: str
    context_window: int
    current_tokens: int
    utilization: float
    remaining_tokens: int
    warning: bool
    overflow: bool


class CompressRequest(BaseModel):
    """压缩请求"""
    messages: List[Dict[str, Any]]
    model: Optional[str] = "kimi"
    preserve_recent: Optional[int] = 10


class CompressResponse(BaseModel):
    """压缩响应"""
    compressed_messages: List[Dict[str, Any]]
    original_count: int
    compressed_count: int
    original_tokens: int
    compressed_tokens: int
    tokens_saved: int
    compression_ratio: float


# 全局引擎实例
engine: Optional[OmniaChatEngineOptimized] = None
memory_manager: Optional[MemoryManagerV2] = None

# 会话存储（简单的内存存储，生产环境应使用 Redis 等）
sessions: Dict[str, List[Dict[str, str]]] = {}


@app.on_event("startup")
async def startup_event():
    """启动时初始化引擎"""
    global engine, memory_manager
    
    logger.info("🚀 启动 Omnia API Server (Optimized)...")
    
    # 初始化引擎（使用优化版本）
    engine = OmniaChatEngineOptimized(
        max_loops=8,
        halt_threshold=0.85,
        enable_mla=True,
        model_name="kimi"  # 默认使用 Kimi
    )
    
    # 初始化记忆管理器
    memory_manager = MemoryManagerV2(
        max_memories=10000,
        enable_compression=True
    )
    
    logger.info("✅ 引擎初始化完成（Token 管理已启用）")


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
        "version": "2.0.0",
        "features": ["token_management", "auto_compression", "context_monitoring"],
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health():
    """详细健康检查"""
    return {
        "status": "healthy",
        "engine": "initialized" if engine else "not_initialized",
        "memory": "initialized" if memory_manager else "not_initialized",
        "stats": engine.get_stats() if engine else {},
        "token_stats": engine.get_token_usage() if engine else {}
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    处理对话请求
    
    集成循环推理引擎和 Token 管理：
    - 自动检测上下文溢出
    - 自动压缩历史消息
    - 返回 token 使用信息
    """
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        # 获取或创建会话历史
        session_id = request.conversation_id or datetime.now().isoformat()
        conversation_history = request.conversation_history or sessions.get(session_id, [])
        
        # 处理消息
        result = await engine.process_message(
            user_message=request.message,
            conversation_history=conversation_history,
            metadata=request.context or {}
        )
        
        # 更新会话历史
        conversation_history.append({"role": "user", "content": request.message})
        conversation_history.append({"role": "assistant", "content": result["response"]})
        sessions[session_id] = conversation_history
        
        # 存储到记忆
        if memory_manager:
            memory_manager.add_memory(
                content=f"User: {request.message}",
                role="user"
            )
            memory_manager.add_memory(
                content=f"Assistant: {result['response']}",
                role="assistant"
            )
        
        return ChatResponse(
            response=result["response"],
            conversation_id=session_id,
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
        "token": engine.get_token_usage()
    }


@app.post("/token/check", response_model=TokenStatusResponse)
async def check_token_status(messages: List[Dict[str, Any]], model: str = "kimi"):
    """
    检查 token 状态
    
    Args:
        messages: 消息列表
        model: 模型名称
        
    Returns:
        Token 状态信息
    """
    result = check_context_overflow(messages, model)
    
    return TokenStatusResponse(
        model=result["model"],
        context_window=result["context_window"],
        current_tokens=result["current_tokens"],
        utilization=result["utilization"],
        remaining_tokens=result["max_tokens"] - result["current_tokens"],
        warning=result["warning"],
        overflow=result["overflow"]
    )


@app.post("/token/compress", response_model=CompressResponse)
async def compress_messages(request: CompressRequest):
    """
    压缩消息历史
    
    Args:
        request: 压缩请求
        
    Returns:
        压缩后的消息和统计信息
    """
    from core.cognition.token_manager import smart_compress_history
    
    compressed, stats = smart_compress_history(
        request.messages,
        request.model,
        request.preserve_recent
    )
    
    return CompressResponse(
        compressed_messages=compressed,
        original_count=stats.get("original_count", len(request.messages)),
        compressed_count=len(compressed),
        original_tokens=stats.get("original_tokens", 0),
        compressed_tokens=stats.get("compressed_tokens", 0),
        tokens_saved=stats.get("tokens_saved", 0),
        compression_ratio=stats.get("compression_ratio", 1.0)
    )


@app.get("/models")
async def list_models():
    """列出支持的模型及其上下文窗口"""
    from core.cognition.token_manager import MODEL_CONTEXT_WINDOWS
    
    models = []
    for name, config in MODEL_CONTEXT_WINDOWS.items():
        models.append({
            "name": config.name,
            "context_window": config.context_window,
            "max_output": config.max_output,
            "recommended_utilization": config.recommended_utilization
        })
    
    return {"models": models, "count": len(models)}


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """获取会话历史"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    history = sessions[session_id]
    token_info = check_context_overflow(history, "kimi")
    
    return {
        "session_id": session_id,
        "message_count": len(history),
        "token_info": token_info
    }


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """清空会话历史"""
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "cleared", "session_id": session_id}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


def run_server(host: str = "0.0.0.0", port: int = 5001):
    """启动服务器"""
    import uvicorn
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("OMNIA_PORT", 5001))
    run_server(port=port)
