#!/usr/bin/env python3
"""调试推理深度问题"""

import sys
sys.path.insert(0, 'src')

from core.cognition.chat_integration import create_chat_engine

# 创建引擎
engine = create_chat_engine(max_loops=8, halt_threshold=0.85)

# 测试消息
message = "今天天气怎么样？"
print(f"测试消息: {message}\n")

# 手动调用内部方法来调试
from core.cognition.chat_integration import ChatContext

context = ChatContext(
    user_message=message,
    conversation_history=[],
    metadata={}
)

# 1. 评估复杂度
context.complexity = engine.planner.estimate_complexity(message, context.metadata)
print(f"复杂度: {context.complexity.value}")

# 2. 获取最大深度
max_depth = engine._get_max_depth_for_complexity(context.complexity)
print(f"最大深度: {max_depth}")

# 3. 运行推理
print(f"\n开始推理循环...")
reasoning_result = engine._run_reasoning(context, max_depth)

print(f"\n推理结果:")
print(f"  depth: {reasoning_result['depth']}")
print(f"  confidence: {reasoning_result['confidence']:.2f}")
print(f"  output: {reasoning_result['output']}")

print(f"\n推理轨迹:")
for i, step in enumerate(reasoning_result['trace']):
    print(f"  步骤 {i+1}: depth={step['depth']}, conf={step['confidence']:.2f}")
