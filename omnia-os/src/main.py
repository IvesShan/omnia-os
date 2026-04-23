#!/usr/bin/env python3
"""
Omnia 主程序 - 演示循环推理集成

使用方式：
    python src/main.py
"""

import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.cognition.chat_integration import OmniaChatEngine


def main():
    """主程序入口"""
    print("=" * 60)
    print("Omnia - 集成循环推理的 AI 系统")
    print("=" * 60)
    print()
    
    # 创建对话引擎
    print("初始化对话引擎...")
    engine = OmniaChatEngine(
        max_loops=8,
        halt_threshold=0.85,
        enable_mla=False  # 暂时禁用 MLA 压缩
    )
    print("✅ 引擎初始化完成")
    print()
    
    # 测试对话
    test_messages = [
        "你好",
        "今天天气怎么样？",
        "帮我写一个 Python 脚本来计算斐波那契数列",
        "分析一下量子计算的基本原理和应用前景",
    ]
    
    print("开始测试对话...")
    print("-" * 60)
    
    for i, msg in enumerate(test_messages, 1):
        print(f"\n[测试 {i}] 用户: {msg}")
        print("-" * 40)
        
        # 处理消息
        result = engine.process_message(msg)
        
        # 显示结果
        print(f"响应: {result['response'][:200]}...")
        print(f"\n元数据:")
        print(f"  - 复杂度: {result['metadata']['complexity']}")
        print(f"  - 推理深度: {result['metadata']['reasoning_depth']}")
        print(f"  - 响应风格: {result['metadata']['response_style']}")
        print(f"  - 推理置信度: {result['metadata']['reasoning_confidence']:.2f}")
        print(f"  - 处理时间: {result['metadata']['elapsed_time']:.3f}s")
        print("-" * 40)
    
    # 显示统计信息
    print("\n" + "=" * 60)
    print("统计信息:")
    print("-" * 60)
    stats = engine.get_stats()
    print(f"总对话数: {stats['total_conversations']}")
    print(f"平均推理深度: {stats['avg_depth']:.2f}")
    print(f"简单任务: {stats['simple_tasks']}")
    print(f"中等任务: {stats['medium_tasks']}")
    print(f"复杂任务: {stats['complex_tasks']}")
    print("=" * 60)
    
    print("\n✅ 测试完成！")


if __name__ == "__main__":
    main()
