#!/bin/bash

# Omnia Brain - 神经图谱启动脚本

echo "🧠 Omnia Brain - 神经图谱 HUD"
echo "================================"
echo ""

cd "$(dirname "$0")"

# 检查 node_modules
if [ ! -d "node_modules" ]; then
    echo "📦 安装依赖..."
    npm install
fi

echo "🚀 启动开发服务器..."
echo ""
echo "访问地址: http://localhost:5173"
echo ""
echo "✨ 新功能:"
echo "  - 3D 神经图谱（替换了原 KnowledgeGraph）"
echo "  - 发光节点 + 光晕效果"
echo "  - 悬停显示节点信息"
echo "  - 自动旋转动画"
echo "  - 点击节点选中"
echo ""

npm run dev
