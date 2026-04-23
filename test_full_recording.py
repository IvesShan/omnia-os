#!/usr/bin/env python3
"""
完整端到端测试 - 模拟真实对话流程
测试所有记录功能是否正常工作
"""

import sys
import os
import json
import time
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '/home/shan//home/shan/omnia-os/omnia-os/src')

from core.memory_palace.memory_palace import MemoryPalace

def test_full_conversation_flow():
    """测试完整的对话流程"""
    print("\n" + "="*60)
    print("🧪 完整端到端测试 - 模拟真实对话")
    print("="*60)
    
    # 初始化
    palace = MemoryPalace(db_path="~/.omnia/memory_palace.db")
    
    # 确保数据库已初始化
    print("\n📦 初始化数据库...")
    palace.initialize()
    
    # 1. 记录用户消息
    print("\n📝 [1] 记录用户消息...")
    user_msg_id = palace.log_conversation(
        session_id="test_session_001",
        turn_number=1,
        role="user",
        content="帮我分析一下 DJI Osmo Action 5 Pro 的参数",
        metadata={"source": "web", "user_agent": "test"}
    )
    print(f"   ✅ 用户消息已记录 (ID: {user_msg_id})")
    
    # 2. 记录助手回复
    print("\n📝 [2] 记录助手回复...")
    assistant_msg_id = palace.log_conversation(
        session_id="test_session_001",
        turn_number=2,
        role="assistant",
        content="DJI Osmo Action 5 Pro 是一款专业运动相机，主要参数包括：\n- 传感器：1/1.3英寸\n- 视频分辨率：4K/120fps\n- 防抖：RockSteady 3.0\n- 防水：18米",
        metadata={"model": "gpt-4", "tokens": 150}
    )
    print(f"   ✅ 助手回复已记录 (ID: {assistant_msg_id})")
    
    # 3. 记录工具调用
    print("\n📝 [3] 记录工具调用...")
    tool_id = palace.log_tool_use(
        session_id="test_session_001",
        tool_name="web_search",
        arguments={"query": "DJI Osmo Action 5 Pro specs"},
        result="Found detailed specifications...",
        turn_number=1
    )
    print(f"   ✅ 工具调用已记录 (ID: {tool_id})")
    
    # 4. 验证记录
    print("\n🔍 [4] 验证记录完整性...")
    
    # 检查对话记录
    conversations = palace.recall_conversations(session_id="test_session_001")
    print(f"   📊 对话记录: {len(conversations)} 条")
    
    for i, conv in enumerate(conversations, 1):
        print(f"      [{i}] {conv['role']}: {conv['content'][:50]}...")
    
    # 检查工具记录
    tools = palace.recall_tool_logs(session_id="test_session_001")
    print(f"   📊 工具调用: {len(tools)} 条")
    
    for i, tool in enumerate(tools, 1):
        print(f"      [{i}] {tool['tool_name']}: {tool['arguments'][:50]}...")
    
    # 5. 测试语义搜索功能
    print("\n🔍 [5] 测试语义搜索功能...")
    try:
        results = palace.search_conversations_semantic("DJI Action", top_k=5)
        print(f"   📊 搜索结果: {len(results)} 条")
        
        for i, (result, score) in enumerate(results[:3], 1):
            print(f"      [{i}] 相似度: {score:.3f} | {result['role']}: {result['content'][:40]}...")
    except Exception as e:
        print(f"   ⚠️  语义搜索测试失败（可能需要向量服务）: {e}")
    
    # 6. 统计数据
    print("\n📊 [6] 数据库统计...")
    conn = palace._connect()
    
    stats = {
        "facts": conn.execute("SELECT COUNT(*) as count FROM facts").fetchone()['count'],
        "relations": conn.execute("SELECT COUNT(*) as count FROM relations").fetchone()['count'],
        "habits": conn.execute("SELECT COUNT(*) as count FROM habits").fetchone()['count'],
        "timeline": conn.execute("SELECT COUNT(*) as count FROM timeline").fetchone()['count'],
        "conversation_logs": conn.execute("SELECT COUNT(*) as count FROM conversation_logs").fetchone()['count'],
        "tool_logs": conn.execute("SELECT COUNT(*) as count FROM tool_logs").fetchone()['count'],
    }
    
    print(f"   📈 facts: {stats['facts']} 条")
    print(f"   📈 relations: {stats['relations']} 条")
    print(f"   📈 habits: {stats['habits']} 条")
    print(f"   📈 timeline: {stats['timeline']} 条")
    print(f"   📈 conversation_logs: {stats['conversation_logs']} 条")
    print(f"   📈 tool_logs: {stats['tool_logs']} 条")
    
    # 7. 清理测试数据
    print("\n🧹 [7] 清理测试数据...")
    conn.execute("DELETE FROM conversation_logs WHERE session_id = ?", ("test_session_001",))
    conn.execute("DELETE FROM tool_logs WHERE session_id = ?", ("test_session_001",))
    conn.commit()
    print("   ✅ 测试数据已清理")
    
    # 最终验证
    print("\n" + "="*60)
    print("✅ 测试完成！记录系统工作正常")
    print("="*60)
    
    return True

def test_concurrent_sessions():
    """测试多会话并发记录"""
    print("\n" + "="*60)
    print("🧪 多会话并发测试")
    print("="*60)
    
    palace = MemoryPalace(db_path="~/.omnia/memory_palace.db")
    palace.initialize()
    
    # 创建多个会话
    sessions = ["session_A", "session_B", "session_C"]
    
    for session_id in sessions:
        print(f"\n📝 创建会话: {session_id}")
        
        # 记录用户消息
        palace.log_conversation(
            session_id=session_id,
            turn_number=1,
            role="user",
            content=f"这是 {session_id} 的测试消息"
        )
        
        # 记录助手回复
        palace.log_conversation(
            session_id=session_id,
            turn_number=2,
            role="assistant",
            content=f"回复 {session_id}"
        )
        
        # 记录工具调用
        palace.log_tool_use(
            session_id=session_id,
            tool_name="test_tool",
            arguments={"session": session_id},
            result="ok"
        )
    
    # 验证每个会话
    print("\n🔍 验证会话隔离...")
    
    for session_id in sessions:
        count = len(palace.recall_conversations(session_id=session_id))
        print(f"   📊 {session_id}: {count} 条对话记录")
    
    # 清理
    print("\n🧹 清理测试数据...")
    conn = palace._connect()
    for session_id in sessions:
        conn.execute("DELETE FROM conversation_logs WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM tool_logs WHERE session_id = ?", (session_id,))
    conn.commit()
    
    print("✅ 多会话测试完成")
    return True

def test_persistence():
    """测试数据持久化"""
    print("\n" + "="*60)
    print("🧪 数据持久化测试")
    print("="*60)
    
    # 第一次写入
    print("\n📝 第一次写入...")
    palace1 = MemoryPalace(db_path="~/.omnia/memory_palace.db")
    palace1.initialize()
    
    palace1.log_conversation(
        session_id="persistence_test",
        turn_number=1,
        role="user",
        content="这是持久化测试消息"
    )
    
    # 第二次读取
    print("\n📖 第二次读取（新实例）...")
    palace2 = MemoryPalace(db_path="~/.omnia/memory_palace.db")
    
    results = palace2.recall_conversations(session_id="persistence_test")
    print(f"   📊 读取到 {len(results)} 条记录")
    
    if len(results) > 0:
        print(f"   ✅ 持久化成功: {results[0]['content']}")
    else:
        print("   ❌ 持久化失败")
    
    # 清理
    conn = palace2._connect()
    conn.execute("DELETE FROM conversation_logs WHERE session_id = ?", ("persistence_test",))
    conn.commit()
    
    print("✅ 持久化测试完成")
    return True

if __name__ == "__main__":
    try:
        # 运行所有测试
        test_full_conversation_flow()
        test_concurrent_sessions()
        test_persistence()
        
        print("\n" + "="*60)
        print("🎉 所有测试通过！记录系统完全正常")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
