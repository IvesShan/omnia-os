# Omnia Chat Handler - 融合三家最佳实践
# 核心策略：工具执行后完全重建消息列表
# 新增：神经图谱上下文增强

import json
from core.config import MEMORY_PALACE_DB
import uuid
from typing import Any
import re

def handle_chat(message: str, history: list, api_key: str, provider: str, system_prompt: str, all_tools_schema: list = None) -> dict:
    """
    融合 Hermes + FreeCode + OpenClaw 最佳实践的聊天处理器。
    
    核心策略：
    1. 工具执行后完全重建消息列表（FreeCode）
    2. 工具结果添加明确警告（OpenClaw）
    3. 双系统提示强化禁止（Hermes）
    4. 极简总结提示
    5. 神经图谱上下文增强（NEW）
    """
    from omnia.chat import _call_model_messages
    from core.actuator.tool_registry import TOOLS_SCHEMA, check_tool_safety, dispatch_tool
    from core.cognition.context_compressor import ContextCompressor
    from core.plugin.hooks import HookRegistry, HookType, HookContext, get_hook_registry
    from core.cognition.prompt_builder import PromptBuilder, PromptContext, get_prompt_builder
    from core.neural_graph.context_enhancer import get_graph_enhancer
    from core.memory_palace.memory_palace_with_graph import MemoryPalace
    from core.neural_graph.updater import NeuralGraphUpdater
    from pathlib import Path
    
    import omnia.web_server as ws
    _store_confirmation = ws._store_confirmation
    
    hooks = get_hook_registry()
    prompt_builder = get_prompt_builder()
    
    # 初始化 MemoryPalace（带 Neural Graph Hook）
    session_id = str(uuid.uuid4())[:8]
    memory_db = MEMORY_PALACE_DB
    
    # 初始化 NeuralGraphUpdater 并设置 hook
    try:
        graph_updater = NeuralGraphUpdater()
        mp = MemoryPalace(str(memory_db), graph_updater=graph_updater)
        print(f"[Chat] MemoryPalace initialized with NeuralGraphUpdater hook")
    except Exception as e:
        print(f"[Chat] Failed to init NeuralGraphUpdater, falling back to basic MemoryPalace: {e}")
        mp = MemoryPalace(str(memory_db))
    
    # ========== 触发 ON_MESSAGE Hook ==========
    try:
        on_message_context = HookContext(
            type=HookType.ON_MESSAGE,
            message=message,
            metadata={
                "session_id": session_id,
                "history_length": len(history),
                "provider": provider
            }
        )
        hooks.trigger(HookType.ON_MESSAGE, on_message_context)
        print(f"[Chat] ON_MESSAGE Hook triggered for: {message[:50]}...")
    except Exception as e:
        print(f"[Chat] Failed to trigger ON_MESSAGE hook: {e}")
    
    # 记录用户消息
    try:
        mp.log_conversation(session_id, 0, "user", message)
        print(f"[Chat] Logged user message to conversation_logs, session={session_id}")
    except Exception as e:
        print(f"[Chat] Failed to log user message: {e}")
    
    # 使用传入的工具 schema，如果没有则使用原生工具
    tools_schema = all_tools_schema if all_tools_schema else TOOLS_SCHEMA
    
    MAX_TOOL_ROUNDS = 5
    
    # 保存原始消息
    original_message = message
    
    # ========== 神经图谱上下文增强 ==========
    graph_context_prompt = ""
    try:
        graph_enhancer = get_graph_enhancer()
        graph_context_prompt = graph_enhancer.get_context_prompt(message)
        if graph_context_prompt:
            print(f"[Chat] Graph context enhanced for: {message[:50]}...")
    except Exception as e:
        print(f"[Chat] Graph enhancement failed: {e}")
        graph_context_prompt = ""
    
    # 构建初始提示
    prompt_context = PromptContext(mode="normal")
    dynamic_prompt = prompt_builder.build_for_provider(provider, prompt_context)
    
    # 如果有图谱上下文，追加到系统提示
    if graph_context_prompt:
        dynamic_prompt = dynamic_prompt + "\n" + graph_context_prompt
    
    messages: list[dict] = [{"role": "system", "content": dynamic_prompt}]
    
    # 添加历史
    for h in history:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    
    # 添加当前消息
    messages.append({"role": "user", "content": message})
    
    steps: list[dict] = []
    compressor = ContextCompressor()
    tool_calls_executed = False
    
    for round_num in range(MAX_TOOL_ROUNDS):
        print(f"[Chat] Round {round_num + 1}, messages: {len(messages)}, use_tools: {not tool_calls_executed}")
        
        # 关键修复：如果已经执行过工具，完全重建消息列表（FreeCode 方案）
        if tool_calls_executed:
            print(f"[Chat] REBUILDING messages for summarization (FreeCode strategy)")
            
            # 策略 1: 完全重建，不保留历史
            messages = []
            
            # 策略 2: 极简的系统提示
            messages.append({
                "role": "system",
                "content": f"""你刚刚执行了一些工具操作并获得了结果。

现在你的唯一任务是：
1. 用自然语言总结你发现了什么
2. 回答用户的原始问题：{original_message}

严格禁止：
❌ 输出任何工具调用格式（XML/JSON/函数调用）
❌ 再次调用工具
❌ 提及"工具"、"函数"、"API调用"

正确做法：
✅ 直接回答用户的问题
✅ 像和朋友聊天一样自然
✅ 用自然语言描述你的发现"""
            })
            
            # 策略 3: 格式化的工具结果（OpenClaw 方案）
            formatted_results = []
            for i, step in enumerate(steps, 1):
                formatted_results.append(f"""
[工具结果 {i}]
工具: {step['tool']}
参数: {step['arguments']}
结果: {step['result_summary'][:500]}
[结束]
""")
            
            # 策略 4: 添加明确的问题，包含工具结果
            formatted_results_text = "\n".join(formatted_results)
            messages.append({
                "role": "user",
                "content": f"""{formatted_results_text}

基于以上工具执行结果，请回答：

{original_message}

记住：用自然语言回答，不要输出任何工具调用格式。"""
            })
            
            print(f"[Chat] Rebuilt messages: {len(messages)} (no history)")
        
        # 调用模型
        use_tools = tools_schema if not tool_calls_executed else None
        data = _call_model_messages(api_key, provider, messages, tools=use_tools)
        msg = data["choices"][0]["message"]
        
        # 检查是否调用了工具
        tool_calls = msg.get("tool_calls") or []
        content = msg.get("content", "")
        
        if not tool_calls:
            # 没有工具调用，处理返回文本
            reply = content
            
            # Hook: POST_RESPONSE (自动记忆)
            hook_context = HookContext(
                type=HookType.POST_RESPONSE,
                response=reply,
                metadata={
                    "user_message": message,
                    "assistant_message": reply,
                    "tool_calls_executed": tool_calls_executed,
                    "steps_count": len(steps)
                }
            )
            hooks.trigger(HookType.POST_RESPONSE, hook_context)
            
            # 记录助手回复
            try:
                mp.log_conversation(session_id, 0, "assistant", reply)
                print(f"[Chat] Logged assistant reply to conversation_logs, session={session_id}")
            except Exception as e:
                print(f"[Chat] Failed to log assistant reply: {e}")
            
            return {
                "reply": reply,
                "steps": steps,
                "tool_calls_executed": tool_calls_executed,
                "graph_context_used": bool(graph_context_prompt),
            }
        
        # 有工具调用
        print(f"[Chat] Tool calls: {len(tool_calls)}")
        messages.append(msg)  # 添加 assistant 消息
        
        for tc in tool_calls:
            tool_name = tc.get("function", {}).get("name", "")
            raw_arguments = tc.get("function", {}).get("arguments", "{}")
            
            print(f"[Chat] Tool: {tool_name}, Raw args: {raw_arguments[:100]}")
            
            # 解析参数
            try:
                tool_args = json.loads(raw_arguments)
                print(f"[Chat] Parsed args: {tool_args}")
            except json.JSONDecodeError as e:
                print(f"[Chat] JSON parse error: {e}, raw={raw_arguments}")
                tool_args = {}
            except Exception as e:
                print(f"[Chat] Unexpected error parsing args: {e}")
                tool_args = {}
            
            print(f"[Chat] Tool: {tool_name}, Args: {tool_args}, Args type: {type(tool_args)}")
            
            # 触发 PRE_TOOL_USE Hook
            pre_hook_context = HookContext(
                type=HookType.PRE_TOOL_USE,
                tool_name=tool_name,
                tool_args=tool_args
            )
            hooks.trigger(HookType.PRE_TOOL_USE, pre_hook_context)
            
            # 验证参数
            print(f"[Chat] Validating args for {tool_name}: {tool_args}")
            validation_error = None
            if tool_name == "read_file" and "path" not in tool_args:
                validation_error = "read_file requires 'path' argument"
            elif tool_name == "list_directory" and "path" not in tool_args:
                validation_error = "list_directory requires 'path' argument"
            elif tool_name == "execute_shell" and "command" not in tool_args:
                validation_error = "execute_shell requires 'command' argument"
            elif tool_name == "write_file" and ("path" not in tool_args or "content" not in tool_args):
                validation_error = "write_file requires 'path' and 'content' arguments"
            elif tool_name == "web_search" and "query" not in tool_args:
                validation_error = "web_search requires 'query' argument"
            
            if validation_error:
                result = {"error": validation_error}
                print(f"[Chat] Validation failed: {validation_error}")
            else:
                # 安全检查
                safety = check_tool_safety(tool_name, tool_args)
                if safety.requires_confirm:
                    cid = uuid.uuid4().hex[:8]
                    _store_confirmation(cid, {
                        "messages": messages.copy(),
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                        "tool_call_id": tc.get("id", "unknown"),
                        "api_key": api_key,
                        "provider": provider,
                        "reason": safety.reason,
                    })
                    return {
                        "needs_confirm": True,
                        "confirm_id": cid,
                        "reason": safety.reason,
                        "tool": tool_name,
                        "arguments": tool_args,
                    }
                
                # 执行工具
                result = dispatch_tool(tool_name, tool_args)

                # 记录工具调用
                try:
                    mp.log_tool_use(
                        session_id=session_id,
                        turn_number=round_num,
                        tool_name=tool_name,
                        arguments=tool_args,
                        result=str(result)[:1000]  # 限制结果长度
                    )
                    print(f"[Chat] Logged tool call: {tool_name}, session={session_id}")
                except Exception as e:
                    print(f"[Chat] Failed to log tool call: {e}")
            
            # 触发 POST_TOOL_USE Hook
            post_hook_context = HookContext(
                type=HookType.POST_TOOL_USE,
                tool_name=tool_name,
                tool_args=tool_args,
                tool_result=result
            )
            hooks.trigger(HookType.POST_TOOL_USE, post_hook_context)
            
            tool_calls_executed = True
            
            # 记录步骤
            steps.append({
                "tool": tool_name,
                "arguments": tool_args,
                "result_summary": str(result)[:200],
            })
            
            # 压缩结果（OpenClaw 方案：添加警告）
            result_str = str(result)
            if len(result_str) > 1000:
                compressed = compressor.compress(result_str, max_tokens=500)
                result_summary = f"[COMPRESSED] {compressed}"
            else:
                result_summary = result_str
            
            # 添加工具结果消息（OpenClaw 方案：明确警告）
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", "unknown"),
                "name": tool_name,
                "content": f"""⚠️ 这是工具执行结果，请勿再次调用工具。

工具: {tool_name}
结果: {result_summary}

请基于此结果回答用户问题，不要再次调用工具。"""
            })
    
    # 达到最大轮数
    return {
        "reply": "抱歉，我尝试了多次但仍未完成任务。请尝试换一种方式提问。",
        "steps": steps,
        "tool_calls_executed": tool_calls_executed,
        "graph_context_used": bool(graph_context_prompt),
    }
