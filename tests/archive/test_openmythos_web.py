#!/usr/bin/env python3
"""Test OpenMythos Web API"""

import requests
import json

BASE_URL = "http://localhost:5001"

def test_health():
    """测试健康检查"""
    print("\n=== 测试健康检查 ===")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        print(f"状态: {response.status_code}")
        print(f"结果: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return True
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False

def test_analyze():
    """测试复杂度分析"""
    print("\n=== 测试复杂度分析 ===")
    
    try:
        response = requests.post(f"{BASE_URL}/api/openmythos/analyze", json={
            "message": "设计一个分布式系统架构"
        }, timeout=10)
        
        print(f"状态: {response.status_code}")
        print(f"结果: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return True
    except Exception as e:
        print(f"❌ 复杂度分析失败: {e}")
        return False

def test_chat():
    """测试对话"""
    print("\n=== 测试对话 ===")
    
    try:
        response = requests.post(f"{BASE_URL}/api/openmythos/chat", json={
            "message": "你好"
        }, timeout=30)
        
        print(f"状态: {response.status_code}")
        result = response.json()
        print(f"答案: {result.get('answer', '')[:200]}")
        print(f"置信度: {result.get('confidence')}")
        print(f"迭代次数: {result.get('iterations')}")
        return True
    except Exception as e:
        print(f"❌ 对话失败: {e}")
        return False

def test_stats():
    """测试统计信息"""
    print("\n=== 测试统计信息 ===")
    
    try:
        response = requests.get(f"{BASE_URL}/api/openmythos/stats", timeout=5)
        
        print(f"状态: {response.status_code}")
        print(f"结果: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return True
    except Exception as e:
        print(f"❌ 统计信息失败: {e}")
        return False

if __name__ == "__main__":
    print("OpenMythos Web API 测试")
    print("=" * 60)
    
    results = []
    results.append(("健康检查", test_health()))
    results.append(("复杂度分析", test_analyze()))
    results.append(("对话", test_chat()))
    results.append(("统计信息", test_stats()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
    
    success_count = sum(1 for _, s in results if s)
    print(f"\n总计: {success_count}/{len(results)} 通过")
