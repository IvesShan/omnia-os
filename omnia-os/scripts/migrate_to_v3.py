#!/usr/bin/env python3
"""
数据迁移脚本：Memory V1 → Memory V3

直接使用 MemoryV3 类的方法进行迁移
"""

import sqlite3
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.memory.memory_v3 import MemoryV3


def migrate():
    """执行迁移"""
    source_db = str(Path.home() / ".omnia" / "memory_palace.db")
    target_db = str(Path.home() / ".omnia" / "memory_v3.db")
    
    print("=" * 60)
    print("开始迁移 Memory V1 → Memory V3")
    print("=" * 60)
    
    # 连接源数据库
    source_conn = sqlite3.connect(source_db)
    source_conn.row_factory = sqlite3.Row
    source_cursor = source_conn.cursor()
    
    # 初始化目标数据库
    if Path(target_db).exists():
        backup_path = target_db + f".backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        import shutil
        shutil.copy(target_db, backup_path)
        print(f"📦 已备份旧数据库到: {backup_path}")
        Path(target_db).unlink()
    
    memory_v3 = MemoryV3(target_db)
    print(f"✅ 已初始化目标数据库: {target_db}\n")
    
    stats = {}
    
    # 1. 迁移 facts
    print("[1/5] 迁移 facts...")
    source_cursor.execute('''
        SELECT category, key, value, source, created_at, updated_at, strength
        FROM facts ORDER BY id
    ''')
    facts_rows = source_cursor.fetchall()
    for row in facts_rows:
        memory_v3.add_fact(
            key=row['key'],
            value=row['value'],
            category=row['category'],
            source=row['source'] or 'unknown',
            priority=int((row['strength'] or 1.0) * 10)
        )
    stats['facts'] = len(facts_rows)
    print(f"  ✅ 已迁移 {len(facts_rows)} 条")
    
    # 2. 迁移 relations
    print("[2/5] 迁移 relations...")
    source_cursor.execute('''
        SELECT subject, predicate, object, context, created_at, strength
        FROM relations ORDER BY id
    ''')
    relations_rows = source_cursor.fetchall()
    for row in relations_rows:
        memory_v3.add_relation(
            subject=row['subject'],
            predicate=row['predicate'],
            object=row['object'],
            context=row['context'],
            strength=row['strength'] or 1.0
        )
    stats['relations'] = len(relations_rows)
    print(f"  ✅ 已迁移 {len(relations_rows)} 条")
    
    # 3. 迁移 habits
    print("[3/5] 迁移 habits...")
    source_cursor.execute('''
        SELECT domain, pattern, evidence, certainty, created_at, last_observed_at
        FROM habits ORDER BY id
    ''')
    habits_rows = source_cursor.fetchall()
    for row in habits_rows:
        memory_v3.add_habit(
            domain=row['domain'],
            pattern=row['pattern'],
            evidence=row['evidence'],
            certainty=row['certainty'] or 0.5
        )
    stats['habits'] = len(habits_rows)
    print(f"  ✅ 已迁移 {len(habits_rows)} 条")
    
    # 4. 迁移 timeline
    print("[4/5] 迁移 timeline...")
    source_cursor.execute('''
        SELECT event_date, event_type, title, description, tags, related_facts, session_key
        FROM timeline ORDER BY id
    ''')
    timeline_rows = source_cursor.fetchall()
    for row in timeline_rows:
        memory_v3.add_timeline_event(
            event_date=row['event_date'],
            title=row['title'],
            event_type=row['event_type'],
            description=row['description'],
            tags=json.loads(row['tags']) if row['tags'] else None
        )
    stats['timeline'] = len(timeline_rows)
    print(f"  ✅ 已迁移 {len(timeline_rows)} 条")
    
    # 5. 迁移 conversation_logs
    print("[5/5] 迁移 conversation_logs...")
    source_cursor.execute('''
        SELECT session_id, turn_number, role, content, persona, created_at, metadata
        FROM conversation_logs ORDER BY id
    ''')
    conv_rows = source_cursor.fetchall()
    for row in conv_rows:
        memory_v3.log_conversation(
            session_id=row['session_id'],
            role=row['role'],
            content=row['content'],
            persona=row['persona'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None,
            turn_number=row['turn_number']
        )
    stats['conversation_logs'] = len(conv_rows)
    print(f"  ✅ 已迁移 {len(conv_rows)} 条")
    
    source_conn.close()
    
    # 打印统计
    print("\n" + "=" * 60)
    print("迁移完成！")
    print("=" * 60)
    total = 0
    for table, count in stats.items():
        print(f"  ✅ {table}: {count} 条")
        total += count
    print(f"\n总计: {total} 条记录")
    
    # 验证
    print("\n验证迁移结果...")
    print("-" * 40)
    verify_migration(source_db, target_db, stats)


def verify_migration(source_db: str, target_db: str, expected: dict):
    """验证迁移结果"""
    source_conn = sqlite3.connect(source_db)
    target_conn = sqlite3.connect(target_db)
    
    tables = ['facts', 'relations', 'habits', 'timeline', 'conversation_logs']
    
    all_match = True
    for table in tables:
        source_count = source_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        target_count = target_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        expected_count = expected.get(table, 0)
        
        match = "✅" if target_count == expected_count else "❌"
        if target_count != expected_count:
            all_match = False
        
        print(f"  {table}: {source_count} → {target_count} (期望 {expected_count}) {match}")
    
    source_conn.close()
    target_conn.close()
    
    if all_match:
        print("\n🎉 迁移验证通过！")
    else:
        print("\n⚠️ 迁移验证失败，请检查数据")


if __name__ == "__main__":
    migrate()
