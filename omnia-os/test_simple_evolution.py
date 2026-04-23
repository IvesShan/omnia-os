#!/usr/bin/env python3
"""
简单的进化测试 - 不使用 asyncio.run()
"""

import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("\n" + "=" * 60)
print("Omnia 进化测试 - 简单版")
print("=" * 60)

# 测试 1: 检查模块是否可以导入
print("\n测试 1: 模块导入...")
try:
    from core.cognition.chat_integration import OmniaChatEngine
    from core.llm_client import create_llm_client
    print("✅ 模块导入成功")
except Exception as e:
    print(f"❌ 模块导入失败: {e}")
    sys.exit(1)

# 测试 2: 检查 LLM 客户端配置
print("\n测试 2: LLM 客户端配置...")
try:
    client = create_llm_client()
    print(f"✅ 客户端创建成功")
    print(f"   Provider: {client.config.provider}")
    print(f"   Model: {client.config.model}")
    print(f"   API Key: {client.config.api_key[:20]}...")
except Exception as e:
    print(f"❌ 客户端创建失败: {e}")
    sys.exit(1)

# 测试 3: 检查对话引擎配置
print("\n测试 3: 对话引擎配置...")
try:
    engine = OmniaChatEngine(
        max_loops=8,
        halt_threshold=0.85,
        enable_mla=False
    )
    print("✅ 引擎创建成功")
    print(f"   Max loops: {engine.reasoning_engine.max_loops}")
    print(f"   Halt threshold: {engine.reasoning_engine.act.halt_threshold}")
except Exception as e:
    print(f"❌ 引擎创建失败: {e}")
    sys.exit(1)

# 测试 4: 检查方法签名
print("\n测试 4: 方法签名检查...")
import inspect
sig = inspect.signature(engine.process_message)
print(f"✅ process_message 签名: {sig}")
print(f"   是否异步: {inspect.iscoroutinefunction(engine.process_message)}")

sig2 = inspect.signature(engine._run_reasoning)
print(f"✅ _run_reasoning 签名: {sig2}")
print(f"   是否异步: {inspect.iscoroutinefunction(engine._run_reasoning)}")

sig3 = inspect.signature(engine._reasoning_step)
print(f"✅ _reasoning_step 签名: {sig3}")
print(f"   是否异步: {inspect.iscoroutinefunction(engine._reasoning_step)}")

print("\n" + "=" * 60)
print("✅ 所有基础测试通过！")
print("=" * 60)
print("\n下一步: 需要在实际环境中测试异步调用")
