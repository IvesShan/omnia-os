#!/usr/bin/env python3
"""批量修复数据库连接问题 - 改进版"""

import re
from pathlib import Path
from typing import List, Tuple

def fix_database_connections(content: str) -> Tuple[str, int]:
    """
    修复数据库连接问题
    返回: (修复后的内容, 修复数量)
    """
    lines = content.split('\n')
    fixed_count = 0
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # 检查是否是数据库连接行
        match = re.search(r'^(\s*)conn\s*=\s*sqlite3\.connect\(([^)]+)\)', line)
        if match:
            indent = match.group(1)
            args = match.group(2)
            
            # 检查后续是否有 conn.close()
            has_close = False
            close_line_idx = -1
            for j in range(i+1, min(i+100, len(lines))):
                if 'conn.close()' in lines[j]:
                    has_close = True
                    close_line_idx = j
                    break
                # 如果遇到下一个 conn = 或函数定义或 return，停止搜索
                if re.search(r'conn\s*=\s*sqlite3\.connect\(', lines[j]) or \
                   re.search(r'^def\s+\w+\s*\(', lines[j]) or \
                   re.search(r'^class\s+\w+', lines[j]) or \
                   re.search(r'^\s*return\s+', lines[j]):
                    break
            
            if has_close:
                # 修改连接行为 with 语句
                lines[i] = f'{indent}with sqlite3.connect({args}) as conn:'
                fixed_count += 1
                
                # 删除 conn.close() 行
                del lines[close_line_idx]
                
                # 增加缩进后续行（直到 conn.close() 原来的位置）
                # 注意：close_line_idx 已经被删除，所以后续行的索引都减 1
                for j in range(i+1, close_line_idx):  # close_line_idx 已经减 1
                    if lines[j].strip() and not lines[j].strip().startswith('#'):
                        # 增加缩进
                        lines[j] = '    ' + lines[j]
        
        i += 1
    
    return '\n'.join(lines), fixed_count


def fix_file(file_path: str) -> int:
    """修复单个文件，返回修复的数量"""
    path = Path(file_path)
    if not path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return 0
    
    content = path.read_text()
    fixed_content, fixed_count = fix_database_connections(content)
    
    if fixed_count > 0:
        path.write_text(fixed_content)
        print(f"✅ {file_path}: 修复了 {fixed_count} 处")
    else:
        print(f"⏭️  {file_path}: 无需修复")
    
    return fixed_count


def main():
    # 需要修复的文件列表
    files_to_fix = [
        "src/core/cognition/prompt_builder.py",
        "src/core/neural_graph/context_enhancer.py",
        "src/core/neural_graph/conversation_processor.py",
        "src/core/neural_graph/vector_store.py",
        "src/core/neural_graph/vector_integration.py",
        "src/core/neural_graph/graph.py",
        "src/core/topic_recognizer.py",
        "src/core/reminder_engine.py",
        "src/core/neural_graph_algorithms.py",
        "src/core/memory/fts_search.py",
        "src/core/memory/palace.py",
        "src/core/actuator/tool_registry.py",
        "src/core/actuator/plan_store.py",
        "src/monitoring/conversation_monitor.py",
        "src/monitoring/anomaly_detector.py",
        "src/monitoring/performance_monitor.py",
    ]
    
    total_fixed = 0
    for file_path in files_to_fix:
        fixed = fix_file(file_path)
        total_fixed += fixed
    
    print(f"\n📊 总计修复: {total_fixed} 处数据库连接问题")


if __name__ == "__main__":
    main()
