#!/usr/bin/env python3
"""合并分散的 MemoryPalace 数据库"""
import sqlite3
from pathlib import Path

# 数据库路径
DB1 = Path.home() / ".omnia" / "memory_palace.db"
DB2 = Path.home() / ".openclaw" / "workspace" / "omnia-os" / ".omnia" / "memory_palace.db"
TARGET = Path.home() / ".omnia" / "memory_palace.db"

def merge_databases():
    print(f"源数据库 1: {DB1}")
    print(f"源数据库 2: {DB2}")
    print(f"目标数据库: {TARGET}")
    print()
    
    # 确保目标数据库存在
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    
    # 连接目标数据库
    conn = sqlite3.connect(str(TARGET))
    cursor = conn.cursor()
    
    # 创建表结构（如果不存在）
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            strength REAL DEFAULT 1.0,
            embedding BLOB,
            UNIQUE(category, key)
        );
        
        CREATE TABLE IF NOT EXISTS relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object TEXT NOT NULL,
            context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            strength REAL DEFAULT 1.0
        );
        
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            pattern TEXT NOT NULL,
            evidence TEXT,
            certainty REAL DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_observed_at TIMESTAMP,
            embedding BLOB
        );
        
        CREATE TABLE IF NOT EXISTS timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            event TEXT NOT NULL,
            context TEXT,
            impact TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS conversation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    
    # 从 DB2 导入数据（它有更多业务数据）
    if DB2.exists():
        print(f"从 {DB2} 导入数据...")
        conn2 = sqlite3.connect(str(DB2))
        cursor2 = conn2.cursor()
        
        # 导入 facts
        try:
            rows = cursor2.execute("SELECT category, key, value, source, strength, embedding FROM facts").fetchall()
            for row in rows:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO facts (category, key, value, source, strength, embedding)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, row)
                except Exception as e:
                    print(f"  插入 fact 失败: {e}")
            print(f"  导入 {len(rows)} 条 facts")
        except Exception as e:
            print(f"  导入 facts 失败: {e}")
        
        # 导入 relations
        try:
            rows = cursor2.execute("SELECT subject, predicate, object, context, strength FROM relations").fetchall()
            for row in rows:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO relations (subject, predicate, object, context, strength)
                        VALUES (?, ?, ?, ?, ?)
                    """, row)
                except Exception as e:
                    print(f"  插入 relation 失败: {e}")
            print(f"  导入 {len(rows)} 条 relations")
        except Exception as e:
            print(f"  导入 relations 失败: {e}")
        
        # 导入 habits
        try:
            rows = cursor2.execute("SELECT domain, pattern, evidence, certainty FROM habits").fetchall()
            for row in rows:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO habits (domain, pattern, evidence, certainty)
                        VALUES (?, ?, ?, ?)
                    """, row)
                except Exception as e:
                    print(f"  插入 habit 失败: {e}")
            print(f"  导入 {len(rows)} 条 habits")
        except Exception as e:
            print(f"  导入 habits 失败: {e}")
        
        # 导入 conversation_logs
        try:
            rows = cursor2.execute("SELECT session_id, role, content, timestamp FROM conversation_logs").fetchall()
            for row in rows:
                try:
                    cursor.execute("""
                        INSERT INTO conversation_logs (session_id, role, content, timestamp)
                        VALUES (?, ?, ?, ?)
                    """, row)
                except Exception as e:
                    print(f"  插入 conversation_log 失败: {e}")
            print(f"  导入 {len(rows)} 条 conversation_logs")
        except Exception as e:
            print(f"  导入 conversation_logs 失败: {e}")
        
        conn2.close()
    
    conn.commit()
    
    # 显示最终统计
    print("\n=== 最终数据库统计 ===")
    for table in ['facts', 'relations', 'habits', 'timeline', 'conversation_logs']:
        count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count} 条")
    
    conn.close()
    print("\n✅ 合并完成！")

if __name__ == "__main__":
    merge_databases()
