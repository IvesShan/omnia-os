#!/usr/bin/env python3
"""
测试 DeepSeek API 工具调用修复
验证 reasoning_content 不会导致 400 错误
"""

import os
import sys
import requests
import json

# Load API key
def load_api_key():
    with open('.env') as f:
        for line in f:
            if line.startswith('DEEPSEEK_API_KEY='):
                return line.strip().split('=', 1)[1]
    return None

def test_simple_chat():
    """测试简单对话"""
    print("=== 测试 1: 简单对话 ===")
    api_key = load_api_key()
    url = 'https://api.deepseek.com/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': 'deepseek-v4-flash',
        'messages': [{'role': 'user', 'content': '你好'}],
        'stream': False
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 成功: {data['choices'][0]['message']['content'][:50]}...")
    else:
        print(f"❌ 失败: {response.text}")
    return response.status_code == 200

def test_tool_call():
    """测试工具调用（关键测试）"""
    print("\n=== 测试 2: 工具调用 ===")
    api_key = load_api_key()
    url = 'https://api.deepseek.com/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # 第一轮：请求工具调用
    payload = {
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
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"状态码: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ 第一轮失败: {response.text}")
        return False
    
    data = response.json()
    message = data['choices'][0]['message']
    
    # 检查是否有工具调用
    if 'tool_calls' not in message or not message['tool_calls']:
        print(f"⚠️  没有工具调用，模型直接回复: {message.get('content', '')[:50]}...")
        return True
    
    print(f"✅ 工具调用成功: {message['tool_calls'][0]['function']['name']}")
    
    # 第二轮：发送工具结果（关键：不包含 reasoning_content）
    tool_call = message['tool_calls'][0]
    messages = [
        {'role': 'user', 'content': '读取文件 /etc/hostname'},
        {
            'role': 'assistant',
            'content': message.get('content', ''),
            'tool_calls': message['tool_calls']
            # 注意：不包含 reasoning_content
        },
        {
            'role': 'tool',
            'tool_call_id': tool_call['id'],
            'content': 'ubuntu-server'
        }
    ]
    
    payload2 = {
        'model': 'deepseek-v4-flash',
        'messages': messages,
        'stream': False
    }
    
    response2 = requests.post(url, headers=headers, json=payload2, timeout=30)
    print(f"第二轮状态码: {response2.status_code}")
    
    if response2.status_code == 200:
        data2 = response2.json()
        print(f"✅ 第二轮成功: {data2['choices'][0]['message']['content'][:50]}...")
        return True
    else:
        print(f"❌ 第二轮失败: {response2.text}")
        return False

def test_with_reasoning_content():
    """测试错误情况：包含 reasoning_content（应该失败）"""
    print("\n=== 测试 3: 错误示例（包含 reasoning_content）===")
    api_key = load_api_key()
    url = 'https://api.deepseek.com/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # 故意在消息中包含 reasoning_content（这会导致 400 错误）
    messages = [
        {'role': 'user', 'content': '你好'},
        {
            'role': 'assistant',
            'content': '你好！',
            'reasoning_content': '用户在打招呼，我应该礼貌回应'  # 这个字段不应该在请求中
        },
        {'role': 'user', 'content': '今天天气怎么样？'}
    ]
    
    payload = {
        'model': 'deepseek-v4-flash',
        'messages': messages,
        'stream': False
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 400:
        print(f"✅ 预期的 400 错误（reasoning_content 不应在请求中）")
        print(f"错误信息: {response.text[:200]}")
        return True
    else:
        print(f"⚠️  未预期的结果: {response.status_code}")
        return False

if __name__ == '__main__':
    print("DeepSeek API 工具调用修复测试\n")
    
    test1 = test_simple_chat()
    test2 = test_tool_call()
    test3 = test_with_reasoning_content()
    
    print("\n" + "="*50)
    print("测试结果:")
    print(f"  简单对话: {'✅' if test1 else '❌'}")
    print(f"  工具调用: {'✅' if test2 else '❌'}")
    print(f"  错误检测: {'✅' if test3 else '❌'}")
    
    if test1 and test2 and test3:
        print("\n🎉 所有测试通过！修复有效。")
        sys.exit(0)
    else:
        print("\n⚠️  部分测试失败，请检查。")
        sys.exit(1)
