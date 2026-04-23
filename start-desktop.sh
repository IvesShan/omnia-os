#!/bin/bash
# Omnia Desktop - Development Mode Launcher
# 启动开发模式（自动启动后端 + 打开桌面应用）

cd "$(dirname "$0")"

echo "🚀 Starting Omnia Desktop (Dev Mode)..."
echo ""

# 启动后端服务
echo "1. Starting backend services..."
./start.sh

# 等待后端启动
sleep 2

# 启动 Tauri 开发模式
echo "2. Launching Tauri desktop app..."
npm run tauri dev
