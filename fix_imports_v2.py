#!/usr/bin/env python3
"""修复 stream_chat.py 的导入"""
import re

file_path = "/home/shan/omnia-os/src/omnia/stream_chat.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 删除未使用的导入
content = re.sub(r'from typing import Optional, Generator, Dict', 'from typing import Generator, Dict', content)
content = re.sub(r'from datetime import datetime\n', '', content)
content = re.sub(r'from omnia\.tool_optimizer import ToolExecutionOptimizer, ToolResult, ParallelToolExecutor', 'from omnia.tool_optimizer import ToolExecutionOptimizer, ParallelToolExecutor', content)
content = re.sub(r'from omnia\.long_task_handler import LongTaskHandler, handle_long_task_stream\n', '', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("修复完成")
