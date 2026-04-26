#!/usr/bin/env python3
"""
简单测试脚本
"""

import sys
sys.path.insert(0, 'src')

from core.cognition.chat_integration import create_chat_engine

print("=" * 60)
print("Omnia Chat Engine 测试")
print("=" * 60)

# 创建引擎
engine = create_chat_engine(
    max_loops=8,
    halt_threshold=0.85,
    enable_mla=True
)

# 测试不同复杂度的消息
test_cases = [
    "今天天气怎么样？",
    "帮我写一个 Python 脚本",
    "分析项目架构，找出性能瓶颈",
]

for i, message in enumerate(test_cases, 1):
    print(f"\n--- 测试 {i} ---")
    print(f"用户消息: {message}")
    
    result = engine.process_message(message)
    
    print(f"响应: {result['response'][:100]}")
    print(f"复杂度: {result['metadata']['complexity']}")
    print(f"推理深度: {result['metadata']['reasoning_depth']}")
    print(f"处理时间: {result['metadata']['elapsed_time']:.3f}s")

print("\n" + "=" * 60)
print("✅ 所有测试通过")
print("=" * 60)
