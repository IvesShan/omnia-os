#!/usr/bin/env python3
"""
清理测试数据脚本
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.memory_palace import MemoryPalace

def cleanup_test_data():
    """清理测试数据"""
    print("🧹 开始清理测试数据...\n")
    
    memory = MemoryPalace()
    
    # 1. 清理 facts 表中的测试数据
    print("📋 检查 facts 表...")
    test_facts = memory.query_facts("测试")
    
    if test_facts:
        print(f"   找到 {len(test_facts)} 条测试记录")
        
        for fact in test_facts:
            if fact.get('category') == '测试类别' or fact.get('key') == '测试键':
                print(f"   - 删除: [{fact['category']}] {fact['key']} = {fact['value']}")
                memory.delete_fact(fact['id'])
    else:
        print("   ✅ 没有找到测试记录")
    
    # 2. 清理 timeline 表中的测试数据
    print("\n📅 检查 timeline 表...")
    # 注意：MemoryPalace 可能没有 delete_timeline 方法，需要直接操作数据库
    cursor = memory.conn.cursor()
    
    # 查找包含"测试"的 timeline 记录
    cursor.execute("""
        SELECT id, event_type, title 
        FROM timeline 
        WHERE title LIKE '%测试%' OR description LIKE '%测试%'
    """)
    
    test_timelines = cursor.fetchall()
    
    if test_timelines:
        print(f"   找到 {len(test_timelines)} 条测试时间线记录")
        
        for tl in test_timelines:
            tl_id, event_type, title = tl
            # 只删除明显的测试记录
            if '测试记录功能' in title or '测试消息' in title:
                print(f"   - 删除: [{event_type}] {title[:50]}...")
                cursor.execute("DELETE FROM timeline WHERE id = ?", (tl_id,))
    else:
        print("   ✅ 没有找到测试时间线记录")
    
    # 提交更改
    memory.conn.commit()
    
    # 3. 验证清理结果
    print("\n🔍 验证清理结果...")
    
    # 重新查询
    remaining_test_facts = memory.query_facts("测试")
    cursor.execute("""
        SELECT COUNT(*) FROM timeline 
        WHERE title LIKE '%测试记录功能%' OR description LIKE '%测试记录功能%'
    """)
    remaining_test_timeline = cursor.fetchone()[0]
    
    print(f"   - 剩余测试 facts: {len([f for f in remaining_test_facts if f.get('category') == '测试类别'])} 条")
    print(f"   - 剩余测试 timeline: {remaining_test_timeline} 条")
    
    print("\n✅ 清理完成！")
    
    memory.close()

if __name__ == "__main__":
    cleanup_test_data()
