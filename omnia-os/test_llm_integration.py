#!/usr/bin/env python3
"""测试真实 LLM 集成"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.cognition.chat_integration import create_chat_engine

print("=" * 60)
print("测试真实 LLM 集成")
print("=" * 60)

# 创建引擎
engine = create_chat_engine(max_loops=3, halt_threshold=0.85)

# 测试消息
test_message = "今天天气怎么样？"

print(f"\n测试消息: {test_message}")
print(f"\n开始推理...\n")

# 处理消息
result = engine.process_message(test_message)

print(f"\n响应: {result['response']}")
print(f"\n元数据:")
print(f"  复杂度: {result['metadata']['complexity']}")
print(f"  推理深度: {result['metadata']['reasoning_depth']}")
print(f"  置信度: {result['metadata']['reasoning_confidence']:.2f}")
print(f"  响应风格: {result['metadata']['response_style']}")
print(f"  处理时间: {result['metadata']['elapsed_time']:.3f}s")

print("\n" + "=" * 60)
print("✅ 测试完成")
