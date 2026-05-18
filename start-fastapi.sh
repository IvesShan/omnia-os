#!/bin/bash
# ============================================================
# Omnia FastAPI 版本启动脚本
# 启动主应用 (端口 8765) + 管理后端 (端口 5001)
# ============================================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录（脚本所在目录）
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
OMNIA_HOME="$HOME/.omnia"
LOG_DIR="$PROJECT_ROOT/logs"

# 创建必要的目录
mkdir -p "$OMNIA_HOME" "$LOG_DIR"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           Omnia FastAPI 版本启动脚本                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}项目目录:${NC} $PROJECT_ROOT"
echo -e "${YELLOW}日志目录:${NC} $LOG_DIR"
echo ""

# ============================================================
# 第一步：清理旧进程
# ============================================================
echo -e "${BLUE}[1/3] 清理旧进程...${NC}"

# 杀死可能残留的进程
KILL_PATTERNS=(
    "src.omnia.main"
    "src.backend.main"
    "web_server.py"
    "uvicorn.*8765"
    "uvicorn.*5001"
)

for pattern in "${KILL_PATTERNS[@]}"; do
    pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo -e "  → 杀死进程: ${YELLOW}$pattern${NC} (PID: $pids)"
        pkill -f "$pattern" 2>/dev/null || true
        sleep 0.5
    fi
done

# 释放端口 8765 和 5001
for port in 8765 5001; do
    lsof_pid=$(lsof -ti :$port 2>/dev/null || true)
    if [ -n "$lsof_pid" ]; then
        echo -e "  → 释放端口 ${YELLOW}$port${NC} (PID: $lsof_pid)"
        kill -9 $lsof_pid 2>/dev/null || true
    fi
done

echo -e "${GREEN}  ✓ 清理完成${NC}"
echo ""

# ============================================================
# 第二步：启动 FastAPI 主应用 (端口 8765)
# ============================================================
echo -e "${BLUE}[2/3] 启动 FastAPI 主应用 (端口 8765)...${NC}"

cd "$PROJECT_ROOT"
nohup python3 -m uvicorn src.omnia.main:app \
    --host 0.0.0.0 \
    --port 8765 \
    --log-level info \
    > "$LOG_DIR/omnia-main.log" 2>&1 &

MAIN_PID=$!
echo "$MAIN_PID" > "$OMNIA_HOME/omnia-main.pid"
echo -e "  → 主应用 PID: ${GREEN}$MAIN_PID${NC}"
echo -e "  → 日志文件: ${GREEN}$LOG_DIR/omnia-main.log${NC}"

# 等待启动
sleep 2

# 检查是否启动成功
if kill -0 $MAIN_PID 2>/dev/null; then
    echo -e "${GREEN}  ✓ 主应用启动成功${NC}"
else
    echo -e "${RED}  ✗ 主应用启动失败，请查看日志: $LOG_DIR/omnia-main.log${NC}"
    exit 1
fi

# ============================================================
# 第三步：启动管理后端 (端口 5001)
# ============================================================
echo -e "${BLUE}[3/3] 启动管理后端 (端口 5001)...${NC}"

nohup python3 -m uvicorn src.backend.main:app \
    --host 0.0.0.0 \
    --port 5001 \
    --log-level info \
    > "$LOG_DIR/omnia-backend.log" 2>&1 &

BACKEND_PID=$!
echo "$BACKEND_PID" > "$OMNIA_HOME/omnia-backend.pid"
echo -e "  → 管理后端 PID: ${GREEN}$BACKEND_PID${NC}"
echo -e "  → 日志文件: ${GREEN}$LOG_DIR/omnia-backend.log${NC}"

# 等待启动
sleep 2

# 检查是否启动成功
if kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${GREEN}  ✓ 管理后端启动成功${NC}"
else
    echo -e "${RED}  ✗ 管理后端启动失败，请查看日志: $LOG_DIR/omnia-backend.log${NC}"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Omnia FastAPI 版本启动完成!                   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BLUE}主应用:${NC}    http://127.0.0.1:8765"
echo -e "  ${BLUE}管理后端:${NC}  http://127.0.0.1:5001"
echo ""
echo -e "  ${YELLOW}停止服务:${NC}  bash stop-fastapi.sh"
echo -e "  ${YELLOW}查看日志:${NC}  tail -f $LOG_DIR/omnia-main.log"
echo ""
