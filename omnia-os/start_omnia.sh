#!/bin/bash
# Omnia 启动脚本
# 启动 API 服务器和守护进程

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${BLUE}  Omnia - AI Operating System${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo ""

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚠️  虚拟环境不存在，正在创建...${NC}"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -q fastapi uvicorn numpy pydantic
else
    source .venv/bin/activate
fi

# 检查依赖
echo -e "${BLUE}📦 检查依赖...${NC}"
pip install -q fastapi uvicorn numpy pydantic 2>/dev/null || true

# 启动自检
echo -e "${BLUE}🔍 运行自检...${NC}"
python3 scripts/self_diagnosis.py 2>/dev/null || {
    echo -e "${YELLOW}⚠️  自检脚本不存在或失败，跳过${NC}"
}

# 启动 API 服务器
PORT=${OMNIA_PORT:-8765}
echo -e "${GREEN}🚀 启动 API 服务器 (端口: $PORT)...${NC}"
echo ""

python3 src/api_server.py &
API_PID=$!

# 等待启动
sleep 2

# 检查是否成功
if kill -0 $API_PID 2>/dev/null; then
    echo -e "${GREEN}✅ Omnia API 已启动${NC}"
    echo -e "${BLUE}   地址: http://localhost:$PORT${NC}"
    echo -e "${BLUE}   文档: http://localhost:$PORT/docs${NC}"
    echo ""
    echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"
    echo ""
    
    # 保存 PID
    echo $API_PID > /tmp/omnia_api.pid
    
    # 等待
    wait $API_PID
else
    echo -e "${RED}❌ 启动失败${NC}"
    exit 1
fi
