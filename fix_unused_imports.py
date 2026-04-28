#!/usr/bin/env python3
"""
批量修复未使用的导入
"""
import re
import subprocess
import sys
from pathlib import Path
from collections import defaultdict

def get_unused_imports():
    """获取所有未使用的导入"""
    result = subprocess.run(
        ["./venv/bin/python3", "-m", "pyflakes", "src/"],
        capture_output=True,
        text=True,
        cwd="/home/shan/omnia-os"
    )
    
    unused = defaultdict(list)
    for line in result.stdout.split('\n'):
        if 'imported but unused' in line:
            # 格式: src/backend/main.py:13:1: 'os' imported but unused
            parts = line.split(':')
            if len(parts) >= 3:
                file_path = parts[0]
                line_num = int(parts[1])
                # 提取模块名
                match = re.search(r"'([^']+)' imported but unused", line)
                if match:
                    module_name = match.group(1)
                    unused[file_path].append((line_num, module_name))
    
    return unused

def fix_file(file_path, imports_to_remove):
    """修复单个文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 按行号降序排序，从后往前删除
    imports_to_remove.sort(key=lambda x: x[0], reverse=True)
    
    removed_count = 0
    for line_num, module_name in imports_to_remove:
        if line_num <= len(lines):
            line = lines[line_num - 1]
            # 检查是否包含模块名
            if module_name in line:
                # 检查是否是多行导入（包含逗号）
                if ',' in line and 'import' in line:
                    # 多行导入，暂时跳过
                    print(f"  跳过多行导入: {file_path}:{line_num}")
                    continue
                else:
                    # 单行导入，删除
                    del lines[line_num - 1]
                    removed_count += 1
                    print(f"  删除: {file_path}:{line_num} - {module_name}")
    
    if removed_count > 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    
    return removed_count

def main():
    print("获取未使用的导入...")
    unused = get_unused_imports()
    
    print(f"\n找到 {len(unused)} 个文件需要修复")
    
    total_removed = 0
    for file_path, imports in unused.items():
        full_path = Path(f"/home/shan/omnia-os/{file_path}")
        if full_path.exists():
            print(f"\n修复 {file_path}...")
            removed = fix_file(full_path, imports)
            total_removed += removed
    
    print(f"\n总计删除 {total_removed} 个未使用的导入")

if __name__ == "__main__":
    main()
