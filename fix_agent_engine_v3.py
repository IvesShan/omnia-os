#!/usr/bin/env python3
"""
修复 agent_engine.py，添加 status 事件 (v3)
只修改 process_stream_with_tools 方法
"""

# 读取原文件
with open('/home/shan/omnia-os/src/omnia/services/agent_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 process_stream_with_tools 方法的开始
method_start = content.find('    async def process_stream_with_tools(')
if method_start == -1:
    print("❌ 找不到 process_stream_with_tools 方法")
    exit(1)

# 找到方法的结束位置（下一个方法或类结束）
# 简单起见，我们找到下一个 "    async def" 或 "    def" 或文件结束
method_end = content.find('\n    async def ', method_start + 1)
if method_end == -1:
    method_end = content.find('\n    def ', method_start + 1)
if method_end == -1:
    method_end = len(content)

# 提取方法内容
method_content = content[method_start:method_end]

# 1. 在工具调用循环开始时添加 status 事件
# 找到 "rounds += 1" 后面添加
old_text = '            rounds += 1\n            \n            # 检查用户是否请求中断'
new_text = '''            rounds += 1
            
            # 发送状态更新
            yield {
                "type": "status",
                "message": f"第 {rounds} 轮思考中..."
            }
            
            # 检查用户是否请求中断'''
method_content = method_content.replace(old_text, new_text)

# 2. 在 LLM 调用前添加 status 事件
# 找到 "# 流式调用 LLM" 注释
old_text = '            # 流式调用 LLM'
new_text = '''            # 发送状态更新
            yield {
                "type": "status",
                "message": "正在思考..."
            }
            
            # 流式调用 LLM'''
method_content = method_content.replace(old_text, new_text)

# 3. 在工具执行前添加 status 事件
# 找到 "# 执行工具" 注释
old_text = '            # 执行工具\n            try:'
new_text = '''            # 发送状态更新
            yield {
                "type": "status",
                "message": f"正在执行工具: {tool_name}..."
            }
            
            # 执行工具
            try:'''
method_content = method_content.replace(old_text, new_text)

# 替换原方法
new_content = content[:method_start] + method_content + content[method_end:]

# 写入修改后的文件
with open('/home/shan/omnia-os/src/omnia/services/agent_engine.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ agent_engine.py 已修改，添加了 status 事件")
