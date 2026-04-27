#!/usr/bin/env python3
"""
测试本地模型集成

验证：
1. 本地 API 服务可用
2. LocalLLMClient 工作正常
3. 智能路由器选择正确
"""

import asyncio
import aiohttp
import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


async def test_api():
    """测试 llama.cpp API"""
    print("=" * 50)
    print("测试 1: llama.cpp API")
    print("=" * 50)
    
    url = "http://localhost:8080/v1/chat/completions"
    payload = {
        "model": "gemma-4-E4B-it-OBLITERATED-Q8_0.gguf",
        "messages": [{"role": "user", "content": "你好，请用一句话介绍自己"}],
        "max_tokens": 100
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=30) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data['choices'][0]['message']['content']
                    print(f"✅ API 响应成功")
                    print(f"📝 内容: {content[:100]}")
                    return True
                else:
                    print(f"❌ API 错误: {resp.status}")
                    return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False


async def test_client():
    """测试 LocalLLMClient"""
    print("\n" + "=" * 50)
    print("测试 2: LocalLLMClient")
    print("=" * 50)
    
    try:
        from core.providers.local_client import LocalLLMClient
        
        client = LocalLLMClient()
        
        # 健康检查
        if await client.health_check():
            print("✅ 健康检查通过")
        else:
            print("❌ 健康检查失败")
            return False
        
        # 聊天测试
        response = await client.chat([
            {"role": "user", "content": "1+1等于几？"}
        ])
        
        print(f"✅ 聊天成功")
        print(f"📝 响应: {response['content'][:100]}")
        print(f"📊 Token: {response['usage']}")
        
        return True
    except Exception as e:
        print(f"❌ 客户端测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_router():
    """测试智能路由器"""
    print("\n" + "=" * 50)
    print("测试 3: 智能路由器")
    print("=" * 50)
    
    try:
        from core.providers.smart_router import SmartModelRouter, ModelTier
        
        router = SmartModelRouter()
        
        # 测试模型选择
        messages = [{"role": "user", "content": "你好"}]
        model_id, tier = await router.select_model(messages)
        
        print(f"✅ 模型选择: {model_id}")
        print(f"📊 层级: {tier.value}")
        
        if tier == ModelTier.LOCAL:
            print("✅ 正确选择本地模型")
        else:
            print("⚠️ 选择了云端模型（本地可能不可用）")
        
        # 测试聊天
        response = await router.chat(messages)
        print(f"✅ 路由聊天成功")
        print(f"📝 响应: {response['content'][:100]}")
        
        return True
    except Exception as e:
        print(f"❌ 路由器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_streaming():
    """测试流式输出"""
    print("\n" + "=" * 50)
    print("测试 4: 流式输出")
    print("=" * 50)
    
    try:
        from core.providers.local_client import LocalLLMClient
        
        client = LocalLLMClient()
        
        print("📝 流式响应: ", end="", flush=True)
        async for chunk in client.stream([
            {"role": "user", "content": "数到5"}
        ]):
            print(chunk, end="", flush=True)
        print()
        
        print("✅ 流式输出成功")
        return True
    except Exception as e:
        print(f"❌ 流式测试失败: {e}")
        return False


async def main():
    """运行所有测试"""
    print("\n" + "🚀 " * 20)
    print("Omnia 本地模型集成测试")
    print("🚀 " * 20 + "\n")
    
    results = []
    
    # 测试 1: API
    results.append(("API 测试", await test_api()))
    
    # 测试 2: Client
    results.append(("Client 测试", await test_client()))
    
    # 测试 3: Router
    results.append(("Router 测试", await test_router()))
    
    # 测试 4: Streaming
    results.append(("Streaming 测试", await test_streaming()))
    
    # 汇总
    print("\n" + "=" * 50)
    print("测试汇总")
    print("=" * 50)
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, s in results if s)
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！本地模型集成成功！")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
