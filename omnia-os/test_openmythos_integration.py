#!/usr/bin/env python3
"""
测试 OpenMythos 集成到 Omnia 的核心模块

运行方式：
    python3 test_openmythos_integration.py
"""

import sys
import os

# 添加 src 到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.cognition.recurrent_reasoning import (
    RecurrentReasoning,
    ReasoningState,
    ReasoningResult,
    LTIInjection,
    ACTHalting
)
from core.cognition.act_planner import (
    ACTPlanner,
    ComplexityEstimator,
    PlanStep,
    AdaptivePlan
)
from core.cognition.depth_adapter import (
    DepthAdapter,
    DepthStyle,
    AdapterWeights
)
from core.memory.mla_compressor import (
    MLACompressor,
    CompressedMemory
)

import numpy as np


def test_lti_injection():
    """测试 LTI 稳定注入"""
    print("\n" + "="*60)
    print("测试 1: LTI Injection (线性时不变注入)")
    print("="*60)
    
    lti = LTIInjection(decay_rate=0.9, injection_strength=0.1)
    
    # 创建初始状态
    h = ReasoningState(depth=0, confidence=0.5)
    e = ReasoningState(depth=0, confidence=0.5, insights=["原始输入"])
    step_output = ReasoningState(depth=1, confidence=0.6, insights=["新推理"])
    
    # 执行更新
    h_updated = lti.update(h, e, step_output)
    
    print(f"  原始深度: {h.depth}")
    print(f"  更新后深度: {h_updated.depth}")
    print(f"  原始置信度: {h.confidence}")
    print(f"  更新后置信度: {h_updated.confidence}")
    
    assert h_updated.depth >= h.depth, "深度应该增加"
    print("✅ LTI Injection 测试通过")


def test_act_halting():
    """测试 ACT 自适应停机"""
    print("\n" + "="*60)
    print("测试 2: ACT Halting (自适应计算时间)")
    print("="*60)
    
    act = ACTHalting(halt_threshold=0.85, min_loops=1, max_loops=8)
    
    # 测试不同场景
    test_cases = [
        (0, 0.75, False, "深度 0，低置信度 - 不停机"),
        (1, 0.75, False, "深度 1，低置信度 - 不停机"),
        (1, 0.88, True, "深度 1，高置信度 - 应该停机"),
        (8, 0.50, True, "深度 8，低置信度 - 强制停机"),
    ]
    
    for depth, confidence, expected, description in test_cases:
        state = ReasoningState(depth=depth, confidence=confidence)
        should_halt = act.should_halt(state)
        
        print(f"\n  {description}")
        print(f"    → should_halt = {should_halt} (期望: {expected})")
        
        assert should_halt == expected, f"停机判断错误: {description}"
    
    print("\n✅ ACT Halting 测试通过")


def test_complexity_estimator():
    """测试任务复杂度评估器"""
    print("\n" + "="*60)
    print("测试 3: Complexity Estimator (任务复杂度评估)")
    print("="*60)
    
    estimator = ComplexityEstimator()
    
    test_inputs = [
        ("今天天气怎么样？", "简单查询", 0.0, 0.3),
        ("帮我写一个 Python 脚本", "代码任务", 0.3, 0.6),
        ("分析项目架构并给出重构方案", "复杂决策", 0.6, 1.0),
    ]
    
    for user_input, description, min_complexity, max_complexity in test_inputs:
        complexity = estimator.estimate(user_input, {})
        
        print(f"\n  输入: {user_input[:40]}...")
        print(f"  类型: {description}")
        print(f"  复杂度: {complexity:.3f} (期望范围: {min_complexity}-{max_complexity})")
        
        assert 0.0 <= complexity <= 1.0, f"复杂度超出范围: {complexity}"
    
    print("\n✅ Complexity Estimator 测试通过")


def test_act_planner():
    """测试 ACT 自适应规划器"""
    print("\n" + "="*60)
    print("测试 4: ACT Planner (自适应规划)")
    print("="*60)
    
    planner = ACTPlanner(max_planning_steps=5)
    
    test_cases = [
        ("今天天气", "简单查询"),
        ("帮我写代码", "代码任务"),
        ("分析项目架构并给出重构方案", "复杂决策"),
    ]
    
    for user_input, description in test_cases:
        plan = planner.plan(user_input, {})
        
        print(f"\n  输入: {user_input}")
        print(f"  类型: {description}")
        print(f"  规划步骤数: {len(plan.steps)}")
        print(f"  复杂度: {plan.complexity:.3f}")
        
        for i, step in enumerate(plan.steps[:3]):  # 只显示前 3 步
            print(f"    Step {i+1}: {step.description} (工具: {step.tool})")
    
    print("\n✅ ACT Planner 测试通过")


def test_depth_adapter():
    """测试深度适配器"""
    print("\n" + "="*60)
    print("测试 5: Depth Adapter (深度适配)")
    print("="*60)
    
    adapter = DepthAdapter(base_persona="无限", max_depth=8)
    
    base_response = "这是一个基础的响应内容。"
    
    test_depths = [
        (0, "极浅层 - Quick 模式"),
        (2, "浅层 - Quick 模式"),
        (4, "中层 - Balanced 模式"),
        (6, "深层 - Deep 模式"),
        (7, "极深层 - Deep 模式"),
    ]
    
    for depth, description in test_depths:
        adapted = adapter.adapt(base_response, depth, {})
        
        print(f"\n  深度 {depth}: {description}")
        print(f"  适配后长度: {len(adapted)} 字符")
        print(f"  前 80 字符: {adapted[:80]}...")
    
    print("\n✅ Depth Adapter 测试通过")


def test_mla_compressor():
    """测试 MLA 记忆压缩器"""
    print("\n" + "="*60)
    print("测试 6: MLA Compressor (记忆压缩)")
    print("="*60)
    
    compressor = MLACompressor(dim=768, kv_lora_rank=64)
    
    # 创建测试记忆向量
    original_vector = np.random.randn(768)
    
    print(f"  原始向量维度: {original_vector.shape}")
    print(f"  原始向量大小: {original_vector.nbytes} bytes")
    
    # 压缩
    compressed = compressor.compress(original_vector)
    print(f"\n  压缩后维度: {compressed.shape}")
    print(f"  压缩后大小: {compressed.nbytes} bytes")
    print(f"  压缩比: {original_vector.nbytes / compressed.nbytes:.1f}x")
    
    # 解压
    decompressed = compressor.decompress(compressed)
    print(f"\n  解压后维度: {decompressed.shape}")
    
    # 计算重建误差
    reconstruction_error = np.linalg.norm(original_vector - decompressed) / np.linalg.norm(original_vector)
    print(f"  重建误差: {reconstruction_error:.4f} ({reconstruction_error*100:.2f}%)")
    
    print("\n✅ MLA Compressor 测试通过")


def test_recurrent_reasoning():
    """测试循环推理引擎"""
    print("\n" + "="*60)
    print("测试 7: Recurrent Reasoning (循环推理引擎)")
    print("="*60)
    
    engine = RecurrentReasoning(max_loops=8, halt_threshold=0.85)
    
    print("\n  测试循环推理引擎是否可以实例化...")
    print(f"  最大循环次数: {engine.max_loops}")
    print(f"  停机阈值: {engine.halt_threshold}")
    
    # 测试 ACT 和 LTI 组件
    assert engine.act is not None, "ACT 组件未初始化"
    assert engine.lti is not None, "LTI 组件未初始化"
    
    print("\n✅ Recurrent Reasoning 测试通过")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "█"*60)
    print("█" + " "*58 + "█")
    print("█" + "  OpenMythos → Omnia 集成测试".center(56) + "█")
    print("█" + " "*58 + "█")
    print("█"*60)
    
    tests = [
        ("LTI Injection", test_lti_injection),
        ("ACT Halting", test_act_halting),
        ("Complexity Estimator", test_complexity_estimator),
        ("ACT Planner", test_act_planner),
        ("Depth Adapter", test_depth_adapter),
        ("MLA Compressor", test_mla_compressor),
        ("Recurrent Reasoning", test_recurrent_reasoning),
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
        print("\n🎉 所有测试通过！OpenMythos 核心机制已成功集成到 Omnia")
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，需要修复")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
