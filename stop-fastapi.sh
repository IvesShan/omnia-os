#!/bin/bash
# ============================================================
# Omnia FastAPI 版本停止脚本
# 停止主应用 + 管理后端 + MCP 子进程
# ============================================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
OMNIA_HOME="$HOME/.omnia"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           Omnia FastAPI 版本停止脚本                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================
# 第一步：通过 PID 文件停止服务
# ============================================================
echo -e "${BLUE}[1/3] 通过 PID 文件停止服务...${NC}"

PID_DIR="$OMNIA_HOME"
MAIN_PID_FILE="$PID_DIR/omnia-main.pid"
BACKEND_PID_FILE="$PID_DIR/omnia-backend.pid"

# 停止主应用
if [ -f "$MAIN_PID_FILE" ]; then
    main_pid=$(cat "$MAIN_PID_FILE")
    if kill -0 "$main_pid" 2>/dev/null; then
        echo -e "  → 停止主应用 (PID: ${YELLOW}$main_pid${NC})"
        kill -15 "$main_pid" 2>/dev/null || true
        sleep 1
        # 强制终止（如果仍然存在）
        if kill -0 "$main_pid" 2>/dev/null; then
            echo -e "  → 强制终止主应用 (PID: ${YELLOW}$main_pid${NC})"
            kill -9 "$main_pid" 2>/dev/null || true
        fi
    fi
    rm -f "$MAIN_PID_FILE"
fi

# 停止管理后端
if [ -f "$BACKEND_PID_FILE" ]; then
    backend_pid=$(cat "$BACKEND_PID_FILE")
    if kill -0 "$backend_pid" 2>/dev/null; then
        echo -e "  → 停止管理后端 (PID: ${YELLOW}$backend_pid${NC})"
        kill -15 "$backend_pid" 2>/dev/null || true
        sleep 1
        if kill -0 "$backend_pid" 2>/dev/null; then
            echo -e "  → 强制终止管理后端 (PID: ${YELLOW}$backend_pid${NC})"
            kill -9 "$backend_pid" 2>/dev/null || true
        fi
    fi
    rm -f "$BACKEND_PID_FILE"
fi

echo -e "${GREEN}  ✓ PID 文件处理完成${NC}"
echo ""

# ============================================================
# 第二步：按模式匹配清除残留进程
# ============================================================
echo -e "${BLUE}[2/3] 按模式匹配清除残留进程...${NC}"

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
        echo -e "  → 匹配模式 '${YELLOW}$pattern${NC}': PID(s) $pids"
        pkill -9 -f "$pattern" 2>/dev/null || true
        sleep 0.3
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

# ============================================================
# 第三步：清理 MCP 子进程（防止孤儿进程导致 stdio 管道竞争）
# ============================================================
echo -e "${BLUE}[3/3] 清理 MCP 子进程...${NC}"

MCP_PATTERNS=(
    "server-filesystem"
    "server-puppeteer"
    "mcp-server-git"
    "mcp-server-fetch"
    "mcp-server-python"
)

for pattern in "${MCP_PATTERNS[@]}"; do
    pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo -e "  → 清理 MCP ${YELLOW}$pattern${NC}: PID(s) $pids"
        pkill -9 -f "$pattern" 2>/dev/null || true
    fi
done

# 清理残留的 Node.js MCP 进程
node_mcp_pids=$(pgrep -af "node.*mcp" 2>/dev/null | grep -v "grep" | awk '{print $1}' || true)
if [ -n "$node_mcp_pids" ]; then
    echo -e "  → 清理残留 Node.js MCP 进程"
    echo "$node_mcp_pids" | xargs kill -9 2>/dev/null || true
fi

# 清理 uv tool 启动的 MCP 进程
uv_mcp_pids=$(pgrep -af "uv tool uvx mcp" 2>/dev/null | grep -v "grep" | awk '{print $1}' || true)
if [ -n "$uv_mcp_pids" ]; then
    echo -e "  → 清理残留 uv MCP 进程"
    echo "$uv_mcp_pids" | xargs kill -9 2>/dev/null || true
fi

echo -e "${GREEN}  ✓ MCP 进程清理完成${NC}"
echo ""

echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Omnia FastAPI 版本已停止                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
