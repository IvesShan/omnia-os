#!/bin/bash
# ============================================================
# Omnia FastAPI 启动脚本
# 功能：启动 FastAPI 版本的 Omnia 服务
# 端口：8765
# ============================================================

cd "$(dirname "$0")"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 停止旧进程
echo -e "${YELLOW}Stopping existing processes...${NC}"
pkill -f "uvicorn.*src.omnia.main" 2>/dev/null
pkill -f "python3.*web_server" 2>/dev/null
sleep 1

# 启动 FastAPI 服务
echo -e "${GREEN}Starting Omnia FastAPI server...${NC}"
nohup uvicorn src.omnia.main:app --host 0.0.0.0 --port 8765 --reload > /tmp/omnia_fastapi.log 2>&1 &

echo -e "${GREEN}Omnia FastAPI started at http://127.0.0.1:8765/${NC}"
echo -e "PID: ${GREEN}$!${NC}"
echo -e "Log: ${YELLOW}/tmp/omnia_fastapi.log${NC}"
