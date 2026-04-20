#!/usr/bin/env python3
"""迁移脚本：为现有 Memory Palace 数据添加向量"""

import sqlite3
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.shared_vector_service import get_vector_service


def migrate(db_path: str = "~/.omnia/memory_palace.db"):
    """为现有数据添加 embedding 列并生成向量"""
    db_path = Path(db_path).expanduser()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    vector_service = get_vector_service()
    
    print(f"📦 迁移数据库: {db_path}")
    
    # 1. 检查并添加 embedding 列
    for table in ['facts', 'relations', 'habits']:
        cursor = conn.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'embedding' not in columns:
            print(f"  ➕ 为 {table} 添加 embedding 列...")
            conn.execute(f"ALTER TABLE {table} ADD COLUMN embedding BLOB")
            conn.commit()
        else:
            print(f"  ✓ {table} 已有 embedding 列")
    
    # 2. 为 facts 生成向量
    print("\n📊 为 facts 生成向量...")
    rows = conn.execute("SELECT id, value FROM facts WHERE embedding IS NULL").fetchall()
    print(f"  找到 {len(rows)} 条需要生成向量的记录")
    
    for i, row in enumerate(rows):
        if i % 10 == 0:
            print(f"  处理 {i+1}/{len(rows)}...")
        embedding = vector_service.encode(row['value'])
        conn.execute("UPDATE facts SET embedding = ? WHERE id = ?", 
                     (embedding.tobytes(), row['id']))
    
    conn.commit()
    print(f"  ✓ facts 向量生成完成")
    
    # 3. 为 relations 生成向量
    print("\n📊 为 relations 生成向量...")
    rows = conn.execute("SELECT id, subject, predicate, object, context FROM relations WHERE embedding IS NULL").fetchall()
    print(f"  找到 {len(rows)} 条需要生成向量的记录")
    
    for i, row in enumerate(rows):
        if i % 10 == 0:
            print(f"  处理 {i+1}/{len(rows)}...")
        text = f"{row['subject']} {row['predicate']} {row['object']}"
        if row['context']:
            text += f" {row['context']}"
        embedding = vector_service.encode(text)
        conn.execute("UPDATE relations SET embedding = ? WHERE id = ?", 
                     (embedding.tobytes(), row['id']))
    
    conn.commit()
    print(f"  ✓ relations 向量生成完成")
    
    # 4. 为 habits 生成向量
    print("\n📊 为 habits 生成向量...")
    rows = conn.execute("SELECT id, pattern FROM habits WHERE embedding IS NULL").fetchall()
    print(f"  找到 {len(rows)} 条需要生成向量的记录")
    
    for i, row in enumerate(rows):
        if i % 10 == 0:
            print(f"  处理 {i+1}/{len(rows)}...")
        embedding = vector_service.encode(row['pattern'])
        conn.execute("UPDATE habits SET embedding = ? WHERE id = ?", 
                     (embedding.tobytes(), row['id']))
    
    conn.commit()
    print(f"  ✓ habits 向量生成完成")
    
    # 5. 统计结果
    print("\n📈 最终统计:")
    for table in ['facts', 'relations', 'habits']:
        total = conn.execute(f"SELECT COUNT(*) as cnt FROM {table}").fetchone()['cnt']
        with_vec = conn.execute(f"SELECT COUNT(*) as cnt FROM {table} WHERE embedding IS NOT NULL").fetchone()['cnt']
        print(f"  {table}: {total} 条记录, {with_vec} 条有向量 ({with_vec/total*100 if total > 0 else 0:.1f}%)")
    
    conn.close()
    print("\n✅ 迁移完成！")


if __name__ == "__main__":
    migrate()
