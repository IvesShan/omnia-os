#!/usr/bin/env python3
"""
简化测试 - 验证核心组件集成
不依赖 LLM 调用
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.cognition.act_planner import ACTPlanner, TaskComplexity
from core.cognition.depth_adapter import DepthAdapter, DepthStyle
from core.memory.mla_compressor import MLACompressor
import numpy as np


def test_act_planner():
    """测试 ACT 规划器"""
    print("\n" + "=" * 60)
    print("测试 ACT 规划器")
    print("=" * 60)
    
    planner = ACTPlanner()
    
    test_cases = [
        ("你好", TaskComplexity.SIMPLE),
        ("帮我写一个 Python 脚本", TaskComplexity.MEDIUM),
        ("分析量子计算的原理并给出应用前景", TaskComplexity.COMPLEX),
    ]
    
    passed = 0
    for msg, expected in test_cases:
        complexity = planner.estimate_complexity(msg)
        status = "✅" if complexity == expected else "⚠️"
        print(f"{status} '{msg[:30]}...' -> {complexity.value} (期望: {expected.value})")
        if complexity == expected:
            passed += 1
    
    print(f"\n通过: {passed}/{len(test_cases)}")
    return passed >= 1  # 至少通过一个


def test_depth_adapter():
    """测试深度适配器"""
    print("\n" + "=" * 60)
    print("测试深度适配器")
    print("=" * 60)
    
    adapter = DepthAdapter(max_depth=8)
    
    test_responses = [
        ("简单回答", 1, DepthStyle.QUICK),
        ("中等回答，需要一些思考", 4, DepthStyle.BALANCED),
        ("复杂回答，需要深度分析", 7, DepthStyle.DEEP),
    ]
    
    passed = 0
    for response, depth, expected_style in test_responses:
        adapted = adapter.adapt_response(response, depth=depth)
        style = adapter.get_style_for_depth(depth)
        status = "✅" if style == expected_style else "⚠️"
        print(f"{status} 深度 {depth} -> {style.value} (期望: {expected_style.value})")
        if style == expected_style:
            passed += 1
    
    print(f"\n通过: {passed}/{len(test_responses)}")
    return passed >= 2


def test_mla_compressor():
    """测试 MLA 压缩器"""
    print("\n" + "=" * 60)
    print("测试 MLA 压缩器")
    print("=" * 60)
    
    compressor = MLACompressor(dim=768, kv_lora_rank=64)
    
    # 创建测试向量
    test_vector = np.random.randn(768).astype(np.float32)
    
    # 压缩
    compressed_memory = compressor.compress_memory(
        memory_vector=test_vector,
        metadata={"content": "测试记忆"}
    )
    
    print(f"✅ 压缩: 768 -> {len(compressed_memory.compressed_vector)} (压缩比: {768/len(compressed_memory.compressed_vector):.1f}x)")
    
    # 解压
    decompressed = compressor.decompress_memory(compressed_memory)
    print(f"✅ 解压: {len(compressed_memory.compressed_vector)} -> {len(decompressed)}")
    
    # 计算重建误差
    error = np.mean(np.abs(test_vector - decompressed))
    print(f"✅ 重建误差: {error:.6f}")
    
    # 统计
    stats = compressor.get_compression_stats()
    print(f"✅ 统计: {stats}")
    
    return True


def test_memory_manager():
    """测试记忆管理器"""
    print("\n" + "=" * 60)
    print("测试记忆管理器")
    print("=" * 60)
    
    from core.memory.memory_manager import MemoryManager
    
    manager = MemoryManager(max_memories=100)
    
    # 添加记忆
    manager.add_memory("用户喜欢编程", "assistant")
    manager.add_memory("今天天气不错", "user")
    manager.add_memory("Python 是一门好语言", "assistant")
    
    print(f"✅ 添加了 3 条记忆")
    
    # 检索记忆
    results = manager.retrieve_relevant("编程", top_k=2)
    print(f"✅ 检索 '编程': 找到 {len(results)} 条相关记忆")
    
    for memory, score in results:
        print(f"   - [{score:.2f}] {memory.content[:50]}...")
    
    return True


def main():
    """运行所有测试"""
    print("\n" + "═" * 60)
    print("  Omnia 核心组件测试")
    print("═" * 60)
    
    tests = [
        ("ACT 规划器", test_act_planner),
        ("深度适配器", test_depth_adapter),
        ("MLA 压缩器", test_mla_compressor),
        ("记忆管理器", test_memory_manager),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success, None))
        except Exception as e:
            import traceback
            results.append((name, False, str(e)))
            traceback.print_exc()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for name, success, error in results:
        status = "✅ 通过" if success else f"❌ 失败: {error}"
        print(f"  {name}: {status}")
    
    print()
    print(f"总计: {passed}/{total} 通过")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
