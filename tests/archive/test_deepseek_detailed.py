#!/usr/bin/env python3
"""
详细测试 DeepSeek API 工具调用
逐步排查 400 错误的原因
"""

import os
import requests
import json

def load_api_key():
    with open('.env') as f:
        for line in f:
            if line.startswith('DEEPSEEK_API_KEY='):
                return line.strip().split('=', 1)[1]
    return None

def test_tool_call_detailed():
    """详细测试工具调用的每个步骤"""
    api_key = load_api_key()
    url = 'https://api.deepseek.com/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    print("=== 步骤 1: 第一轮请求（工具调用）===")
    payload1 = {
        'model': 'deepseek-v4-flash',
        'messages': [{'role': 'user', 'content': '读取文件 /etc/hostname'}],
        'tools': [{
            'type': 'function',
            'function': {
                'name': 'read_file',
                'description': '读取文件内容',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'path': {'type': 'string', 'description': '文件路径'}
                    },
                    'required': ['path']
                }
            }
        }],
        'stream': False
    }
    
    response1 = requests.post(url, headers=headers, json=payload1, timeout=30)
    print(f"状态码: {response1.status_code}")
    
    if response1.status_code != 200:
        print(f"❌ 失败: {response1.text}")
        return
    
    data1 = response1.json()
    message1 = data1['choices'][0]['message']
    
    print(f"\n第一轮响应:")
    print(f"  content: {message1.get('content', '')[:100]}")
    print(f"  reasoning_content: {message1.get('reasoning_content', '')[:100]}")
    print(f"  tool_calls: {message1.get('tool_calls', [])}")
    
    if 'tool_calls' not in message1 or not message1['tool_calls']:
        print("⚠️  没有工具调用")
        return
    
    tool_call = message1['tool_calls'][0]
    print(f"\n工具调用详情:")
    print(f"  id: {tool_call.get('id')}")
    print(f"  type: {tool_call.get('type')}")
    print(f"  function.name: {tool_call['function'].get('name')}")
    print(f"  function.arguments: {tool_call['function'].get('arguments')}")
    
    # 测试不同的第二轮请求格式
    print("\n=== 步骤 2: 测试不同的第二轮请求格式 ===")
    
    # 格式 1: 包含 reasoning_content
    print("\n--- 格式 1: 包含 reasoning_content ---")
    messages1 = [
        {'role': 'user', 'content': '读取文件 /etc/hostname'},
        {
            'role': 'assistant',
            'content': message1.get('content', ''),
            'reasoning_content': message1.get('reasoning_content', ''),
            'tool_calls': message1['tool_calls']
        },
        {
            'role': 'tool',
            'tool_call_id': tool_call['id'],
            'content': 'ubuntu-server'
        }
    ]
    
    payload2_1 = {
        'model': 'deepseek-v4-flash',
        'messages': messages1,
        'stream': False
    }
    
    response2_1 = requests.post(url, headers=headers, json=payload2_1, timeout=30)
    print(f"状态码: {response2_1.status_code}")
    if response2_1.status_code == 200:
        print(f"✅ 成功")
    else:
        print(f"❌ 失败: {response2_1.text[:300]}")
    
    # 格式 2: 不包含 reasoning_content
    print("\n--- 格式 2: 不包含 reasoning_content ---")
    messages2 = [
        {'role': 'user', 'content': '读取文件 /etc/hostname'},
        {
            'role': 'assistant',
            'content': message1.get('content', ''),
            'tool_calls': message1['tool_calls']
        },
        {
            'role': 'tool',
            'tool_call_id': tool_call['id'],
            'content': 'ubuntu-server'
        }
    ]
    
    payload2_2 = {
        'model': 'deepseek-v4-flash',
        'messages': messages2,
        'stream': False
    }
    
    response2_2 = requests.post(url, headers=headers, json=payload2_2, timeout=30)
    print(f"状态码: {response2_2.status_code}")
    if response2_2.status_code == 200:
        print(f"✅ 成功")
    else:
        print(f"❌ 失败: {response2_2.text[:300]}")
    
    # 格式 3: content 为空字符串
    print("\n--- 格式 3: content 为空字符串 ---")
    messages3 = [
        {'role': 'user', 'content': '读取文件 /etc/hostname'},
        {
            'role': 'assistant',
            'content': '',
            'reasoning_content': message1.get('reasoning_content', ''),
            'tool_calls': message1['tool_calls']
        },
        {
            'role': 'tool',
            'tool_call_id': tool_call['id'],
            'content': 'ubuntu-server'
        }
    ]
    
    payload2_3 = {
        'model': 'deepseek-v4-flash',
        'messages': messages3,
        'stream': False
    }
    
    response2_3 = requests.post(url, headers=headers, json=payload2_3, timeout=30)
    print(f"状态码: {response2_3.status_code}")
    if response2_3.status_code == 200:
        print(f"✅ 成功")
    else:
        print(f"❌ 失败: {response2_3.text[:300]}")
    
    # 格式 4: 不包含 content
    print("\n--- 格式 4: 不包含 content ---")
    messages4 = [
        {'role': 'user', 'content': '读取文件 /etc/hostname'},
        {
            'role': 'assistant',
            'reasoning_content': message1.get('reasoning_content', ''),
            'tool_calls': message1['tool_calls']
        },
        {
            'role': 'tool',
            'tool_call_id': tool_call['id'],
            'content': 'ubuntu-server'
        }
    ]
    
    payload2_4 = {
        'model': 'deepseek-v4-flash',
        'messages': messages4,
        'stream': False
    }
    
    response2_4 = requests.post(url, headers=headers, json=payload2_4, timeout=30)
    print(f"状态码: {response2_4.status_code}")
    if response2_4.status_code == 200:
        print(f"✅ 成功")
    else:
        print(f"❌ 失败: {response2_4.text[:300]}")

if __name__ == '__main__':
    test_tool_call_detailed()
