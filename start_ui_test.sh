#!/bin/bash
echo "🚀 启动 Omnia UI 测试..."
echo ""

# 检查后端是否运行
if ! pgrep -f "omnia_backend.py" > /dev/null; then
    echo "⚠️  后端未运行，正在启动..."
    python3 src/omnia/web_server.py &
    sleep 3
fi

# 检查测试服务器
if ! pgrep -f "http.server 8888" > /dev/null; then
    echo "📡 启动测试服务器..."
    cd /home/shan/omnia-os
    python3 -m http.server 8888 &
    sleep 2
fi

echo ""
echo "✅ 测试环境已就绪！"
echo ""
echo "📍 测试页面: http://localhost:8888/test_frontend_ui.html"
echo "📍 后端 API: http://localhost:5001"
echo ""
echo "💡 提示："
echo "  - 点击「运行所有测试」按钮进行完整测试"
echo "  - 可以手动切换模式并测试聊天功能"
echo "  - 状态每 5 秒自动刷新"
echo ""
