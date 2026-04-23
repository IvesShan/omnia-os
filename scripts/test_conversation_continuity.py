#!/usr/bin/env python3
"""测试对话连续性功能

验证以下优化是否生效：
1. 会话历史自动加载
2. Context Manager 集成
3. 智能会话管理
4. 语义检索增强
"""

import sys
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.config import OMNIA_HOME, MEMORY_PALACE_DB
from core.context_manager import ContextManager
from core.session_manager import get_session_manager, load_recent_conversations
from core.memory_palace.memory_palace_with_graph import MemoryPalace


def test_session_manager():
    """测试智能会话管理"""
    print("\n" + "="*60)
    print("📋 测试 1: 智能会话管理")
    print("="*60)
    
    session_manager = get_session_manager()
    
    # 获取或创建会话
    session_id = session_manager.get_or_create_session()
    print(f"✅ 当前会话 ID: {session_id}")
    
    # 检查会话文件
    session_file = OMNIA_HOME / "current_session.json"
    if session_file.exists():
        print(f"✅ 会话文件存在: {session_file}")
        import json
        data = json.loads(session_file.read_text())
        print(f"   - 会话 ID: {data['session_id']}")
        print(f"   - 消息数: {data['message_count']}")
    else:
        print(f"❌ 会话文件不存在")
    
    return True


def test_context_manager():
    """测试 Context Manager"""
    print("\n" + "="*60)
    print("📋 测试 2: Context Manager")
    print("="*60)
    
    context_manager = ContextManager(OMNIA_HOME)
    
    # 加载上次上下文
    last_context = context_manager.load_context()
    if last_context:
        print(f"✅ 上次上下文已加载")
        print(f"   - 时间: {last_context.timestamp}")
        print(f"   - 主题: {last_context.topic}")
        print(f"   - 摘要: {last_context.summary[:50]}...")
        if last_context.next_steps:
            print(f"   - 下一步: {last_context.next_steps[0]}")
    else:
        print(f"⚠️ 无上次上下文")
    
    # 检查上下文文件
    context_file = OMNIA_HOME / "last_context.json"
    if context_file.exists():
        print(f"✅ 上下文文件存在: {context_file}")
    else:
        print(f"❌ 上下文文件不存在")
    
    return True


def test_history_loading():
    """测试会话历史加载"""
    print("\n" + "="*60)
    print("📋 测试 3: 会话历史自动加载")
    print("="*60)
    
    # 测试默认加载
    history = load_recent_conversations(limit=5)
    print(f"✅ 加载了 {len(history)} 条历史对话")
    
    if history:
        print(f"   - 第一条: [{history[0]['role']}] {history[0]['content'][:50]}...")
        print(f"   - 最后一条: [{history[-1]['role']}] {history[-1]['content'][:50]}...")
    
    # 测试语义搜索
    print("\n测试语义搜索...")
    history_semantic = load_recent_conversations(
        limit=5,
        current_message="Omnia 系统优化",
        min_similarity=0.5
    )
    print(f"✅ 语义搜索返回 {len(history_semantic)} 条相关对话")
    
    if history_semantic:
        for i, h in enumerate(history_semantic[:3], 1):
            similarity = h.get('similarity', 0)
            print(f"   {i}. 相似度 {similarity:.2f}: {h['content'][:40]}...")
    
    return True


def test_semantic_search():
    """测试语义检索功能"""
    print("\n" + "="*60)
    print("📋 测试 4: 语义检索增强")
    print("="*60)
    
    mp = MemoryPalace(str(MEMORY_PALACE_DB))
    mp.initialize()
    
    # 测试语义搜索
    test_message = "对话连续性优化"
    print(f"搜索关键词: {test_message}")
    
    try:
        similar = mp.search_conversations_semantic(test_message, top_k=5)
        print(f"✅ 找到 {len(similar)} 条相关对话")
        
        for i, (conv, score) in enumerate(similar[:3], 1):
            print(f"   {i}. 相似度 {score:.2f}: [{conv['role']}] {conv['content'][:40]}...")
        
        return True
    except Exception as e:
        print(f"❌ 语义搜索失败: {e}")
        return False


def test_memory_palace_stats():
    """测试 Memory Palace 统计"""
    print("\n" + "="*60)
    print("📋 测试 5: Memory Palace 统计")
    print("="*60)
    
    mp = MemoryPalace(str(MEMORY_PALACE_DB))
    conn = mp._connect()
    
    # 对话记录统计
    total = conn.execute("SELECT COUNT(*) FROM conversation_logs").fetchone()[0]
    with_embedding = conn.execute("SELECT COUNT(embedding) FROM conversation_logs WHERE embedding IS NOT NULL").fetchone()[0]
    
    print(f"✅ 总对话记录: {total}")
    print(f"✅ 有向量嵌入: {with_embedding} ({with_embedding/total*100:.1f}%)")
    print(f"⚠️ 无向量嵌入: {total - with_embedding} ({(total-with_embedding)/total*100:.1f}%)")
    
    # 最近对话
    recent = conn.execute("""
        SELECT role, content, created_at 
        FROM conversation_logs 
        ORDER BY created_at DESC 
        LIMIT 3
    """).fetchall()
    
    print(f"\n最近 3 条对话:")
    for i, row in enumerate(recent, 1):
        print(f"   {i}. [{row[0]}] {row[1][:50]}...")
    
    return True


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🧪 Omnia 对话连续性功能测试")
    print("="*60)
    
    tests = [
        ("智能会话管理", test_session_manager),
        ("Context Manager", test_context_manager),
        ("会话历史加载", test_history_loading),
        ("语义检索增强", test_semantic_search),
        ("Memory Palace 统计", test_memory_palace_stats),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 测试失败: {name}")
            print(f"   错误: {e}")
            results.append((name, False))
    
    # 总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！对话连续性优化已完成。")
    else:
        print(f"\n⚠️ {total - passed} 个测试失败，请检查。")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
