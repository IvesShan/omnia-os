#!/usr/bin/env python3
"""
记忆系统集成测试 v2

测试：
1. MemoryManager 关键词提取
2. 记忆检索优化
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


def test_keyword_extraction():
    """测试关键词提取"""
    print_header("测试 1: 关键词提取")
    
    mm = MemoryManager()
    
    test_texts = [
        "用户的名字是原点",
        "用户经营无人机维修公司",
        "Omnia 是一个自主的 AI 操作系统"
    ]
    
    for text in test_texts:
        keywords = mm._extract_keywords(text)
        print(f"\n文本: {text}")
        print(f"关键词: {keywords}")


def test_memory_retrieval():
    """测试记忆检索"""
    print_header("测试 2: 记忆检索优化")
    
    mm = MemoryManager()
    
    # 添加记忆
    memories = [
        ("原点", "用户的名字是原点"),
        ("无人机", "用户经营无人机维修公司"),
        ("编程", "用户喜欢编程"),
        ("Omnia", "Omnia 是一个自主的 AI 操作系统"),
        ("无限", "无限是用户的 AI 助手")
    ]
    
    for keyword, content in memories:
        mm.add_memory(content, "assistant")
        print(f"添加: {content}")
        print(f"  关键词: {mm._extract_keywords(content)}")
    
    # 测试检索
    queries = [
        "原点是谁",
        "无人机",
        "Omnia 是什么"
    ]
    
    for query in queries:
        print(f"\n查询: {query}")
        print(f"查询关键词: {mm._extract_keywords(query)}")
        
        results = mm.retrieve_relevant(query, top_k=3, min_score=0.1)
        print(f"找到 {len(results)} 条:")
        for memory, score in results:
            print(f"  [{score:.2f}] {memory.content}")


async def test_full_integration():
    """测试完整集成"""
    print_header("测试 3: 完整集成")
    
    # 创建记忆管理器
    mm = MemoryManager()
    
    # 添加一些记忆
    mm.add_memory("用户的名字是原点", "assistant")
    mm.add_memory("用户经营无人机维修公司喵修匠", "assistant")
    mm.add_memory("Omnia 是一个自主的 AI 操作系统", "assistant")
    
    # 创建适配器
    adapter = LLMReasoningAdapter(memory_manager=mm, max_loops=2)
    
    # 测试对话
    result = await adapter.process("你好，我叫什么名字？")
    
    print(f"\n用户: 你好，我叫什么名字？")
    print(f"Omnia: {result['response'][:200]}...")
    print(f"\n推理深度: {result['depth']}")
    print(f"使用记忆: {len(result['memories_used'])} 条")


async def main():
    print("\n" + "=" * 60)
    print("Omnia 记忆系统集成测试 v2")
    print("=" * 60)
    
    # 测试 1
    test_keyword_extraction()
    
    # 测试 2
    test_memory_retrieval()
    
    # 测试 3
    await test_full_integration()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
