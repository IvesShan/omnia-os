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
    "uvicorn"
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

# 1.3 释放端口 5001（兼容 Linux + macOS）
echo -e "  → 释放端口 ${YELLOW}5001${NC}..."
if [ "$OS_TYPE" = "macos" ]; then
    # macOS: 使用 lsof
    lsof_pid=$(lsof -ti :5001 2>/dev/null || true)
    if [ -n "$lsof_pid" ]; then
        echo -e "  → 端口 5001 被 PID $lsof_pid 占用"
        kill -9 $lsof_pid 2>/dev/null || true
    fi
else
    # Linux: 使用 fuser
    fuser -k 5001/tcp 2>/dev/null || true
fi
sleep 1

# 1.4 额外清理：清除所有可能残留的 Python omnia 进程
echo -e "  → 最终清理..."
for pid in $(pgrep -f "python3.*omnia" 2>/dev/null || true); do
    kill "$pid" 2>/dev/null || true
done
sleep 0.5
for pid in $(pgrep -f "python3.*omnia" 2>/dev/null || true); do
    kill -9 "$pid" 2>/dev/null || true
done

sleep 1

# 验证端口 5001 是否释放
if command -v lsof &>/dev/null; then
    if lsof -i :5001 >/dev/null 2>&1; then
        echo -e "  ${RED}⚠ 端口 5001 仍有残留，强制释放...${NC}"
        if [ "$OS_TYPE" = "macos" ]; then
            kill -9 $(lsof -ti :5001) 2>/dev/null || true
        else
            fuser -k -9 5001/tcp 2>/dev/null || true
        fi
        sleep 1
    fi
fi

echo -e "${GREEN}  ✓ 所有进程已清除${NC}"
echo ""

# ============================================================
# 第二步：清理临时文件
# ============================================================
echo -e "${BLUE}[2/4] 清理临时文件...${NC}"

# 删除锁文件和运行时标记
rm -f "$OMNIA_HOME"/*.pid 2>/dev/null || true
rm -f "$PROJECT_ROOT"/.pids/*.pid 2>/dev/null || true

echo -e "${GREEN}  ✓ 临时文件已清理${NC}"
echo ""

# ============================================================
# 第三步：检查环境
# ============================================================
echo -e "${BLUE}[3/4] 检查运行环境...${NC}"

# 3.1 Python 检查
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON_CMD="$cmd"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}  ✗ 错误：未找到 Python 环境${NC}"
    exit 1
fi

PYTHON_VER=$($PYTHON_CMD --version 2>&1)
echo -e "  ✓ Python: ${GREEN}$PYTHON_VER${NC}"

# 3.2 虚拟环境检测
VENV_PYTHON=""
if [ -f "$PROJECT_ROOT/venv/bin/python3" ]; then
    # 检查 venv 是否为当前系统编译（跨平台兼容性检查）
    VENV_ARCH=$("$PROJECT_ROOT/venv/bin/python3" -c "import platform; print(platform.machine())" 2>/dev/null || echo "unknown")
    SYS_ARCH=$($PYTHON_CMD -c "import platform; print(platform.machine())" 2>/dev/null || echo "unknown")
    VENV_OS=$("$PROJECT_ROOT/venv/bin/python3" -c "import sys; print(sys.platform)" 2>/dev/null || echo "unknown")
    SYS_OS=$($PYTHON_CMD -c "import sys; print(sys.platform)" 2>/dev/null || echo "unknown")

    if [ "$VENV_ARCH" = "$SYS_ARCH" ] && [ "$VENV_OS" = "$SYS_OS" ]; then
        VENV_PYTHON="$PROJECT_ROOT/venv/bin/python3"
        echo -e "  ✓ 虚拟环境: ${GREEN}venv/bin/python3${NC} ($VENV_ARCH)"
    else
        echo -e "  ${YELLOW}⚠ venv 不兼容（源: $VENV_OS/$VENV_ARCH, 当前: $SYS_OS/$SYS_ARCH）${NC}"
        echo -e "  ${YELLOW}  需要重新创建虚拟环境：python3 -m venv venv && venv/bin/pip install -r requirements.txt${NC}"
        echo -e "  ${YELLOW}  临时使用系统 Python...${NC}"
    fi
elif [ -f "$PROJECT_ROOT/.venv/bin/python3" ]; then
    VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python3"
    echo -e "  ✓ 虚拟环境: ${GREEN}.venv/bin/python3${NC}"
else
    echo -e "  ${YELLOW}⚠ 未检测到虚拟环境，使用系统 Python${NC}"
fi

# 3.3 .env 检查
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo -e "  ✓ 配置文件: ${GREEN}.env${NC}"
else
    echo -e "  ${YELLOW}⚠ 未找到 .env 文件，部分功能可能受限${NC}"
fi

# 3.4 依赖检查
DEP_MISSING=false
$PYTHON_CMD -c "import flask" 2>/dev/null || DEP_MISSING=true
if [ "$DEP_MISSING" = true ]; then
    echo -e "  ${YELLOW}⚠ 缺少依赖，正在安装...${NC}"
    if [ -n "$VENV_PYTHON" ]; then
        "$VENV_PYTHON" -m pip install -r "$PROJECT_ROOT/requirements.txt" -q 2>/dev/null || true
    else
        $PYTHON_CMD -m pip install -r "$PROJECT_ROOT/requirements.txt" -q 2>/dev/null || true
    fi
    echo -e "${GREEN}  ✓ 依赖安装完成${NC}"
fi

echo ""

# ============================================================
# 第四步：启动所有服务
# ============================================================
echo -e "${BLUE}[4/4] 启动 Omnia 服务...${NC}"

# 确定使用哪个 Python
if [ -n "$VENV_PYTHON" ]; then
    USE_PYTHON="$VENV_PYTHON"
else
    USE_PYTHON="$PYTHON_CMD"
fi

PYTHON_USED=$($USE_PYTHON --version 2>&1)
echo -e "  ┌─ 使用: ${GREEN}$USE_PYTHON${NC} ($PYTHON_USED)"
echo ""

# 4.1 启动 Web Server（Flask，端口 5001）
echo -e "  ┌─ ${YELLOW}Web Server${NC} (http://localhost:5001)"
echo -e "  │  端口: 5001"
nohup "$USE_PYTHON" "$PROJECT_ROOT/src/omnia/web_server.py" \
    > "$OMNIA_HOME/web_server.log" 2>&1 &
WEB_PID=$!
echo "$WEB_PID" > "$OMNIA_HOME/web_server.pid"
echo -e "  │  PID: ${GREEN}$WEB_PID${NC}"
echo -e "  │  日志: $OMNIA_HOME/web_server.log"
echo -e "  └─ ${GREEN}✓ 已启动${NC}"

sleep 2

# 4.2 启动守护进程（Persona Daemon）
echo -e "  ┌─ ${YELLOW}守护进程${NC} (后台服务)"
echo -e "  │  功能: 上下文管理 + 记忆服务 + 心跳"
nohup "$USE_PYTHON" "$PROJECT_ROOT/scripts/start_daemon.py" \
    > "$OMNIA_HOME/daemon_start.log" 2>&1 &
sleep 2
if [ -f "$OMNIA_HOME/daemon.pid" ]; then
    DAEMON_PID=$(cat "$OMNIA_HOME/daemon.pid")
    echo -e "  │  PID: ${GREEN}$DAEMON_PID${NC}"
else
    echo -e "  │  ${YELLOW}⚠ daemon.pid 未生成，可能启动较慢${NC}"
fi
echo -e "  │  日志: $OMNIA_HOME/daemon.log"
echo -e "  └─ ${GREEN}✓ 已启动${NC}"

sleep 1

# 4.3 启动看门狗（Watchdog）
echo -e "  ┌─ ${YELLOW}看门狗${NC} (健康监控)"
echo -e "  │  功能: 自动检测进程状态，异常时重启"
nohup "$USE_PYTHON" "$PROJECT_ROOT/scripts/watchdog.py" \
    > "$OMNIA_HOME/watchdog_output.log" 2>&1 &
WATCHDOG_PID=$!
echo "$WATCHDOG_PID" > "$OMNIA_HOME/watchdog.pid"
echo -e "  │  PID: ${GREEN}$WATCHDOG_PID${NC}"
echo -e "  │  日志: $OMNIA_HOME/watchdog.log"
echo -e "  └─ ${GREEN}✓ 已启动${NC}"

# 等待 Web Server 就绪
echo ""
echo -e "${YELLOW}等待服务就绪...${NC}"
for i in $(seq 1 10); do
    if curl -s http://localhost:5001/health >/dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Web Server 响应正常${NC}"
        break
    fi
    sleep 1
done

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Omnia 重启完成！                           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BLUE}Web 管理界面:${NC}  http://localhost:5001"
echo -e "  ${BLUE}健康检查:${NC}      http://localhost:5001/health"
echo -e "  ${BLUE}API 状态:${NC}      http://localhost:5001/api/status"
echo ""
echo -e "  ${BLUE}进程列表:${NC}"
echo -e "    Web Server:   $(cat $OMNIA_HOME/web_server.pid 2>/dev/null || echo 'N/A')"
echo -e "    守护进程:     $(cat $OMNIA_HOME/daemon.pid 2>/dev/null || echo 'N/A')"
echo -e "    看门狗:       $(cat $OMNIA_HOME/watchdog.pid 2>/dev/null || echo 'N/A')"
echo ""
echo -e "  ${BLUE}日志文件:${NC}"
echo -e "    Web:          $OMNIA_HOME/web_server.log"
echo -e "    守护进程:     $OMNIA_HOME/daemon.log"
echo -e "    看门狗:       $OMNIA_HOME/watchdog.log"
echo ""

# 如果服务未就绪，给出提示
if ! curl -s http://localhost:5001/health >/dev/null 2>&1; then
    echo -e "${YELLOW}  ⚠ 服务仍在启动中，请稍后刷新页面...${NC}"
    echo -e "  ${YELLOW}  查看启动日志: tail -f $OMNIA_HOME/web_server.log${NC}"
fi
echo ""
