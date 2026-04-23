#!/usr/bin/env python3
"""简单的前端测试 - 验证核心功能"""

import requests
import json

BASE_URL = "http://localhost:5001"

print("="*60)
print("🧪 Omnia 前端核心功能测试")
print("="*60)

# 1. 测试模型状态
print("\n[1] 测试模型状态 API...")
try:
    r = requests.get(f"{BASE_URL}/api/model/status", timeout=5)
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.json()}")
except Exception as e:
    print(f"❌ 错误: {e}")

# 2. 测试模型切换
print("\n[2] 测试模型切换...")
try:
    r = requests.post(
        f"{BASE_URL}/api/model/mode",
        json={"mode": "local_only"},
        timeout=5
    )
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.json()}")
    
    # 验证切换
    r2 = requests.get(f"{BASE_URL}/api/model/status", timeout=5)
    print(f"当前模式: {r2.json().get('current_mode')}")
except Exception as e:
    print(f"❌ 错误: {e}")

# 3. 测试聊天
print("\n[3] 测试聊天功能...")
try:
    r = requests.post(
        f"{BASE_URL}/api/chat",
        json={"message": "你好"},
        timeout=30
    )
    print(f"状态码: {r.status_code}")
    data = r.json()
    print(f"响应键: {list(data.keys())}")
    
    # 检查不同的响应字段
    if "response" in data:
        print(f"✅ response 字段存在，长度: {len(data['response'])}")
        print(f"内容预览: {data['response'][:100]}...")
    elif "content" in data:
        print(f"✅ content 字段存在，长度: {len(data['content'])}")
        print(f"内容预览: {data['content'][:100]}...")
    elif "reply" in data:
        print(f"✅ reply 字段存在，长度: {len(data['reply'])}")
        print(f"内容预览: {data['reply'][:100]}...")
    else:
        print(f"⚠️ 响应结构: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
except Exception as e:
    print(f"❌ 错误: {e}")

# 4. 测试前端页面
print("\n[4] 测试前端页面...")
try:
    r = requests.get(f"{BASE_URL}/", timeout=5)
    print(f"状态码: {r.status_code}")
    print(f"页面大小: {len(r.text)} bytes")
    
    # 检查关键元素
    checks = {
        "Omnia标题": "Omnia" in r.text,
        "导航": "仪表盘" in r.text,
        "模型切换": "model-switcher" in r.text or "模型管理" in r.text
    }
    
    for name, exists in checks.items():
        print(f"  {'✓' if exists else '✗'} {name}")
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*60)
print("✅ 测试完成")
print("="*60)
