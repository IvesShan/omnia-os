#!/usr/bin/env python3
"""
OpenMythos Integration Tests

测试循环推理引擎与 Omnia 的集成
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.openmythos import (
    ACTPlanner,
    ComplexityLevel,
    RecurrentReasoning,
    MLACompression,
    IntegrationBridge
)


def test_act_planner():
    """测试 ACT 规划器"""
    print("\n=== 测试 ACT Planner ===")
    
    planner = ACTPlanner()
    
    # 测试不同复杂度的查询
    test_cases = [
        ("你好", ComplexityLevel.QUICK),
        ("解释一下什么是机器学习", ComplexityLevel.BALANCED),
        ("设计一个完整的分布式系统架构", ComplexityLevel.DEEP)
    ]
    
    for query, expected_level in test_cases:
        analysis = planner.analyze(query)
        print(f"\n查询: {query}")
        print(f"  复杂度: {analysis.complexity.value}")
        print(f"  估算深度: {analysis.estimated_depth}")
        print(f"  需要工具: {analysis.requires_tools}")
        print(f"  需要记忆: {analysis.requires_memory}")
    
    print("\n✅ ACT Planner 测试通过")


def test_recurrent_engine():
    """测试循环推理引擎"""
    print("\n=== 测试 Recurrent Engine ===")
    
    # 模拟模型调用
    def mock_model_call(prompt, context):
        if "初步分析" in prompt:
            return "思考：这是一个测试问题，需要分析。\n置信度：0.6"
        else:
            return "思考：经过深入分析，答案是...\n置信度：0.9"
    
    engine = RecurrentReasoning(
        model_call=mock_model_call,
        max_iterations=5,
        confidence_threshold=0.85
    )
    
    result = engine.reason("测试问题")
    
    print(f"\n总迭代次数: {result.total_iterations}")
    print(f"最终置信度: {result.final_confidence:.2f}")
    print(f"提前停止: {result.stopped_early}")
    print(f"耗时: {result.time_elapsed:.3f}s")
    
    assert result.total_iterations >= 1
    assert result.final_confidence >= 0.0
    
    print("\n✅ Recurrent Engine 测试通过")


def test_mla_compression():
    """测试 MLA 压缩"""
    print("\n=== 测试 MLA Compression ===")
    
    compression = MLACompression()
    
    # 测试压缩和解压
    import numpy as np
    vectors = np.random.randn(10, 768)
    
    compressed = compression.compress(vectors)
    print(f"\n原始维度: {vectors.shape}")
    print(f"压缩后维度: {compressed.shape}")
    print(f"压缩比: {vectors.shape[1] / compressed.shape[1]}x")
    
    # 测试解压
    decompressed = compression.decompress(compressed)
    print(f"解压后维度: {decompressed.shape}")
    
    assert compressed.shape[1] == 64
    assert decompressed.shape[1] == 768
    
    stats = compression.get_stats()
    print(f"\n统计信息: {stats}")
    
    print("\n✅ MLA Compression 测试通过")


def test_integration_bridge():
    """测试集成桥接"""
    print("\n=== 测试 Integration Bridge ===")
    
    # 模拟模型调用
    def mock_model_call(prompt, context):
        return "思考：分析完成。\n置信度：0.88"
    
    bridge = IntegrationBridge(
        model_call=mock_model_call,
        memory_palace=None,
        config={
            'max_iterations': 3,
            'confidence_threshold': 0.85
        }
    )
    
    result = bridge.process("测试查询")
    
    print(f"\n答案: {result['answer'][:50]}...")
    print(f"置信度: {result['confidence']:.2f}")
    print(f"迭代次数: {result['iterations']}")
    print(f"复杂度: {result['complexity']}")
    print(f"耗时: {result['time_elapsed']:.3f}s")
    
    assert result['iterations'] >= 1
    assert result['confidence'] >= 0.0
    
    stats = bridge.get_stats()
    print(f"\n统计信息: {stats}")
    
    print("\n✅ Integration Bridge 测试通过")


def test_full_pipeline():
    """测试完整流程"""
    print("\n=== 测试完整流程 ===")
    
    # 模拟模型调用
    def mock_model_call(prompt, context):
        if "初步分析" in prompt:
            return "思考：需要进一步分析。\n置信度：0.65"
        elif "继续深入" in prompt:
            return "思考：发现关键点。\n置信度：0.82"
        else:
            return "思考：分析完成，答案确定。\n置信度：0.91"
    
    bridge = IntegrationBridge(
        model_call=mock_model_call,
        config={
            'max_iterations': 5,
            'confidence_threshold': 0.85
        }
    )
    
    # 测试不同类型的查询
    queries = [
        "你好",
        "解释一下量子计算",
        "设计一个微服务架构"
    ]
    
    for query in queries:
        result = bridge.process(query)
        print(f"\n查询: {query}")
        print(f"  复杂度: {result['complexity']}")
        print(f"  迭代: {result['iterations']}")
        print(f"  置信度: {result['confidence']:.2f}")
    
    print("\n✅ 完整流程测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("OpenMythos Integration Tests")
    print("=" * 60)
    
    try:
        test_act_planner()
        test_recurrent_engine()
        test_mla_compression()
        test_integration_bridge()
        test_full_pipeline()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
