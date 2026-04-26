#!/usr/bin/env python3
"""
测试 LLM 客户端进化
"""

import asyncio
import sys
import os

# 添加 src 到路径
sys.path.insert(0, '/home/shan/omnia-os/omnia-os/src')

from core.llm_client import LLMClient


async def test_llm_client():
    """测试 LLM 客户端"""
    
    print("=" * 60)
    print("测试 Omnia LLM 客户端进化")
    print("=" * 60)
    print()
    
    # 创建客户端
    client = LLMClient()
    
    print(f"✅ 客户端初始化成功")
    print(f"   Provider: {client.config.provider}")
    print(f"   Model: {client.config.model}")
    print(f"   API Key: {client.config.api_key[:20]}...")
    print()
    
    # 测试简单对话
    print("📝 测试 1: 简单对话")
    print("-" * 40)
    
    messages = [
        {"role": "user", "content": "你好，请用一句话介绍你自己"}
    ]
    
    result = await client.chat(messages)
    
    if "error" in result:
        print(f"❌ 错误: {result['error']}")
    else:
        content = result["choices"][0]["message"]["content"]
        print(f"✅ 响应: {content[:200]}...")
        print(f"   Provider: {result.get('provider', 'unknown')}")
        print(f"   Usage: {result.get('usage', {})}")
    
    print()
    
    # 测试复杂对话
    print("📝 测试 2: 复杂对话")
    print("-" * 40)
    
    messages = [
        {"role": "user", "content": "请解释一下什么是量子计算，用简单的语言"}
    ]
    
    result = await client.chat(messages)
    
    if "error" in result:
        print(f"❌ 错误: {result['error']}")
    else:
        content = result["choices"][0]["message"]["content"]
        print(f"✅ 响应: {content[:200]}...")
        print(f"   Provider: {result.get('provider', 'unknown')}")
        print(f"   Usage: {result.get('usage', {})}")
    
    print()
    print("=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)
    
    # 关闭客户端
    await client.close()


if __name__ == "__main__":
    asyncio.run(test_llm_client())
