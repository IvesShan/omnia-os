#!/bin/bash
# DJI 诊断工具启动脚本
# Omnia OS - 2026

echo "🚀 启动 DJI 诊断工具..."

# 切换到脚本目录
cd "$(dirname "$0")"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python3"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
pip3 install -q flask flask-cors 2>/dev/null

# 启动API服务
echo "🌐 启动 API 服务 (端口 5002)..."
python3 api.py &
API_PID=$!

# 等待API启动
sleep 2

# 检查API是否启动成功
if curl -s http://localhost:5002/api/dji/health > /dev/null; then
    echo "✅ API 服务已就绪"
else
    echo "❌ API 服务启动失败"
    kill $API_PID 2>/dev/null
    exit 1
fi

# 打开浏览器
echo "🌍 打开浏览器..."
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:5002/../dji/index.html
elif command -v open &> /dev/null; then
    open http://localhost:5002/../dji/index.html
fi

echo ""
echo "✨ DJI 诊断工具已启动！"
echo "📍 Web界面: file://$(pwd)/index.html"
echo "📍 API地址: http://localhost:5002"
echo ""
echo "按 Ctrl+C 停止服务..."

# 等待用户中断
trap "echo ''; echo '🛑 停止服务...'; kill $API_PID; exit 0" INT TERM
wait $API_PID
