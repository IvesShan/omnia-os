from __future__ import annotations
# Omnia Chat Handler V2 - 彻底解决工具调用问题
# 改进：
# 1. 使用统一的 tool_trigger 模块
# 2. 工具执行后保留最近 3 轮对话
# 3. 智能终止检测
# 4. 增强错误恢复

import json
from typing import Any, List, Dict, Optional
import re


def analyze_tool_results(steps: list) -> dict:
    """
    分析工具执行结果，判断是否已获得足够信息。
    
    Returns:
        {
            "sufficient": bool,  # 是否已足够回答问题
            "has_error": bool,   # 是否有错误
            "summary": str,      # 结果摘要
        }
    """
    if not steps:
        return {"sufficient": False, "has_error": False, "summary": "无工具执行"}
    
    has_error = False
    successful_count = 0
    result_types = set()
    
    for step in steps:
        result = step.get("result_summary", "")
        
        # 检查错误
        if "error" in result.lower() or "失败" in result or "exception" in result.lower():
            has_error = True
        else:
            successful_count += 1
        
        # 分析结果类型
        if "read_file" in step.get("tool", ""):
            result_types.add("file_content")
        elif "execute_shell" in step.get("tool", ""):
            result_types.add("command_output")
        elif "list_directory" in step.get("tool", ""):
            result_types.add("directory_listing")
    
    # 判断是否足够
    # 如果有成功的文件读取或命令执行，通常已足够
    sufficient = successful_count > 0 and not has_error
    
    summary = f"执行了 {len(steps)} 个工具，成功 {successful_count} 个"
    if has_error:
        summary += "，有错误"
    
    return {
        "sufficient": sufficient,
        "has_error": has_error,
        "summary": summary,
        "result_types": list(result_types),
    }


def build_context_aware_prompt(
    original_message: str,
    steps: list,
    analysis: dict,
    recent_history: List[dict] = None,
) -> str:
    """
    构建上下文感知的提示。
    根据工具执行情况，生成合适的提示。
    """
    base_prompt = f"原始问题：{original_message}\n\n"
    
    # 添加工具执行摘要
    if steps:
        base_prompt += "## 已执行的工具\n\n"
        for i, step in enumerate(steps, 1):
            tool = step.get("tool", "unknown")
            args = step.get("arguments", {})
            result_preview = step.get("result_summary", "")[:200]
            base_prompt += f"{i}. **{tool}**\n"
            base_prompt += f"   参数: {json.dumps(args, ensure_ascii=False)}\n"
            base_prompt += f"   结果: {result_preview}\n\n"
    
    # 根据分析结果生成指导
    if analysis["has_error"]:
        base_prompt += """## ⚠️ 注意

部分工具执行失败。请：
1. 分析失败原因
2. 如果可以，尝试其他方法
3. 如果无法完成，明确告知用户原因
"""
    elif analysis["sufficient"]:
        base_prompt += """## ✅ 信息已足够

工具已返回足够信息。请：
1. 基于工具结果回答问题
2. 不要编造或臆测
3. 如果结果不完整，明确说明
"""
    else:
        base_prompt += """## 📋 需要更多信息

当前信息可能不足以完整回答问题。请：
1. 评估是否需要继续调用工具
2. 如果需要，调用合适的工具
3. 如果已有足够信息，直接回答
"""
    
    # 添加历史上下文（如果有）
    if recent_history and len(recent_history) > 0:
        base_prompt += "\n## 最近对话\n\n"
        for msg in recent_history[-4:]:  # 最近 2 轮
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:100]
            base_prompt += f"[{role}] {content}...\n"
    
    return base_prompt


def handle_chat(
    message: str,
    history: list,
    api_key: str,
    provider: str,
    system_prompt: str,
    all_tools_schema: list = None
) -> dict:
    """
    改进版聊天处理器。
    
    核心改进：
    1. 使用 tool_trigger 模块统一判断
    2. 工具执行后保留最近 3 轮对话
    3. 智能终止检测
    4. 增强错误恢复
    """
    from omnia.chat import _call_model_messages
    from core.actuator.tool_registry import TOOLS_SCHEMA, check_tool_safety, dispatch_tool
    from core.plugin.hooks import HookRegistry, HookType, HookContext, get_hook_registry
    from core.cognition.prompt_builder import PromptBuilder, PromptContext, get_prompt_builder
    from core.neural_graph.context_enhancer import get_graph_enhancer
    from core.memory_palace.memory_palace_with_graph import MemoryPalace
    from core.neural_graph.updater import NeuralGraphUpdater
    from core.session_manager import get_session_manager, load_recent_conversations, merge_histories
    from core.context_manager import ContextManager, save_current_context
    from omnia.tool_trigger import analyze_message, get_tool_choice_for_provider, get_suggested_tool_prompt
    from omnia.tool_call_validator import validate_tool_execution, build_retry_prompt
    from pathlib import Path

    hooks = get_hook_registry()
    prompt_builder = get_prompt_builder()
    
    # ========== 会话管理 ==========
    session_manager = get_session_manager()
    session_id = session_manager.get_or_create_session()
    
    memory_db = settings.memory_palace_db
    
    try:
        graph_updater = NeuralGraphUpdater()
        mp = MemoryPalace(str(memory_db), graph_updater=graph_updater)
        print(f"[Chat] MemoryPalace initialized with NeuralGraphUpdater hook")
    except Exception as e:
        print(f"[Chat] Failed to init NeuralGraphUpdater: {e}")
        mp = MemoryPalace(str(memory_db))
    
    # ========== 自动加载历史 ==========
    if len(history) < 10:
        print(f"[Chat] Loading history from database...")
        db_history = load_recent_conversations(limit=40, current_message=message, min_similarity=0.3)
        history = merge_histories(history, db_history, max_total=80)
        print(f"[Chat] History merged: {len(history)} messages")
    
    context_manager = ContextManager(settings.omnia_home)
    last_context = context_manager.load_context()
    
    # ========== 触发 Hooks ==========
    try:
        on_message_context = HookContext(
            type=HookType.ON_MESSAGE,
            message=message,
            metadata={
                "session_id": session_id,
                "history_length": len(history),
                "provider": provider,
            }
        )
        hooks.trigger(HookType.ON_MESSAGE, on_message_context)
    except Exception as e:
        print(f"[Chat] Hook error: {e}")
    
    try:
        mp.log_conversation(session_id, 0, "user", message)
    except Exception as e:
        print(f"[Chat] Failed to log: {e}")
    
    tools_schema = all_tools_schema if all_tools_schema else TOOLS_SCHEMA
    MAX_TOOL_ROUNDS = 5
    
    original_message = message
    
    # ========== 神经图谱增强 ==========
    graph_context_prompt = ""
    try:
        graph_enhancer = get_graph_enhancer()
        graph_context_prompt = graph_enhancer.get_context_prompt(message)
    except Exception as e:
        print(f"[Chat] Graph enhancement failed: {e}")
    
    # ========== 构建系统提示 ==========
    prompt_context = PromptContext(mode="normal")
    dynamic_prompt = prompt_builder.build_for_provider(provider, prompt_context)
    
    if last_context:
        context_prompt = f"""

## 上次会话上下文

📅 时间: {last_context.timestamp}
📌 主题: {last_context.topic}
📝 摘要: {last_context.summary}
"""
        if last_context.next_steps:
            context_prompt += f"\n➡️ 下一步: {', '.join(last_context.next_steps[:3])}"
        dynamic_prompt = dynamic_prompt + context_prompt
    
    if graph_context_prompt:
        dynamic_prompt = dynamic_prompt + "\n" + graph_context_prompt
    
    # ========== 工具触发分析 ==========
    last_assistant_msg = ""
    if history and len(history) > 0:
        for h in reversed(history):
            if h.get("role") == "assistant":
                last_assistant_msg = h.get("content", "")
                break
    
    trigger_result = analyze_message(message, last_assistant_msg, history)
    print(f"[Chat] Trigger analysis: type={trigger_result.trigger_type}, confidence={trigger_result.confidence:.2f}")
    
    # 对于不支持 required 的 Provider，添加提示
    tool_hint = ""
    if trigger_result.should_trigger and provider.lower() not in ["kimi", "openai", "anthropic"]:
        tool_hint = get_suggested_tool_prompt(trigger_result)
        if tool_hint:
            dynamic_prompt = dynamic_prompt + "\n" + tool_hint
    
    # ========== 构建消息列表 ==========
    messages: list[dict] = [{"role": "system", "content": dynamic_prompt}]
    
    for h in history:
        if h.get("role") in ("user", "assistant"):
            messages.append({"role": h["role"], "content": h["content"]})
    
    messages.append({"role": "user", "content": message})
    
    print(f"[Chat] Initial messages: {len(messages)}")
    
    steps = []
    tool_calls_executed = False
    recent_history = []  # 保存最近对话
    
    for round_num in range(MAX_TOOL_ROUNDS):
        print(f"\n[Chat] === Round {round_num + 1}/{MAX_TOOL_ROUNDS} ===")
        
        # ========== 改进：工具执行后保留最近 3 轮对话 ==========
        if tool_calls_executed:
            # 保存最近 3 轮（6 条消息）
            recent_history = messages[-7:] if len(messages) >= 7 else messages[1:]  # 排除 system
            
            # 分析工具结果
            analysis = analyze_tool_results(steps)
            print(f"[Chat] Tool analysis: {analysis}")
            
            # 构建上下文感知提示
            context_prompt = build_context_aware_prompt(original_message, steps, analysis, recent_history)
            
            # 重建消息列表（保留系统提示 + 最近对话摘要）
            messages = [{"role": "system", "content": dynamic_prompt}]
            
            # 添加上下文提示
            messages.append({
                "role": "user",
                "content": context_prompt
            })
            
            print(f"[Chat] Rebuilt messages with context: {len(messages)}")
        
        # ========== 调用模型 ==========
        use_tools = tools_schema
        tool_choice = get_tool_choice_for_provider(trigger_result, provider) if use_tools else None
        
        if tool_choice:
            print(f"[Chat] Tool choice: {tool_choice}")
        
        data = _call_model_messages(api_key, provider, messages, tools=use_tools, tool_choice=tool_choice)
        msg = data["choices"][0]["message"]
        
        tool_calls = msg.get("tool_calls") or []
        content = msg.get("content", "")
        
        # ========== 没有工具调用 ==========
        if not tool_calls:
            reply = content
            # ========== 工具调用验证 ==========
            # 检测模型是否虚假声称调用了工具
            validation = validate_tool_execution(
                response=reply,
                tool_calls=[],
                tool_results=[],
                user_message=original_message
            )
            
            if not validation["valid"] and validation["false_claim"]:
                print(f"[Chat] ⚠️ 检测到虚假声称: {validation['reason']}")
                
                # 构建重试提示
                retry_prompt = build_retry_prompt(
                    original_message,
                    reply,
                    validation["reason"]
                )
                
                # 添加重试消息
                messages.append({
                    "role": "user",
                    "content": retry_prompt
                })
                
                # 强制下一轮使用工具
                trigger_result = type('obj', (object,), {
                    'should_trigger': True,
                    'trigger_type': 'forced_retry',
                    'confidence': 1.0,
                    'suggested_tools': []
                })()
                
                # 继续下一轮循环
                continue
            # ========== 验证结束 ==========

            
            # Hook: POST_RESPONSE
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
            
            try:
                mp.log_conversation(session_id, 0, "assistant", reply)
            except Exception as e:
                print(f"[Chat] Failed to log reply: {e}")
            
            # 保存上下文
            try:
                save_current_context(
                    topic=extract_topic(message),
                    summary=summarize_conversation(message, reply),
                    active_project=detect_active_project(message, reply),
                    next_steps=extract_next_steps(reply),
                )
            except Exception as e:
                print(f"[Chat] Failed to save context: {e}")
            
            return {
                "reply": reply,
                "steps": steps,
                "tool_calls_executed": tool_calls_executed,
                "graph_context_used": bool(graph_context_prompt),
                "session_id": session_id,
                "history_loaded": len(history),
                "trigger_analysis": {
                    "type": trigger_result.trigger_type,
                    "confidence": trigger_result.confidence,
                },
            }
        
        # ========== 有工具调用 ==========
        print(f"[Chat] Tool calls: {len(tool_calls)}")
        messages.append(msg)
        
        for tc in tool_calls:
            tool_name = tc.get("function", {}).get("name", "")
            raw_arguments = tc.get("function", {}).get("arguments", "{}")
            
            print(f"[Chat] Tool: {tool_name}, Raw args: {raw_arguments[:100]}")
            
            try:
                tool_args = json.loads(raw_arguments)
            except json.JSONDecodeError as e:
                print(f"[Chat] JSON parse error: {e}")
                tool_args = {}
            
            # 安全检查
            if not check_tool_safety(tool_name, tool_args):
                print(f"[Chat] Tool blocked: {tool_name}")
                messages.append({
                    "role": "tool",
                    "name": tool_name,
                    "content": json.dumps({"error": "Tool blocked by safety policy"})
                })
                continue
            
            # 执行工具
            try:
                result = dispatch_tool(tool_name, tool_args)
                print(f"[Chat] Tool result: {str(result)[:200]}")
                
                steps.append({
                    "tool": tool_name,
                    "arguments": tool_args,
                    "result_summary": str(result)[:500]
                })
                
                tool_calls_executed = True
                
                messages.append({
                    "role": "tool",
                    "name": tool_name,
                    "content": json.dumps(result, ensure_ascii=False)
                })
                
            except Exception as e:
                print(f"[Chat] Tool execution error: {e}")
                import traceback
                traceback.print_exc()
                messages.append({
                    "role": "tool",
                    "name": tool_name,
                    "content": json.dumps({"error": str(e)})
                })
        
        # ========== 智能终止检测 ==========
        if tool_calls_executed and round_num >= 1:
            analysis = analyze_tool_results(steps)
            
            # 如果已经有足够信息且没有错误，下一轮不再强制工具
            if analysis["sufficient"] and not analysis["has_error"]:
                print(f"[Chat] Smart termination: sufficient results detected")
                # 下一轮将不再强制工具调用
                trigger_result = type('obj', (object,), {
                    'should_trigger': False,
                    'trigger_type': 'auto_terminated',
                    'confidence': 0.0,
                    'suggested_tools': []
                })()
    
    # ========== 超过最大轮数 ==========
    reply = "抱歉，工具调用次数超过限制。请尝试简化您的请求。"
    
    try:
        save_current_context(
            topic=extract_topic(message),
            summary="工具调用超限",
            next_steps=["简化请求"],
        )
    except Exception as e:
        print(f"[Chat] Failed to save context: {e}")
    
    return {
        "reply": reply,
        "steps": steps,
        "tool_calls_executed": tool_calls_executed,
        "error": "max_rounds_exceeded",
    }


# ========== 辅助函数 ==========

def extract_topic(message: str) -> str:
    topic = message.strip()[:50]
    if len(message) > 50:
        topic += "..."
    return topic


def summarize_conversation(user_message: str, assistant_reply: str) -> str:
    summary = user_message.strip()[:100]
    if len(user_message) > 100:
        summary += "..."
    return summary


def detect_active_project(user_message: str, assistant_reply: str) -> str:
    keywords = ["Omnia", "喵修匠", "懂机帝", "OpenClaw", "项目"]
    text = user_message + " " + assistant_reply
    for keyword in keywords:
        if keyword in text:
            return keyword
    return None


def extract_next_steps(reply: str) -> list:
    if "下一步" in reply:
        lines = reply.split("\n")
        steps = []
        for line in lines:
            if "下一步" in line or line.strip().startswith("-"):
                steps.append(line.strip())
        return steps[:3]
    return []
