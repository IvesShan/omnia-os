#!/usr/bin/env python3
"""
记忆系统集成测试

测试：
1. MemoryManager 基础功能
2. LLMReasoningAdapter 记忆集成
3. 完整对话流程
"""

import asyncio
import sys
sys.path.insert(0, '/home/shan/omnia-os/omnia-os/src')

from core.memory.memory_manager import MemoryManager
from core.cognition.llm_reasoning_adapter import LLMReasoningAdapter


def print_header(title: str):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def test_memory_manager():
    """测试 MemoryManager 基础功能"""
    print_header("测试 1: MemoryManager 基础功能")
    
    # 创建记忆管理器
    mm = MemoryManager(max_memories=100)
    
    # 添加记忆
    print("\n📝 添加记忆...")
    mm.add_memory("用户的名字是原点", "assistant")
    mm.add_memory("用户经营无人机维修公司", "assistant")
    mm.add_memory("用户喜欢编程和蓝色", "assistant")
    mm.add_memory("Omnia 是一个自主的 AI 操作系统", "assistant")
    mm.add_memory("无限是用户的 AI 助手", "assistant")
    
    print(f"✅ 已添加 {mm.stats['total_memories']} 条记忆")
    
    # 检索相关记忆
    print("\n🔍 检索相关记忆...")
    results = mm.retrieve_relevant("用户是谁", top_k=3)
    
    print(f"找到 {len(results)} 条相关记忆：")
    for memory, score in results:
        print(f"  [{score:.2f}] {memory.content}")
    
    # 获取最近记忆
    print("\n📚 最近记忆...")
    recent = mm.get_recent_memories(3)
    for m in recent:
        print(f"  - {m.content}")
    
    # 统计信息
    stats = mm.get_stats()
    print(f"\n📊 统计: {stats}")
    
    return mm


async def test_llm_adapter_with_memory():
    """测试 LLM 推理适配器与记忆集成"""
    print_header("测试 2: LLM 推理适配器 + 记忆集成")
    
    # 创建记忆管理器
    mm = MemoryManager(max_memories=100)
    mm.add_memory("用户的名字是原点", "assistant")
    mm.add_memory("用户经营无人机维修公司", "assistant")
    mm.add_memory("用户喜欢编程和蓝色", "assistant")
    
    # 创建 LLM 推理适配器
    adapter = LLMReasoningAdapter(memory_manager=mm, max_loops=3)
    
    print("\n🧠 处理用户输入...")
    print("用户: 你好，我是谁？")
    
    try:
        result = await adapter.process("你好，我是谁？")
        
        print(f"\n🤖 Omnia 回复:")
        print(f"  {result['response'][:200]}...")
        print(f"\n📊 推理深度: {result['depth']}")
        print(f"📊 置信度: {result['confidence']:.2f}")
        print(f"📊 使用记忆: {len(result['memories_used'])} 条")
        
        if result['memories_used']:
            print("\n📚 使用的记忆:")
            for m in result['memories_used'][:3]:
                print(f"  - {m[:80]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_conversation_flow():
    """测试完整对话流程"""
    print_header("测试 3: 完整对话流程")
    
    # 创建记忆管理器
    mm = MemoryManager(max_memories=100)
    
    # 预加载一些记忆
    mm.add_memory("原点是用户的名字", "assistant")
    mm.add_memory("用户经营无人机维修公司喵修匠", "assistant")
    mm.add_memory("用户正在开发 Omnia AI 操作系统", "assistant")
    
    # 创建适配器
    adapter = LLMReasoningAdapter(memory_manager=mm, max_loops=3)
    
    # 模拟对话
    conversations = [
        "你好",
        "我叫什么名字？",
        "我在做什么项目？"
    ]
    
    for user_input in conversations:
        print(f"\n👤 用户: {user_input}")
        
        try:
            result = await adapter.process(user_input)
            
            # 保存对话到记忆
            mm.add_memory(user_input, "user")
            mm.add_memory(result['response'][:200], "assistant")
            
            print(f"🤖 Omnia: {result['response'][:150]}...")
            print(f"   [深度={result['depth']}, 记忆={len(result['memories_used'])}]")
            
        except Exception as e:
            print(f"❌ 错误: {e}")
    
    print(f"\n📊 总记忆数: {mm.stats['total_memories']}")
    
    return True


async def main():
    print("\n" + "=" * 60)
    print("Omnia 记忆系统集成测试")
    print("=" * 60)
    
    results = []
    
    # 测试 1: MemoryManager
    try:
        mm = test_memory_manager()
        results.append(("MemoryManager 基础功能", True))
    except Exception as e:
        print(f"❌ 测试 1 失败: {e}")
        results.append(("MemoryManager 基础功能", False))
    
    # 测试 2: LLM 适配器 + 记忆
    try:
        success = await test_llm_adapter_with_memory()
        results.append(("LLM 适配器 + 记忆集成", success))
    except Exception as e:
        print(f"❌ 测试 2 失败: {e}")
        results.append(("LLM 适配器 + 记忆集成", False))
    
    # 测试 3: 完整对话流程
    try:
        success = await test_conversation_flow()
        results.append(("完整对话流程", success))
    except Exception as e:
        print(f"❌ 测试 3 失败: {e}")
        results.append(("完整对话流程", False))
    
    # 总结
    print_header("测试总结")
    passed = sum(1 for _, s in results if s)
    total = len(results)
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {status}: {name}")
    
    print(f"\n总体: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！记忆系统集成成功！")
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息")


if __name__ == "__main__":
    asyncio.run(main())
