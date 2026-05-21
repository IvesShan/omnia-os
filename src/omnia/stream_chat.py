# Omnia Stream Chat - SSE 流式输出 (优化版本)
"""
SSE (Server-Sent Events) 流式聊天端点
支持：
- 多轮工具调用 + 并行执行 + 缓存
- 长任务自动分解 + 状态持久化 + 断点续传
"""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Generator, Dict
from pathlib import Path


from src.omnia.config import settings
from omnia.wake import assemble_wake_prompt
from omnia.tool_trigger import check_and_run
from omnia.chat import _load_api_key, _build_model_config
from omnia.tool_optimizer import ToolExecutionOptimizer, ParallelToolExecutor
from src.core.actuator.tool_executor import ToolCallExecutor
from src.core.actuator.tool_registry import TOOLS_SCHEMA
from src.core.memory_palace.memory_palace import MemoryPalace

PROJECT_ROOT = Path(__file__).parent.parent.parent
MAX_TOOL_ITERATIONS = 50  # 提高上限，长任务由 LongTaskHandler 处理
LONG_TASK_THRESHOLD = 5  # 预估步骤超过这个值就使用长任务处理器

# 动态上限配置
DYNAMIC_LIMITS = {
    "simple": 10,      # 简单任务：读取、列表等
    "medium": 30,      # 中等任务：分析、整理等
    "complex": 100,    # 复杂任务：多文件处理、批量操作
    "unlimited": 500,  # 超复杂任务：完整项目分析
}

# API Provider selection
_current_provider = None

# 全局优化器实例
_optimizer = None
_tool_executor = None  # 统一工具执行器
_executor = ThreadPoolExecutor(max_workers=4)  # 并行执行线程池


def get_optimizer():
    """获取优化器实例"""
    global _optimizer
    if _optimizer is None:
        _optimizer = ToolExecutionOptimizer(
            enable_cache=True,
            enable_recovery=True,
            enable_parallel=True,  # 启用并行执行
            max_tokens_per_round=8000,
            max_rounds=MAX_TOOL_ITERATIONS
        )
    return _optimizer

def get_tool_executor():
    """获取统一工具执行器实例（含安全检查 + MCP 支持）"""
    global _tool_executor
    if _tool_executor is None:
        _tool_executor = ToolCallExecutor()
    return _tool_executor


async def stream_chat(message: str, history: list = None, provider: str = None) -> AsyncGenerator[str, None]:
    """
    流式聊天处理 - 支持长任务
    
    自动检测任务复杂度：
    - 简单任务：直接执行（最多 50 轮）
    - 复杂任务：使用 LongTaskHandler（自动分解 + 持久化 + 断点续传）
    """
    history = history or []
    
    # === 优先检查本地模型模式 ===
    model_mode = os.environ.get("OMNIA_MODEL_MODE", "cloud")
    
    if model_mode == "local":
        # 使用本地模型
        print("[stream_chat] Using local model (GPU accelerated)")
        provider = "local"
        api_key = None  # 本地模型不需要 API key
    else:
        # 云端模型：加载API配置
        # 如果传入了provider，优先加载对应key；否则自动检测
        key_name, api_key = _load_api_key(prefer_provider=provider)
        if not api_key:
            yield f"data: {json.dumps({'type': 'error', 'message': 'No API key configured'})}\n\n"
            return
        
        # 检测provider (基于 .env 配置自动检测)
        if not provider:
            if "DEEPSEEK" in key_name.upper():
                provider = "deepseek"
            elif "QIANFAN" in key_name.upper():
                provider = "qianfan"
            elif "OPENAI" in key_name.upper():
                provider = "openai"
            elif "MIMO" in key_name.upper():
                provider = "xiaomi"
            else:
                provider = "kimi"  # 默认 fallback
    
    # === 统一流程 ===
    # 不判断复杂度，直接执行
    # 记录用户消息
    import uuid
    session_id = str(uuid.uuid4())
    try:
        mp = MemoryPalace(db_path=str(settings.memory_palace_db))
        mp.initialize()
        mp.log_conversation(session_id, 0, "user", message)
    except Exception as e:
        print(f"[stream_chat] Failed to log user message: {e}")
    
    async for chunk in _stream_chat_unified(message, history, api_key, provider, MAX_TOOL_ITERATIONS, {}, session_id):
        yield chunk


def _get_dynamic_limit(analysis: Dict) -> int:
    """根据任务复杂度动态调整上限 - 更激进的策略"""
    estimated = analysis.get("estimated_steps", 1)
    is_complex = analysis.get("is_complex", False)
    
    # 更激进的策略：给足够的空间完成任务
    if estimated <= 2:
        return DYNAMIC_LIMITS["simple"]
    elif estimated <= 5:
        return DYNAMIC_LIMITS["medium"]
    elif is_complex or estimated > 10:
        return DYNAMIC_LIMITS["complex"]
    else:
        return DYNAMIC_LIMITS["unlimited"]


def _build_headers(api_key: str, provider: str) -> dict:
    """根据 provider 构建正确的请求头
    
    Xiaomi MiMo 使用 api-key 头，其他使用 Authorization: Bearer
    """
    headers = {
        "Content-Type": "application/json",
    }
    if provider == "xiaomi":
        headers["api-key"] = api_key
    else:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


async def _stream_chat_unified(
    message: str,
    history: list,
    api_key: str,
    provider: str,
    max_iterations: int,
    context: dict,
    session_id: str = None
) -> Generator[str, None, None]:
    """
    统一流式聊天处理 (支持工具调用 + 长任务 + 并行执行)
    
    参数:
        message: 用户消息
        history: 历史消息列表
        api_key: API密钥
        provider: 提供商名称 (deepseek/kimi/openai/qianfan/local/xiaomi)
        max_iterations: 最大迭代轮数
        context: 上下文信息
        session_id: 会话ID
    """
    # 消息历史
    messages = list(history)
    
    # 发送初始状态事件
    yield f"data: {json.dumps({'type': 'status', 'message': '正在分析问题...'})}\n\n"
    
    # 组装系统提示词 (wake prompt)
    try:
        system_prompt = assemble_wake_prompt()
    except Exception as e:
        print(f"[stream_chat] Failed to assemble wake prompt: {e}")
        system_prompt = "You are Omnia, an AI assistant."

    # ========== 前置工具检查钩子（方案A）==========
    _tool_result = check_and_run(message)
    if _tool_result:
        print("[stream_chat] 命中关键词，注入工具检查结果")
        _tool_warning = "\n\n[系统强制工具检查结果 - 请基于以下实际数据回答用户]\n"
        _tool_warning += _tool_result
        _tool_warning += "\n[/系统强制工具检查结果]\n"
        system_prompt += _tool_warning
    # ========== 前置工具检查结束 ==========
    
    # 添加系统消息
    system_message = {"role": "system", "content": system_prompt}
    if messages and messages[0].get("role") == "system":
        messages[0] = system_message
    else:
        messages.insert(0, system_message)
    
    # 添加用户消息
    messages.append({"role": "user", "content": message})
    
    # 获取模型配置
    url, model = _build_model_config(provider)
    
    total_input_tokens = 0
    total_output_tokens = 0
    full_content = ""  # 累积完整回复内容
    assistant_reply = ""  # 当前轮次助手回复
    
    # === DeepSeek 思考模式追踪 ===
    # 一旦模型进入过思考模式（返回过非空 reasoning_content），
    # 所有后续 assistant 消息都必须包含 reasoning_content 字段
    thinking_mode_active = False
    
    # === 执行历史记录（用于循环检测和反思）===
    execution_history = []  # 记录每次工具调用: [{name, args, result_summary, iteration}]
    
    # === 工具迭代循环 ===
    iteration = 0
    while iteration < max_iterations:
        iteration += 1
        
        # === 循环检测 & 执行摘要注入 ===
        if execution_history:
            # 检测严格循环（完全相同参数）
            if len(execution_history) >= 2:
                last = execution_history[-1]
                prev = execution_history[-2]
                if last['name'] == prev['name'] and last['args'] == prev['args']:
                    loop_msg = "检测到工具调用循环：工具 {} 以相同参数被连续调用".format(last['name'])
                    print("[stream_chat] ⚠️ {}".format(loop_msg))
                    yield "data: " + json.dumps({'type': 'status', 'message': '⚠️ 检测到循环: {} 重复调用'.format(last['name'])}) + "\n\n"
                    yield "data: " + json.dumps({'type': 'error', 'message': loop_msg}) + "\n\n"
                    done_msg = full_content + "\n\n⚠️ 执行中断：{}。建议换用其他方法解决问题。".format(loop_msg)
                    yield "data: " + json.dumps({'type': 'done', 'full_content': done_msg}) + "\n\n"
                    return
            
            # 构建执行摘要，注入到系统提示中
            summary = "\n\n【执行摘要 - 请仔细阅读并调整策略】\n"
            summary += "当前进度: 第 {} 轮 / 最多 {} 轮\n".format(iteration, max_iterations)
            summary += "已执行步骤（最近5次）:\n"
            for i, entry in enumerate(execution_history[-5:], 1):
                status = "✅" if entry.get('success', False) else "❌"
                args_str = json.dumps(entry['args'], ensure_ascii=False)
                if len(args_str) > 80:
                    args_str = args_str[:77] + "..."
                summary += "  {}. {} {}({}) → {}\n".format(i, status, entry['name'], args_str, entry['result_summary'])
            
            summary += "\n【策略提示 - 必须遵守】\n"
            summary += "1. 如果上一步失败了，请分析原因并换用不同方法\n"
            summary += "2. 不要重复执行已经失败过的相同操作（相同工具+相同参数）\n"
            summary += "3. 考虑使用其他工具、调整参数，或改变解决思路\n"
            summary += "4. 如果连续尝试同一方向都失败，请尝试完全不同的方法\n"
            summary += "【执行摘要结束】\n"
            
            # 将摘要注入到系统消息中（messages[0] 是系统消息）
            if messages and messages[0].get("role") == "system":
                messages[0]["content"] += summary
        
        # 发送当前轮次状态
        yield "data: " + json.dumps({'type': 'status', 'message': '第 {}/{} 轮思考中...'.format(iteration, max_iterations)}) + "\n\n"
        
        # === 构建请求参数 ===
        headers = _build_headers(api_key, provider)
        
        payload = {
            "model": model,
            "messages": messages,
            "tools": TOOLS_SCHEMA,
            "temperature": 0.7,
            "stream": True,
            # stream_options only supported by OpenAI, not DeepSeek/Kimi/Qianfan
            **({"stream_options": {"include_usage": True}} if provider == "openai" else {}),
        }
        
        # 流式请求
        try:
            import requests
            # 发送API调用状态
            yield f"data: {json.dumps({'type': 'status', 'message': '等待AI响应...'})}\n\n"
            
            response = requests.post(url, headers=headers, json=payload, stream=True, timeout=120)
        except ImportError:
            yield f"data: {json.dumps({'type': 'error', 'message': 'requests module not available'})}\n\n"
            return
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Request failed: {str(e)}'})}\n\n"
            return
        
        if response.status_code != 200:
            # 记录详细的错误信息
            error_text = response.text
            error_msg = f"API error {response.status_code}: {error_text[:500]}"
            print(f"[stream_chat] API Error Details: {error_text}")
            print(f"[stream_chat] Request payload: model={payload.get('model')}, messages={len(messages)}, tools={len(TOOLS_SCHEMA)}")
            print(f"[stream_chat] Last message role: {messages[-1].get('role') if messages else 'N/A'}")
            if messages and messages[-1].get("role") == "assistant":
                print(f"[stream_chat] Last assistant message keys: {list(messages[-1].keys())}")
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
            return
        
        # 解析流式响应
        tool_calls_buffer = {}  # 用字典合并增量
        content = ""
        reasoning_content = ""  # DeepSeek V4 思考模式需要
        has_seen_reasoning = False  # 追踪本轮是否进入过思考模式 (用于逻辑判断)
        finish_reason = None
        
        # Kimi/Anthropic 格式 SSE 支持
        anthropic_event_buffer = None
        current_tool_index = 0
        
        for line in response.iter_lines():
            if not line:
                continue
            
            line = line.decode('utf-8')
            
            # === Anthropic/Kimi 格式 SSE ===
            if provider == "kimi":
                if line.startswith('event:'):
                    anthropic_event_buffer = line[7:]
                    continue
                
                if line.startswith('data:') and anthropic_event_buffer:
                    data_str = line[5:]
                    event_type = anthropic_event_buffer
                    anthropic_event_buffer = None
                    
                    try:
                        data = json.loads(data_str) if data_str else {}
                    except json.JSONDecodeError:
                        continue
                    
                    if event_type == 'message_start':
                        pass
                    
                    elif event_type == 'content_block_start':
                        block = data.get('content_block', {})
                        if block.get('type') == 'tool_use':
                            idx = current_tool_index
                            tool_calls_buffer[idx] = {
                                'id': block.get('id', ''),
                                'type': 'function',
                                'function': {
                                    'name': block.get('name', ''),
                                    'arguments': ''
                                }
                            }
                            current_tool_index += 1
                    
                    elif event_type == 'content_block_delta':
                        delta = data.get('delta', {})
                        delta_type = delta.get('type', '')
                        
                        if delta_type == 'text_delta':
                            text = delta.get('text', '')
                            if text:
                                content += text
                                full_content += text
                                assistant_reply += text
                                yield f"data: {json.dumps({'type': 'token', 'content': text})}\n\n"

                        
                        elif delta_type == 'thinking_delta':
                            thinking = delta.get('thinking', '')
                            if thinking:
                                reasoning_content += thinking
                                thinking_mode_active = True
                                yield f"data: {json.dumps({'type': 'thinking', 'content': thinking})}\n\n"

                        
                        elif delta_type == 'input_json_delta':
                            partial_json = delta.get('partial_json', '')
                            if partial_json:
                                idx = current_tool_index
                                if idx in tool_calls_buffer:
                                    tool_calls_buffer[idx]['function']['arguments'] += partial_json
                    
                    elif event_type == 'content_block_stop':
                        # Anthropic SSE 格式: {"type":"content_block_stop","index":N}
                        # 只有 index 字段，没有 content_block
                        # tool_use block 的递增在 content_block_start 中已处理
                        pass
                    
                    elif event_type == 'message_delta':
                        delta = data.get('delta', {})
                        stop_reason = delta.get('stop_reason', '')
                        if stop_reason in ('end_turn', 'tool_use'):
                            finish_reason = stop_reason
                    
                    elif event_type == 'message_stop':
                        finish_reason = 'stop'
                
                continue  # Kimi 格式处理完毕，跳到下一行
            
            # === OpenAI 格式 SSE (DeepSeek/Xiaomi/QianFan/OpenAI) ===
            if line.startswith('data: '):
                data_str = line[5:]
                
                
                if data_str == '[DONE]':
                    break
                
                try:
                    data = json.loads(data_str)
                    if data is None:
                        print("[Stream] Warning: data is None")
                        continue
                    
                    # 捕获 token usage（流式响应的最后一个 chunk）
                    if 'usage' in data:
                        usage = data.get('usage') or {}
                        total_input_tokens = usage.get('prompt_tokens', 0)
                        total_output_tokens = usage.get('completion_tokens', 0)
                        print(f"[Stream] Token usage - Input: {total_input_tokens}, Output: {total_output_tokens}")
                    
                    if 'choices' in data and len(data['choices']) > 0:
                        choice = data['choices'][0]
                        if choice is None:
                            print("[Stream] Warning: choice is None")
                            continue
                        delta = choice.get('delta', {})
                        
                        # 文本内容 - 支持 content 和 reasoning_content (Gemma 3 / DeepSeek thinking mode)
                        text_chunk = ""
                        if 'content' in delta and delta['content']:
                            text_chunk = delta['content']
                        if 'reasoning_content' in delta and delta['reasoning_content']:
                            # DeepSeek V4 / Gemma 3 thinking mode: 收集并输出到前端
                            reasoning_content += delta["reasoning_content"]
                            _ = True  # has_seen_reasoning (unused)
                            thinking_mode_active = True  # 全局追踪：进入思考模式
                            # 将思考内容作为 'thinking' 事件输出
                            yield "data: " + json.dumps({"type": "thinking", "content": delta["reasoning_content"]}) + "\n\n"
                        
                        if text_chunk:
                            content += text_chunk
                            full_content += text_chunk
                            assistant_reply += text_chunk
                            yield f"data: {json.dumps({'type': 'token', 'content': text_chunk})}\n\n"
                        
                        # 工具调用 - 增量合并
                        if 'tool_calls' in delta and delta['tool_calls']:
                            for tc in delta['tool_calls']:
                                tc_id = tc.get('id', '')
                                tc_index = tc.get('index', 0)
                                
                                # 使用 index 作为 key 来合并
                                if tc_index not in tool_calls_buffer:
                                    tool_calls_buffer[tc_index] = {
                                        'id': tc_id,
                                        'type': 'function',
                                        'function': {
                                            'name': '',
                                            'arguments': ''
                                        }
                                    }
                                
                                # 增量更新
                                if tc.get('function'):
                                    if tc['function'].get('name'):
                                        tool_calls_buffer[tc_index]['function']['name'] += tc['function']['name']
                                    if tc['function'].get('arguments'):
                                        tool_calls_buffer[tc_index]['function']['arguments'] += tc['function']['arguments']
                                if tc_id:
                                    tool_calls_buffer[tc_index]['id'] = tc_id
                        
                        # 结束原因
                        if choice.get('finish_reason'):
                            finish_reason = choice['finish_reason']
                    
                    # 也处理 reasoning_content 出现在 delta 顶层但不是 choices 中的情况
                    if 'reasoning_content' in data and data['reasoning_content'] and 'choices' not in data:
                        # 某些 API 实现可能将 reasoning_content 放在顶层
                        reasoning_content += data["reasoning_content"]
                        _ = True  # has_seen_reasoning (unused)
                        thinking_mode_active = True
                
                except json.JSONDecodeError:
                    continue
        
        # 将合并后的 tool_calls 转换为列表
        tool_calls = list(tool_calls_buffer.values())
        
        # 检查是否有工具调用
        has_tool_calls = tool_calls and any((tc.get("function") or {}).get("name") for tc in tool_calls)
        
        if not has_tool_calls:
            # 没有工具调用，检查是否完成
            if finish_reason == "stop":
                # 正常完成，发送 done 事件
                # 记录助手回复
                if session_id and full_content:
                    try:
                        mp = MemoryPalace(db_path=str(settings.memory_palace_db))
                        mp.initialize()
                        mp.log_conversation(session_id, 1, "assistant", full_content)
                    except Exception as e:
                        print(f"[stream_chat] Failed to log assistant reply: {e}")
                yield f"data: {json.dumps({'type': 'done', 'full_content': full_content})}\n\n"
                return
            
            # 没有工具调用但也没完成
            if content.strip():
                # MiMo/DeepSeek 思考模式修复：必须包含 reasoning_content
                assistant_msg = {"role": "assistant", "content": content}
                if reasoning_content:
                    assistant_msg["reasoning_content"] = reasoning_content
                elif thinking_mode_active:
                    assistant_msg["reasoning_content"] = ""
                messages.append(assistant_msg)
                # 记录助手回复
                if session_id and full_content:
                    try:
                        mp = MemoryPalace(db_path=str(settings.memory_palace_db))
                        mp.initialize()
                        mp.log_conversation(session_id, 1, "assistant", full_content)
                    except Exception as e:
                        print(f"[stream_chat] Failed to log assistant reply: {e}")
                yield f"data: {json.dumps({'type': 'done', 'full_content': full_content})}\n\n"
                return
            
            continue
        
        # 有工具调用，执行
        assistant_message = {"role": "assistant", "content": content or ""}
        
        # ███████████████████████████████████████████████████████████████████████
        # DeepSeek 思考模式修复：一旦进入思考模式，所有 assistant 消息
        # 都必须包含 reasoning_content 字段（即使是空字符串）
        # 参考: https://api-docs.deepseek.com/zh-cn/quick_start/error_codes
        # 错误: "The reasoning_content in the thinking mode must be passed back"
        # ███████████████████████████████████████████████████████████████████████
        if reasoning_content:
            assistant_message["reasoning_content"] = reasoning_content
        elif thinking_mode_active:
            # 思考模式已激活，但本轮没有 reasoning_content
            # 必须传回空字符串以满足 DeepSeek API 要求
            assistant_message["reasoning_content"] = ""
        
        if tool_calls:
            assistant_message["tool_calls"] = tool_calls
        messages.append(assistant_message)
        
        # 使用统一工具执行器（支持安全检查 + MCP 工具）
        tool_exec = get_tool_executor()
        
        # 预处理工具调用
        for tc in tool_calls:
            fn = tc.get("function") or {}
            tool_name = fn.get("name", "")
            args_str = fn.get("arguments", "{}")
            try:
                args = json.loads(args_str) if args_str else {}
            except Exception:
                args = {}
            
            yield f"data: {json.dumps({'type': 'status', 'message': f'Executing tool: {tool_name}...'})}\n\n"


            yield f"data: {json.dumps({'type': 'tool_call', 'name': tool_name, 'arguments': args})}\n\n"


            # 统一执行（含安全检查 + MCP 支持）
            exec_result = await tool_exec.execute_single(tool_name, args)
            
            result_content = exec_result.output if exec_result.success else (exec_result.error or "执行失败")
            
            yield f"data: {json.dumps({'type': 'tool_result', 'name': tool_name, 'content': result_content[:200]})}\n\n"


            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": result_content
            })
            
            execution_history.append({
                'name': tool_name,
                'args': args,
                'result_summary': result_content[:100],
                'success': exec_result.success,
                'iteration': iteration
            })
        # 记录中间步骤
        if session_id:
            try:
                mp = MemoryPalace(db_path=str(settings.memory_palace_db))
                mp.initialize()
                mp.log_conversation(session_id, iteration, "assistant", f"[Tool calls executed: {len(tool_calls)} tools]")
            except Exception as e:
                pass
        
        # 重置当前轮次内容，准备下一轮
        content = ""
        reasoning_content = ""
        assistant_reply = ""
    
    # 达到最大迭代次数
    yield f"data: {json.dumps({'type': 'done', 'full_content': full_content + '\n\n⚠️ 已达到最大迭代次数，任务可能未完全完成。'})}\n\n"
