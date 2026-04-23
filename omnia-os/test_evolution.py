#!/usr/bin/env python3
"""
测试 Omnia 进化效果
"""

import sys
import os
import asyncio

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.cognition.chat_integration import OmniaChatEngine
from core.llm_client import create_llm_client


async def test_llm_client():
    """测试 LLM 客户端"""
    print("\n" + "=" * 60)
    print("测试 1: LLM 客户端")
    print("=" * 60)
    
    client = create_llm_client()
    print(f"✅ 客户端创建成功")
    print(f"   Provider: {client.config.provider}")
    print(f"   Model: {client.config.model}")
    print(f"   API Key: {client.config.api_key[:20]}...")
    
    # 测试简单对话
    print("\n测试简单对话...")
    response = await client.chat([
        {"role": "user", "content": "你好，请用一句话介绍自己"}
    ])
    
    if "error" in response:
        print(f"❌ 错误: {response['error']}")
    else:
        print(f"✅ 响应: {response['choices'][0]['message']['content'][:100]}...")
        print(f"   Provider: {response.get('provider')}")
        print(f"   Usage: {response.get('usage')}")
    
    await client.close()
    return response


async def test_chat_engine():
    """测试对话引擎"""
    print("\n" + "=" * 60)
    print("测试 2: 对话引擎（循环推理）")
    print("=" * 60)
    
    engine = OmniaChatEngine(
        max_loops=8,
        halt_threshold=0.85,
        enable_mla=False  # 暂时禁用 MLA
    )
    print("✅ 引擎创建成功")
    
    # 测试简单问题
    print("\n测试简单问题...")
    result1 = await engine.process_message("你好")
    print(f"响应: {result1['response'][:100]}...")
    print(f"元数据: {result1['metadata']}")
    
    # 测试复杂问题
    print("\n测试复杂问题...")
    result2 = await engine.process_message("分析一下量子计算的基本原理和应用前景")
    print(f"响应: {result2['response'][:150]}...")
    print(f"元数据: {result2['metadata']}")
    
    # 显示统计
    print("\n统计信息:")
    stats = engine.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    return result2


async def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("Omnia 进化测试")
    print("=" * 60)
    
    try:
        # 测试 1: LLM 客户端
        await test_llm_client()
        
        # 测试 2: 对话引擎
        await test_chat_engine()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
