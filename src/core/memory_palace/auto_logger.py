"""Auto Logger — Automatic conversation and tool logging for Omnia.

Hooks into the chat and tool execution pipeline to log everything to Memory Palace.
Also extracts entities and relations for neural graph in real-time.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from core.memory_palace import MemoryPalace


class AutoLogger:
    """Automatic logger that records all conversations and tool uses.
    
    Now with real-time neural graph extraction!
    """

    def __init__(self, memory_palace: Optional[MemoryPalace] = None):
        self.memory = memory_palace or MemoryPalace()
        self.memory.initialize()  # Ensure tables exist
        
        # Current session
        self.session_id: str = self._generate_session_id()
        self.turn_number: int = 0
        
        # Neural graph processor (lazy load)
        self._graph_processor = None
        
        # 缓存上一条消息用于配对处理
        self._last_user_message: Optional[str] = None
        
    def _get_graph_processor(self):
        """Lazy load graph processor."""
        if self._graph_processor is None:
            from core.neural_graph.conversation_processor import ConversationProcessor
            self._graph_processor = ConversationProcessor()
        return self._graph_processor

    def _generate_session_id(self) -> str:
        """Generate a unique session ID based on date and UUID."""
        date_str = datetime.now().strftime("%Y%m%d")
        unique_id = uuid.uuid4().hex[:8]
        return f"{date_str}_{unique_id}"

    def new_session(self) -> str:
        """Start a new conversation session."""
        self.session_id = self._generate_session_id()
        self.turn_number = 0
        self._last_user_message = None
        return self.session_id

    def log_user_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Log a user message."""
        self.turn_number += 1
        self._last_user_message = content  # 缓存用户消息
        
        return self.memory.log_conversation(
            session_id=self.session_id,
            turn_number=self.turn_number,
            role="user",
            content=content,
            metadata=metadata,
        )

    def log_assistant_message(
        self, 
        content: str, 
        persona: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Log an assistant message and extract entities/relations for neural graph."""
        result = self.memory.log_conversation(
            session_id=self.session_id,
            turn_number=self.turn_number,
            role="assistant",
            content=content,
            persona=persona,
            metadata=metadata,
        )
        
        # 🧠 实时处理：提取实体和关系
        if self._last_user_message:
            try:
                processor = self._get_graph_processor()
                extraction = processor.process_single_turn(
                    user_message=self._last_user_message,
                    assistant_message=content,
                    session_id=self.session_id,
                    use_llm=False,  # 实时处理不用 LLM，太快了
                )
                
                # 记录提取结果（可选）
                if extraction['nodes_added'] > 0 or extraction['edges_added'] > 0:
                    print(f"[AutoLogger] 🧠 提取: {extraction['nodes_added']} 节点, {extraction['edges_added']} 边")
                    
            except (ValueError) as e:
                # 不影响主流程
                print(f"[AutoLogger] ⚠️ 神经图谱提取失败: {e}")
        
        return result

    def log_tool_invocation(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> int:
        """Log a tool invocation."""
        return self.memory.log_tool_use(
            session_id=self.session_id,
            turn_number=self.turn_number,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
        )

    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the current session."""
        conversations = self.memory.get_conversation_session(self.session_id)
        tool_logs = self.memory.recall_tool_logs(session_id=self.session_id)
        
        return {
            "session_id": self.session_id,
            "turns": len(conversations),
            "tool_invocations": len(tool_logs),
            "conversation_preview": [
                {"role": c["role"], "content": c["content"][:100] + "..."}
                for c in conversations[:5]
            ],
        }


# Singleton instance
_auto_logger: Optional[AutoLogger] = None


def get_auto_logger() -> AutoLogger:
    """Get the singleton AutoLogger instance."""
    global _auto_logger
    if _auto_logger is None:
        _auto_logger = AutoLogger()
    return _auto_logger


# Convenience functions for hooks
def log_user_message(content: str, metadata: Optional[Dict[str, Any]] = None) -> int:
    """Log a user message."""
    return get_auto_logger().log_user_message(content, metadata)


def log_assistant_message(
    content: str, 
    persona: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """Log an assistant message."""
    return get_auto_logger().log_assistant_message(content, persona, metadata)


def log_tool_invocation(
    tool_name: str,
    arguments: Dict[str, Any],
    result: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    duration_ms: Optional[int] = None,
) -> int:
    """Log a tool invocation."""
    return get_auto_logger().log_tool_invocation(
        tool_name, arguments, result, success, error_message, duration_ms
    )


def new_session() -> str:
    """Start a new conversation session."""
    return get_auto_logger().new_session()
