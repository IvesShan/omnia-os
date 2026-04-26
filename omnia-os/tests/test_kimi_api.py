#!/usr/bin/env python3
"""测试 Kimi API 连接"""

import os
import sys
import asyncio

# 添加项目路径
sys.path.insert(0, '/home/shan/omnia-os/omnia-os/src')

from core.llm_client import LLMClient, LLMConfig


async def test_kimi_api():
    """测试 Kimi API"""
    
    # 配置 Kimi API
    config = LLMConfig(
        provider="kimi",
        api_key="sk-kimi-IPff6UIJUNHm7FHpVj1sAgL49qsz8CStU5ubvUZiYWgSKthWBRGKzefc5UJcexWf",
        base_url="https://api.moonshot.cn/v1",
        model="moonshot-v1-8k"
    )
    
    client = LLMClient(config)
    
    print("🔍 测试 Kimi API 连接...")
    print(f"   API Key: {config.api_key[:20]}...")
    print(f"   Base URL: {config.base_url}")
    print(f"   Model: {config.model}")
    
    # 测试简单对话
    messages = [
        {"role": "user", "content": "你好，请用一句话介绍你自己。"}
    ]
    
    print("\n📤 发送消息: 你好，请用一句话介绍你自己。")
    
    response = await client.chat(messages)
    
    if "error" in response:
        print(f"\n❌ API 调用失败: {response['error']}")
    else:
        print("\n✅ API 调用成功！")
        content = response["choices"][0]["message"]["content"]
        print(f"\n🤖 Kimi 回复: {content}")
        
        # 显示 token 使用情况
        usage = response.get("usage", {})
        if usage:
            print(f"\n📊 Token 使用:")
            print(f"   输入: {usage.get('prompt_tokens', 0)}")
            print(f"   输出: {usage.get('completion_tokens', 0)}")
            print(f"   总计: {usage.get('total_tokens', 0)}")
    
    await client.close()
    print("\n✨ 测试完成！")


if __name__ == "__main__":
    asyncio.run(test_kimi_api())
