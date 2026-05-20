"""
聊天相关 Pydantic 模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class ChatRequest(BaseModel):
    """聊天请求"""
    message: Optional[str] = Field(None, description="用户消息（简单模式）")
    messages: Optional[List[dict]] = Field(None, description="消息历史（完整模式）")
    history: Optional[List[dict]] = Field(None, description="历史消息（兼容 Flask）")
    provider: Optional[str] = Field(None, description="Provider 名称")
    tools: Optional[List[dict]] = Field(None, description="工具列表")
    stream: bool = Field(False, description="是否流式")
    
    def get_messages(self) -> List[dict]:
        """获取消息列表（兼容多种格式）
        
        注意：返回的是副本，不会修改原始 history
        """
        # 优先使用 messages
        if self.messages:
            return list(self.messages)  # 返回副本
        
        # 兼容 Flask 格式：message + history
        # 创建副本，避免修改原始 history
        messages = list(self.history) if self.history else []
        if self.message:
            messages.append({"role": "user", "content": self.message})
        
        return messages


class ChatResponse(BaseModel):
    """聊天响应"""
    ok: bool = True
    content: Optional[str] = None
    error: Optional[str] = None
    provider: Optional[str] = None
    usage: Optional[dict] = None
    tool_calls: Optional[int] = Field(None, description="工具调用次数")
    rounds: Optional[int] = Field(None, description="执行轮数")


class StreamEvent(BaseModel):
    """流式事件"""
    type: str  # token, tool_call, tool_result, done, error
    content: Optional[str] = None
    name: Optional[str] = None
    arguments: Optional[dict] = None
    message: Optional[str] = None
    full_content: Optional[str] = None
