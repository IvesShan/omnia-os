#!/usr/bin/env python3
"""测试对话记录功能"""

import sys
import os
sys.path.insert(0, '/home/shan//home/shan/omnia-os/omnia-os/src')

from pathlib import Path
from core.memory_palace.memory_palace import MemoryPalace

# 数据库路径
memory_db = Path.home() / '.omnia' / 'memory_palace.db'
print(f"Database path: {memory_db}")
print(f"Database exists: {memory_db.exists()}")

# 初始化 MemoryPalace
mp = MemoryPalace(str(memory_db))

# 测试记录对话
session_id = "test_session_001"
print(f"\n=== 测试记录对话 ===")
print(f"Session ID: {session_id}")

# 记录用户消息
try:
    mp.log_conversation(session_id, 0, "user", "测试用户消息")
    print("✅ 用户消息记录成功")
except Exception as e:
    print(f"❌ 用户消息记录失败: {e}")

# 记录助手回复
try:
    mp.log_conversation(session_id, 0, "assistant", "测试助手回复")
    print("✅ 助手回复记录成功")
except Exception as e:
    print(f"❌ 助手回复记录失败: {e}")

# 记录工具调用
try:
    mp.log_tool_use(
        session_id=session_id,
        turn_number=0,
        tool_name="test_tool",
        arguments={"arg1": "value1"},
        result="测试结果"
    )
    print("✅ 工具调用记录成功")
except Exception as e:
    print(f"❌ 工具调用记录失败: {e}")

# 查询记录
print(f"\n=== 查询记录 ===")

import sqlite3
conn = sqlite3.connect(str(memory_db))
cursor = conn.cursor()

# 查询对话记录
cursor.execute("SELECT COUNT(*) FROM conversation_logs")
count = cursor.fetchone()[0]
print(f"对话记录总数: {count}")

cursor.execute("SELECT * FROM conversation_logs ORDER BY created_at DESC LIMIT 5")
rows = cursor.fetchall()
print(f"\n最近 5 条对话记录:")
for row in rows:
    print(f"  - {row}")

# 查询工具调用记录
cursor.execute("SELECT COUNT(*) FROM tool_calls")
count = cursor.fetchone()[0]
print(f"\n工具调用记录总数: {count}")

cursor.execute("SELECT * FROM tool_calls ORDER BY created_at DESC LIMIT 5")
rows = cursor.fetchall()
print(f"\n最近 5 条工具调用记录:")
for row in rows:
    print(f"  - {row}")

conn.close()

print("\n✅ 测试完成！")
