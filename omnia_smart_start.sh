#!/bin/bash
# Omnia 智能启动脚本
# 避免进程冲突

echo "🔍 检查 Omnia 状态..."

# 检查端口
if ss -tlnp | grep -q ":5001"; then
    echo "✅ Omnia 已在运行 (端口 5001)"
    echo ""
    echo "进程信息:"
    ps aux | grep -E 'web_server|_daemon' | grep -v grep
    
    echo ""
    echo "测试访问:"
    curl -s http://localhost:5001/ | head -5
    
    exit 0
fi

echo "🧹 清理旧进程..."
pkill -9 -f "web_server.py" 2>/dev/null
pkill -9 -f "_daemon_runner.py" 2>/dev/null
sleep 2

echo ""
echo "🚀 启动 Omnia..."
cd ~/omnia-os

# 只启动 Web 服务器（不启动守护进程）
nohup python3 src/omnia/web_server.py > /tmp/omnia_web.log 2>&1 &

sleep 3

echo ""
echo "=== 进程状态 ==="
ps aux | grep web_server | grep -v grep

echo ""
echo "=== 端口状态 ==="
ss -tlnp | grep 5001

echo ""
echo "✅ Omnia 启动完成！"
echo "访问地址: http://localhost:5001"
