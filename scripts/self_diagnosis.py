#!/usr/bin/env python3
"""
Omnia 自检脚本
快速诊断系统状态，避免随机探索

使用方法:
    python3 scripts/self_diagnosis.py          # 完整报告
    python3 scripts/self_diagnosis.py --quick  # 快速检查
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 数据库路径
DB_PATH = Path.home() / ".omnia" / "memory_palace.db"

def get_db_connection():
    """获取数据库连接"""
    import sqlite3
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def check_api():
    """检查 API 状态"""
    try:
        import requests
        response = requests.get("http://localhost:5001/api/status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            return {
                "status": "online",
                "model": data.get("model", "unknown"),
                "python_version": data.get("python_version", "unknown"),
                "skills_count": data.get("skills_count", 0),
                "cpu_percent": data.get("cpu_percent", 0),
                "memory_percent": data.get("memory_percent", 0),
            }
    except Exception as e:
        return {"status": "offline", "error": str(e)}
    return {"status": "unknown"}

def check_database():
    """检查数据库状态"""
    conn = get_db_connection()
    if not conn:
        return {"status": "not_found", "path": str(DB_PATH)}
    
    cursor = conn.cursor()
    
    # 获取数据库大小
    db_size = DB_PATH.stat().st_size / (1024 * 1024)  # MB
    
    # 获取各表的数量
    tables = {}
    for table in ["facts", "relations", "habits", "timeline", "neural_nodes", "neural_edges"]:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            tables[table] = cursor.fetchone()[0]
        except:
            tables[table] = 0
    
    conn.close()
    
    return {
        "status": "ok",
        "path": str(DB_PATH),
        "size_mb": round(db_size, 2),
        **tables
    }

def check_daemon():
    """检查守护进程状态"""
    try:
        result = os.popen("pgrep -f 'start_daemon.py'").read()
        if result.strip():
            return {"status": "running", "pid": result.strip()}
    except:
        pass
    return {"status": "stopped"}

def check_webui():
    """检查 WebUI 状态"""
    try:
        import requests
        response = requests.get("http://localhost:5001/", timeout=2)
        return {"status": "online", "port": 5001}
    except:
        return {"status": "offline"}

def check_memory_health():
    """检查记忆健康度"""
    conn = get_db_connection()
    if not conn:
        return {"status": "no_database"}
    
    cursor = conn.cursor()
    
    # 检查重复记忆
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT title FROM timeline
            GROUP BY title
            HAVING COUNT(*) > 1
        )
    """)
    duplicate_titles = cursor.fetchone()[0]
    
    # 检查异常数据
    cursor.execute("""
        SELECT COUNT(*) FROM timeline
        WHERE title LIKE '%Sender (untrusted metadata)%'
           OR title LIKE '%```json%'
           OR title LIKE '%```%'
    """)
    anomalies = cursor.fetchone()[0]
    
    # 检查 embedding 覆盖率
    cursor.execute("SELECT COUNT(*) FROM timeline WHERE embedding IS NOT NULL")
    with_embedding = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM timeline")
    total = cursor.fetchone()[0]
    
    embedding_coverage = (with_embedding / total * 100) if total > 0 else 0
    
    # 检查 facts 平均强度
    cursor.execute("SELECT AVG(strength) FROM facts")
    avg_strength = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return {
        "status": "healthy" if duplicate_titles == 0 and anomalies == 0 else "issues_found",
        "duplicate_titles": duplicate_titles,
        "anomalies": anomalies,
        "embedding_coverage": round(embedding_coverage, 1),
        "facts_avg_strength": round(avg_strength, 2),
    }

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="快速检查（只返回 JSON）")
    parser.add_argument("--full", action="store_true", help="完整报告")
    args = parser.parse_args()
    
    if args.quick:
        # 快速检查 - 只返回关键状态
        result = {
            "api": check_api()["status"] == "online",
            "database": check_database()["status"] == "ok",
            "daemon": check_daemon()["status"] == "running",
            "memory_count": check_database().get("timeline", 0),
        }
        print(json.dumps(result, indent=2))
        return
    
    # 完整报告
    print("="*60)
    print("🏥 Omnia 自检报告")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # API 状态
    print("\n📡 API 状态:")
    api = check_api()
    if api["status"] == "online":
        print(f"   ✅ 在线")
        print(f"   模型: {api.get('model', 'unknown')}")
        print(f"   Python: {api.get('python_version', 'unknown')}")
        print(f"   技能数: {api.get('skills_count', 0)}")
        print(f"   CPU: {api.get('cpu_percent', 0)}%, 内存: {api.get('memory_percent', 0)}%")
    else:
        print(f"   ❌ 离线: {api.get('error', 'unknown')}")
    
    # 数据库状态
    print("\n💾 数据库状态:")
    db = check_database()
    if db["status"] == "ok":
        print(f"   ✅ 正常")
        print(f"   路径: {db['path']}")
        print(f"   大小: {db['size_mb']} MB")
        print(f"   Facts: {db.get('facts', 0)}")
        print(f"   Relations: {db.get('relations', 0)}")
        print(f"   Habits: {db.get('habits', 0)}")
        print(f"   Timeline: {db.get('timeline', 0)}")
        print(f"   Neural Nodes: {db.get('neural_nodes', 0)}")
        print(f"   Neural Edges: {db.get('neural_edges', 0)}")
    else:
        print(f"   ❌ {db['status']}: {db.get('path', 'unknown')}")
    
    # 守护进程
    print("\n🔄 守护进程:")
    daemon = check_daemon()
    if daemon["status"] == "running":
        print(f"   ✅ 运行中 (PID: {daemon['pid']})")
    else:
        print(f"   ⚠️  未运行")
    
    # WebUI
    print("\n🌐 WebUI:")
    webui = check_webui()
    if webui["status"] == "online":
        print(f"   ✅ 在线 (端口 {webui['port']})")
    else:
        print(f"   ⚠️  离线")
    
    # 记忆健康度
    print("\n🧠 记忆健康度:")
    health = check_memory_health()
    if health["status"] == "healthy":
        print(f"   ✅ 健康")
    else:
        print(f"   ⚠️  发现问题")
    
    print(f"   重复标题: {health['duplicate_titles']}")
    print(f"   异常数据: {health['anomalies']}")
    print(f"   Embedding 覆盖率: {health['embedding_coverage']}%")
    print(f"   Facts 平均强度: {health['facts_avg_strength']}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
