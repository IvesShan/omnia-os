#!/bin/bash
# Omnia 快速开始脚本
# 用于开发环境快速启动

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "Omnia 快速启动"
echo "========================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查后端是否运行
if curl -s http://localhost:5001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} 后端已在运行"
else
    echo -e "${YELLOW}启动后端...${NC}"
    cd "$PROJECT_ROOT"
    python3 backend/standalone_main.py &
    BACKEND_PID=$!
    echo "后端 PID: $BACKEND_PID"
    sleep 2
fi

# 启动 Tauri 开发模式
echo ""
echo -e "${YELLOW}启动 Tauri 开发模式...${NC}"
cd "$PROJECT_ROOT/src-tauri"
cargo tauri dev
