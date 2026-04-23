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
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Generator
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, Response
from flask_cors import CORS

from core.config import MEMORY_PALACE_DB
from omnia.wake import assemble_wake_prompt
from omnia.chat import _load_api_key, _build_model_config
from omnia.tool_optimizer import ToolExecutionOptimizer, ToolResult, ParallelToolExecutor
from omnia.long_task_handler import LongTaskHandler, handle_long_task_stream
from omnia.smart_pauser import SmartPauser, get_pauser, PauseReason
from core.actuator.tool_registry import TOOLS_SCHEMA, dispatch_tool
from core.memory_palace.memory_palace import MemoryPalace

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

def stream_chat(message: str, history: list = None) -> Generator[str, None, None]:
    """
    流式聊天处理 - 支持长任务
    
    自动检测任务复杂度：
    - 简单任务：直接执行（最多 50 轮）
    - 复杂任务：使用 LongTaskHandler（自动分解 + 持久化 + 断点续传）
    """
    history = history or []
    
    # 加载API配置
    key_name, api_key = _load_api_key()
    if not api_key:
        yield f"data: {json.dumps({'type': 'error', 'message': 'No API key configured'})}\n\n"
        return
    
    # 检测provider
    provider = "kimi"
    if "QIANFAN" in key_name.upper():
        provider = "qianfan"
    elif "OPENAI" in key_name.upper():
        provider = "openai"
    
    # === 统一流程 ===
    # 不判断复杂度，直接执行
    # 记录用户消息
    import uuid
    session_id = str(uuid.uuid4())
    try:
        mp = MemoryPalace(db_path=str(MEMORY_PALACE_DB))
        mp.initialize()
        mp.log_conversation(session_id, 0, "user", message)
    except Exception as e:
        print(f"[stream_chat] Failed to log user message: {e}")
    
    yield from _stream_chat_unified(message, history, api_key, provider, MAX_TOOL_ITERATIONS, {}, session_id)


def _get_dynamic_limit(analysis: Dict) -> int:
    """根据任务复杂度动态调整上限 - 更激进的策略"""
    estimated = analysis.get("estimated_steps", 1)
    is_complex = analysis.get("is_complex", False)
    
    # 更激进的策略：给足够的空间完成任务
    if estimated <= 2:
        base_limit = 20  # 简单任务也提高上限
    elif estimated <= 5:
        base_limit = 50   # 中等任务
    elif estimated <= 10:
        base_limit = 100  # 复杂任务
    elif estimated <= 20:
        base_limit = 200  # 很复杂的任务
    else:
        base_limit = 500  # 超复杂任务
    
    # 如果检测到复杂关键词，额外增加 50%
    if is_complex:
        return min(int(base_limit * 1.5), 500)
    
    return base_limit


def _stream_chat_unified(message: str, history: list, api_key: str, provider: str, max_iterations: int = None, analysis: Dict = None, session_id: str = None) -> Generator[str, None, None]:
    """统一流程：所有任务持续输出思考过程"""
    # 收集助手回复
    assistant_reply = ""
    max_iterations = max_iterations or MAX_TOOL_ITERATIONS
    analysis = analysis or {}
    
    # Token 统计
    total_input_tokens = 0
    total_output_tokens = 0
    
    # 构建系统提示词
    system_prompt = assemble_wake_prompt(message)
    
    # 初始化消息
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message}
    ]
    
    # 添加上下文（简化版）
    if history:
        for h in history[-5:]:
            if isinstance(h, dict) and "role" in h:
                messages.insert(-1, h)
    
    full_content = ""
    iteration = 0
    
    # === 使用动态上限 ===
    hard_limit = max_iterations
    
    while iteration < MAX_TOOL_ITERATIONS:
        iteration += 1
        
        # 硬性上限检测（使用动态限制）
        if iteration >= hard_limit:
            summary = f"【执行总结】\n已完成 {iteration} 轮执行\n内容长度：{len(full_content)} 字符"
            status_msg = f'⚠️ 已达到执行上限 ({hard_limit}轮)'
            yield f"data: {json.dumps({'type': 'status', 'message': status_msg})}\n\n"
            yield f"data: {json.dumps({'type': 'token', 'content': summary})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'full_content': full_content + '\n\n' + summary})}\n\n"
            return
        
        # 调用模型
        try:
            url, model = _build_model_config(provider)
            
            # 准备请求
            import requests
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": messages,
                "tools": TOOLS_SCHEMA,
                "temperature": 0.7,
                "stream": True,
                "stream_options": {"include_usage": True}  # 启用 token 统计
            }
            
            # 流式请求
            response = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
            
            if response.status_code != 200:
                error_msg = f"API error {response.status_code}"
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                return
            
            # 解析流式响应
            tool_calls_buffer = {}  # 用字典合并增量
            content = ""
            finish_reason = None
            
            for line in response.iter_lines():
                if not line:
                    continue
                
                line = line.decode('utf-8')
                
                if line.startswith('data: '):
                    data_str = line[6:]
                    
                    
                    if data_str == '[DONE]':
                        break
                    
                    try:
                        data = json.loads(data_str)
                        
                        # 捕获 token usage（流式响应的最后一个 chunk）
                        if 'usage' in data:
                            usage = data.get('usage', {})
                            total_input_tokens = usage.get('prompt_tokens', 0)
                            total_output_tokens = usage.get('completion_tokens', 0)
                            print(f"[Stream] Token usage - Input: {total_input_tokens}, Output: {total_output_tokens}")
                        
                        if 'choices' in data and len(data['choices']) > 0:
                            choice = data['choices'][0]
                            delta = choice.get('delta', {})
                            
                            # 文本内容
                            if 'content' in delta and delta['content']:
                                content += delta['content']
                                full_content += delta['content']
                                assistant_reply += delta['content']
                                yield f"data: {json.dumps({'type': 'token', 'content': delta['content']})}\n\n"
                            
                            # 工具调用 - 增量合并
                            if 'tool_calls' in delta:
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
                    
                    except json.JSONDecodeError:
                        continue
            
            # 将合并后的 tool_calls 转换为列表
            tool_calls = list(tool_calls_buffer.values())
            
            # 检查是否有工具调用
            has_tool_calls = tool_calls and any(tc.get("function", {}).get("name") for tc in tool_calls)
            
            if not has_tool_calls:
                # 没有工具调用，检查是否完成
                if finish_reason == "stop":
                    # 正常完成，发送 done 事件
                    # 记录助手回复
                    if session_id and full_content:
                        try:
                            mp = MemoryPalace(db_path=str(MEMORY_PALACE_DB))
                            mp.initialize()
                            mp.log_conversation(session_id, 1, "assistant", full_content)
                        except Exception as e:
                            print(f"[stream_chat] Failed to log assistant reply: {e}")
                    token_info = f"\n\n---\n📊 **Token 使用**: 输入 {total_input_tokens} | 输出 {total_output_tokens} | 总计 {total_input_tokens + total_output_tokens}"
                    yield f"data: {json.dumps({'type': 'done', 'full_content': full_content + token_info})}\n\n"
                    return
                
                # 没有工具调用但也没完成
                if content.strip():
                    messages.append({"role": "assistant", "content": content})
                    # 记录助手回复
                    if session_id and full_content:
                        try:
                            mp = MemoryPalace(db_path=str(MEMORY_PALACE_DB))
                            mp.initialize()
                            mp.log_conversation(session_id, 1, "assistant", full_content)
                        except Exception as e:
                            print(f"[stream_chat] Failed to log assistant reply: {e}")
                    # 添加 token 统计到响应
                    token_info = f"\n\n---\n📊 **Token 使用**: 输入 {total_input_tokens} | 输出 {total_output_tokens} | 总计 {total_input_tokens + total_output_tokens}"
                    yield f"data: {json.dumps({'type': 'done', 'full_content': full_content + token_info})}\n\n"
                    return
                
                continue
            
            # 有工具调用，执行
            assistant_message = {"role": "assistant", "content": content or ""}
            if tool_calls:
                assistant_message["tool_calls"] = tool_calls
            messages.append(assistant_message)
            
            # 使用优化器执行工具（支持并行 + 缓存）
            optimizer = get_optimizer()
            
            # 预处理工具调用：解析 arguments JSON 字符串
            processed_tool_calls = []
            for tc in tool_calls:
                fn = tc.get("function", {})
                tool_name = fn.get("name", "")
                args_str = fn.get("arguments", "{}")
                try:
                    args = json.loads(args_str) if args_str else {}
                except:
                    args = {}
                processed_tool_calls.append({
                    "name": tool_name,
                    "arguments": args
                })
            
            # 分析是否可并行执行
            can_parallel, groups = ParallelToolExecutor.can_execute_in_parallel(processed_tool_calls)
            # groups 是分组的索引列表，如果不冲突且有多于1个工具，则可并行
            
            if can_parallel and len(tool_calls) > 1:
                # 并行执行
                yield f"data: {json.dumps({'type': 'status', 'message': f'⚡ 并行执行 {len(tool_calls)} 个工具...'})}\n\n"
                
                results = optimizer.execute_tools_parallel(tool_calls)
                
                for tool_call, result in zip(tool_calls, results):
                    function_name = tool_call.get("function", {}).get("name", "")
                    result_str = json.dumps(result.result) if isinstance(result.result, (dict, list)) else str(result.result)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", ""),
                        "name": function_name,
                        "content": result_str[:4000]
                    })
                    
                    yield f"data: {json.dumps({'type': 'status', 'message': f'✅ {function_name}'})}\n\n"
            else:
                # 串行执行（带缓存）
                for tool_call in tool_calls:
                    function_name = tool_call.get("function", {}).get("name", "")
                    arguments_str = tool_call.get("function", {}).get("arguments", "{}")
                    
                    try:
                        arguments = json.loads(arguments_str) if arguments_str else {}
                    except:
                        arguments = {}
                    
                    # 使用优化器执行（带缓存）
                    result = optimizer.execute_tool(function_name, arguments)
                    result_str = json.dumps(result.result) if isinstance(result.result, (dict, list)) else str(result.result)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", ""),
                        "name": function_name,
                        "content": result_str[:4000]
                    })
                    
                    yield f"data: {json.dumps({'type': 'status', 'message': f'✅ {function_name}'})}\n\n"
            
            continue
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'处理错误: {str(e)}'})}\n\n"
            return
    
    # 达到最大轮次
    # token_info = (已移除重复发送) f"\n\n---\n📊 **Token 使用**: 输入 {total_input_tokens} | 输出 {total_output_tokens} | 总计 {total_input_tokens + total_output_tokens}"
    # 记录助手回复
    if session_id and assistant_reply:
        try:
            mp = MemoryPalace(db_path=str(MEMORY_PALACE_DB))
            mp.initialize()
            mp.log_conversation(session_id, 1, "assistant", assistant_reply)
        except Exception as e:
            print(f"[stream_chat] Failed to log assistant reply: {e}")

