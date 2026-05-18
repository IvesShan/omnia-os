#!/usr/bin/env python3
"""
修复 agent_engine.py，添加 status 事件
"""

import re

# 读取原文件
with open('/home/shan/omnia-os/src/omnia/services/agent_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 在工具调用循环开始时添加 status 事件
# 找到 "while rounds < self.max_tool_rounds:" 后的 "rounds += 1"
pattern1 = r'(while rounds < self\.max_tool_rounds:\s*\n\s*rounds \+= 1)'
replacement1 = r'''\1
            
            # 发送状态更新
            yield {
                "type": "status",
                "message": f"第 {rounds} 轮思考中..."
            }'''
content = re.sub(pattern1, replacement1, content)

# 2. 在 LLM 调用前添加 status 事件
# 找到 "# 流式调用 LLM" 注释
pattern2 = r'(            # 流式调用 LLM)'
replacement2 = r'''# 发送状态更新
            yield {
                "type": "status",
                "message": "正在思考..."
            }
            \1'''
content = re.sub(pattern2, replacement2, content)

# 3. 在工具执行前添加 status 事件
# 找到 "# 执行工具" 注释和 "try:" 语句
pattern3 = r'(            # 执行工具\s*\n\s*try:)'
replacement3 = r'''# 发送状态更新
            yield {
                "type": "status",
                "message": f"正在执行工具: {tool_name}..."
            }
            \1'''
content = re.sub(pattern3, replacement3, content)

# 写入修改后的文件
with open('/home/shan/omnia-os/src/omnia/services/agent_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ agent_engine.py 已修改，添加了 status 事件")
