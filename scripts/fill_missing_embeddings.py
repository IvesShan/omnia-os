"""补充缺失的向量嵌入"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from core.memory_palace.memory_palace import MemoryPalace
from core.config import MEMORY_PALACE_DB

def main():
    mp = MemoryPalace(db_path=str(MEMORY_PALACE_DB))
    mp.initialize()
    conn = mp._conn
    cursor = conn.cursor()
    
    # 获取 vector_service
    vs = mp.vector_service
    if vs is None:
        print("❌ vector_service 不可用")
        return
    
    tables = [
        ('facts', 'id, key, value', lambda row: f"{row[1]}: {row[2]}"),
        ('habits', 'id, pattern, domain, evidence', 
         lambda row: f"[{row[2]}] {row[1]}: {row[3]}" if row[3] else f"[{row[2]}] {row[1]}"),
    ]
    
    total_filled = 0
    
    for table, select_cols, text_fn in tables:
        cursor.execute(f'SELECT {select_cols} FROM "{table}" WHERE embedding IS NULL')
        rows = cursor.fetchall()
        
        if not rows:
            print(f'{table}: 无缺失嵌入 ✅')
            continue
        
        print(f'{table}: 补充 {len(rows)} 条缺失嵌入...')
        
        for row in rows:
            row_id = row[0]
            text = text_fn(row)
            try:
                embedding = vs.encode(text)
                if embedding is not None:
                    embedding_blob = embedding.tobytes()
                    cursor.execute(
                        f'UPDATE "{table}" SET embedding = ? WHERE id = ?',
                        (embedding_blob, row_id)
                    )
                    total_filled += 1
                else:
                    print(f'  ⚠️ ID {row_id}: 生成嵌入返回 None')
            except Exception as e:
                print(f'  ❌ ID {row_id}: {e}')
        
        conn.commit()
    
    conn.close()
    mp.close()
    
    print(f'\n✅ 完成！共补充 {total_filled} 条缺失嵌入')

if __name__ == '__main__':
    main()
