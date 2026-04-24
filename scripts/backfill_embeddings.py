#!/usr/bin/env python3
"""Backfill missing embeddings for timeline and facts."""

import sys
import sqlite3
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.vector_ipc import get_hybrid_vector_service


def backfill_embeddings(db_path: str = None, batch_size: int = 50):
    """Backfill missing embeddings for timeline and facts."""
    if db_path is None:
        db_path = Path.home() / ".omnia" / "memory_palace.db"
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    vector_service = get_hybrid_vector_service()
    
    print("=" * 60)
    print("🔄 Embedding 补全工具")
    print("=" * 60)
    
    # === Timeline ===
    print("\n📋 检查 Timeline...")
    cursor = conn.execute("""
        SELECT id, title, description 
        FROM timeline 
        WHERE embedding IS NULL OR embedding = ''
    """)
    missing = cursor.fetchall()
    
    if missing:
        print(f"   缺失 embedding: {len(missing)} 条")
        
        updated = 0
        for i in range(0, len(missing), batch_size):
            batch = missing[i:i+batch_size]
            for row in batch:
                try:
                    # 使用 description 或 title 生成 embedding
                    text = row['description'] or row['title']
                    if text:
                        embedding = vector_service.encode(text)
                        embedding_blob = embedding.tobytes()
                        
                        conn.execute(
                            "UPDATE timeline SET embedding = ? WHERE id = ?",
                            (embedding_blob, row['id'])
                        )
                        updated += 1
                except Exception as e:
                    print(f"   ⚠️  失败 #{row['id']}: {e}")
            
            conn.commit()
            print(f"   进度: {min(i+batch_size, len(missing))}/{len(missing)}")
        
        print(f"   ✅ Timeline 补全完成: {updated} 条")
    else:
        print("   ✅ Timeline 全部有 embedding")
    
    # === Facts ===
    print("\n📊 检查 Facts...")
    cursor = conn.execute("""
        SELECT rowid, value 
        FROM facts 
        WHERE embedding IS NULL OR embedding = ''
    """)
    missing = cursor.fetchall()
    
    if missing:
        print(f"   缺失 embedding: {len(missing)} 条")
        
        updated = 0
        for row in missing:
            try:
                text = row['value']
                if text:
                    embedding = vector_service.encode(text)
                    embedding_blob = embedding.tobytes()
                    
                    conn.execute(
                        "UPDATE facts SET embedding = ? WHERE rowid = ?",
                        (embedding_blob, row['rowid'])
                    )
                    updated += 1
            except Exception as e:
                print(f"   ⚠️  失败 #{row['rowid']}: {e}")
        
        conn.commit()
        print(f"   ✅ Facts 补全完成: {updated} 条")
    else:
        print("   ✅ Facts 全部有 embedding")
    
    # === 验证 ===
    print("\n📈 最终统计:")
    
    cursor = conn.execute("SELECT COUNT(*) FROM timeline")
    total = cursor.fetchone()[0]
    cursor = conn.execute("SELECT COUNT(*) FROM timeline WHERE embedding IS NOT NULL AND embedding != ''")
    with_emb = cursor.fetchone()[0]
    print(f"   Timeline: {with_emb}/{total} ({with_emb/total*100:.1f}%)")
    
    cursor = conn.execute("SELECT COUNT(*) FROM facts")
    total = cursor.fetchone()[0]
    cursor = conn.execute("SELECT COUNT(*) FROM facts WHERE embedding IS NOT NULL AND embedding != ''")
    with_emb = cursor.fetchone()[0]
    print(f"   Facts: {with_emb}/{total} ({with_emb/total*100:.1f}%)")
    
    conn.close()
    print("\n" + "=" * 60)
    print("✅ 补全完成!")
    print("=" * 60)


if __name__ == "__main__":
    backfill_embeddings()
