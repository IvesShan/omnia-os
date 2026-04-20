# Omnia Stream Chat - 统一流程版本
"""
统一流程：所有任务走同一个流程
- 自动分析复杂度
- 动态调整迭代上限
- 持续输出思考过程
- 用户看到统一的体验
"""

from __future__ import annotations

import json
import re
import time
import traceback
from typing import Dict, Generator

from omnia.wake import assemble_wake_prompt
from omnia.chat import _load_api_key, _build_model_config
from omnia.tool_optimizer import ToolExecutionOptimizer
from core.actuator.tool_registry import TOOLS_SCHEMA, dispatch_tool
from core.actuator.plan_store import get_plan_store

PROJECT_ROOT = Path(__file__).parent.parent.parent
MAX_TOOL_ITERATIONS = 50

# 全局优化器实例
_optimizer = None


def get_optimizer():
    """获取优化器实例"""
    global _optimizer
    if _optimizer is None:
        _optimizer = ToolExecutionOptimizer(
            enable_cache=True,
            enable_recovery=True,
            enable_parallel=True,
            max_tokens_per_round=8000,
            max_rounds=MAX_TOOL_ITERATIONS
        )
    return _optimizer


def stream_chat(message: str, history: list = None) -> Generator[str, None, None]:
    """
    统一流程：所有任务持续输出思考过程
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
    
    # 分析任务复杂度
    analysis = analyze_task_complexity(message)
    
    # 动态调整上限
    dynamic_limit = get_dynamic_limit(analysis)
    yield f"data: {json.dumps({'type': 'config', 'max_iterations': dynamic_limit, 'complexity': analysis}, ensure_ascii=False)}\n\n"
    
    # === 统一流程 ===
    yield from stream_chat_unified(message, history, api_key, provider, dynamic_limit, analysis)


def analyze_task_complexity(message: str) -> Dict:
    """分析任务复杂度"""
    # 1. 数字编号格式
    numbered_steps = len(re.findall(r'\d[)\.]\s*', message))
    
    # 2. 分隔符
    separator_steps = message.count("和") + message.count("然后") + message.count("接着") + message.count("之后")
    
    # 3. 动词数量
    action_verbs = ["读取", "列出", "执行", "显示", "查看", "检查", "分析", "生成", "发送", "创建", "删除", "修改", "搜索", "下载", "上传"]
    action_count = sum(1 for verb in action_verbs if verb in message)
    
    estimated_steps = max(numbered_steps, separator_steps + 1, action_count)
    
    # 复杂关键词
    complex_keywords = [
        "同时", "然后", "接着", "之后", "完成", "全部", "所有",
        "批量", "多个", "一系列", "逐步", "按顺序", "依次",
        "分析", "整理", "汇总", "生成报告", "完整"
    ]
    
    is_complex = any(kw in message for kw in complex_keywords) or estimated_steps > 3
    
    return {
        "is_complex": is_complex,
        "estimated_steps": estimated_steps,
        "numbered_steps": numbered_steps,
        "action_count": action_count,
    }


def get_dynamic_limit(analysis: Dict) -> int:
    """根据任务复杂度动态调整上限"""
    estimated = analysis.get("estimated_steps", 1)
    is_complex = analysis.get("is_complex", False)
    
    if estimated <= 2:
        base_limit = 20
    elif estimated <= 5:
        base_limit = 50
    elif estimated <= 10:
        base_limit = 100
    elif estimated <= 20:
        base_limit = 200
    else:
        base_limit = 500
    
    if is_complex:
        return min(int(base_limit * 1.5), 500)
    
    return base_limit


def stream_chat_unified(
    message: str, 
    history: list, 
    api_key: str, 
    provider: str, 
    max_iterations: int,
    analysis: Dict
) -> Generator[str, None, None]:
    """统一流程：持续输出思考过程"""
    
    # 构建系统提示词
    system_prompt = assemble_wake_prompt(message)
    
    # 初始化消息
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message}
    ]
    
    # 添加历史
    if history:
        for h in history[-5:]:
            if isinstance(h, dict) and "role" in h:
                messages.insert(-1, h)
    
    full_content = ""
    iteration = 0
    hard_limit = max_iterations
    
    # === 主循环 ===
    while iteration < MAX_TOOL_ITERATIONS:
        iteration += 1
        
        # 硬性上限检测
        if iteration >= hard_limit:
            summary = f"\n\n【执行总结】已完成 {iteration} 轮，内容长度 {len(full_content)} 字符"
            yield f"data: {json.dumps({'type': 'token', 'content': summary}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'full_content': full_content + summary}, ensure_ascii=False)}\n\n"
            return
        
        # === 持续思考输出 ===
        if iteration == 1:
            yield f"data: {json.dumps({'type': 'token', 'content': '🤔 思考中...'}, ensure_ascii=False)}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'token', 'content': f'\n继续第 {iteration} 轮...'}, ensure_ascii=False)}\n\n"
        
        # 调用模型
        try:
            import requests
            
            url, model = _build_model_config(provider)
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": messages,
                "tools": TOOLS_SCHEMA,
                "tool_choice": "auto",
                "stream": True,
                "temperature": 0.7,
            }
            
            response = requests.post(url, headers=headers, json=payload, stream=True, timeout=300)
            
            # 处理流式响应
            tool_calls = []
            content_chunks = []
            finish_reason = None
            
            for line in response.iter_lines():
                if not line:
                    continue
                
                line_text = line.decode('utf-8')
                if not line_text.startswith('data: '):
                    continue
                
                data_str = line_text[6:]
                if data_str == '[DONE]':
                    break
                
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                
                delta = data.get('choices', [{}])[0].get('delta', {})
                finish_reason = data.get('choices', [{}])[0].get('finish_reason')
                
                # 内容
                if 'content' in delta and delta['content']:
                    content_chunks.append(delta['content'])
                    yield f"data: {json.dumps({'type': 'token', 'content': delta['content']}, ensure_ascii=False)}\n\n"
                
                # 工具调用
                if 'tool_calls' in delta:
                    for tc in delta['tool_calls']:
                        idx = tc.get('index', 0)
                        
                        # 扩展列表
                        while len(tool_calls) <= idx:
                            tool_calls.append({
                                'id': '',
                                'type': 'function',
                                'function': {'name': '', 'arguments': ''}
                            })
                        
                        # 合并增量
                        if 'id' in tc:
                            tool_calls[idx]['id'] = tc['id']
                        if 'function' in tc:
                            if 'name' in tc['function']:
                                tool_calls[idx]['function']['name'] = tc['function']['name']
                            if 'arguments' in tc['function']:
                                tool_calls[idx]['function']['arguments'] += tc['function']['arguments']
            
            # 累积内容
            content = ''.join(content_chunks)
            if content:
                full_content += content
            
            # 检查是否需要执行工具
            if finish_reason == 'tool_calls' or (tool_calls and not content):
                # 执行工具
                valid_tool_calls = [tc for tc in tool_calls if tc['function']['name']]
                
                if valid_tool_calls:
                    # 输出工具执行信息
                    tool_names = [tc['function']['name'] for tc in valid_tool_calls]
                    yield f"data: {json.dumps({'type': 'token', 'content': f'\n⚡ 执行工具: {\"、\".join(tool_names)}...'}, ensure_ascii=False)}\n\n"
                    
                    # 执行工具
                    for tc in valid_tool_calls:
                        tool_name = tc['function']['name']
                        try:
                            tool_args = json.loads(tc['function']['arguments'])
                        except json.JSONDecodeError:
                            tool_args = {}
                        
                        try:
                            result = dispatch_tool(tool_name, tool_args)
                            result_str = str(result)[:500] if result else '完成'
                            yield f"data: {json.dumps({'type': 'token', 'content': f'\n✅ {tool_name}: {result_str}'}, ensure_ascii=False)}\n\n"
                            
                            # 添加到消息
                            messages.append({
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [{
                                    "id": tc['id'],
                                    "type": "function",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": tc['function']['arguments']
                                    }
                                }]
                            })
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc['id'],
                                "content": str(result)[:2000] if result else '完成'
                            })
                        except Exception as e:
                            yield f"data: {json.dumps({'type': 'token', 'content': f'\n❌ {tool_name} 失败: {str(e)}'}, ensure_ascii=False)}\n\n"
                    
                    # 继续循环
                    continue
            
            # 完成
            if finish_reason == 'stop' or not tool_calls:
                yield f"data: {json.dumps({'type': 'done', 'full_content': full_content}, ensure_ascii=False)}\n\n"
                return
        
        except Exception as e:
            error_msg = f"执行失败: {str(e)}"
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'full_content': full_content + f'\\n\\n错误: {error_msg}'}, ensure_ascii=False)}\n\n"
            return
    
    # 达到迭代上限
    yield f"data: {json.dumps({'type': 'done', 'full_content': full_content}, ensure_ascii=False)}\n\n"
