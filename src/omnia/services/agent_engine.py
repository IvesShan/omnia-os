"""
agent_engine_v2.py — Agent 执行引擎（IDE 上下文增强版）

基于原版 agent_engine.py，添加 IDE 上下文自动注入功能
"""

import json
import time
import asyncio
import re
from typing import List, Dict, Any, Optional, AsyncGenerator
from pathlib import Path
from datetime import datetime

from src.omnia.services.tool_registry import tool_registry
from src.omnia.services.safety_gate import check_tool_safety
from src.omnia.services.tool_trigger import (
    analyze_message,
    get_tool_choice_for_provider,
    get_suggested_tool_prompt,
    check_and_run,
    ToolTriggerResult,
)
from src.omnia.services.tool_call_validator import (
    validate_tool_execution,
    build_retry_prompt,
    analyze_tool_results,
)
from src.omnia.services.context_manager import (
    save_current_context,
    load_last_context,
    extract_topic,
    extract_next_steps,
)

from src.omnia.interrupt_manager import check_interrupt
from src.omnia.services.auto_memory import auto_memory
from src.core.plugin.hooks import HookRegistry, HookType, HookContext, get_hook_registry


class AgentEngine:
    """Agent 执行引擎 — 单例"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.max_tool_rounds = 1000
        self.tool_injection_enabled = True
        self.api_tool_providers = {"deepseek", "openai", "kimi", "xiaomi"}
        self._steps: List[Dict] = []

    def _load_ide_context(self) -> Optional[Dict[str, Any]]:
        """加载 VS Code 扩展上报的 IDE 上下文"""
        try:
            from src.omnia.config import settings
            context_file = settings.omnia_home / "ide_context.json"
            if not context_file.exists():
                return None
            data = json.loads(context_file.read_text(encoding="utf-8"))
            # 检查是否在 5 分钟内
            received_at = data.get("received_at", "")
            if received_at:
                last_update = datetime.fromisoformat(received_at)
                elapsed = (datetime.now() - last_update).total_seconds()
                if elapsed > 300:  # 5 分钟
                    return None
            return data
        except Exception:
            return None

    def _build_ide_context_prompt(self) -> str:
        """构建 IDE 上下文提示词"""
        ide_ctx = self._load_ide_context()
        if not ide_ctx:
            return ""

        ide_prompt = "\n\n## 🖥️ 用户 VS Code IDE 环境\n"
        ide_prompt += "（以下信息由 VS Code 扩展实时上报，你可以参考这些信息来更好地帮助用户）\n\n"

        file_name = ide_ctx.get("file")
        if file_name:
            ide_prompt += f"- **当前文件**: {Path(file_name).name}\n"
            ide_prompt += f"- **文件路径**: {file_name}\n"

        language = ide_ctx.get("language")
        if language:
            ide_prompt += f"- **编程语言**: {language}\n"

        line = ide_ctx.get("line")
        column = ide_ctx.get("column")
        if line is not None:
            ide_prompt += f"- **光标位置**: 第 {line} 行"
            if column is not None:
                ide_prompt += f", 第 {column} 列"
            ide_prompt += "\n"

        selected = ide_ctx.get("selectedText", "")
        if selected:
            ide_prompt += f"- **用户选中的代码**: \n```\n{selected[:500]}\n```\n"

        full_content = ide_ctx.get("fullContent", "")
        if full_content and len(full_content) > 0:
            max_len = 3000
            content = full_content[:max_len]
            if len(full_content) > max_len:
                content += "\n... (已截断)"
            ide_prompt += f"\n- **当前文件内容**:\n```{language or ''}\n{content}\n```\n"

        return ide_prompt

    def inject_system_prompt(self, messages: List[dict]) -> List[dict]:
        """将工具系统提示注入到 system message 中"""
        if not self.tool_injection_enabled:
            return messages

        schemas = tool_registry.get_all_schemas()
        if not schemas:
            return messages

        tool_prompt = tool_registry.get_system_prompt()

        # ===== 注入 IDE 上下文（Phase 1） =====
        ide_prompt = self._build_ide_context_prompt()
        if ide_prompt:
            tool_prompt += ide_prompt

        last_ctx = load_last_context()
        if last_ctx:
            ctx_summary = f"""

## 上次会话上下文

📅 时间: {last_ctx.timestamp}
📌 主题: {last_ctx.topic}
📝 摘要: {last_ctx.summary}
"""
            if last_ctx.next_steps:
                ctx_summary += f"➡️ 下一步: {', '.join(last_ctx.next_steps[:3])}"
            tool_prompt += ctx_summary

        has_system = any(m.get("role") == "system" for m in messages)

        if has_system:
            new_messages = []
            for m in messages:
                if m.get("role") == "system":
                    enhanced = {
                        "role": "system",
                        "content": m["content"] + "\n\n" + tool_prompt,
                    }
                    new_messages.append(enhanced)
                else:
                    new_messages.append(m)
            return new_messages
        else:
            return [{"role": "system", "content": tool_prompt}] + messages

    async def process_with_tools(
        self,
        llm_client,
        messages: List[dict],
        provider: str = "deepseek",
        stream: bool = False,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """非流式处理消息并自动执行工具调用"""
        tool_calls_made = 0
        rounds = 0
        execution_history = []
        total_content = ""
        repeat_count = 0

        # 记录用户消息到记忆库
        if session_id:
            user_msg = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    user_msg = m.get("content", "")
                    break
            if user_msg:
                try:
                    auto_memory.log_user_message(session_id, user_msg)
                except Exception:
                    import traceback
                    print(f"[AutoMemory] Failed to log: {traceback.format_exc()}")

        current_messages = self.inject_system_prompt(messages)

        while rounds < self.max_tool_rounds:
            rounds += 1
            
            if check_interrupt():
                return {
                    "content": "任务已被用户中断。",
                    "tool_calls": tool_calls_made,
                    "rounds": rounds,
                    "interrupted": True,
                }

            result = await llm_client.chat(
                messages=current_messages,
                provider=provider,
                tools=tool_registry.get_all_schemas(),
                stream=False,
            )

            content = result.get("content", "")
            api_tool_calls = result.get("tool_calls", [])

            tool_call = None
            if api_tool_calls:
                tool_call = api_tool_calls[0]

            if not tool_call:
                validation = validate_tool_execution(
                    response=content,
                    tool_calls=[],
                    tool_results=[],
                    user_message=messages[-1].get("content", "") if messages else "",
                )
                if not validation["valid"] and validation["false_claim"]:
                    current_messages.append({"role": "user", "content": validation["retry_hint"]})
                    continue

                # 记录助手回复到记忆库
                if session_id and content:
                    try:
                        auto_memory.log_assistant_reply(session_id, content, tool_calls_made)
                    except Exception:
                        import traceback
                        print(f"[AutoMemory] Failed to log: {traceback.format_exc()}")

                return {
                    "content": content,
                    "tool_calls": tool_calls_made,
                    "rounds": rounds,
                    "usage": result.get("usage"),
                }

            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("arguments", {})
            safety = check_tool_safety(tool_name, tool_args)

            if not safety.allowed:
                error_msg = f"❌ 安全拦截: {safety.reason}"
                current_messages.append({
                    "role": "tool",
                    "content": error_msg,
                    "tool_call_id": tool_call.get("id", f"call_{rounds}"),
                })
                execution_history.append({
                    'name': tool_name,
                    'args': tool_args,
                    'result_summary': error_msg[:80],
                    'success': False,
                    'iteration': rounds,
                })
                tool_calls_made += 1
                continue

            assistant_msg = {
                "role": "assistant",
                "content": content or f"我需要调用工具 {tool_name}。",
            }
            rc = result.get("reasoning_content", "")
            if rc:
                assistant_msg["reasoning_content"] = rc
                self._thinking_mode_active = True
            elif getattr(self, '_thinking_mode_active', False):
                assistant_msg["reasoning_content"] = ""
            
            assistant_msg["tool_calls"] = [{
                "id": tool_call.get("id", f"call_{rounds}"),
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(tool_args, ensure_ascii=False),
                },
            }]
            current_messages.append(assistant_msg)

            try:
                exec_result = await tool_registry.execute(tool_name, tool_args)
                # 工具结果返回：支持大文件完整读取（参考 OpenClaw 做法）
                raw_result = exec_result.get("result", exec_result)
                if isinstance(raw_result, dict) and "content" in raw_result:
                    raw_content = raw_result["content"]
                    if isinstance(raw_content, str) and len(raw_content) > 2000000:
                        # 仅当超过200万字符才截断（Kimi支持200万上下文）
                        total_lines = raw_content.count(chr(10))
                        raw_result = dict(raw_result)
                        raw_result["content"] = raw_content[:2000000] + (
                            "\n\n[文件过大已截断：共 " + str(len(raw_content)) + " 字符，" + str(total_lines) + " 行。"
                            "当前显示前 200 万字符。如需查看特定范围，请使用 offset 和 limit 参数]"
                        )
                result_content = json.dumps(raw_result, ensure_ascii=False)
                error = exec_result.get("error")

                if error:
                    tool_result_msg = f"工具 [{tool_name}] 执行失败: {error}"
                    current_messages.append({
                        "role": "tool",
                        "content": tool_result_msg,
                        "tool_call_id": tool_call.get("id", f"call_{rounds}"),
                    })
                    execution_history.append({
                        'name': tool_name,
                        'args': tool_args,
                        'result_summary': f"ERROR: {error}"[:80],
                        'success': False,
                        'iteration': rounds,
                    })
                else:
                    tool_result_msg = f"✅ {result_content}"
                    current_messages.append({
                        "role": "tool",
                        "content": tool_result_msg,
                        "tool_call_id": tool_call.get("id", f"call_{rounds}"),
                    })
                    execution_history.append({
                        'name': tool_name,
                        'args': tool_args,
                        'result_summary': result_content[:80],
                        'success': True,
                        'iteration': rounds,
                    })

                # 循环检测（非流式版本）
                if execution_history:
                    last = execution_history[-1]
                    if len(execution_history) >= 2:
                        prev = execution_history[-2]
                        if last['name'] == prev['name'] and last['args'] == prev['args']:
                            repeat_count += 1
                            if repeat_count >= 2:
                                for msg in current_messages:
                                    if msg.get('role') == 'system':
                                        msg['content'] += f"\n\n[WARNING] You have called tool '{tool_name}' {repeat_count} times with the same args. This is a loop. Please change strategy or reply directly.\n"
                                        break
                                if repeat_count >= 3:
                                    return {
                                        "content": f"[Loop detected] Tool '{tool_name}' called {repeat_count} times with identical args. Stopped. Possible causes: 1) Large file needs chunked reading 2) Path does not exist 3) Try a different approach.",
                                        "tool_calls": tool_calls_made,
                                        "rounds": rounds,
                                        "interrupted": True,
                                    }
                        else:
                            repeat_count = 0
                    else:
                        repeat_count = 0
                else:
                    repeat_count = 0

                tool_calls_made += 1
                
                if len(current_messages) > MAX_HISTORY + 2:
                    preserved = [current_messages[0]]
                    last_user_idx = 0
                    for i in range(len(current_messages) - 1, -1, -1):
                        if current_messages[i].get("role") == "user":
                            last_user_idx = i
                            break
                    tail = current_messages[-MAX_HISTORY:]
                    if last_user_idx > 0 and current_messages[last_user_idx] not in tail:
                        tail.insert(0, current_messages[last_user_idx])
                    current_messages = preserved + tail

            except Exception as e:
                error_msg = f"工具 [{tool_name}] 执行异常: {str(e)}"
                current_messages.append({
                    "role": "tool",
                    "content": error_msg,
                    "tool_call_id": tool_call.get("id", f"call_{rounds}"),
                })
                execution_history.append({
                    'name': tool_name,
                    'args': tool_args,
                    'result_summary': f"EXCEPTION: {str(e)}"[:80],
                    'success': False,
                    'iteration': rounds,
                })

        return {
            "content": f"已执行 {self.max_tool_rounds} 轮工具调用。任务自动完成，模型未主动停止。",
            "tool_calls": tool_calls_made,
            "rounds": rounds,
            "paused": True,
        }

    async def process_stream_with_tools(
        self,
        llm_client,
        messages: List[dict],
        provider: str = "deepseek",
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[dict, None]:
        """流式处理消息并自动执行工具调用"""
        tool_calls_made = 0
        rounds = 0
        total_tokens = 0
        self._steps = []
        original_user_message = ""
        original_system_content = ""
        original_system_idx = None

        for m in reversed(messages):
            if m.get("role") == "user":
                original_user_message = m.get("content", "")
                break

        # 记录用户消息到记忆库
        if session_id and original_user_message:
            try:
                auto_memory.log_user_message(session_id, original_user_message)
            except Exception:
                import traceback
                print(f"[AutoMemory] Failed to log: {traceback.format_exc()}")

        trigger_result = analyze_message(original_user_message, "", messages)
        preroll_result = check_and_run(original_user_message)
        if preroll_result:
            yield {"type": "preroll", "content": preroll_result}

        if trigger_result.should_trigger and provider.lower() not in {"kimi", "openai", "anthropic"}:
            tool_hint = get_suggested_tool_prompt(trigger_result)
            if tool_hint:
                for i in range(len(messages) - 1, -1, -1):
                    if messages[i].get("role") == "user":
                        messages[i] = {
                            "role": "user",
                            "content": messages[i]["content"] + "\n" + tool_hint,
                        }
                        break

        current_messages = self.inject_system_prompt(messages)
        
        for i, m in enumerate(current_messages):
            if m.get("role") == "system":
                original_system_content = m["content"]
                original_system_idx = i
                break

        execution_history = []
        total_content = ""
        
        while rounds < self.max_tool_rounds:
            rounds += 1
            
            # ═══ 循环检测 ═══
            if execution_history:
                # 2次重复 = 警告，3次重复 = 终止
                if len(execution_history) >= 2:
                    last = execution_history[-1]
                    prev = execution_history[-2]
                    if last['name'] == prev['name'] and last['args'] == prev['args']:
                        # 已有2次重复，注入强力警告
                        loop_warning = "\n\n⚠️【关键警告】你已经连续2次调用工具 '{}' 且参数完全相同。".format(last['name'])
                        loop_warning += "这是循环行为。如果再次调用相同工具，任务将被强制终止。"
                        loop_warning += "请立即改变策略，使用不同方法或直接回复用户。"
                        if original_system_idx is not None:
                            current_messages[original_system_idx]["content"] += loop_warning
                    
                    if len(execution_history) >= 3:
                        prev2 = execution_history[-3]
                        if (last['name'] == prev['name'] == prev2['name'] and 
                            last['args'] == prev['args'] == prev2['args']):
                            loop_msg = "检测到工具调用循环：工具 {} 以相同参数连续调用3次，已强制终止".format(last['name'])
                            yield {"type": "status", "message": "⚠️ 检测到循环，已终止"}
                            yield {"type": "error", "message": loop_msg}
                            yield {
                                "type": "done",
                                "full_content": "⚠️ 执行中断：{}。工具在重复执行相同操作，可能是：1) 文件太大需要分段查看 2) 路径不存在 3) 请尝试用不同方法解决。".format(loop_msg),
                                "show_summary": tool_calls_made > 0,
                                "stats": {"rounds_executed": rounds, "tools_called": tool_calls_made},
                            }
                            return
                
                # 注入执行摘要到 system message（限制长度）
                MAX_SUMMARY_LEN = 2000
                summary = "\n\n【执行摘要 - 最近3步】\n"
                for i, entry in enumerate(execution_history[-3:], 1):
                    status = "✅" if entry.get('success', False) else "❌"
                    result = entry['result_summary'][:60]
                    summary += "  {}. {} {} → {}\n".format(i, status, entry['name'], result)
                
                if execution_history[-1].get('success', False):
                    summary += "\n💡 上一步成功。请继续下一步或总结结果回复用户。"
                else:
                    summary += "\n💡 上一步失败。请换方法，不要重复相同操作。"
                
                if original_system_idx is not None:
                    base_content = original_system_content
                    if len(base_content) > 4000:
                        base_content = base_content[:4000] + "\n...[截断]"
                    current_messages[original_system_idx] = {
                        "role": "system",
                        "content": base_content + summary,
                    }
            
            yield {"type": "status", "message": "第 {} 轮思考中...".format(rounds)}
            
            if check_interrupt():
                yield {"type": "status", "message": "任务已被用户中断"}
                yield {
                    "type": "done",
                    "full_content": "任务已被用户中断。",
                    "show_summary": tool_calls_made > 0,
                    "stats": {"rounds_executed": rounds, "tools_called": tool_calls_made},
                }
                return

            full_content = ""
            pending_tool_calls = []
            has_api_tool_call = False
            round_usage = {}

            yield {"type": "status", "message": "正在思考..."}
            
            # 发送等待AI响应的状态
            yield {"type": "status", "message": "等待AI响应..."}
            
            # 每轮最多等待120秒
            round_start = time.time()
            async for event in llm_client.stream_chat(
                messages=current_messages,
                provider=provider,
                tools=tool_registry.get_all_schemas(),
            ):
                event_type = event.get("type")

                # 检查是否超时
                if time.time() - round_start > 300:
                    print(f"[AgentEngine] Round {rounds} timed out after 300s")
                    yield {"type": "status", "message": "⏱️ 请求超时（5分钟），正在结束..."}
                    timeout_msg = full_content + "\n\n[请求超时：本轮处理超过5分钟]"
                    yield {"type": "done", "full_content": timeout_msg}
                    return
                
                if event_type == "token":
                    full_content += event.get("content") or ""
                    total_content += event.get("content") or ""
                    yield event

                elif event_type == "thinking":
                    self._reasoning_content = event.get("content", "")
                    self._thinking_mode_active = True
                    yield event

                elif event_type == "tool_call_end":
                    pending_tool_calls = event.get("tool_calls", [])
                    has_api_tool_call = True
                    full_content = event.get("full_content", full_content)
                    round_usage = event.get("usage", {})
                    # Forward individual tool_call events to frontend for display
                    for tc in pending_tool_calls:
                        yield {
                            "type": "tool_call",
                            "name": tc.get("name", ""),
                            "arguments": tc.get("arguments", {}),
                            "id": tc.get("id", ""),
                        }

                elif event_type == "tool_call":
                    # 单个工具调用事件（来自 [DONE] 路径）
                    pending_tool_calls.append(event)
                    has_api_tool_call = True
                    # Forward to frontend for display
                    yield event

                elif event_type == "done":
                    full_content = event.get("full_content", full_content)
                    round_usage = event.get("usage", {})
                    rc = event.get("reasoning_content", "")
                    if rc:
                        self._reasoning_content = rc
                        self._thinking_mode_active = True

                elif event_type == "error":
                    yield event
                    return

            if round_usage:
                total_tokens += round_usage.get("total_tokens", 0)

            tool_call = None

            if has_api_tool_call and pending_tool_calls:
                tool_call = pending_tool_calls[0]
                if isinstance(tool_call, dict):
                    if "name" not in tool_call and "function" in tool_call:
                        func = tool_call.get("function", {})
                        tool_call = {
                            "name": func.get("name", ""),
                            "arguments": func.get("arguments", {}),
                            "id": tool_call.get("id", f"call_{rounds}"),
                        }

            if not tool_call:
                # Safety net: detect pseudo-tool-calls like "I need to call xxx" without actual call
                pseudo_patterns = [
                    r'我需要调用\s+(\w+)',
                    r'I need to call\s+(\w+)',
                    r'让我调用\s+(\w+)',
                    r'Let me call\s+(\w+)',
                ]
                for pattern in pseudo_patterns:
                    match = re.search(pattern, full_content, re.IGNORECASE)
                    if match:
                        pseudo_tool = match.group(1)
                        loop_msg = "检测到伪工具调用：模型声称要调用 '{}' 但没有真正调用。可能是模型不支持function calling格式。".format(pseudo_tool)
                        yield {"type": "status", "message": "⚠️ " + loop_msg}
                        yield {
                            "type": "done",
                            "full_content": full_content + "\n\n⚠️ " + loop_msg + "\n\n请直接回答用户问题，或尝试使用其他模型（如 DeepSeek/Xiaomi 对工具支持更好）。",
                            "show_summary": False,
                            "stats": {"rounds_executed": rounds, "tools_called": tool_calls_made},
                        }
                        return

                validation = validate_tool_execution(
                    response=full_content,
                    tool_calls=[],
                    tool_results=[],
                    user_message=original_user_message,
                )

                if not validation["valid"] and validation["false_claim"]:
                    yield {"type": "validation_failed", "reason": validation["reason"]}
                    current_messages.append({"role": "user", "content": validation["retry_hint"]})
                    trigger_result = ToolTriggerResult(
                        should_trigger=True,
                        trigger_type="forced_retry",
                        confidence=1.0,
                        suggested_tools=[],
                    )
                    continue

                try:
                    save_current_context(
                        topic=extract_topic(original_user_message),
                        summary=full_content[:200] if full_content else "",
                        next_steps=extract_next_steps(full_content),
                    )
                except Exception as e:
                    pass

                # 记录助手回复到记忆库（无工具调用的直接回复）
                if session_id and full_content:
                    try:
                        auto_memory.log_assistant_reply(session_id, full_content, tool_calls_made)
                    except Exception:
                        import traceback
                        print(f"[AutoMemory] Failed to log: {traceback.format_exc()}")

                yield {
                    "type": "done",
                    "full_content": full_content,
                    "show_summary": tool_calls_made > 0,
                    "stats": {
                        "total_tokens_used": total_tokens,
                        "rounds_executed": rounds,
                        "tools_called": tool_calls_made,
                        "trigger_type": trigger_result.trigger_type,
                    },
                }
                return

            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("arguments", {})

            safety = check_tool_safety(tool_name, tool_args)

            if not safety.allowed:
                yield {"type": "tool_error", "name": tool_name, "content": f"❌ 安全拦截: {safety.reason}"}
                current_messages.append({
                    "role": "tool",
                    "content": f"❌ 安全拦截: {safety.reason}",
                    "tool_call_id": tool_call.get("id", f"call_{rounds}"),
                })
                execution_history.append({
                    'name': tool_name,
                    'args': tool_args,
                    'result_summary': f"安全拦截: {safety.reason}"[:80],
                    'success': False,
                    'iteration': rounds,
                })
                tool_calls_made += 1
                continue

            if safety.requires_confirm:
                yield {"type": "safety_warning", "name": tool_name, "level": safety.level, "reason": safety.reason}

            assistant_msg = {
                "role": "assistant",
                "content": full_content or f"我需要调用工具 {tool_name}。",
            }
            # 一旦进入过 thinking 模式，所有后续 assistant 消息都必须包含 reasoning_content
            if getattr(self, '_thinking_mode_active', False):
                assistant_msg["reasoning_content"] = getattr(self, '_reasoning_content', "") or ""
                self._reasoning_content = ""
            
            if has_api_tool_call:
                assistant_msg["tool_calls"] = [{
                    "id": tool_call.get("id", f"call_{rounds}"),
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(tool_args, ensure_ascii=False),
                    },
                }]
            current_messages.append(assistant_msg)

            yield {"type": "status", "message": f"正在执行工具: {tool_name}..."}
            
            try:
                # Execute tool with timeout and heartbeat
                import asyncio
                tool_task = asyncio.create_task(tool_registry.execute(tool_name, tool_args))
                
                # Send heartbeat every 5 seconds while tool is executing
                heartbeat_count = 0
                while not tool_task.done():
                    try:
                        await asyncio.wait_for(asyncio.shield(tool_task), timeout=5.0)
                        break  # Task completed
                    except asyncio.TimeoutError:
                        heartbeat_count += 1
                        yield {"type": "status", "message": f"⏳ 工具 {tool_name} 执行中 ({heartbeat_count * 5}s)..."}
                
                exec_result = await tool_task
                # 工具结果返回：支持大文件完整读取（参考 OpenClaw 做法）
                raw_result = exec_result.get("result", exec_result)
                if isinstance(raw_result, dict) and "content" in raw_result:
                    raw_content = raw_result["content"]
                    if isinstance(raw_content, str) and len(raw_content) > 2000000:
                        # 仅当超过200万字符才截断（Kimi支持200万上下文）
                        total_lines = raw_content.count(chr(10))
                        raw_result = dict(raw_result)
                        raw_result["content"] = raw_content[:2000000] + (
                            "\n\n[文件过大已截断：共 " + str(len(raw_content)) + " 字符，" + str(total_lines) + " 行。"
                            "当前显示前 200 万字符。如需查看特定范围，请使用 offset 和 limit 参数]"
                        )
                result_content = json.dumps(raw_result, ensure_ascii=False)
                error = exec_result.get("error")

                if error:
                    error_msg = f"工具 [{tool_name}] 执行失败: {error}"
                    yield {"type": "tool_error", "name": tool_name, "content": error_msg}
                    current_messages.append({
                        "role": "tool",
                        "content": error_msg,
                        "tool_call_id": tool_call.get("id", f"call_{rounds}"),
                    })
                    execution_history.append({
                        'name': tool_name,
                        'args': tool_args,
                        'result_summary': f"ERROR: {error}"[:80],
                        'success': False,
                        'iteration': rounds,
                    })
                else:
                    success_msg = f"✅ {result_content}"
                    yield {"type": "tool_result", "name": tool_name, "content": success_msg}
                    current_messages.append({
                        "role": "tool",
                        "content": success_msg,
                        "tool_call_id": tool_call.get("id", f"call_{rounds}"),
                    })
                    execution_history.append({
                        'name': tool_name,
                        'args': tool_args,
                        'result_summary': result_content[:80],
                        'success': True,
                        'iteration': rounds,
                    })

                tool_calls_made += 1
                
                # 修剪消息历史，防止 token 无限增长
                MAX_HISTORY = 60
                if len(current_messages) > MAX_HISTORY + 2:
                    preserved = [current_messages[0]]
                    last_user_idx = 0
                    for i in range(len(current_messages) - 1, -1, -1):
                        if current_messages[i].get("role") == "user":
                            last_user_idx = i
                            break
                    tail = current_messages[-MAX_HISTORY:]
                    if last_user_idx > 0 and current_messages[last_user_idx] not in tail:
                        tail.insert(0, current_messages[last_user_idx])
                    current_messages = preserved + tail

            except Exception as e:
                error_msg = f"工具 [{tool_name}] 执行异常: {str(e)}"
                yield {"type": "tool_error", "name": tool_name, "content": error_msg}
                current_messages.append({
                    "role": "tool",
                    "content": error_msg,
                    "tool_call_id": tool_call.get("id", f"call_{rounds}"),
                })
                execution_history.append({
                    'name': tool_name,
                    'args': tool_args,
                    'result_summary': f"EXCEPTION: {str(e)}"[:80],
                    'success': False,
                    'iteration': rounds,
                })

        yield {
            "type": "done",
            "full_content": "已执行大量工具调用轮次，任务自动完成。模型未主动停止，可能任务较复杂。",
            "show_summary": tool_calls_made > 0,
            "stats": {
                "total_tokens_used": total_tokens,
                "rounds_executed": rounds,
                "tools_called": tool_calls_made,
            },
        }

    def _extract_text_tool_call(self, content: str) -> Optional[Dict[str, Any]]:
        """从 LLM 回复文本中提取工具调用（增强版，支持多种伪格式）"""
        if not content:
            return None

        # 格式1: JSON {tool:"name", args:{}}
        patterns = [
            r'\{\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"args"\s*:\s*(\{.*?\})\s*\}',
            r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:\s*(\{.*?\})\s*\}',
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                name = match.group(1)
                try:
                    args = json.loads(match.group(2))
                    return {"name": name, "arguments": args}
                except json.JSONDecodeError:
                    continue

        # 格式2: XML <tool_call> <tool_name>xxx</tool_name> <arguments>{"path":"/tmp"}</arguments>
        xml_pattern = r'<tool_call>.*?<tool_name>([^<]+)</tool_name>.*?<arguments>(\{[^}]*\})</arguments>'
        match = re.search(xml_pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            try:
                args = json.loads(match.group(2))
                return {"name": name, "arguments": args}
            except:
                pass

        # 格式3: Markdown code block with tool name
        code_pattern = r'```(?:json)?\s*\n?\s*\{\s*"(?:action|tool|name)"\s*:\s*"([^"]+)"\s*,\s*"(?:action_input|args|arguments|input)"\s*:\s*(\{.*?\})\s*\}'
        match = re.search(code_pattern, content, re.DOTALL)
        if match:
            name = match.group(1)
            try:
                args = json.loads(match.group(2))
                return {"name": name, "arguments": args}
            except:
                pass

        return None


agent_engine = AgentEngine()
