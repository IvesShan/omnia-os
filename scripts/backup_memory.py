#!/usr/bin/env python3
"""Omnia 记忆备份脚本

功能：
1. 自动备份 memory_palace.db
2. 保留最近 7 天的备份
3. 压缩旧备份
"""

import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import MEMORY_PALACE_DB, OMNIA_HOME


def create_backup(db_path: Path, backup_dir: Path) -> Path:
    """创建数据库备份"""
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成备份文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"backup_{timestamp}.db"
    
    # 复制数据库
    shutil.copy2(db_path, backup_file)
    
    return backup_file


def compress_old_backups(backup_dir: Path, days: int = 7):
    """压缩旧备份（超过指定天数）"""
    cutoff = datetime.now() - timedelta(days=days)
    
    for backup in backup_dir.glob("backup_*.db"):
        # 检查文件时间
        file_time = datetime.fromtimestamp(backup.stat().st_mtime)
        
        if file_time < cutoff:
            # 压缩文件
            compressed = backup.with_suffix(".db.gz")
            with open(backup, 'rb') as f_in:
                with gzip.open(compressed, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # 删除原文件
            backup.unlink()
            print(f"   🗜️  压缩: {backup.name} -> {compressed.name}")


def clean_old_backups(backup_dir: Path, keep_days: int = 30):
    """清理过期备份（超过指定天数）"""
    cutoff = datetime.now() - timedelta(days=keep_days)
    
    for backup in backup_dir.glob("backup_*.db.gz"):
        file_time = datetime.fromtimestamp(backup.stat().st_mtime)
        
        if file_time < cutoff:
            backup.unlink()
            print(f"   🗑️  删除: {backup.name}")


def get_backup_stats(backup_dir: Path) -> dict:
    """获取备份统计"""
    backups = list(backup_dir.glob("backup_*.db*"))
    
    total_size = sum(b.stat().st_size for b in backups)
    
    return {
        "count": len(backups),
        "total_size_mb": round(total_size / (1024**2), 2),
        "latest": max(backups, key=lambda p: p.stat().st_mtime).name if backups else None
    }


def main():
    print("=" * 60)
    print("Omnia 记忆备份")
    print("=" * 60)
    print()
    
    backup_dir = OMNIA_HOME / "backups"
    
    # 1. 创建备份
    print("1️⃣ 创建备份")
    try:
        backup_file = create_backup(MEMORY_PALACE_DB, backup_dir)
        size_mb = round(backup_file.stat().st_size / (1024**2), 2)
        print(f"   ✅ 备份成功: {backup_file.name} ({size_mb} MB)")
    except Exception as e:
        print(f"   ❌ 备份失败: {e}")
        return
    print()
    
    # 2. 压缩旧备份
    print("2️⃣ 压缩旧备份（>7 天）")
    compress_old_backups(backup_dir, days=7)
    print()
    
    # 3. 清理过期备份
    print("3️⃣ 清理过期备份（>30 天）")
    clean_old_backups(backup_dir, keep_days=30)
    print()
    
    # 4. 统计
    print("4️⃣ 备份统计")
    stats = get_backup_stats(backup_dir)
    print(f"   备份数量: {stats['count']}")
    print(f"   总大小: {stats['total_size_mb']} MB")
    print(f"   最新备份: {stats['latest']}")
    print()
    
    print("=" * 60)
    print("✅ 备份完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
