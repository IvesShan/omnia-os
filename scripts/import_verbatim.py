#!/usr/bin/env python3
"""
导入 verbatim_db 的消息到 conversation_logs
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path.home() / ".omnia" / "memory_palace.db"
VERBATIM_DIR = Path("/home/shan/.openclaw/workspace/verbatim_db/embeddings")

def import_verbatim():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    total = 0
    skipped = 0
    
    for json_file in sorted(VERBATIM_DIR.glob("*.json")):
        if json_file.suffix == ".lock":
            continue
            
        print(f"处理 {json_file.name}...")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        messages = data.get('messages', [])
        
        for msg in messages:
            msg_id = msg.get('id', '')
            msg_type = msg.get('type', 'user')
            session_id = msg.get('session_id', 'unknown')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            
            # 检查是否已导入（用 metadata 存储 verbatim_id）
            cursor.execute(
                "SELECT COUNT(*) FROM conversation_logs WHERE metadata LIKE ?",
                (f'%{msg_id}%',)
            )
            if cursor.fetchone()[0] > 0:
                skipped += 1
                continue
            
            # 插入消息
            cursor.execute("""
                INSERT INTO conversation_logs 
                (session_id, turn_number, role, content, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session_id,
                1,  # 默认 turn_number
                msg_type,
                content,
                json.dumps({
                    "source": "verbatim_import",
                    "verbatim_id": msg_id,
                    "original_timestamp": timestamp
                })
            ))
            total += 1
        
        print(f"  导入 {len(messages)} 条消息，累计 {total} 条")
    
    conn.commit()
    
    # 统计
    cursor.execute("SELECT COUNT(*) FROM conversation_logs")
    final_count = cursor.fetchone()[0]
    
    print(f"\n{'='*50}")
    print(f"📊 导入完成!")
    print(f"   新导入: {total}")
    print(f"   跳过: {skipped}")
    print(f"   conversation_logs 总数: {final_count}")
    
    conn.close()

if __name__ == "__main__":
    import_verbatim()
