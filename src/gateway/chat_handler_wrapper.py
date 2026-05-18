"""Gateway Chat Handler Wrapper - 让 Gateway 可以调用现有的 chat_handler。

这个模块将现有的 chat_handler 包装成 Gateway 可以调用的格式。
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from src.core.config import MEMORY_PALACE_DB
from src.core.cognition.prompt_builder import PromptContext, get_prompt_builder
from src.core.neural_graph.context_enhancer import get_graph_enhancer
from src.core.memory_palace.memory_palace_with_graph import MemoryPalace
from src.core.neural_graph.updater import NeuralGraphUpdater
from omnia.chat import _call_model_messages
from src.core.actuator.tool_registry import TOOLS_SCHEMA, check_tool_safety, dispatch_tool
from pathlib import Path


class ChatHandlerWrapper:
    """包装 chat_handler，让 Gateway 可以调用。"""
    
    def __init__(self, api_key: str, provider: str = "kimi", system_prompt: str = ""):
        self.api_key = api_key
        self.provider = provider
        self.system_prompt = system_prompt
        self.memory_db = MEMORY_PALACE_DB
    
    async def handle_message(
        self,
        user_id: str,
        chat_id: str,
        content: str,
        history: Optional[List[Dict]] = None,
        tools_schema: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        处理来自 Gateway 的消息。
        
        Args:
            user_id: 用户 ID
            chat_id: 聊天会话 ID
            content: 消息内容
            history: 历史消息列表
            tools_schema: 工具 schema 列表
            
        Returns:
            处理结果字典
        """
        from omnia.web_server import _store_confirmation
        
        # 初始化 MemoryPalace
        session_id = chat_id or str(uuid.uuid4())[:8]
        try:
            graph_updater = NeuralGraphUpdater()
            mp = MemoryPalace(str(self.memory_db), graph_updater=graph_updater)
            print(f"[Gateway] MemoryPalace initialized with NeuralGraphUpdater hook")
        except Exception as e:
            print(f"[Gateway] Failed to init NeuralGraphUpdater: {e}")
            mp = MemoryPalace(str(self.memory_db))
        
        # 记录用户消息
        try:
            mp.log_conversation(session_id, 0, "user", content)
            print(f"[Gateway] Logged user message, session={session_id}")
        except Exception as e:
            print(f"[Gateway] Failed to log user message: {e}")
        
        # 使用传入的工具 schema，如果没有则使用原生工具
        tools = tools_schema if tools_schema else TOOLS_SCHEMA
        
        MAX_TOOL_ROUNDS = 5
        original_message = content
        
        # ========== 神经图谱上下文增强 ==========
        graph_context_prompt = ""
        try:
            graph_enhancer = get_graph_enhancer()
            graph_context_prompt = graph_enhancer.get_context_prompt(content)
            if graph_context_prompt:
                print(f"[Gateway] Graph context enhanced for: {content[:50]}...")
        except Exception as e:
            print(f"[Gateway] Graph enhancement failed: {e}")
        
        # 构建初始提示
        from src.core.cognition.prompt_builder import PromptContext, get_prompt_builder
        prompt_builder = get_prompt_builder()
        prompt_context = PromptContext(mode="normal")
        dynamic_prompt = prompt_builder.build_for_provider(self.provider, prompt_context)
        
        # 如果有图谱上下文，追加到提示
        if graph_context_prompt:
            dynamic_prompt += f"\n\n{graph_context_prompt}"
        
        # 构建消息列表
        messages = [{"role": "system", "content": dynamic_prompt}]
        
        # 添加历史消息
        if history:
            for msg in history:
                role = msg.get("role", "user")
                msg_content = msg.get("content", "")
                if role in ("user", "assistant"):
                    messages.append({"role": role, "content": msg_content})
        
        # 添加当前消息
        messages.append({"role": "user", "content": content})
        
        # 调用模型
        try:
            response = _call_model_messages(
                messages=messages,
                api_key=self.api_key,
                provider=self.provider,
                tools=tools,
            )
        except Exception as e:
            print(f"[Gateway] Model call failed: {e}")
            return {"error": str(e)}
        
        # 处理工具调用
        tool_rounds = 0
        while tool_rounds < MAX_TOOL_ROUNDS:
            # 检查是否有工具调用
            tool_calls = response.get("tool_calls", [])
            if not tool_calls:
                break
            
            tool_rounds += 1
            print(f"[Gateway] Tool round {tool_rounds}, {len(tool_calls)} tools to call")
            
            # 执行工具
            tool_results = []
            for tool_call in tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("arguments", {})
                tool_id = tool_call.get("id", "")
                
                # 检查工具安全性
                is_safe, reason = check_tool_safety(tool_name, tool_args)
                if not is_safe:
                    tool_results.append({
                        "tool_call_id": tool_id,
                        "status": "error",
                        "content": f"❌ 工具被拒绝: {reason}",
                    })
                    continue
                
                # 执行工具
                try:
                    result = dispatch_tool(tool_name, tool_args)
                    tool_results.append({
                        "tool_call_id": tool_id,
                        "status": "success",
                        "content": result,
                    })
                except Exception as e:
                    tool_results.append({
                        "tool_call_id": tool_id,
                        "status": "error",
                        "content": f"❌ 工具执行失败: {str(e)}",
                    })
            
            # 重建消息列表（FreeCode 策略）
            messages = [{"role": "system", "content": dynamic_prompt}]
            if history:
                for msg in history:
                    role = msg.get("role", "user")
                    msg_content = msg.get("content", "")
                    if role in ("user", "assistant"):
                        messages.append({"role": role, "content": msg_content})
            
            messages.append({"role": "user", "content": content})
            
            # 添加助手消息（包含工具调用）
            messages.append({
                "role": "assistant",
                "content": response.get("content", ""),
                "tool_calls": tool_calls,
            })
            
            # 添加工具结果
            for result in tool_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": result["tool_call_id"],
                    "content": result["content"],
                })
            
            # 再次调用模型
            try:
                response = _call_model_messages(
                    messages=messages,
                    api_key=self.api_key,
                    provider=self.provider,
                    tools=tools,
                )
            except Exception as e:
                print(f"[Gateway] Model call failed in tool round {tool_rounds}: {e}")
                return {"error": str(e)}
        
        # 记录助手消息
        assistant_content = response.get("content", "")
        try:
            mp.log_conversation(session_id, 0, "assistant", assistant_content)
            print(f"[Gateway] Logged assistant message")
        except Exception as e:
            print(f"[Gateway] Failed to log assistant message: {e}")
        
        # 返回结果
        return {
            "content": assistant_content,
            "tool_calls": response.get("tool_calls", []),
            "session_id": session_id,
        }
