#!/bin/bash
# Omnia 启动脚本 (优化版 - 带自动 Token 管理)
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

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Omnia - AI Operating System (优化版)${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
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

# 验证优化版组件
echo -e "${BLUE}🔍 验证优化版组件...${NC}"
python3 -c "
import sys
sys.path.insert(0, 'src')
from core.cognition.chat_integration_optimized import OmniaChatEngineOptimized
from core.cognition.token_manager import estimate_messages_tokens, check_context_overflow
print('  ✅ 优化版引擎可用')
" 2>&1 || {
    echo -e "${RED}❌ 优化版组件验证失败，回退到标准版${NC}"
    exec ./start_omnia.sh
}

# 启动 API 服务器 (优化版)
PORT=${OMNIA_PORT:-8765}
echo -e "${GREEN}🚀 启动 API 服务器 (优化版, 端口: $PORT)...${NC}"
echo ""

python3 src/api_server_optimized.py &
API_PID=$!

# 等待启动
sleep 2

# 检查是否成功
if kill -0 $API_PID 2>/dev/null; then
    echo -e "${GREEN}✅ Omnia API (优化版) 已启动${NC}"
    echo -e "${BLUE}   地址: http://localhost:$PORT${NC}"
    echo -e "${BLUE}   文档: http://localhost:$PORT/docs${NC}"
    echo -e "${BLUE}   Token 状态: http://localhost:$PORT/token-status${NC}"
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
