#!/usr/bin/env python3
"""
Omnia Chat Integration 测试

测试循环推理引擎在对话流程中的效果
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.cognition.chat_integration import create_chat_engine


def test_chat_engine():
    """测试对话引擎"""
    print("\n" + "=" * 60)
    print("Omnia Chat Engine 集成测试")
    print("=" * 60)
    
    # 创建引擎
    engine = create_chat_engine(
        max_loops=8,
        halt_threshold=0.85,
        enable_mla=True
    )
    
    # 测试不同复杂度的消息
    test_cases = [
        {
            "message": "今天天气怎么样？",
            "expected_complexity": "simple",
            "expected_depth_range": (1, 2),
        },
        {
            "message": "帮我写一个 Python 脚本，计算斐波那契数列",
            "expected_complexity": "simple",
            "expected_depth_range": (1, 3),
        },
        {
            "message": "分析项目架构，找出性能瓶颈，并给出优化方案",
            "expected_complexity": "medium",
            "expected_depth_range": (2, 5),
        },
    ]
    
    print("\n开始测试...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- 测试 {i} ---")
        print(f"用户消息: {test_case['message']}")
        
        # 处理消息
        result = engine.process_message(test_case['message'])
        
        # 显示结果
        print(f"\n响应: {result['response']}")
        print(f"\n元数据:")
        metadata = result['metadata']
        print(f"  复杂度: {metadata['complexity']}")
        print(f"  推理深度: {metadata['reasoning_depth']}")
        print(f"  响应风格: {metadata['response_style']}")
        print(f"  推理置信度: {metadata['reasoning_confidence']:.2f}")
        print(f"  处理时间: {metadata['elapsed_time']:.3f}s")
        
        # 验证结果
        actual_complexity = metadata['complexity']
        expected_complexity = test_case['expected_complexity']
        
        if actual_complexity == expected_complexity:
            print(f"  ✅ 复杂度评估正确")
        else:
            print(f"  ⚠️  复杂度评估: 期望 {expected_complexity}, 实际 {actual_complexity}")
        
        actual_depth = metadata['reasoning_depth']
        min_depth, max_depth = test_case['expected_depth_range']
        
        if min_depth <= actual_depth <= max_depth:
            print(f"  ✅ 推理深度在预期范围内 ({min_depth}-{max_depth})")
        else:
            print(f"  ⚠️  推理深度: 期望 {min_depth}-{max_depth}, 实际 {actual_depth}")
    
    # 显示统计信息
    print("\n" + "=" * 60)
    print("统计信息:")
    stats = engine.get_stats()
    print(f"  总对话数: {stats['total_conversations']}")
    print(f"  平均推理深度: {stats['avg_depth']:.2f}")
    print(f"  简单任务: {stats['simple_tasks']}")
    print(f"  中等任务: {stats['medium_tasks']}")
    print(f"  复杂任务: {stats['complex_tasks']}")
    print("=" * 60)
    
    print("\n✅ 集成测试完成！")


if __name__ == "__main__":
    test_chat_engine()
