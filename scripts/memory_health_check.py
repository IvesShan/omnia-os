#!/usr/bin/env python3
"""Omnia 记忆健康检查脚本

检查项：
1. 数据库完整性
2. 记忆增长率
3. 向量服务状态
4. 磁盘空间
"""

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import MEMORY_PALACE_DB, OMNIA_HOME


def check_database_integrity(db_path: Path) -> bool:
    """检查数据库完整性"""
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 运行完整性检查
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        
        conn.close()
        return result == "ok"
    except Exception as e:
        print(f"❌ 数据库完整性检查失败: {e}")
        return False


def check_memory_growth(db_path: Path) -> dict:
    """检查记忆增长率"""
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 获取各表的记录数
        stats = {}
        for table in ['facts', 'relations', 'habits', 'timeline', 'conversation_logs']:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        
        conn.close()
        return stats
    except Exception as e:
        print(f"❌ 记忆统计失败: {e}")
        return {}


def check_disk_space(omnia_home: Path) -> dict:
    """检查磁盘空间"""
    try:
        import shutil
        total, used, free = shutil.disk_usage(omnia_home.parent)
        return {
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "usage_percent": round(used / total * 100, 1)
        }
    except Exception as e:
        print(f"❌ 磁盘空间检查失败: {e}")
        return {}


def check_vector_service():
    """检查向量服务"""
    try:
        from core.shared_vector_service import get_vector_service
        vs = get_vector_service()
        
        # 测试编码
        test_text = "测试向量服务"
        embedding = vs.encode(test_text)
        
        return {
            "status": "ok",
            "embedding_dim": len(embedding)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def check_backup(omnia_home: Path) -> dict:
    """检查备份状态"""
    backup_dir = omnia_home / "backups"
    if not backup_dir.exists():
        return {
            "status": "no_backup",
            "latest": None
        }
    
    # 查找最新的备份
    backups = list(backup_dir.glob("backup_*.db"))
    if not backups:
        return {
            "status": "no_backup",
            "latest": None
        }
    
    latest = max(backups, key=lambda p: p.stat().st_mtime)
    age_hours = (datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)).total_seconds() / 3600
    
    return {
        "status": "ok" if age_hours < 48 else "stale",
        "latest": str(latest.name),
        "age_hours": round(age_hours, 1)
    }


def main():
    print("=" * 60)
    print("Omnia 记忆健康检查")
    print("=" * 60)
    print()
    
    # 1. 数据库完整性
    print("1️⃣ 数据库完整性")
    if check_database_integrity(MEMORY_PALACE_DB):
        print("   ✅ 数据库完整")
    else:
        print("   ❌ 数据库损坏！")
    print()
    
    # 2. 记忆统计
    print("2️⃣ 记忆统计")
    stats = check_memory_growth(MEMORY_PALACE_DB)
    if stats:
        for table, count in stats.items():
            print(f"   {table}: {count:,} 条")
    print()
    
    # 3. 磁盘空间
    print("3️⃣ 磁盘空间")
    disk = check_disk_space(OMNIA_HOME)
    if disk:
        print(f"   总计: {disk['total_gb']} GB")
        print(f"   已用: {disk['used_gb']} GB ({disk['usage_percent']}%)")
        print(f"   可用: {disk['free_gb']} GB")
        
        if disk['usage_percent'] > 90:
            print("   ⚠️  磁盘空间不足！")
        else:
            print("   ✅ 磁盘空间充足")
    print()
    
    # 4. 向量服务
    print("4️⃣ 向量服务")
    vector = check_vector_service()
    if vector['status'] == 'ok':
        print(f"   ✅ 向量服务正常 (维度: {vector['embedding_dim']})")
    else:
        print(f"   ❌ 向量服务异常: {vector.get('error')}")
    print()
    
    # 5. 备份状态
    print("5️⃣ 备份状态")
    backup = check_backup(OMNIA_HOME)
    if backup['status'] == 'ok':
        print(f"   ✅ 最新备份: {backup['latest']} ({backup['age_hours']} 小时前)")
    elif backup['status'] == 'stale':
        print(f"   ⚠️  备份过期: {backup['latest']} ({backup['age_hours']} 小时前)")
    else:
        print("   ⚠️  未找到备份")
    print()
    
    print("=" * 60)
    print("✅ 健康检查完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
