#!/bin/bash

# Omnia Neural Graph 3D 安装脚本
# 用于安装 3d-force-graph 和相关依赖

echo "🧠 Omnia Neural Graph 3D 安装脚本"
echo "=================================="
echo ""

# 检查包管理器
if command -v npm &> /dev/null; then
    PKG_MANAGER="npm"
elif command -v pnpm &> /dev/null; then
    PKG_MANAGER="pnpm"
elif command -v yarn &> /dev/null; then
    PKG_MANAGER="yarn"
else
    echo "❌ 错误: 未找到 npm, pnpm 或 yarn"
    echo "请先安装 Node.js: https://nodejs.org/"
    exit 1
fi

echo "✅ 使用包管理器: $PKG_MANAGER"
echo ""

# 进入项目目录
cd "$(dirname "$0")"
echo "📁 项目目录: $(pwd)"
echo ""

# 安装依赖
echo "📦 安装依赖..."
case $PKG_MANAGER in
    npm)
        npm install 3d-force-graph three-spritetext
        ;;
    pnpm)
        pnpm add 3d-force-graph three-spritetext
        ;;
    yarn)
        yarn add 3d-force-graph three-spritetext
        ;;
esac

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 安装成功！"
    echo ""
    echo "🚀 启动开发服务器:"
    echo "   $PKG_MANAGER run dev"
    echo ""
    echo "📖 查看使用文档:"
    echo "   cat NEURAL_GRAPH_GUIDE.md"
    echo ""
    echo "🌐 访问地址:"
    echo "   http://localhost:5173"
else
    echo ""
    echo "❌ 安装失败，请检查网络连接或手动安装:"
    echo "   $PKG_MANAGER install"
fi
