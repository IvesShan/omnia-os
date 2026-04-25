#!/bin/bash
# Omnia V2 启动脚本
# 创建时间: 2026-04-26

set -e

cd /home/shan/omnia-os/omnia-os

echo "🚀 启动 Omnia V2..."
echo ""

# 检查虚拟环境
if [ -d ".venv" ]; then
    echo "✅ 激活虚拟环境"
    source .venv/bin/activate
fi

# 检查配置文件
if [ ! -f ".env" ]; then
    echo "⚠️  警告: .env 文件不存在"
    echo "   请确保已配置 API 密钥"
fi

# 启动 API Server V2
echo "📡 启动 API Server V2 (端口 8765)..."
python3 -m uvicorn src.api_server_v2:app --host 0.0.0.0 --port 8765 &

# 等待启动
sleep 2

# 检查服务
if curl -s http://localhost:8765/health > /dev/null; then
    echo "✅ API Server V2 启动成功"
    echo ""
    echo "📍 端点:"
    echo "   - API: http://localhost:8765"
    echo "   - 文档: http://localhost:8765/docs"
    echo "   - 健康检查: http://localhost:8765/health"
else
    echo "❌ API Server V2 启动失败"
    exit 1
fi

echo ""
echo "🎉 Omnia V2 已就绪!"
