#!/bin/bash
# 停止飞书机器人

pkill -f "feishu_bot_v3.py" 2>/dev/null

if pgrep -f "feishu_bot_v3.py" > /dev/null; then
    echo "⚠️  停止失败，尝试强制终止..."
    pkill -9 -f "feishu_bot_v3.py"
fi

echo "✅ 飞书机器人已停止"
