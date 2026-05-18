"""
对话摘要压缩路由
负责：将长对话历史压缩为摘要，保留关键上下文
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import json

from src.omnia.services.llm_client import LLMClient
from src.omnia.dependencies import get_llm_client

router = APIRouter()

# 摘要压缩的系统提示
SUMMARY_SYSTEM_PROMPT = """你是一个对话摘要专家。你的任务是将一段对话历史压缩成简洁的摘要。

**要求：**
1. 保留所有重要信息、决策、结论、任务状态
2. 保留用户的具体需求和偏好
3. 保留技术细节、代码片段、配置信息
4. 保留待办事项和未完成的任务
5. 保持时间顺序
6. 使用简洁的语言，避免冗余

**输出格式：**
- 使用中文
- 按时间顺序整理
- 突出关键信息
- 如果有代码或配置，保留原样"""

SUMMARY_USER_TEMPLATE = """请将以下对话历史压缩成摘要：

{conversation}

---
请输出压缩后的摘要："""


class SummarizeRequest(BaseModel):
    """对话摘要请求"""
    messages: List[dict]  # 对话历史
    max_length: Optional[int] = 500  # 摘要最大长度


class AutoSummarizeRequest(BaseModel):
    """自动摘要压缩请求"""
    messages: List[dict]  # 对话历史


class SummarizeResponse(BaseModel):
    """对话摘要响应"""
    ok: bool
    summary: Optional[str] = None
    error: Optional[str] = None
    token_saved: Optional[int] = None  # 节省的 token 数量
    messages: Optional[List[dict]] = None  # 压缩后的消息


@router.post("/chat/summarize", response_model=SummarizeResponse)
async def summarize_conversation(
    req: SummarizeRequest,
    client: LLMClient = Depends(get_llm_client)
):
    """
    将对话历史压缩成摘要
    
    用途：
    - 当对话历史过长时，调用此接口压缩旧消息
    - 保留关键上下文，减少 token 使用
    """
    if not req.messages:
        return SummarizeResponse(ok=True, summary="", token_saved=0)
    
    # 构建对话文本
    conversation_lines = []
    for msg in req.messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if role == "user":
            conversation_lines.append(f"用户: {content}")
        elif role == "assistant":
            conversation_lines.append(f"助手: {content}")
        elif role == "system":
            conversation_lines.append(f"系统: {content}")
    
    conversation_text = "\n".join(conversation_lines)
    
    # 估算原始 token 数（粗略）
    original_tokens = len(conversation_text) // 2
    
    # 如果对话很短，不需要压缩
    if len(req.messages) <= 5 or original_tokens < 1000:
        return SummarizeResponse(
            ok=True, 
            summary=conversation_text, 
            token_saved=0
        )
    
    try:
        # 使用 LLM 生成摘要
        messages = [
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": SUMMARY_USER_TEMPLATE.format(
                conversation=conversation_text
            )}
        ]
        
        # 调用 LLM
        response = await client.chat(
            messages=messages,
            provider="deepseek"
        )
        
        summary = response.get("content", "")
        
        # 估算压缩后的 token 数
        summary_tokens = len(summary) // 2
        token_saved = original_tokens - summary_tokens
        
        return SummarizeResponse(
            ok=True,
            summary=summary,
            token_saved=max(0, token_saved)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/summarize/auto", response_model=SummarizeResponse)
async def auto_summarize_conversation(
    req: AutoSummarizeRequest,
    client: LLMClient = Depends(get_llm_client)
):
    """
    自动压缩对话历史
    
    用途：
    - 当对话历史超过阈值时，自动压缩旧消息
    - 返回压缩后的消息列表，保留最近的消息
    """
    if not req.messages:
        return SummarizeResponse(ok=True, messages=[], token_saved=0)
    
    # 配置
    COMPRESS_THRESHOLD = 50
    KEEP_RECENT = 20
    
    # 如果消息数量未超过阈值，直接返回
    if len(req.messages) <= COMPRESS_THRESHOLD:
        return SummarizeResponse(ok=True, messages=req.messages, token_saved=0)
    
    # 分离旧消息和新消息
    old_messages = req.messages[:-KEEP_RECENT]
    recent_messages = req.messages[-KEEP_RECENT:]
    
    # 构建旧消息文本
    conversation_lines = []
    for msg in old_messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if role == "user":
            conversation_lines.append(f"用户: {content}")
        elif role == "assistant":
            conversation_lines.append(f"助手: {content}")
        elif role == "system":
            conversation_lines.append(f"系统: {content}")
    
    conversation_text = "\n".join(conversation_lines)
    original_tokens = len(conversation_text) // 2
    
    try:
        # 使用 LLM 生成摘要
        messages = [
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": SUMMARY_USER_TEMPLATE.format(
                conversation=conversation_text
            )}
        ]
        
        # 调用 LLM
        response = await client.chat(
            messages=messages,
            provider="deepseek"
        )
        
        summary = response.get("content", "")
        summary_tokens = len(summary) // 2
        token_saved = original_tokens - summary_tokens
        
        # 构建压缩后的消息列表
        compressed_messages = [
            {"role": "system", "content": f"[对话摘要] {summary}"}
        ] + recent_messages
        
        return SummarizeResponse(
            ok=True,
            messages=compressed_messages,
            token_saved=max(0, token_saved)
        )
    except Exception as e:
        # 压缩失败时返回原消息
        return SummarizeResponse(
            ok=True,
            messages=req.messages,
            token_saved=0
        )


@router.get("/chat/summarize/health")
async def summarize_health():
    """摘要服务健康检查"""
    return {"status": "ok", "service": "summary"}
