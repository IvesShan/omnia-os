#!/bin/bash
# Omnia Web 管理面板启动脚本

cd /home/shan/omnia-os

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3"
    exit 1
fi

# 检查依赖
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "安装依赖..."
    pip3 install -r src/backend/requirements.txt
fi

# 启动服务
echo "🚀 启动 Omnia 管理面板..."
echo "📍 地址: http://localhost:5001"
echo "📚 API 文档: http://localhost:5001/api/docs"
echo ""

python3 -m uvicorn src.backend.main:app --host 0.0.0.0 --port 5001 --reload
