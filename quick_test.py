#!/usr/bin/env python3
"""
快速测试飞书SDK修复
"""

import json
import sys

print("快速测试飞书SDK修复")
print("=" * 50)

# 测试1: 导入修复
print("1. 测试导入修复...")
try:
    from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody
    print("   ✅ 导入成功")
except ImportError as e:
    print(f"   ❌ 导入失败: {e}")
    sys.exit(1)

# 测试2: 构建请求
print("2. 测试请求构建...")
try:
    req = CreateMessageRequest.builder() \
        .receive_id_type("chat_id") \
        .request_body(CreateMessageRequestBody.builder()
            .receive_id("test_123")
            .msg_type("text")
            .content(json.dumps({"text": "测试"}))
            .build()) \
        .build()
    print("   ✅ 请求构建成功")
    print(f"   接收ID类型: {req.receive_id_type}")
    print(f"   消息类型: {req.request_body.msg_type}")
except Exception as e:
    print(f"   ❌ 构建失败: {e}")
    sys.exit(1)

# 测试3: 配置文件检查
print("3. 检查配置文件...")
import os
config_path = "config/feishu.json"
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
    print(f"   ✅ 配置文件存在")
    print(f"   App ID: {config.get('app_id', '未设置')}")
    print(f"   已启用: {config.get('enabled', False)}")
else:
    print(f"   ⚠️  配置文件不存在: {config_path}")

print("=" * 50)
print("✅ 所有测试通过！")
print("可以启动飞书服务了。")