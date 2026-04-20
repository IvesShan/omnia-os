#!/usr/bin/env python3
"""为 Memory Palace 现有数据生成向量嵌入

Usage:
    python scripts/regenerate_embeddings.py [--dry-run]
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import sqlite3
from core.shared_vector_service import get_vector_service


def regenerate_embeddings(db_path: str = "~/.omnia/memory_palace.db", dry_run: bool = False):
    """为所有缺失向量的记录生成嵌入"""
    vector_service = get_vector_service()
    conn = sqlite3.connect(Path(db_path).expanduser())
    conn.row_factory = sqlite3.Row
    
    stats = {
        "facts": {"total": 0, "updated": 0},
        "relations": {"total": 0, "updated": 0},
        "habits": {"total": 0, "updated": 0},
        "timeline": {"total": 0, "updated": 0},
    }
    
    # 1. Facts
    print("\n📋 Processing facts...")
    rows = conn.execute("SELECT id, category, key, value FROM facts WHERE embedding IS NULL").fetchall()
    stats["facts"]["total"] = len(rows)
    
    for row in rows:
        text = f"{row['category']}: {row['key']} = {row['value']}"
        embedding = vector_service.encode(text)
        
        if not dry_run:
            conn.execute(
                "UPDATE facts SET embedding = ? WHERE id = ?",
                (embedding.tobytes(), row['id'])
            )
        stats["facts"]["updated"] += 1
        print(f"  ✓ {text[:50]}...")
    
    # 2. Relations
    print("\n🔗 Processing relations...")
    rows = conn.execute("SELECT id, subject, predicate, object, context FROM relations WHERE embedding IS NULL").fetchall()
    stats["relations"]["total"] = len(rows)
    
    for row in rows:
        text = f"{row['subject']} {row['predicate']} {row['object']}"
        if row['context']:
            text += f" ({row['context']})"
        embedding = vector_service.encode(text)
        
        if not dry_run:
            conn.execute(
                "UPDATE relations SET embedding = ? WHERE id = ?",
                (embedding.tobytes(), row['id'])
            )
        stats["relations"]["updated"] += 1
        print(f"  ✓ {text[:50]}...")
    
    # 3. Habits
    print("\n🔄 Processing habits...")
    rows = conn.execute("SELECT id, domain, pattern FROM habits WHERE embedding IS NULL").fetchall()
    stats["habits"]["total"] = len(rows)
    
    for row in rows:
        text = f"{row['domain']}: {row['pattern']}"
        embedding = vector_service.encode(text)
        
        if not dry_run:
            conn.execute(
                "UPDATE habits SET embedding = ? WHERE id = ?",
                (embedding.tobytes(), row['id'])
            )
        stats["habits"]["updated"] += 1
        print(f"  ✓ {text[:50]}...")
    
    # 4. Timeline
    print("\n📅 Processing timeline...")
    rows = conn.execute("SELECT id, title, description FROM timeline WHERE embedding IS NULL").fetchall()
    stats["timeline"]["total"] = len(rows)
    
    for row in rows:
        text = row['description'] or row['title']
        embedding = vector_service.encode(text)
        
        if not dry_run:
            conn.execute(
                "UPDATE timeline SET embedding = ? WHERE id = ?",
                (embedding.tobytes(), row['id'])
            )
        stats["timeline"]["updated"] += 1
        print(f"  ✓ {text[:50]}...")
    
    if not dry_run:
        conn.commit()
    
    conn.close()
    
    # Summary
    print("\n" + "="*50)
    print("📊 Summary:")
    print("="*50)
    for table, data in stats.items():
        print(f"  {table}: {data['updated']}/{data['total']} updated")
    
    if dry_run:
        print("\n⚠️  DRY RUN - No changes were made")
    else:
        print("\n✅ All embeddings regenerated!")
    
    return stats


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    regenerate_embeddings(dry_run=dry_run)
