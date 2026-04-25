#!/bin/bash
# 启动优化后的 Omnia API Server

cd /home/shan/omnia-os/omnia-os

echo "🚀 启动 Omnia API Server (Optimized)..."
echo "📊 Token 管理已启用"
echo "🔗 API 地址: http://localhost:5001"
echo ""

# 检查依赖
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "⚠️ 缺少依赖，正在安装..."
    pip install fastapi uvicorn httpx pydantic
fi

# 启动服务器
python3 -m uvicorn src.api_server_optimized:app --host 0.0.0.0 --port 5001 --reload
