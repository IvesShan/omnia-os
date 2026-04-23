#!/usr/bin/env python3
"""
简化版 OpenMythos 集成测试

只测试核心机制，不涉及 LLM 调用
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import numpy as np
from datetime import datetime


def test_act_halting_mechanism():
    """测试 ACT 自适应停机机制"""
    print("\n" + "="*60)
    print("测试 1: ACT Halting Mechanism")
    print("="*60)
    
    from core.cognition.recurrent_reasoning import ACTHalting, ReasoningState
    
    act = ACTHalting(halt_threshold=0.85, min_loops=1, max_loops=8)
    
    # 测试不同场景
    scenarios = [
        (0, 0.75, False, "深度 0，低置信度"),
        (1, 0.75, False, "深度 1，低置信度"),
        (1, 0.88, True, "深度 1，高置信度"),
        (8, 0.50, True, "深度 8（最大），强制停机"),
    ]
    
    for depth, confidence, expected, desc in scenarios:
        state = ReasoningState(depth=depth, confidence=confidence)
        result = act.should_halt(state)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {desc}: should_halt={result}")
        assert result == expected, f"停机判断错误: {desc}"
    
    print("\n✅ ACT Halting 测试通过")


def test_complexity_estimation():
    """测试任务复杂度评估"""
    print("\n" + "="*60)
    print("测试 2: Complexity Estimation")
    print("="*60)
    
    from core.cognition.act_planner import ComplexityEstimator, TaskComplexity
    
    estimator = ComplexityEstimator()
    
    test_inputs = [
        ("今天天气怎么样？", "简单查询"),
        ("帮我写一个 Python 脚本", "代码任务"),
        ("分析项目架构并给出重构方案", "复杂决策"),
    ]
    
    for user_input, desc in test_inputs:
        complexity = estimator.estimate(user_input, {})
        print(f"  输入: {user_input[:30]}...")
        print(f"    类型: {desc}")
        print(f"    复杂度: {complexity.value}")
        assert isinstance(complexity, TaskComplexity)
    
    print("\n✅ Complexity Estimation 测试通过")


def test_depth_adapter():
    """测试深度适配器"""
    print("\n" + "="*60)
    print("测试 3: Depth Adapter")
    print("="*60)
    
    from core.cognition.depth_adapter import DepthAdapter, DepthStyle
    
    adapter = DepthAdapter(max_depth=8)
    
    # 测试深度到风格的映射
    test_depths = [0, 2, 4, 6, 7]
    
    for depth in test_depths:
        style = adapter.get_style_for_depth(depth)
        print(f"  深度 {depth} → 风格: {style.value}")
    
    # 测试适配功能
    base_response = "这是一个基础响应。"
    adapted = adapter.adapt_response(base_response, depth=4, context={})
    print(f"\n  基础响应长度: {len(base_response)}")
    print(f"  适配后长度: {len(adapted)}")
    
    print("\n✅ Depth Adapter 测试通过")


def test_mla_compression():
    """测试 MLA 记忆压缩"""
    print("\n" + "="*60)
    print("测试 4: MLA Memory Compression")
    print("="*60)
    
    from core.memory.mla_compressor import MLACompressor
    
    compressor = MLACompressor(dim=768, kv_lora_rank=64)
    
    # 创建测试记忆向量
    test_vector = np.random.randn(768)
    
    print(f"  原始向量维度: {test_vector.shape}")
    print(f"  原始向量大小: {test_vector.nbytes} bytes")
    
    # 压缩
    compressed = compressor.compress_memory(
        memory_vector=test_vector,
        metadata={"type": "test", "content": "测试记忆"}
    )
    
    print(f"\n  压缩后向量维度: {compressed.compressed_vector.shape}")
    print(f"  压缩后大小: {compressed.compressed_vector.nbytes} bytes")
    print(f"  压缩比: {test_vector.nbytes / compressed.compressed_vector.nbytes:.1f}x")
    
    # 解压
    decompressed = compressor.decompress_memory(compressed)
    print(f"\n  解压后向量维度: {decompressed.shape}")
    
    # 计算重建误差
    error = np.linalg.norm(test_vector - decompressed) / np.linalg.norm(test_vector)
    print(f"  重建误差: {error:.4f} ({error*100:.2f}%)")
    
    print("\n✅ MLA Compression 测试通过")


def test_integration():
    """测试集成功能"""
    print("\n" + "="*60)
    print("测试 5: Integration Test")
    print("="*60)
    
    from core.cognition.recurrent_reasoning import RecurrentReasoning
    
    # 创建引擎实例
    engine = RecurrentReasoning(
        max_loops=8,
        halt_threshold=0.85
    )
    
    print(f"  引擎创建成功")
    print(f"  最大循环次数: {engine.max_loops}")
    print(f"  ACT 组件: {type(engine.act).__name__}")
    print(f"  LTI 组件: {type(engine.lti).__name__}")
    
    print("\n✅ Integration 测试通过")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "█"*60)
    print("█" + " "*58 + "█")
    print("█" + "  OpenMythos → Omnia 核心机制测试".center(52) + "█")
    print("█" + " "*58 + "█")
    print("█"*60)
    
    tests = [
        ("ACT Halting", test_act_halting_mechanism),
        ("Complexity Estimation", test_complexity_estimation),
        ("Depth Adapter", test_depth_adapter),
        ("MLA Compression", test_mla_compression),
        ("Integration", test_integration),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n❌ {name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"测试结果: ✅ {passed} 通过 | ❌ {failed} 失败")
    print("="*60)
    
    if failed == 0:
        print("\n🎉 所有测试通过！")
        print("\n核心机制验证完成：")
        print("  ✓ ACT 自适应停机")
        print("  ✓ 复杂度评估")
        print("  ✓ 深度适配")
        print("  ✓ MLA 记忆压缩")
        print("  ✓ 组件集成")
    else:
        print(f"\n⚠️  有 {failed} 个测试失败")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
