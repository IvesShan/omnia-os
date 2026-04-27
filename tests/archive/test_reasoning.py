#!/usr/bin/env python3
"""测试 DeepSeek v4 Flash 的 reasoning_content 处理"""
import os
import sys
import json
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get('QIANFAN_ACCESS_KEY', ''),
    base_url='https://qianfan.baidubce.com/v2',
    default_headers={'Authorization': f'Bearer {os.environ.get("QIANFAN_ACCESS_KEY", "")}'}
)

def log(msg):
    print(msg, flush=True)

# =============================================
# TEST 1: 第一轮，观察 reasoning_content 行为
# =============================================
log("=" * 60)
log("TEST 1: 第一轮推理 - 观察 reasoning_content")
log("=" * 60)

try:
    stream = client.chat.completions.create(
        model='deepseek-v4-flash',
        messages=[
            {'role': 'user', 'content': '1+1等于几？直接回答不要思考'}
        ],
        stream=True
    )
    
    full_response = ''
    full_reasoning = ''
    has_second_phase = False
    
    for chunk in stream:
        if hasattr(chunk, 'choices') and chunk.choices:
            delta = chunk.choices[0].delta
            finish_reason = chunk.choices[0].finish_reason
            
            r = getattr(delta, 'reasoning_content', None)
            c = getattr(delta, 'content', None)
            
            if r is not None:
                full_reasoning += r
            if c is not None:
                full_response += c
                has_second_phase = True
    
    log(f"  思考过程: {full_reasoning[:200] if full_reasoning else '(无)'}")
    log(f"  最终回复: {full_response[:200]}")
    log(f"  两阶段模式: {'是' if has_second_phase else '否'}")
    log("  ✅ 第一轮正常")
    
except Exception as e:
    log(f"  ❌ 异常: {e}")
    sys.exit(1)

# =============================================
# TEST 2: 第二轮 - 不带 reasoning_content
# =============================================
log()
log("=" * 60)
log("TEST 2: 第二轮 - 不带 reasoning_content 回传")
log("=" * 60)

try:
    stream2 = client.chat.completions.create(
        model='deepseek-v4-flash',
        messages=[
            {'role': 'user', 'content': '1+1等于几？直接回答不要思考'},
            {'role': 'assistant', 'content': full_response},
            {'role': 'user', 'content': '那2+2呢？'}
        ],
        stream=True
    )
    
    response2 = ''
    reasoning2 = ''
    ok = True
    
    for chunk in stream2:
        if hasattr(chunk, 'choices') and chunk.choices:
            delta = chunk.choices[0].delta
            r = getattr(delta, 'reasoning_content', None)
            c = getattr(delta, 'content', None)
            if r is not None:
                reasoning2 += r
            if c is not None:
                response2 += c
    
    log(f"  第二轮思考: {reasoning2[:200] if reasoning2 else '(无)'}")
    log(f"  第二轮回复: {response2[:200]}")
    log("  ✅ 第二轮正常（不带 reasoning_content 没事）")
    
except Exception as e:
    log(f"  ❌ 异常: {e}")
    if hasattr(e, 'response'):
        log(f"  HTTP状态码: {e.response.status_code}")
        log(f"  响应: {getattr(e.response, 'text', 'N/A')}")
    ok = False

# =============================================
# TEST 3: 有推理内容时传 reasoning_content
# =============================================
log()
log("=" * 60)
log("TEST 3: 带 reasoning_content 回传")
log("=" * 60)

try:
    stream3 = client.chat.completions.create(
        model='deepseek-v4-flash',
        messages=[
            {'role': 'user', 'content': '解释一下量子计算的基本原理，用简单的话说'},
            {'role': 'assistant', 'content': '', 'reasoning_content': full_reasoning if full_reasoning else None},
            {'role': 'user', 'content': '再说详细点'}
        ],
        stream=True
    )
    
    response3 = ''
    reasoning3 = ''
    
    for chunk in stream3:
        if hasattr(chunk, 'choices') and chunk.choices:
            delta = chunk.choices[0].delta
            r = getattr(delta, 'reasoning_content', None)
            c = getattr(delta, 'content', None)
            if r is not None:
                reasoning3 += r
            if c is not None:
                response3 += c
    
    log(f"  思考: {reasoning3[:100] if reasoning3 else '(无)'}")
    log(f"  回复: {response3[:200]}")
    log("  ✅ 第三轮正常（带 reasoning_content 也没事）")
    
except Exception as e:
    log(f"  ❌ 异常: {e}")
    if hasattr(e, 'response'):
        log(f"  状态码: {e.response.status_code}")
        log(f"  响应: {getattr(e.response, 'text', 'N/A')}")

# =============================================
# TEST 4: 工具调用场景 - 模拟 OpenAI 库的自动处理
# =============================================
log()
log("=" * 60)
log("TEST 4: 模拟工具调用 - 多轮带 reasoning")
log("=" * 60)

try:
    # 第一轮：让模型先做思考
    stream4 = client.chat.completions.create(
        model='deepseek-v4-flash',
        messages=[
            {'role': 'user', 'content': '用工具查一下今天的日期，然后告诉我'}
        ],
        tools=[{
            'type': 'function',
            'function': {
                'name': 'get_date',
                'description': '获取当前日期',
                'parameters': {
                    'type': 'object',
                    'properties': {},
                    'required': []
                }
            }
        }],
        stream=True
    )
    
    response4 = ''
    reasoning4 = ''
    tool_calls = None
    
    for chunk in stream4:
        if hasattr(chunk, 'choices') and chunk.choices:
            delta = chunk.choices[0].delta
            r = getattr(delta, 'reasoning_content', None)
            c = getattr(delta, 'content', None)
            
            if r is not None:
                reasoning4 += r
            if c is not None:
                response4 += c
            
            # 检查 tool_calls
            tc = getattr(delta, 'tool_calls', None)
            if tc:
                if tool_calls is None:
                    tool_calls = []
                for t in tc:
                    if t.index is not None:
                        while len(tool_calls) <= t.index:
                            tool_calls.append({'function': {'name': '', 'arguments': ''}})
                        tc_obj = tool_calls[t.index]
                        if t.function and t.function.name:
                            tc_obj['function']['name'] = t.function.name
                        if t.function and t.function.arguments:
                            tc_obj['function']['arguments'] += t.function.arguments
    
    log(f"  思考: {reasoning4[:200] if reasoning4 else '(无)'}")
    if tool_calls:
        for i, tc in enumerate(tool_calls):
            log(f"  工具调用[{i}]: {tc['function']['name']}({tc['function']['arguments']})")
    else:
        log(f"  回复: {response4[:200]}")
        log("  ⚠️ 没有触发工具调用，但没关系")
    
    log("  ✅ 第四轮正常（工具调用场景）")
    
except Exception as e:
    log(f"  ❌ 异常: {e}")
    if hasattr(e, 'response'):
        log(f"  状态码: {e.response.status_code}")
        log(f"  响应: {getattr(e.response, 'text', 'N/A')}")

log()
log("=" * 60)
log("所有测试完成")
log("=" * 60)
