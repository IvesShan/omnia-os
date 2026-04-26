#!/usr/bin/env python3
"""
测试 LLM 集成

测试：
1. LLM 客户端是否正常工作
2. LLM 推理适配器是否正常工作
"""

import asyncio
import sys
import os

# 添加路径
sys.path.insert(0, '/home/shan/omnia-os/omnia-os/src')

from core.llm_client import LLMClient, create_llm_client
from core.cognition.llm_reasoning_adapter import LLMReasoningAdapter, create_llm_reasoning_adapter


async def test_llm_client():
    """测试 LLM 客户端"""
    print("\n" + "="*50)
    print("测试 1: LLM 客户端")
    print("="*50)
    
    client = create_llm_client()
    
    print(f"Provider: {client.config.provider}")
    print(f"Model: {client.config.model}")
    print(f"API Key: {'已配置' if client.config.api_key else '未配置'}")
    
    if not client.config.api_key:
        print("⚠️  未配置 API Key，跳过实际调用测试")
        return False
    
    # 测试简单调用
    print("\n测试调用 LLM...")
    try:
        response = await client.chat([
            {"role": "user", "content": "你好，请用一句话介绍你自己。"}
        ])
        
        if "error" in response:
            print(f"❌ 调用失败: {response['error']}")
            return False
        
        choices = response.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            print(f"✅ LLM 响应: {content[:100]}...")
            return True
        else:
            print("❌ 无响应内容")
            return False
            
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False
    finally:
        await client.close()


async def test_reasoning_adapter():
    """测试推理适配器"""
    print("\n" + "="*50)
    print("测试 2: LLM 推理适配器")
    print("="*50)
    
    adapter = create_llm_reasoning_adapter(max_loops=2)
    
    print(f"LLM 客户端: {adapter.llm_client.config.provider}")
    print(f"推理引擎: {type(adapter.reasoning_engine).__name__}")
    
    # 测试处理
    print("\n测试处理用户输入...")
    try:
        result = await adapter.process("你好，你是谁？")
        
        print(f"✅ 响应深度: {result['depth']}")
        print(f"✅ 置信度: {result['confidence']}")
        print(f"✅ 规划步骤: {result['plan']}")
        print(f"✅ 响应: {result['response'][:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("Omnia LLM 集成测试")
    print("="*60)
    
    results = {}
    
    # 测试 1: LLM 客户端
    results["llm_client"] = await test_llm_client()
    
    # 测试 2: 推理适配器
    results["reasoning_adapter"] = await test_reasoning_adapter()
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")
    
    all_passed = all(results.values())
    print(f"\n总体: {'✅ 全部通过' if all_passed else '❌ 部分失败'}")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
