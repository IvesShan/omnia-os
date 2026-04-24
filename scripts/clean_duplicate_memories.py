#!/usr/bin/env python3
"""
清理重复记忆脚本
P0 优先级 - 立即执行

功能：
1. 扫描并删除重复的 timeline 记忆
2. 清理异常数据（如 "Sender (untrusted metadata)"）
3. 生成清理报告
"""

import sqlite3
import os
from datetime import datetime
from collections import Counter
from pathlib import Path

# 数据库路径 - 使用正确的配置
DB_PATH = Path.home() / ".omnia" / "memory_palace.db"

def get_connection():
    """获取数据库连接"""
    if not DB_PATH.exists():
        print(f"❌ 数据库不存在: {DB_PATH}")
        return None
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def scan_duplicates():
    """扫描重复记忆"""
    print("🔍 扫描重复记忆...")
    
    conn = get_connection()
    if not conn:
        return [], []
    
    cursor = conn.cursor()
    
    # 查找重复的 title
    cursor.execute("""
        SELECT title, COUNT(*) as count
        FROM timeline
        GROUP BY title
        HAVING count > 1
        ORDER BY count DESC
    """)
    
    duplicates = cursor.fetchall()
    print(f"   发现 {len(duplicates)} 种重复标题")
    
    # 统计异常数据
    cursor.execute("""
        SELECT title, COUNT(*) as count
        FROM timeline
        WHERE title LIKE '%Sender (untrusted metadata)%'
           OR title LIKE '%```json%'
           OR title LIKE '%```%'
        GROUP BY title
        ORDER BY count DESC
    """)
    
    anomalies = cursor.fetchall()
    print(f"   发现 {len(anomalies)} 种异常数据")
    
    # 显示前5种重复最多的
    if duplicates:
        print("\n   📊 重复最多的记忆（前5种）:")
        for row in duplicates[:5]:
            print(f"      [{row['count']}次] {row['title'][:60]}...")
    
    # 显示异常数据
    if anomalies:
        print("\n   ⚠️  异常数据（前5种）:")
        for row in anomalies[:5]:
            print(f"      [{row['count']}次] {row['title'][:60]}...")
    
    conn.close()
    
    return duplicates, anomalies

def clean_anomalies(dry_run=True):
    """清理异常数据"""
    print("\n🧹 清理异常数据...")
    
    conn = get_connection()
    if not conn:
        return 0
    
    cursor = conn.cursor()
    
    # 查找所有异常记录
    cursor.execute("""
        SELECT id, title, event_date
        FROM timeline
        WHERE title LIKE '%Sender (untrusted metadata)%'
           OR title LIKE '%```json%'
           OR title LIKE '%```%'
        ORDER BY title, event_date
    """)
    
    anomalies = cursor.fetchall()
    
    if dry_run:
        print(f"   [DRY RUN] 将删除 {len(anomalies)} 条异常记录")
        if anomalies:
            print("   前5条示例:")
            for row in anomalies[:5]:
                print(f"      - ID {row['id']}: {row['title'][:60]}...")
    else:
        # 删除异常记录
        cursor.execute("""
            DELETE FROM timeline
            WHERE title LIKE '%Sender (untrusted metadata)%'
               OR title LIKE '%```json%'
               OR title LIKE '%```%'
        """)
        
        deleted = cursor.rowcount
        conn.commit()
        print(f"   ✅ 已删除 {deleted} 条异常记录")
    
    conn.close()
    return len(anomalies)

def clean_duplicates(dry_run=True):
    """清理重复记忆（保留最早的一条）"""
    print("\n🧹 清理重复记忆...")
    
    conn = get_connection()
    if not conn:
        return 0
    
    cursor = conn.cursor()
    
    # 查找所有重复记录
    cursor.execute("""
        SELECT id, title, event_date
        FROM timeline
        WHERE title IN (
            SELECT title
            FROM timeline
            GROUP BY title
            HAVING COUNT(*) > 1
        )
        ORDER BY title, event_date
    """)
    
    all_records = cursor.fetchall()
    
    # 按标题分组，保留最早的一条
    title_groups = {}
    for row in all_records:
        title = row['title']
        if title not in title_groups:
            title_groups[title] = []
        title_groups[title].append(row['id'])
    
    # 收集要删除的 ID
    to_delete = []
    for title, ids in title_groups.items():
        # 保留第一个（最早的），删除其余的
        to_delete.extend(ids[1:])
    
    if dry_run:
        print(f"   [DRY RUN] 将删除 {len(to_delete)} 条重复记录")
        print(f"   [DRY RUN] 保留 {len(title_groups)} 条唯一记录")
    else:
        if to_delete:
            # 删除重复记录
            placeholders = ','.join('?' * len(to_delete))
            cursor.execute(f"""
                DELETE FROM timeline
                WHERE id IN ({placeholders})
            """, to_delete)
            
            deleted = cursor.rowcount
            conn.commit()
            print(f"   ✅ 已删除 {deleted} 条重复记录")
        else:
            print("   ✅ 没有需要删除的重复记录")
    
    conn.close()
    return len(to_delete)

def generate_report(before_count, after_count, deleted_anomalies, deleted_duplicates):
    """生成清理报告"""
    print("\n" + "="*60)
    print("📊 清理报告")
    print("="*60)
    print(f"清理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"数据库: {DB_PATH}")
    print(f"\n记忆数量:")
    print(f"  清理前: {before_count}")
    print(f"  清理后: {after_count}")
    print(f"  减少: {before_count - after_count}")
    print(f"\n删除详情:")
    print(f"  异常数据: {deleted_anomalies} 条")
    print(f"  重复记忆: {deleted_duplicates} 条")
    print("="*60)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='清理重复记忆')
    parser.add_argument('--execute', action='store_true', 
                       help='实际执行删除（默认只预览）')
    args = parser.parse_args()
    
    dry_run = not args.execute
    
    if dry_run:
        print("⚠️  预览模式 - 使用 --execute 实际执行删除")
    
    print(f"\n📂 数据库路径: {DB_PATH}")
    
    # 获取清理前的记忆数量
    conn = get_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM timeline")
    before_count = cursor.fetchone()[0]
    
    # 获取各表的数量
    cursor.execute("SELECT COUNT(*) FROM facts")
    facts_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM relations")
    relations_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM habits")
    habits_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n📊 当前记忆统计:")
    print(f"   Timeline: {before_count}")
    print(f"   Facts: {facts_count}")
    print(f"   Relations: {relations_count}")
    print(f"   Habits: {habits_count}")
    
    # 扫描重复
    duplicates, anomalies = scan_duplicates()
    
    # 清理异常数据
    deleted_anomalies = clean_anomalies(dry_run)
    
    # 清理重复记忆
    deleted_duplicates = clean_duplicates(dry_run)
    
    # 计算清理后的数量
    after_count = before_count - deleted_anomalies - deleted_duplicates
    
    # 生成报告
    generate_report(before_count, after_count, deleted_anomalies, deleted_duplicates)
    
    if dry_run:
        print("\n💡 使用以下命令实际执行清理:")
        print("   python3 scripts/clean_duplicate_memories.py --execute")

if __name__ == "__main__":
    main()
