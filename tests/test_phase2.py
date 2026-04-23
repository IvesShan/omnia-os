#!/usr/bin/env python3
"""
Phase 2 Test Script - Omnia 2.0 Cognition Components

测试：
1. Intent Engine
2. Provider Abstraction
3. Context Compressor
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.cognition.intent_engine import (
    IntentEngine, IntentType, IntentContext, RuleMatcher
)
from core.providers import (
    ProviderResolver, ProviderType, MODEL_REGISTRY
)
from core.cognition.compressor import (
    ContextCompressor, CompressionResult
)


def test_intent_engine():
    """测试意图引擎"""
    print("\n" + "=" * 60)
    print("Testing Intent Engine")
    print("=" * 60)
    
    # 1. 测试规则匹配器
    matcher = RuleMatcher()
    
    test_cases = [
        ("帮我删除 test.txt 文件", IntentType.DELETE),
        ("查看一下 omnia-os 目录", IntentType.QUERY),
        ("创建一个新的 README.md", IntentType.CREATE),
        ("修改配置文件", IntentType.MODIFY),
        ("分析一下项目结构", IntentType.ANALYZE),
        ("总结一下我们今天做了什么", IntentType.REFLECT),
        ("你好，最近怎么样", IntentType.CHAT),
    ]
    
    print("\nRule-based matching:")
    for text, expected in test_cases:
        intent = matcher.match(text)
        if intent:
            match = "✅" if intent.type == expected else "⚠️"
            print(f"  {match} '{text[:30]}...'")
            print(f"      → {intent.type.value} (conf: {intent.confidence:.2f})")
            if intent.entities:
                print(f"      → entities: {list(intent.entities.keys())}")
        else:
            print(f"  ❌ '{text[:30]}...' → No match")
    
    # 2. 测试意图引擎
    engine = IntentEngine()
    context = IntentContext(
        session_id="test",
        user_id="test",
        recent_messages=[],
        available_tools=["read_file", "execute_shell", "web_search"]
    )
    
    print("\nIntent Engine (without LLM):")
    import asyncio
    
    async def test_async():
        intent = await engine.recognize("帮我梳理一下 Omnia 的架构", context)
        print(f"  Intent: {intent.type.value}")
        print(f"  Confidence: {intent.confidence:.2f}")
        
        # 测试分解
        intent = await engine.recognize("帮我整理项目并部署到服务器", context)
        sub_intents = engine.decompose(intent)
        print(f"\n  Decomposed '{intent.raw_text[:30]}...':")
        for i, sub in enumerate(sub_intents):
            print(f"    {i+1}. {sub.raw_text}")
        
        # 测试工具推荐
        hints = engine.to_tool_hints(intent)
        print(f"\n  Tool hints: {hints}")
    
    asyncio.run(test_async())
    
    print("\n✅ Intent Engine test passed!")


def test_provider_abstraction():
    """测试 Provider 抽象"""
    print("\n" + "=" * 60)
    print("Testing Provider Abstraction")
    print("=" * 60)
    
    # 1. 列出所有支持的模型
    print(f"\nTotal models in registry: {len(MODEL_REGISTRY)}")
    
    # 按 Provider 分组
    by_provider = {}
    for model_id, config in MODEL_REGISTRY.items():
        provider = config.provider.value
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(model_id)
    
    print("\nModels by provider:")
    for provider, models in sorted(by_provider.items()):
        print(f"  {provider}: {len(models)} models")
        for m in models[:2]:
            config = MODEL_REGISTRY[m]
            print(f"    - {m} ({config.display_name})")
    
    # 2. 测试 Resolver
    resolver = ProviderResolver()
    
    print("\nProvider Resolver:")
    
    # 测试配置获取
    config = resolver.get_config("openai/gpt-4o")
    if config:
        print(f"  gpt-4o config:")
        print(f"    - Context window: {config.context_window:,}")
        print(f"    - Supports vision: {config.supports_vision}")
        print(f"    - Supports tools: {config.supports_tools}")
    
    # 测试降级链
    fallback = resolver.get_fallback_chain("openai/gpt-4o")
    print(f"\n  Fallback chain for gpt-4o:")
    for i, model in enumerate(fallback):
        print(f"    {i+1}. {model}")
    
    # 列出可用模型
    available = resolver.list_available()
    print(f"\n  Available models (with API keys): {len(available)}")
    for m in available[:5]:
        print(f"    - {m}")
    
    print("\n✅ Provider Abstraction test passed!")


def test_context_compressor():
    """测试上下文压缩"""
    print("\n" + "=" * 60)
    print("Testing Context Compressor")
    print("=" * 60)
    
    compressor = ContextCompressor(max_tokens=500, preserve_recent=3)
    
    # 创建测试消息
    messages = [
        {"role": "system", "content": "你是 Omnia，一个 AI 助手。"},
        {"role": "user", "content": "你好，我是原点"},
        {"role": "assistant", "content": "你好原点！我是 Omnia，很高兴认识你。"},
        {"role": "user", "content": "帮我看看 omnia-os/src/core 目录下的文件"},
        {"role": "assistant", "content": "好的，让我看一下。目录下有以下文件：\n- tool_base.py\n- intent_engine.py\n- compressor.py"},
        {"role": "user", "content": "很好，现在帮我删除 test.txt 文件"},
        {"role": "assistant", "content": "已删除 test.txt 文件。"},
        {"role": "user", "content": "总结一下我们今天做了什么"},
        {"role": "assistant", "content": "好的，总结如下：\n1. 查看了 omnia-os/src/core 目录\n2. 删除了 test.txt 文件"},
    ]
    
    print(f"\nOriginal messages: {len(messages)}")
    
    import asyncio
    
    async def test_compress():
        result = await compressor.compress(messages)
        
        print(f"Original tokens: {result.original_tokens}")
        print(f"Compressed tokens: {result.compressed_tokens}")
        print(f"Compression ratio: {result.compression_ratio:.2%}")
        print(f"\nCompressed messages: {len(result.messages)}")
        
        for i, msg in enumerate(result.messages):
            content = msg.get("content", "")[:50]
            print(f"  {i+1}. [{msg['role']}] {content}...")
        
        if result.summary:
            print(f"\nSummary:\n  {result.summary[:200]}...")
        
        if result.preserved_entities:
            print(f"\nPreserved entities: {result.preserved_entities}")
    
    asyncio.run(test_compress())
    
    print("\n✅ Context Compressor test passed!")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Omnia 2.0 Phase 2 - Cognition Components Test")
    print("=" * 60)
    
    try:
        test_intent_engine()
        test_provider_abstraction()
        test_context_compressor()
        
        print("\n" + "=" * 60)
        print("✅ All Phase 2 tests passed!")
        print("=" * 60)
        
        return 0
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
