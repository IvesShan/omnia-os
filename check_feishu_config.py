#!/usr/bin/env python3
"""检查飞书机器人配置"""

import os
import requests

# 加载 .env
with open(".env") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ[key.strip()] = value.strip()

APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")

# 获取 access_token
url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
resp = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET})
data = resp.json()

if data.get("code") != 0:
    print(f"❌ 获取 token 失败: {data}")
    exit(1)

token = data["tenant_access_token"]
print(f"✅ Token: {token[:20]}...")

# 获取机器人信息
headers = {"Authorization": f"Bearer {token}"}

# 获取 app 信息
resp = requests.get("https://open.feishu.cn/open-apis/bot/v3/info", headers=headers)
bot_info = resp.json()
print(f"\n🤖 机器人信息:")
if bot_info.get("code") == 0:
    bot = bot_info.get("bot", {})
    print(f"   名称: {bot.get('app_name')}")
    print(f"   Open ID: {bot.get('open_id')}")
    print(f"   激活状态: {bot.get('activate_status')}")
else:
    print(f"   获取失败: {bot_info}")

# 获取应用权限范围
resp = requests.get("https://open.feishu.cn/open-apis/auth/v3/app_scope", headers=headers)
scope_info = resp.json()
print(f"\n📋 应用权限:")
if scope_info.get("code") == 0:
    scopes = scope_info.get("data", {}).get("app_scope", {}).get("scopes", [])
    for scope in scopes[:10]:  # 只显示前10个
        print(f"   - {scope}")
    if len(scopes) > 10:
        print(f"   ... 还有 {len(scopes) - 10} 个权限")
else:
    print(f"   获取失败: {scope_info}")

# 检查事件订阅状态
print(f"\n📡 事件订阅:")
print(f"   请在飞书后台检查:")
print(f"   1. 开发者后台 → 应用 → 事件订阅 → 是否开启")
print(f"   2. 订阅方式: WebSocket 长连接")
print(f"   3. 事件: im.message.receive_v1 是否勾选")
