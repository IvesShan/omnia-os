#!/usr/bin/env python3
"""
测试记忆系统集成

测试内容：
1. 记忆管理器基本功能
2. 记忆检索效果
3. 与对话引擎的集成
"""

import sys
import os

# 添加 Omnia 根目录到 Python 路径
sys.path.insert(0, "/home/shan/omnia-os/omnia-os")

from src.core.memory.memory_manager import MemoryManager


def test_memory_manager():
    """测试记忆管理器"""
    print("=" * 60)
    print("测试 1: 记忆管理器基本功能")
    print("=" * 60)
    
    # 创建记忆管理器
    manager = MemoryManager(max_memories=100, enable_compression=False)
    
    # 添加一些记忆
    print("\n📝 添加记忆...")
    
    manager.add_memory(
        content="用户问：无人机维修需要什么工具？",
        role="user",
        metadata={"topic": "无人机维修"}
    )
    
    manager.add_memory(
        content="助手答：无人机维修需要螺丝刀、焊台、万用表等基础工具。",
        role="assistant",
        metadata={"topic": "无人机维修"}
    )
    
    manager.add_memory(
        content="用户问：Mini 3 Pro 的电池阈值是多少？",
        role="user",
        metadata={"topic": "DJI Mini 3 Pro"}
    )
    
    manager.add_memory(
        content="助手答：Mini 3 Pro 的升级阈值是 15%，正常使用建议保持在 10% 以上。",
        role="assistant",
        metadata={"topic": "DJI Mini 3 Pro"}
    )
    
    manager.add_memory(
        content="用户问：如何提高抖音视频的完播率？",
        role="user",
        metadata={"topic": "抖音运营"}
    )
    
    manager.add_memory(
        content="助手答：提高完播率的关键是黄金3秒钩子和信息前置。",
        role="assistant",
        metadata={"topic": "抖音运营"}
    )
    
    print(f"✅ 已添加 {len(manager.memories)} 条记忆")
    
    # 测试检索
    print("\n" + "=" * 60)
    print("测试 2: 记忆检索效果")
    print("=" * 60)
    
    # 查询 1：无人机相关
    print("\n🔍 查询：'无人机维修工具'")
    results = manager.retrieve_relevant("无人机维修工具", top_k=3)
    
    print(f"找到 {len(results)} 条相关记忆：")
    for memory, score in results:
        print(f"  [{score:.2f}] {memory.role}: {memory.content[:50]}...")
    
    # 查询 2：电池相关
    print("\n🔍 查询：'Mini 3 Pro 电池'")
    results = manager.retrieve_relevant("Mini 3 Pro 电池", top_k=3)
    
    print(f"找到 {len(results)} 条相关记忆：")
    for memory, score in results:
        print(f"  [{score:.2f}] {memory.role}: {memory.content[:50]}...")
    
    # 查询 3：抖音相关
    print("\n🔍 查询：'抖音完播率'")
    results = manager.retrieve_relevant("抖音完播率", top_k=3)
    
    print(f"找到 {len(results)} 条相关记忆：")
    for memory, score in results:
        print(f"  [{score:.2f}] {memory.role}: {memory.content[:50]}...")
    
    # 测试统计
    print("\n" + "=" * 60)
    print("测试 3: 统计信息")
    print("=" * 60)
    
    stats = manager.get_stats()
    print(f"📊 当前记忆数：{stats['current_memories']}")
    print(f"📊 唯一关键词：{stats['unique_keywords']}")
    print(f"📊 总检索次数：{stats['total_retrievals']}")
    print(f"📊 平均检索时间：{stats['avg_retrieval_time'] * 1000:.2f}ms")
    
    # 测试对话历史
    print("\n" + "=" * 60)
    print("测试 4: 对话历史获取")
    print("=" * 60)
    
    history = manager.get_conversation_history(max_turns=3)
    print(f"📝 最近 {len(history)} 条对话：")
    for msg in history:
        print(f"  {msg['role']}: {msg['content'][:50]}...")
    
    # 测试保存和加载
    print("\n" + "=" * 60)
    print("测试 5: 记忆持久化")
    print("=" * 60)
    
    test_file = "/tmp/test_memory.json"
    manager.save_to_file(test_file)
    print(f"✅ 记忆已保存到 {test_file}")
    
    # 创建新管理器并加载
    new_manager = MemoryManager()
    new_manager.load_from_file(test_file)
    print(f"✅ 从文件加载了 {len(new_manager.memories)} 条记忆")
    
    # 验证
    assert len(new_manager.memories) == len(manager.memories), "记忆数量不一致"
    print("✅ 记忆完整性验证通过")
    
    # 清理测试文件
    os.remove(test_file)
    print(f"✅ 测试文件已清理")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    test_memory_manager()
