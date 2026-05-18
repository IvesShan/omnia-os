#!/bin/bash
# ============================================================
# Omnia 一键重启脚本
# 功能：关闭所有后台服务 → 清理 → 重新启动
# 兼容：Linux + macOS
# 在部署出问题时运行：bash omnia-restart.sh
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

# 检测操作系统
OS_TYPE="linux"
if [[ "$(uname)" == "Darwin" ]]; then
    OS_TYPE="macos"
fi

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           Omnia 一键重启脚本                           ║${NC}"
echo -e "${BLUE}║           关闭 → 清理 → 重启                           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}项目目录:${NC} $PROJECT_ROOT"
echo -e "${YELLOW}数据目录:${NC} $OMNIA_HOME"
echo -e "${YELLOW}系统:${NC}     $OS_TYPE"
echo ""

# ============================================================
# 确保数据目录存在
# ============================================================
mkdir -p "$OMNIA_HOME"

# ============================================================
# 第一步：杀死所有 Omnia 相关进程
# ============================================================
echo -e "${BLUE}[1/4] 杀死所有 Omnia 后台进程...${NC}"

# 1.1 通过 PID 文件杀死（精确杀进程）
PID_FILES=(
    "$OMNIA_HOME/daemon.pid"
    "$OMNIA_HOME/web_server.pid"
    "$OMNIA_HOME/fastapi_server.pid"
    "$OMNIA_HOME/watchdog.pid"
    "$PROJECT_ROOT/.pids/daemon.pid"
)

for pid_file in "${PID_FILES[@]}"; do
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file" 2>/dev/null | tr -d ' \n')
        if [ -n "$pid" ] && [ "$pid" -gt 0 ] 2>/dev/null; then
            echo -e "  → 杀死 PID ${YELLOW}$pid${NC} (来自 $pid_file)"
            kill "$pid" 2>/dev/null || true
            sleep 0.5
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$pid_file"
    fi
done

# 1.2 通过进程名模式匹配杀死（兜底）
echo -e "  → 按模式匹配清除残留进程..."

KILL_PATTERNS=(
    "web_server.py"
    "_daemon_runner.py"
    "start_daemon.py"
    "watchdog.py"
    "omnia/web_server"
    "src.backend.main"
    "uvicorn.*src.omnia.main"
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

# 1.3 释放端口 8765（兼容 Linux + macOS）
echo -e "  → 释放端口 ${YELLOW}8765${NC}..."
if [ "$OS_TYPE" = "macos" ]; then
    # macOS: 使用 lsof
    lsof_pid=$(lsof -ti :8765 2>/dev/null || true)
    if [ -n "$lsof_pid" ]; then
        echo -e "  → 端口 8765 被 PID $lsof_pid 占用"
        kill -9 $lsof_pid 2>/dev/null || true
    fi
else
    # Linux: 使用 fuser
    fuser -k 8765/tcp 2>/dev/null || true
fi

# 等待进程完全退出
sleep 1

# 验证端口 8765 是否释放
if [ "$OS_TYPE" = "macos" ]; then
    if lsof -i :8765 >/dev/null 2>&1; then
        echo -e "  ${RED}⚠ 端口 8765 仍有残留，强制释放...${NC}"
        kill -9 $(lsof -ti :8765) 2>/dev/null || true
    else
        echo -e "  ✓ 端口 8765 已释放"
    fi
else
    if ss -tlnp | grep -q ":8765 " 2>/dev/null; then
        echo -e "  ${RED}⚠ 端口 8765 仍有残留，强制释放...${NC}"
        fuser -k -9 8765/tcp 2>/dev/null || true
    else
        echo -e "  ✓ 端口 8765 已释放"
    fi
fi

echo -e "  ${GREEN}✓ 进程清理完成${NC}"
echo ""

# ============================================================
# 第二步：清理临时文件
# ============================================================
echo -e "${BLUE}[2/4] 清理临时文件...${NC}"

# 清理 __pycache__
find "$PROJECT_ROOT/src" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo -e "  ✓ 已清理 __pycache__"

# 清理 .pyc 文件
find "$PROJECT_ROOT/src" -type f -name "*.pyc" -delete 2>/dev/null || true
echo -e "  ✓ 已清理 .pyc 文件"

echo -e "  ${GREEN}✓ 清理完成${NC}"
echo ""

# ============================================================
# 第三步：检查依赖
# ============================================================
echo -e "${BLUE}[3/4] 检查 Python 环境...${NC}"

# 检测 Python 版本
USE_PYTHON=""
if command -v python3 &>/dev/null; then
    USE_PYTHON="python3"
elif command -v python &>/dev/null; then
    USE_PYTHON="python"
else
    echo -e "  ${RED}✗ 未找到 Python，请先安装 Python 3.8+${NC}"
    exit 1
fi

PY_VERSION=$($USE_PYTHON --version 2>&1 | grep -oP '\d+\.\d+')
echo -e "  → Python: ${GREEN}$USE_PYTHON ($PY_VERSION)${NC}"

# 检测 uvicorn
if ! $USE_PYTHON -c "import uvicorn" 2>/dev/null; then
    echo -e "  ${YELLOW}⚠ uvicorn 未安装，正在安装...${NC}"
    $USE_PYTHON -m pip install uvicorn[standard] fastapi pydantic-settings sse-starlette httpx -q
fi
echo -e "  → uvicorn: ${GREEN}✓${NC}"

# 检测 httpx
if ! $USE_PYTHON -c "import httpx" 2>/dev/null; then
    echo -e "  ${YELLOW}⚠ httpx 未安装，正在安装...${NC}"
    $USE_PYTHON -m pip install httpx -q
fi
echo -e "  → httpx: ${GREEN}✓${NC}"

# 检查 .env 文件
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "  ${YELLOW}⚠ 未找到 .env 文件，请确保已配置 API Keys${NC}"
else
    echo -e "  → .env: ${GREEN}✓${NC}"
fi

echo ""

# ============================================================
# 第四步：启动所有服务
# ============================================================
echo -e "${BLUE}[4/4] 启动 Omnia 服务...${NC}"
echo ""

# 4.1 启动 FastAPI Server（端口 8765）
echo -e "  ┌─ ${YELLOW}FastAPI Server${NC} (http://localhost:8765)"
echo -e "  │  端口: 8765"
cd "$PROJECT_ROOT"
nohup $USE_PYTHON -m uvicorn src.omnia.main:app \
    --host 0.0.0.0 \
    --port 8765 \
    --reload \
    > "$OMNIA_HOME/fastapi_server.log" 2>&1 &
FASTAPI_PID=$!
echo "$FASTAPI_PID" > "$OMNIA_HOME/fastapi_server.pid"
echo -e "  │  PID: ${GREEN}$FASTAPI_PID${NC}"
echo -e "  │  日志: $OMNIA_HOME/fastapi_server.log"
echo -e "  └─ ${GREEN}✓ 已启动${NC}"
echo ""

# 等待 FastAPI Server 就绪
echo -e "${YELLOW}等待服务就绪...${NC}"
for i in $(seq 1 15); do
    if curl -s http://localhost:8765/health >/dev/null 2>&1; then
        echo -e "${GREEN}  ✓ FastAPI Server 响应正常${NC}"
        break
    fi
    sleep 1
done

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Omnia 重启完成！                           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BLUE}FastAPI Server:${NC}  http://localhost:8765"
echo -e "  ${BLUE}健康检查:${NC}      http://localhost:8765/health"
echo -e "  ${BLUE}API 文档:${NC}      http://localhost:8765/docs"
echo ""
echo -e "  ${BLUE}进程列表:${NC}"
echo -e "    FastAPI Server: $(cat $OMNIA_HOME/fastapi_server.pid 2>/dev/null || echo 'N/A')"
echo ""
echo -e "  ${BLUE}日志文件:${NC}"
echo -e "    FastAPI:       $OMNIA_HOME/fastapi_server.log"
echo ""

# 如果服务未就绪，给出提示
if ! curl -s http://localhost:8765/health >/dev/null 2>&1; then
    echo -e "${YELLOW}  ⚠ 服务仍在启动中，请稍后刷新页面...${NC}"
    echo -e "  ${YELLOW}  查看启动日志: tail -f $OMNIA_HOME/fastapi_server.log${NC}"
fi
echo ""
