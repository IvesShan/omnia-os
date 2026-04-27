#!/usr/bin/env python3
"""
Omnia 日志轮转工具

功能：
1. 轮转日志文件（重命名为 .old，压缩旧日志）
2. 清理过期日志
3. 限制日志大小

用法：
    python log_rotator.py              # 轮转所有日志
    python log_rotator.py --clean      # 清理过期日志
    python log_rotator.py --status     # 查看日志状态
"""

import argparse
import gzip
import json
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

try:
    from core.config import OMNIA_HOME
except ImportError:
    # 回退到默认路径
    OMNIA_HOME = Path.home() / ".omnia"

# 日志配置
LOG_FILES = [
    "daemon.log",
    "watchdog.log",
    "web_server.log",
    "memory_enhance.log",
]

# 轮转配置
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_LOG_AGE_DAYS = 30  # 保留 30 天
MAX_BACKUP_COUNT = 5  # 最多保留 5 个备份


def get_log_path(log_name: str) -> Path:
    """获取日志文件路径"""
    return OMNIA_HOME / log_name


def get_log_size(log_path: Path) -> int:
    """获取日志文件大小"""
    if log_path.exists():
        return log_path.stat().st_size
    return 0


def format_size(size: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def rotate_log(log_name: str, force: bool = False) -> bool:
    """
    轮转单个日志文件
    
    Args:
        log_name: 日志文件名
        force: 是否强制轮转（忽略大小限制）
    
    Returns:
        是否执行了轮转
    """
    log_path = get_log_path(log_name)
    
    if not log_path.exists():
        return False
    
    log_size = get_log_size(log_path)
    
    # 检查是否需要轮转
    if not force and log_size < MAX_LOG_SIZE:
        return False
    
    print(f"🔄 轮转 {log_name} ({format_size(log_size)})...")
    
    # 轮转现有备份
    for i in range(MAX_BACKUP_COUNT - 1, 0, -1):
        old_backup = log_path.with_suffix(f".log.{i}.gz")
        new_backup = log_path.with_suffix(f".log.{i + 1}.gz")
        if old_backup.exists():
            if new_backup.exists():
                new_backup.unlink()
            old_backup.rename(new_backup)
    
    # 压缩当前日志
    backup_path = log_path.with_suffix(".log.1.gz")
    try:
        with open(log_path, "rb") as f_in:
            with gzip.open(backup_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # 清空原日志文件（而不是删除，保持文件句柄有效）
        log_path.write_text("")
        
        print(f"   ✅ 已压缩到 {backup_path.name}")
        return True
    except Exception as e:
        print(f"   ❌ 轮转失败: {e}")
        return False


def clean_old_logs(log_name: str) -> int:
    """
    清理过期的日志备份
    
    Returns:
        清理的文件数量
    """
    log_path = get_log_path(log_name)
    cleaned = 0
    
    # 清理 .old 文件
    old_file = log_path.with_suffix(".log.old")
    if old_file.exists():
        old_mtime = datetime.fromtimestamp(old_file.stat().st_mtime)
        if datetime.now() - old_mtime > timedelta(days=MAX_LOG_AGE_DAYS):
            old_file.unlink()
            print(f"   🗑️ 已删除过期日志: {old_file.name}")
            cleaned += 1
    
    # 清理过期的 .gz 备份
    for i in range(1, MAX_BACKUP_COUNT + 10):  # 多扫描几个，以防有残留
        backup = log_path.with_suffix(f".log.{i}.gz")
        if backup.exists():
            backup_mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            if datetime.now() - backup_mtime > timedelta(days=MAX_LOG_AGE_DAYS):
                backup.unlink()
                print(f"   🗑️ 已删除过期备份: {backup.name}")
                cleaned += 1
    
    return cleaned


def show_status():
    """显示日志状态"""
    print(f"📁 日志目录: {OMNIA_HOME}")
    print(f"⚙️  配置: 最大 {format_size(MAX_LOG_SIZE)}, 保留 {MAX_LOG_AGE_DAYS} 天")
    print()
    
    total_size = 0
    print(f"{'日志文件':<20} {'大小':>10} {'状态':>10}")
    print("-" * 45)
    
    for log_name in LOG_FILES:
        log_path = get_log_path(log_name)
        size = get_log_size(log_path)
        total_size += size
        
        status = "✅ 正常"
        if size > MAX_LOG_SIZE:
            status = "⚠️ 需轮转"
        elif not log_path.exists():
            status = "— 不存在"
        
        print(f"{log_name:<20} {format_size(size):>10} {status:>10}")
    
    # 统计备份文件
    backup_size = 0
    backup_count = 0
    for gz_file in OMNIA_HOME.glob("*.gz"):
        backup_size += gz_file.stat().st_size
        backup_count += 1
    
    for old_file in OMNIA_HOME.glob("*.old"):
        backup_size += old_file.stat().st_size
        backup_count += 1
    
    print("-" * 45)
    print(f"{'日志总计':<20} {format_size(total_size):>10}")
    print(f"{'备份文件 (' + str(backup_count) + ' 个)':<20} {format_size(backup_size):>10}")
    print(f"{'总计':<20} {format_size(total_size + backup_size):>10}")


def rotate_all(force: bool = False):
    """轮转所有日志"""
    print(f"🔄 开始轮转日志...")
    rotated = 0
    
    for log_name in LOG_FILES:
        if rotate_log(log_name, force):
            rotated += 1
    
    if rotated == 0:
        print("✅ 所有日志都在大小限制内，无需轮转")
    else:
        print(f"✅ 已轮转 {rotated} 个日志文件")


def clean_all():
    """清理所有过期日志"""
    print(f"🧹 开始清理过期日志...")
    cleaned = 0
    
    for log_name in LOG_FILES:
        cleaned += clean_old_logs(log_name)
    
    if cleaned == 0:
        print("✅ 没有过期日志需要清理")
    else:
        print(f"✅ 已清理 {cleaned} 个过期日志文件")


def main():
    parser = argparse.ArgumentParser(description="Omnia 日志轮转工具")
    parser.add_argument("--clean", action="store_true", help="清理过期日志")
    parser.add_argument("--status", action="store_true", help="查看日志状态")
    parser.add_argument("--force", action="store_true", help="强制轮转（忽略大小限制）")
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
    elif args.clean:
        clean_all()
    else:
        rotate_all(force=args.force)


if __name__ == "__main__":
    main()
