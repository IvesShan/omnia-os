#!/bin/bash
# ============================================================
# Omnia FastAPI 版本停止脚本
# ============================================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

OMNIA_HOME="$HOME/.omnia"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           Omnia FastAPI 版本停止脚本                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================
# 第一步：通过 PID 文件停止
# ============================================================
echo -e "${BLUE}[1/2] 通过 PID 文件停止服务...${NC}"

PID_FILES=(
    "$OMNIA_HOME/omnia-main.pid"
    "$OMNIA_HOME/omnia-backend.pid"
)

for pid_file in "${PID_FILES[@]}"; do
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file" 2>/dev/null | tr -d ' \n')
        if [ -n "$pid" ] && [ "$pid" -gt 0 ] 2>/dev/null; then
            echo -e "  → 停止 PID ${YELLOW}$pid${NC} (来自 $pid_file)"
            kill "$pid" 2>/dev/null || true
            sleep 0.5
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$pid_file"
    fi
done

echo -e "${GREEN}  ✓ PID 文件处理完成${NC}"
echo ""

# ============================================================
# 第二步：按进程名模式匹配停止（兜底）
# ============================================================
echo -e "${BLUE}[2/2] 按模式匹配清除残留进程...${NC}"

KILL_PATTERNS=(
    "src.omnia.main"
    "src.backend.main"
    "uvicorn.*8765"
    "uvicorn.*5001"
)

for pattern in "${KILL_PATTERNS[@]}"; do
    pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo -e "  → 匹配模式 '${YELLOW}$pattern${NC}': PID(s) $pids"
        pkill -f "$pattern" 2>/dev/null || true
        sleep 0.3
        pkill -9 -f "$pattern" 2>/dev/null || true
    fi
done

# 释放端口 8765 和 5001
echo -e "  → 释放端口 ${YELLOW}8765${NC} 和 ${YELLOW}5001${NC}..."
for port in 8765 5001; do
    lsof_pid=$(lsof -ti :$port 2>/dev/null || true)
    if [ -n "$lsof_pid" ]; then
        echo -e "    端口 $port 被 PID $lsof_pid 占用"
        kill -9 $lsof_pid 2>/dev/null || true
    fi
done

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Omnia FastAPI 版本已停止                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
