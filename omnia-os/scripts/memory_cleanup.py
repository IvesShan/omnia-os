#!/usr/bin/env python3
"""
Memory Cleanup Script - 定期清理脚本
扫描记忆中的路径，验证有效性，标记或更新失效条目

注意：
- timeline 表存储历史对话，路径是记录的一部分，不应修改
- 只修复 facts 表中的配置路径

Usage:
    python3 memory_cleanup.py [--dry-run] [--fix-paths]
"""

import sqlite3
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional

DB_PATH = Path.home() / ".omnia" / "memory_palace.db"


class MemoryCleaner:
    def __init__(self, db_path: Path = DB_PATH, dry_run: bool = True):
        self.db_path = db_path
        self.dry_run = dry_run
        self.conn = sqlite3.connect(str(db_path))
        self.cursor = self.conn.cursor()
        self.report = {
            "scanned": 0,
            "valid": 0,
            "invalid": 0,
            "fixed": 0,
            "deprecated": 0,
            "issues": []
        }
        
        # 路径迁移规则 (old_prefix -> new_prefix)
        self.path_migrations = [
            ("/home/shan/.openclaw/workspace/omnia-os", "/home/shan/omnia-os/omnia-os"),
            ("/home/shan/.openclaw/workspace", "/home/shan/omnia-os"),
            ("/home/shan/.omnia", "/home/shan/omnia-os/.omnia"),
        ]
    
    def extract_paths(self, text: str) -> List[str]:
        """从文本中提取所有有效路径"""
        if not text:
            return []
        
        # 匹配 /home/shan/ 开头的路径
        # 排除明显不是路径的情况（包含中文、特殊字符等）
        pattern = r'/home/shan/[a-zA-Z0-9_\-./]+'
        paths = re.findall(pattern, text)
        
        # 过滤掉太短的路径（可能是误匹配）
        valid_paths = [p for p in paths if len(p) > 15]
        
        return list(set(valid_paths))  # 去重
    
    def validate_path(self, path_str: str) -> Tuple[bool, Optional[str]]:
        """验证路径是否存在，返回 (是否有效, 建议的替代路径)"""
        path = Path(path_str)
        
        if path.exists():
            return True, None
        
        # 尝试找到替代路径
        alternative = self._find_alternative_path(path_str)
        return False, alternative
    
    def _find_alternative_path(self, old_path: str) -> Optional[str]:
        """尝试找到替代路径"""
        # 应用迁移规则
        for old_prefix, new_prefix in self.path_migrations:
            if old_path.startswith(old_prefix):
                new_path = old_path.replace(old_prefix, new_prefix, 1)
                if Path(new_path).exists():
                    return new_path
        
        return None
    
    def process_facts(self, fix_paths: bool = False):
        """处理 facts 表 - 这里的路径需要修复"""
        print(f"\n📊 Processing facts table...")
        
        self.cursor.execute("""
            SELECT id, key, value, category 
            FROM facts 
            WHERE value LIKE '%/home/shan/%'
        """)
        facts = self.cursor.fetchall()
        
        print(f"   Found {len(facts)} entries with paths")
        
        for fact_id, key, value, category in facts:
            self.report["scanned"] += 1
            paths = self.extract_paths(value)
            
            if not paths:
                self.report["valid"] += 1
                continue
            
            all_valid = True
            fixes = []
            
            for path in paths:
                is_valid, alternative = self.validate_path(path)
                if not is_valid:
                    all_valid = False
                    self.report["invalid"] += 1
                    
                    issue = {
                        "table": "facts",
                        "id": fact_id,
                        "key": key,
                        "invalid_path": path,
                        "alternative": alternative
                    }
                    self.report["issues"].append(issue)
                    
                    print(f"\n   ⚠️  Invalid path in fact [{key}]:")
                    print(f"      {path}")
                    
                    if alternative:
                        print(f"      💡 Alternative: {alternative}")
                        fixes.append((path, alternative))
            
            if all_valid:
                self.report["valid"] += 1
            elif fixes and fix_paths:
                # 应用修复
                new_value = value
                for old_path, new_path in fixes:
                    new_value = new_value.replace(old_path, new_path)
                
                if not self.dry_run:
                    self.cursor.execute("""
                        UPDATE facts
                        SET value = ?, updated_at = ?
                        WHERE id = ?
                    """, (new_value, datetime.now().isoformat(), fact_id))
                    self.conn.commit()
                    print(f"  ✅ Fixed fact [{key}]")
                    self.report["fixed"] += 1
    
    def scan_timeline_paths(self):
        """扫描 timeline 表中的路径（只报告，不修复）"""
        print(f"\n📅 Scanning timeline table for reference...")
        
        self.cursor.execute("""
            SELECT id, title, description 
            FROM timeline 
            WHERE description LIKE '%/home/shan/%'
        """)
        entries = self.cursor.fetchall()
        
        # 统计路径类型
        path_stats = {}
        
        for entry_id, title, description in entries:
            paths = self.extract_paths(description)
            for path in paths:
                # 分类路径
                if ".openclaw" in path:
                    category = "openclaw_legacy"
                elif "/下载/" in path:
                    category = "download_temp"
                elif Path(path).exists():
                    category = "valid"
                else:
                    category = "other_invalid"
                
                path_stats[category] = path_stats.get(category, 0) + 1
        
        if path_stats:
            print(f"   Timeline path statistics:")
            for cat, count in sorted(path_stats.items(), key=lambda x: -x[1]):
                print(f"     - {cat}: {count}")
            print(f"\n   ℹ️  Timeline paths are historical records, not modified.")
    
    def print_summary(self):
        """打印总结报告"""
        print("\n" + "=" * 60)
        print("📊 CLEANUP SUMMARY")
        print("=" * 60)
        print(f"  Scanned:    {self.report['scanned']}")
        print(f"  Valid:      {self.report['valid']}")
        print(f"  Invalid:    {self.report['invalid']}")
        print(f"  Fixed:      {self.report['fixed']}")
        print("=" * 60)
        
        if self.report["issues"]:
            fixable = [i for i in self.report["issues"] if i.get("alternative")]
            not_fixable = [i for i in self.report["issues"] if not i.get("alternative")]
            
            print(f"\n⚠️  Issues breakdown:")
            print(f"   - {len(fixable)} can be auto-fixed")
            print(f"   - {len(not_fixable)} need manual review")
            
            if fixable:
                print(f"\n💡 Fixable issues:")
                for issue in fixable[:5]:  # 只显示前5个
                    print(f"   - {issue['key']}: {issue['invalid_path']}")
                    print(f"     → {issue['alternative']}")
                if len(fixable) > 5:
                    print(f"   ... and {len(fixable) - 5} more")
        
        if self.dry_run:
            print("\n🔍 DRY-RUN MODE: No changes were made")
            print("   Run with --fix-paths to apply fixes")
    
    def close(self):
        """关闭数据库连接"""
        self.conn.close()


def main():
    dry_run = "--fix-paths" not in sys.argv
    fix_paths = "--fix-paths" in sys.argv
    
    print("=" * 60)
    print("🧹 Memory Cleanup Script")
    print("=" * 60)
    print(f"Database: {DB_PATH}")
    print(f"Mode: {'DRY-RUN (no changes)' if dry_run else 'LIVE (will make changes)'}")
    print(f"Fix paths: {fix_paths}")
    
    if not DB_PATH.exists():
        print(f"\n❌ Database not found: {DB_PATH}")
        sys.exit(1)
    
    cleaner = MemoryCleaner(dry_run=dry_run)
    
    try:
        cleaner.process_facts(fix_paths=fix_paths)
        cleaner.scan_timeline_paths()
        cleaner.print_summary()
    finally:
        cleaner.close()


if __name__ == "__main__":
    main()
