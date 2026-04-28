#!/usr/bin/env python3
"""批量修复数据库连接问题"""

import re
from pathlib import Path

# 需要修复的文件列表
FILES_TO_FIX = [
    "src/omnia/__main__.py",
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


def fix_file(file_path: str) -> int:
    """修复单个文件，返回修复的数量"""
    path = Path(file_path)
    if not path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return 0
    
    content = path.read_text()
    original_content = content
    
    # 模式1: conn = sqlite3.connect(...) ... conn.close()
    # 改为: with sqlite3.connect(...) as conn: ...
    
    # 这个比较复杂，需要手动处理
    # 简单策略：找到所有 conn = sqlite3.connect(...)，然后检查是否有 conn.close()
    
    lines = content.split('\n')
    fixed_count = 0
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # 检查是否是数据库连接行
        if re.search(r'conn\s*=\s*sqlite3\.connect\(', line):
            indent = len(line) - len(line.lstrip())
            indent_str = line[:indent]
            
            # 检查后续是否有 conn.close()
            has_close = False
            close_line_idx = -1
            for j in range(i+1, min(i+50, len(lines))):
                if 'conn.close()' in lines[j]:
                    has_close = True
                    close_line_idx = j
                    break
                # 如果遇到下一个 conn = 或函数定义，停止搜索
                if re.search(r'conn\s*=\s*sqlite3\.connect\(', lines[j]) or \
                   re.search(r'^def\s+\w+\s*\(', lines[j]) or \
                   re.search(r'^class\s+\w+', lines[j]):
                    break
            
            if has_close:
                # 修改连接行为 with 语句
                connect_match = re.search(r'conn\s*=\s*sqlite3\.connect\(([^)]+)\)', line)
                if connect_match:
                    args = connect_match.group(1)
                    lines[i] = indent_str + f'with sqlite3.connect({args}) as conn:'
                    fixed_count += 1
                    
                    # 删除 conn.close() 行
                    del lines[close_line_idx]
        
        i += 1
    
    if fixed_count > 0:
        path.write_text('\n'.join(lines))
        print(f"✅ {file_path}: 修复了 {fixed_count} 处")
    
    return fixed_count


def main():
    total_fixed = 0
    for file_path in FILES_TO_FIX:
        fixed = fix_file(file_path)
        total_fixed += fixed
    
    print(f"\n总计修复: {total_fixed} 处数据库连接问题")


if __name__ == "__main__":
    main()
