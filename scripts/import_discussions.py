#!/usr/bin/env python3
"""
导入所有 discussion 文件到 conversation_logs
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path.home() / ".omnia" / "memory_palace.db"
DISCUSSIONS_DIR = Path("/home/shan/.openclaw/workspace/.omnia/discussions")

def import_discussions():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    total_messages = 0
    imported_files = 0
    
    for filepath in sorted(DISCUSSIONS_DIR.glob("*.json")):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            session_id = data.get('session_id', filepath.stem)
            question = data.get('question', '')
            opinions = data.get('opinions', [])
            
            # 检查是否已导入
            cursor.execute(
                "SELECT COUNT(*) FROM conversation_logs WHERE session_id = ?",
                (session_id,)
            )
            if cursor.fetchone()[0] > 0:
                print(f"⏭️  跳过已导入: {session_id}")
                continue
            
            # 记录用户问题
            cursor.execute("""
                INSERT INTO conversation_logs 
                (session_id, turn_number, role, persona, content, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                1,
                "user",
                None,
                question,
                json.dumps({"source": "discussion_import", "file": str(filepath)})
            ))
            total_messages += 1
            
            # 记录每个观点
            for idx, opinion in enumerate(opinions, start=2):
                speaker = opinion.get('speaker', 'unknown')
                content = opinion.get('content', '')
                
                cursor.execute("""
                    INSERT INTO conversation_logs 
                    (session_id, turn_number, role, persona, content, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    idx,
                    "assistant",
                    speaker,
                    content,
                    json.dumps({"source": "discussion_import", "speaker": speaker})
                ))
                total_messages += 1
            
            imported_files += 1
            print(f"✅ 导入: {session_id} ({len(opinions) + 1} 条消息)")
            
        except Exception as e:
            print(f"❌ 错误 {filepath}: {e}")
    
    conn.commit()
    
    # 统计
    cursor.execute("SELECT COUNT(*) FROM conversation_logs")
    final_count = cursor.fetchone()[0]
    
    print(f"\n{'='*50}")
    print(f"📊 导入完成!")
    print(f"   新导入文件: {imported_files}")
    print(f"   新增消息: {total_messages}")
    print(f"   conversation_logs 总数: {final_count}")
    
    conn.close()

if __name__ == "__main__":
    import_discussions()
