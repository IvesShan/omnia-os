#!/usr/bin/env python3
"""清理测试数据脚本 - 自动模式"""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path.home() / ".omnia" / "memory_palace.db"

def cleanup_test_data():
    """清理所有测试相关的数据"""
    if not DB_PATH.exists():
        print(f"❌ 数据库不存在: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("记忆系统测试数据清理")
    print("=" * 80)
    
    # 1. 查找测试数据
    cursor.execute("""
        SELECT category, key, value, created_at 
        FROM facts 
        WHERE category LIKE '%test%' OR key LIKE '%test%'
        ORDER BY created_at DESC
    """)
    
    test_records = cursor.fetchall()
    
    print(f"\n找到 {len(test_records)} 条测试数据：")
    print("-" * 80)
    
    for category, key, value, created_at in test_records:
        value_display = value[:60] + "..." if len(value) > 60 else value
        print(f"  [{category}] {key}: {value_display}")
        print(f"    创建时间: {created_at}")
    
    print("-" * 80)
    
    # 2. 删除测试数据
    if test_records:
        cursor.execute("""
            DELETE FROM facts 
            WHERE category LIKE '%test%' OR key LIKE '%test%'
        """)
        
        deleted = cursor.rowcount
        conn.commit()
        
        print(f"\n✅ 已删除 {deleted} 条测试数据")
    else:
        print("\n✅ 没有找到测试数据")
    
    # 3. 显示剩余数据统计
    cursor.execute("SELECT COUNT(*) FROM facts")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT category) FROM facts")
    categories = cursor.fetchone()[0]
    
    print(f"\n📊 当前记忆统计：")
    print(f"   总记录数：{total}")
    print(f"   分类数：{categories}")
    
    # 4. 显示各分类的记录数
    cursor.execute("""
        SELECT category, COUNT(*) as count 
        FROM facts 
        GROUP BY category 
        ORDER BY count DESC 
        LIMIT 10
    """)
    
    print(f"\n   Top 10 分类：")
    for category, count in cursor.fetchall():
        print(f"     - {category}: {count} 条")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ 清理完成")
    print("=" * 80)

if __name__ == "__main__":
    cleanup_test_data()
