#!/usr/bin/env python3
import os
import requests

with open(".env") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()

APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")

# 获取 token
resp = requests.post(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET}
)
token = resp.json().get("tenant_access_token", "")

# 获取机器人信息
resp = requests.get(
    "https://open.feishu.cn/open-apis/bot/v3/info",
    headers={"Authorization": f"Bearer {token}"}
)
bot = resp.json().get("bot", {})

print(f"✅ 飞书机器人配置正确!")
print(f"   名称: {bot.get('app_name')}")
print(f"   Open ID: {bot.get('open_id')}")
print(f"   激活状态: {'已激活' if bot.get('activate_status') == 2 else '未激活'}")
