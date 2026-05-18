#!/usr/bin/env python3
"""
修复 agent_engine.py，添加 status 事件 (v2)
"""

import re

# 读取原文件
with open('/home/shan/omnia-os/src/omnia/services/agent_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到需要修改的位置
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    new_lines.append(line)
    
    # 1. 在工具调用循环开始时添加 status 事件
    # 找到 "rounds += 1" 后面添加
    if 'rounds += 1' in line and i > 0 and 'while rounds < self.max_tool_rounds' in lines[i-2]:
        # 添加 status 事件
        new_lines.append('            \n')
        new_lines.append('            # 发送状态更新\n')
        new_lines.append('            yield {\n')
        new_lines.append('                "type": "status",\n')
        new_lines.append('                "message": f"第 {rounds} 轮思考中..."\n')
        new_lines.append('            }\n')
    
    # 2. 在 LLM 调用前添加 status 事件
    # 找到 "# 流式调用 LLM" 注释
    if '# 流式调用 LLM' in line:
        # 在注释前添加 status 事件
        new_lines.insert(-1, '            # 发送状态更新\n')
        new_lines.insert(-1, '            yield {\n')
        new_lines.insert(-1, '                "type": "status",\n')
        new_lines.insert(-1, '                "message": "正在思考..."\n')
        new_lines.insert(-1, '            }\n')
    
    # 3. 在工具执行前添加 status 事件
    # 找到 "# 执行工具" 注释
    if '# 执行工具' in line and 'try:' in lines[i+1]:
        # 在注释前添加 status 事件
        new_lines.insert(-1, '            # 发送状态更新\n')
        new_lines.insert(-1, '            yield {\n')
        new_lines.insert(-1, '                "type": "status",\n')
        new_lines.insert(-1, '                "message": f"正在执行工具: {tool_name}..."\n')
        new_lines.insert(-1, '            }\n')
    
    i += 1

# 写入修改后的文件
with open('/home/shan/omnia-os/src/omnia/services/agent_engine.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ agent_engine.py 已修改，添加了 status 事件")
