# Omnia Chat Handler - 融合三家最佳实践
# 核心策略：工具执行后完全重建消息列表
# 新增：神经图谱上下文增强 + 会话历史自动加载

import json
from core.config import MEMORY_PALACE_DB, OMNIA_HOME
from typing import Any

def should_require_tool(user_message: str, provider: str = "deepseek") -> str | None:
    """
    智能判断是否应该强制调用工具。
    
    策略：
    - kimi/openai/anthropic: 支持 tool_choice: "required"，强制调用
    - deepseek: 不支持 "required"，返回 "auto" + 依赖系统提示引导
    
    Args:
        user_message: 用户消息
        provider: 当前使用的 provider
    
    Returns:
        "required" - 强制调用工具（仅对支持的 provider）
        "auto" - 建议模型考虑调用工具
        None - 不传此参数，使用 API 默认行为
    """
    trigger_keywords = [
        # 中文关键词
        "检查", "确认", "验证", "查看", "读取", "读文件",
        "改好了吗", "生效了吗", "有没有", "状态",
        "检查一下", "看一下", "看一下代码", "看看代码",
        "分析", "重新分析", "完整分析", "全面分析",
        # 英文关键词
        "check", "verify", "confirm", "read", "analyze",
    ]
    
    user_lower = user_message.lower()
    
    # 检查是否命中关键词
    triggered = False
    for kw in trigger_keywords:
        if kw in user_lower:
            triggered = True
            break
    
    if not triggered:
        return None
    
    # 根据 provider 决定策略
    providers_support_required = ["kimi", "openai", "anthropic"]
    
    if provider.lower() in providers_support_required:
        return "required"  # 强制调用
    else:
        return "auto"  # 依赖系统提示引导




def handle_chat(message: str, history: list, api_key: str, provider: str, system_prompt: str, all_tools_schema: list = None) -> dict:
    """
    融合 Hermes + FreeCode + OpenClaw 最佳实践的聊天处理器。
    
    核心策略：
    1. 工具执行后完全重建消息列表（FreeCode）
    2. 工具结果添加明确警告（OpenClaw）
    3. 双系统提示强化禁止（Hermes）
    4. 极简总结提示
    5. 神经图谱上下文增强（NEW）
    6. 会话历史自动加载（NEW - 解决对话连续性问题）
    """
    from omnia.chat import _call_model_messages
    from core.actuator.tool_registry import TOOLS_SCHEMA, check_tool_safety, dispatch_tool
    from core.cognition.context_compressor import ContextCompressor
    from core.plugin.hooks import HookRegistry, HookType, HookContext, get_hook_registry
    from core.cognition.prompt_builder import PromptBuilder, PromptContext, get_prompt_builder
    from core.neural_graph.context_enhancer import get_graph_enhancer
    from core.memory_palace.memory_palace_with_graph import MemoryPalace
    from core.neural_graph.updater import NeuralGraphUpdater
    from core.session_manager import get_session_manager, load_recent_conversations, merge_histories
    from core.context_manager import ContextManager, SessionContext, save_current_context
    from pathlib import Path
    

    hooks = get_hook_registry()
    prompt_builder = get_prompt_builder()
    
    # ========== 会话管理（NEW）==========
    session_manager = get_session_manager()
    session_id = session_manager.get_or_create_session()
    
    # 初始化 MemoryPalace（带 Neural Graph Hook）
    memory_db = MEMORY_PALACE_DB
    
    # 初始化 NeuralGraphUpdater 并设置 hook
    try:
        graph_updater = NeuralGraphUpdater()
        mp = MemoryPalace(str(memory_db), graph_updater=graph_updater)
        print(f"[Chat] MemoryPalace initialized with NeuralGraphUpdater hook")
    except Exception as e:
        print(f"[Chat] Failed to init NeuralGraphUpdater, falling back to basic MemoryPalace: {e}")
        mp = MemoryPalace(str(memory_db))
    
    # ========== 自动加载历史（NEW - 解决对话连续性）==========
    # 如果前端传来的历史很短（< 5 条），从数据库加载
    if len(history) < 10:  # 优化: 提高阈值，确保加载足够历史
        print(f"[Chat] Frontend history too short ({len(history)}), loading from database...")
        db_history = load_recent_conversations(
            limit=40,  # 优化: 加载更多历史
            current_message=message,
            min_similarity=0.3,  # 优化: 启用语义搜索
        )
        history = merge_histories(history, db_history, max_total=80)  # 优化: 增加上下文容量
        print(f"[Chat] History merged: {len(history)} messages")
    
    # ========== 加载上次上下文（NEW）==========
    context_manager = ContextManager(OMNIA_HOME)
    last_context = context_manager.load_context()
    
    if last_context:
        print(f"[Chat] Last context loaded: {last_context.topic}")
    
    # ========== 触发 ON_MESSAGE Hook ==========
    try:
        on_message_context = HookContext(
            type=HookType.ON_MESSAGE,
            message=message,
            metadata={
                "session_id": session_id,
                "history_length": len(history),
                "provider": provider,
                "last_context": last_context.to_dict() if last_context else None,
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
    
    # 如果有上次上下文，追加到系统提示
    if last_context:
        context_prompt = f"""

## 上次会话上下文

📅 时间: {last_context.timestamp}
📌 主题: {last_context.topic}
📝 摘要: {last_context.summary}
"""
        if last_context.active_project:
            context_prompt += f"\n🏗️ 项目: {last_context.active_project}"
        if last_context.next_steps:
            context_prompt += f"\n➡️ 下一步: {', '.join(last_context.next_steps[:3])}"
        
        dynamic_prompt = dynamic_prompt + context_prompt
    
    # 如果有图谱上下文，追加到系统提示
    if graph_context_prompt:
        dynamic_prompt = dynamic_prompt + "\n" + graph_context_prompt
    
    messages: list[dict] = [{"role": "system", "content": dynamic_prompt}]
    
    # 添加历史
    for h in history:
        if h.get("role") in ("user", "assistant"):
            messages.append({"role": h["role"], "content": h["content"]})
    
    # 添加当前用户消息
    messages.append({"role": "user", "content": message})
    
    print(f"[Chat] Initial messages: {len(messages)} (system + {len(history)} history + 1 current)")
    
    steps = []
    tool_calls_executed = False
    
    for round_num in range(MAX_TOOL_ROUNDS):
        print(f"\n[Chat] === Round {round_num + 1}/{MAX_TOOL_ROUNDS} ===")
        
        # 策略 1: 工具执行后完全重建（FreeCode 方案）
        if tool_calls_executed:
            # 清空消息列表，只保留系统提示和关键信息
            messages = [{"role": "system", "content": dynamic_prompt}]
            
            # 策略 2: 添加极简的总结提示（改进：允许继续调用工具）
            messages.append({
                "role": "user",
                "content": f"""基于之前的工具执行结果，请回答：{original_message}

注意：
1. 如果工具结果已足够回答问题，用自然语言回答即可
2. 如果还需要更多信息（如读取其他文件、执行其他命令），请继续调用工具
3. 不要编造或臆测，确保回答基于工具返回的实际结果"""
            })
            
            print(f"[Chat] Rebuilt messages: {len(messages)} (no history)")
        
        # 调用模型
        # 策略改进：工具执行后仍然可以继续调用工具（不再禁用）
        # 但通过 MAX_TOOL_ROUNDS 限制总轮数
        use_tools = tools_schema
        
        # 智能判断 tool_choice（不传 None 即为 API 默认行为）
        tool_choice = should_require_tool(message, provider) if use_tools else None
        if tool_choice:
            print(f"[Chat] Tool choice: {tool_choice}")
        
        data = _call_model_messages(api_key, provider, messages, tools=use_tools, tool_choice=tool_choice)
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
            
            # ========== 保存当前上下文（NEW）==========
            try:
                # 提取主题和摘要
                topic = extract_topic(message)
                summary = summarize_conversation(message, reply)
                active_project = detect_active_project(message, reply)
                next_steps = extract_next_steps(reply)
                
                save_current_context(
                    topic=topic,
                    summary=summary,
                    active_project=active_project,
                    next_steps=next_steps,
                )
                print(f"[Chat] Context saved: {topic}")
            except Exception as e:
                print(f"[Chat] Failed to save context: {e}")
            
            return {
                "reply": reply,
                "steps": steps,
                "tool_calls_executed": tool_calls_executed,
                "graph_context_used": bool(graph_context_prompt),
                "session_id": session_id,
                "history_loaded": len(history),
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
            
            print(f"[Chat] Tool: {tool_name}, Args: {tool_args}")
            
            # 安全检查
            if not check_tool_safety(tool_name, tool_args):
                print(f"[Chat] Tool blocked by safety check: {tool_name}")
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
                
                # 记录步骤
                steps.append({
                    "tool": tool_name,
                    "arguments": tool_args,
                    "result_summary": str(result)[:500]
                })
                
                tool_calls_executed = True
                
                # 添加工具结果
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
    
    # 超过最大轮数
    reply = "抱歉，工具调用次数超过限制。请尝试简化您的请求。"
    
    # 保存上下文
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
    """从消息中提取主题"""
    # 简单实现：取前 50 个字符
    topic = message.strip()[:50]
    if len(message) > 50:
        topic += "..."
    return topic


def summarize_conversation(user_message: str, assistant_reply: str) -> str:
    """总结对话"""
    # 简单实现：取用户消息的前 100 个字符
    summary = user_message.strip()[:100]
    if len(user_message) > 100:
        summary += "..."
    return summary


def detect_active_project(user_message: str, assistant_reply: str) -> str:
    """检测活跃项目"""
    # 简单实现：查找关键词
    keywords = ["Omnia", "喵修匠", "懂机帝", "OpenClaw", "项目"]
    text = user_message + " " + assistant_reply
    for keyword in keywords:
        if keyword in text:
            return keyword
    return None


def extract_next_steps(reply: str) -> list:
    """从回复中提取下一步"""
    # 简单实现：查找"下一步"关键词
    if "下一步" in reply:
        # 提取包含"下一步"的句子
        lines = reply.split("\n")
        steps = []
        for line in lines:
            if "下一步" in line or line.strip().startswith("-"):
                steps.append(line.strip())
        return steps[:3]
    return []
