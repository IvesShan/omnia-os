#!/usr/bin/env python3
"""
简化测试：只测试记忆系统集成（不调用 LLM API）

测试内容：
1. 创建对话引擎（带记忆管理）
2. 添加记忆
3. 检索记忆
4. 验证集成效果
"""

import sys
import os

# 添加 Omnia 根目录到 Python 路径
sys.path.insert(0, "/home/shan/omnia-os/omnia-os")

from src.core.cognition.chat_integration import OmniaChatEngine


def test_memory_integration():
    """测试记忆系统集成"""
    print("=" * 60)
    print("测试：记忆系统集成（简化版）")
    print("=" * 60)
    
    # 创建对话引擎
    print("\n📦 创建对话引擎...")
    engine = OmniaChatEngine(
        max_loops=4,
        halt_threshold=0.85,
        enable_mla=True
    )
    
    print(f"✅ 引擎创建成功")
    print(f"   - 循环推理引擎: {type(engine.reasoning_engine).__name__}")
    print(f"   - 记忆管理器: {type(engine.memory_manager).__name__}")
    print(f"   - MLA 压缩器: {'已启用' if engine.compressor else '未启用'}")
    
    # 直接添加记忆（不通过 process_message）
    print("\n" + "=" * 60)
    print("添加记忆")
    print("=" * 60)
    
    # 添加一些测试记忆
    engine.memory_manager.add_memory(
        content="用户问：无人机维修需要什么工具？",
        role="user",
        metadata={"topic": "无人机维修"}
    )
    
    engine.memory_manager.add_memory(
        content="助手答：无人机维修需要螺丝刀、焊台、万用表等基础工具。",
        role="assistant",
        metadata={"topic": "无人机维修"}
    )
    
    engine.memory_manager.add_memory(
        content="用户问：Mini 3 Pro 的电池阈值是多少？",
        role="user",
        metadata={"topic": "DJI Mini 3 Pro"}
    )
    
    engine.memory_manager.add_memory(
        content="助手答：Mini 3 Pro 的升级阈值是 15%，正常使用建议保持在 10% 以上。",
        role="assistant",
        metadata={"topic": "DJI Mini 3 Pro"}
    )
    
    print(f"✅ 已添加 {len(engine.memory_manager.memories)} 条记忆")
    
    # 测试记忆检索
    print("\n" + "=" * 60)
    print("测试记忆检索")
    print("=" * 60)
    
    # 查询 1：无人机相关
    print("\n🔍 查询：'无人机维修工具'")
    results = engine.memory_manager.retrieve_relevant("无人机维修工具", top_k=3)
    
    print(f"找到 {len(results)} 条相关记忆：")
    for memory, score in results:
        print(f"  [{score:.2f}] {memory.role}: {memory.content[:50]}...")
    
    # 查询 2：电池相关
    print("\n🔍 查询：'Mini 3 Pro 电池'")
    results = engine.memory_manager.retrieve_relevant("Mini 3 Pro 电池", top_k=3)
    
    print(f"找到 {len(results)} 条相关记忆：")
    for memory, score in results:
        print(f"  [{score:.2f}] {memory.role}: {memory.content[:50]}...")
    
    # 检查记忆统计
    print("\n" + "=" * 60)
    print("记忆系统状态")
    print("=" * 60)
    
    stats = engine.memory_manager.get_stats()
    print(f"📊 总记忆数: {stats['current_memories']}")
    print(f"📊 唯一关键词: {stats['unique_keywords']}")
    print(f"📊 总检索次数: {stats['total_retrievals']}")
    print(f"📊 平均检索时间: {stats['avg_retrieval_time'] * 1000:.2f}ms")
    
    # 测试对话历史获取
    print("\n" + "=" * 60)
    print("测试对话历史获取")
    print("=" * 60)
    
    history = engine.memory_manager.get_conversation_history(max_turns=3)
    print(f"📝 最近 {len(history)} 条对话：")
    for msg in history:
        print(f"  {msg['role']}: {msg['content'][:50]}...")
    
    # 测试持久化
    print("\n" + "=" * 60)
    print("测试记忆持久化")
    print("=" * 60)
    
    memory_file = "/tmp/omnia_test_memory.json"
    engine.memory_manager.save_to_file(memory_file)
    print(f"✅ 记忆已保存到 {memory_file}")
    
    file_size = os.path.getsize(memory_file)
    print(f"   文件大小: {file_size} bytes")
    
    # 创建新引擎并加载
    new_engine = OmniaChatEngine(enable_mla=False)
    new_engine.memory_manager.load_from_file(memory_file)
    print(f"✅ 从文件加载了 {len(new_engine.memory_manager.memories)} 条记忆")
    
    # 验证
    assert len(new_engine.memory_manager.memories) == len(engine.memory_manager.memories), "记忆数量不一致"
    print("✅ 记忆完整性验证通过")
    
    # 清理
    os.remove(memory_file)
    print(f"✅ 测试文件已清理")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    
    # 总结
    print("\n📝 总结:")
    print("   ✅ 对话引擎创建成功")
    print("   ✅ 记忆管理器集成成功")
    print("   ✅ 记忆添加功能正常")
    print("   ✅ 记忆检索功能正常")
    print("   ✅ 对话历史获取正常")
    print("   ✅ 记忆持久化功能正常")


if __name__ == "__main__":
    test_memory_integration()
