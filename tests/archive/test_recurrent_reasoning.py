#!/usr/bin/env python3
"""
测试循环推理引擎集成

测试场景：
1. 简单问题（应该1-2次循环就停）
2. 中等问题（应该3-4次循环）
3. 复杂问题（应该5-6次循环）
"""

import requests
import json
import time

BASE_URL = "http://localhost:5001"

def test_simple_query():
    """测试简单问题"""
    print("\n" + "="*60)
    print("测试 1: 简单问题")
    print("="*60)
    
    payload = {
        "message": "你好，你是谁？",
        "context": {}
    }
    
    start = time.time()
    response = requests.post(
        f"{BASE_URL}/api/openmythos/chat",
        json=payload,
        timeout=30
    )
    elapsed = time.time() - start
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 成功")
        print(f"  - 回答: {result.get('answer', 'N/A')[:100]}...")
        print(f"  - 置信度: {result.get('confidence', 0):.2f}")
        print(f"  - 迭代次数: {result.get('iterations', 0)}")
        print(f"  - 复杂度: {result.get('complexity', 'N/A')}")
        print(f"  - 耗时: {elapsed:.2f}s")
        print(f"  - 早停: {result.get('stopped_early', False)}")
        return True
    else:
        print(f"❌ 失败: {response.status_code}")
        print(f"  错误: {response.text}")
        return False


def test_medium_query():
    """测试中等问题"""
    print("\n" + "="*60)
    print("测试 2: 中等问题")
    print("="*60)
    
    payload = {
        "message": "请分析一下无人机维修市场的现状和未来发展趋势",
        "context": {
            "domain": "无人机维修"
        }
    }
    
    start = time.time()
    response = requests.post(
        f"{BASE_URL}/api/openmythos/chat",
        json=payload,
        timeout=30
    )
    elapsed = time.time() - start
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 成功")
        print(f"  - 回答: {result.get('answer', 'N/A')[:100]}...")
        print(f"  - 置信度: {result.get('confidence', 0):.2f}")
        print(f"  - 迭代次数: {result.get('iterations', 0)}")
        print(f"  - 复杂度: {result.get('complexity', 'N/A')}")
        print(f"  - 耗时: {elapsed:.2f}s")
        print(f"  - 早停: {result.get('stopped_early', False)}")
        return True
    else:
        print(f"❌ 失败: {response.status_code}")
        print(f"  错误: {response.text}")
        return False


def test_complex_query():
    """测试复杂问题"""
    print("\n" + "="*60)
    print("测试 3: 复杂问题")
    print("="*60)
    
    payload = {
        "message": "我需要设计一个完整的无人机维修培训课程体系，包括课程大纲、教学方法、考核标准和商业运营方案。请给出详细的设计建议。",
        "context": {
            "domain": "无人机维修培训",
            "requirements": ["课程大纲", "教学方法", "考核标准", "商业运营"]
        }
    }
    
    start = time.time()
    response = requests.post(
        f"{BASE_URL}/api/openmythos/chat",
        json=payload,
        timeout=30
    )
    elapsed = time.time() - start
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 成功")
        print(f"  - 回答: {result.get('answer', 'N/A')[:100]}...")
        print(f"  - 置信度: {result.get('confidence', 0):.2f}")
        print(f"  - 迭代次数: {result.get('iterations', 0)}")
        print(f"  - 复杂度: {result.get('complexity', 'N/A')}")
        print(f"  - 耗时: {elapsed:.2f}s")
        print(f"  - 早停: {result.get('stopped_early', False)}")
        return True
    else:
        print(f"❌ 失败: {response.status_code}")
        print(f"  错误: {response.text}")
        return False


def test_stats():
    """测试统计接口"""
    print("\n" + "="*60)
    print("测试 4: 统计接口")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/api/openmythos/stats", timeout=10)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 成功")
        print(f"  - 引擎配置: {result.get('engine', {})}")
        print(f"  - 规划器配置: {result.get('planner', {})}")
        print(f"  - 压缩配置: {result.get('compression', {})}")
        return True
    else:
        print(f"❌ 失败: {response.status_code}")
        return False


def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("🧪 循环推理引擎集成测试")
    print("="*60)
    print(f"目标服务器: {BASE_URL}")
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查服务是否在线
    try:
        response = requests.get(f"{BASE_URL}/api/openmythos/stats", timeout=5)
        if response.status_code != 200:
            print(f"\n❌ 服务不可用: {response.status_code}")
            return
    except Exception as e:
        print(f"\n❌ 无法连接到服务: {e}")
        return
    
    # 运行测试
    results = []
    results.append(("统计接口", test_stats()))
    results.append(("简单问题", test_simple_query()))
    results.append(("中等问题", test_medium_query()))
    results.append(("复杂问题", test_complex_query()))
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} - {name}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！循环推理引擎已成功集成。")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，需要检查。")


if __name__ == "__main__":
    main()
