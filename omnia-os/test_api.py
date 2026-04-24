#!/usr/bin/env python3
"""
测试 Omnia API 集成
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.cognition.chat_integration import OmniaChatEngine


async def test_engine():
    """测试引擎"""
    print("=" * 60)
    print("Omnia 引擎测试")
    print("=" * 60)
    print()
    
    # 初始化引擎
    print("🔧 初始化引擎...")
    engine = OmniaChatEngine(
        max_loops=8,
        halt_threshold=0.85,
        enable_mla=True
    )
    print("✅ 引擎初始化完成")
    print()
    
    # 测试消息
    test_messages = [
        ("简单", "你好"),
        ("中等", "帮我写一个 Python 函数计算斐波那契数列"),
        ("复杂", "分析一下量子计算的基本原理和应用前景"),
    ]
    
    for complexity, msg in test_messages:
        print(f"\n{'─' * 60}")
        print(f"📝 测试 [{complexity}]: {msg}")
        print("─" * 40)
        
        start = time.time()
        result = await engine.process_message(msg)
        elapsed = time.time() - start
        
        print(f"\n📤 响应预览:")
        print(f"   {result['response'][:150]}...")
        print()
        print(f"📊 元数据:")
        print(f"   复杂度: {result['metadata']['complexity']}")
        print(f"   推理深度: {result['metadata']['reasoning_depth']}")
        print(f"   推理置信度: {result['metadata']['reasoning_confidence']:.2f}")
        print(f"   处理时间: {elapsed:.3f}s")
    
    # 统计
    print()
    print("=" * 60)
    print("📈 统计信息:")
    print("-" * 60)
    stats = engine.get_stats()
    print(f"   总对话数: {stats['total_conversations']}")
    print(f"   平均推理深度: {stats['avg_depth']:.2f}")
    print(f"   简单任务: {stats['simple_tasks']}")
    print(f"   中等任务: {stats['medium_tasks']}")
    print(f"   复杂任务: {stats['complex_tasks']}")
    print("=" * 60)
    
    print("\n✅ 测试完成！")


if __name__ == "__main__":
    asyncio.run(test_engine())
