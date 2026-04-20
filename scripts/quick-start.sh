#!/bin/bash
# Omnia 快速启动脚本（最简单的方式）
# 适合新手用户

set -e

echo "🚀 启动 Omnia..."
echo ""

# 检查是否已配置
if [ ! -f ".env" ] || grep -q "your-api-key-here" .env 2>/dev/null; then
    echo "⚠️  检测到未配置"
    echo ""
    echo "请先运行首次启动向导："
    echo "  ./scripts/first-run-wizard.sh"
    echo ""
    exit 1
fi

# 启动守护进程
if [ -f "scripts/start_daemon.py" ]; then
    echo "📡 启动守护进程..."
    python3 scripts/start_daemon.py
fi

# 启动 Tauri 桌面应用
if [ -f "package.json" ]; then
    echo ""
    echo "🖥️  启动桌面应用..."
    echo "   (首次启动可能需要编译，请耐心等待)"
    echo ""
    npm run tauri dev
else
    echo ""
    echo "❌ 未找到 package.json"
    echo "   请确保在 omnia-os 根目录运行此脚本"
    exit 1
fi
