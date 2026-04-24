#!/bin/bash

echo "🧠 启动 Omnia Brain..."
echo "融合项目: VowVector 架构 + porweb 视觉风格"
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

# 检查 Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

echo "✅ Docker 环境检查通过"
echo ""

# 启动服务
echo "🚀 启动服务..."
docker-compose up -d

echo ""
echo "✨ Omnia Brain 已启动！"
echo ""
echo "📍 访问地址:"
echo "   前端:    http://localhost:5173"
echo "   后端:    http://localhost:8000"
echo "   Neo4j:   http://localhost:7474"
echo "   Qdrant:  http://localhost:6333"
echo "   Ollama:  http://localhost:11434"
echo ""
echo "📖 查看日志: docker-compose logs -f"
echo "🛑 停止服务: docker-compose down"
echo ""
