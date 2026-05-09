#!/bin/bash
# 启动飞书机器人

cd /home/shan/omnia-os

# 检查是否已运行
if pgrep -f "feishu_bot_v3.py" > /dev/null; then
    echo "⚠️  飞书机器人已在运行"
    echo "   如需重启，请先运行: ./stop_feishu.sh"
    exit 0
fi

# 启动
source venv/bin/activate
nohup python3 scripts/feishu_bot_v3.py >> logs/feishu_bot.log 2>&1 &

sleep 2

# 检查是否启动成功
if pgrep -f "feishu_bot_v3.py" > /dev/null; then
    echo "✅ 飞书机器人启动成功!"
    echo "   日志: logs/feishu_bot.log"
    echo ""
    echo "   在飞书中给机器人发消息试试!"
else
    echo "❌ 启动失败，请检查日志:"
    tail -20 logs/feishu_bot.log
fi
