#!/usr/bin/env python3
"""
模型切换功能测试脚本
"""

import sys
import asyncio
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.providers.smart_router import SmartModelRouter, ModelMode


async def test_model_router():
    """测试模型路由器"""
    print("=" * 60)
    print("🧪 模型切换功能测试")
    print("=" * 60)
    
    # 初始化路由器
    router = SmartModelRouter()
    print(f"\n✅ SmartModelRouter 初始化成功")
    print(f"   当前模式: {router.mode.value}")
    print(f"   本地模型: {router.config.local_model}")
    
    # 测试模式切换
    print("\n📋 测试模式切换...")
    
    # 切换到本地模式
    print("\n1️⃣ 切换到本地模式")
    router.set_mode(ModelMode.LOCAL_ONLY)
    print(f"   ✅ 当前模式: {router.mode.value}")
    
    # 切换到云端模式
    print("\n2️⃣ 切换到云端模式")
    router.set_mode("cloud_only")
    print(f"   ✅ 当前模式: {router.mode.value}")
    
    # 切换到自动模式
    print("\n3️⃣ 切换到自动模式")
    router.set_mode("auto")
    print(f"   ✅ 当前模式: {router.mode.value}")
    
    # 测试本地模型可用性
    print("\n📋 测试本地模型可用性...")
    try:
        available = await router.is_local_available()
        if available:
            print(f"   ✅ 本地模型可用")
        else:
            print(f"   ⚠️  本地模型不可用（llama.cpp server 未运行）")
    except Exception as e:
        print(f"   ❌ 检查失败: {e}")
    
    # 测试复杂度估算
    print("\n📋 测试复杂度估算...")
    messages = [
        {"role": "user", "content": "你好，请介绍一下你自己"}
    ]
    complexity = router.estimate_complexity(messages)
    print(f"   ✅ 估算复杂度: {complexity} tokens")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)


def test_api_endpoints():
    """测试 API 端点（需要后端运行）"""
    import requests
    
    print("\n" + "=" * 60)
    print("🌐 API 端点测试")
    print("=" * 60)
    
    base_url = "http://localhost:5001"
    
    # 测试状态端点
    print("\n📋 测试 /api/model/status...")
    try:
        response = requests.get(f"{base_url}/api/model/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 当前模式: {data.get('mode_display')}")
            print(f"   ✅ 本地可用: {data.get('local_available')}")
        else:
            print(f"   ❌ 状态码: {response.status_code}")
    except Exception as e:
        print(f"   ⚠️  后端未运行: {e}")
        return
    
    # 测试切换端点
    print("\n📋 测试 /api/model/switch...")
    try:
        response = requests.post(
            f"{base_url}/api/model/switch",
            json={"mode": "cloud_only"},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 切换成功: {data.get('mode_display')}")
        else:
            print(f"   ❌ 切换失败: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    # 测试健康检查
    print("\n📋 测试 /api/model/health...")
    try:
        response = requests.get(f"{base_url}/api/model/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 本地可用: {data.get('local_available')}")
            print(f"   ✅ 响应时间: {data.get('response_time_ms')}ms")
            if data.get('gpu'):
                gpu = data['gpu']
                print(f"   ✅ GPU 内存: {gpu.get('memory_percent')}%")
        else:
            print(f"   ❌ 状态码: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    print("\n" + "=" * 60)
    print("✅ API 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    # 测试路由器
    asyncio.run(test_model_router())
    
    # 测试 API（可选）
    print("\n是否测试 API 端点？(需要后端运行) [y/N]: ", end="")
    choice = input().strip().lower()
    if choice == 'y':
        test_api_endpoints()
