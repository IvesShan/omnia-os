#!/usr/bin/env python3
"""测试 ReasoningState 是否正常工作"""

import sys
sys.path.insert(0, 'src')

from core.cognition.recurrent_reasoning import ReasoningState

# 测试 ReasoningState
state = ReasoningState(depth=0, confidence=0.0)

print(f"初始状态:")
print(f"  depth: {state.depth}")
print(f"  confidence: {state.confidence}")
print(f"  output: '{state.output}'")

# 模拟更新
state.depth = 2
state.confidence = 0.85
state.output = "测试输出"

print(f"\n更新后:")
print(f"  depth: {state.depth}")
print(f"  confidence: {state.confidence}")
print(f"  output: '{state.output}'")

# 测试 dataclass 是否正常工作
print(f"\nReasoningState 字段:")
import dataclasses
for field in dataclasses.fields(state):
    print(f"  {field.name}: {field.type}")
