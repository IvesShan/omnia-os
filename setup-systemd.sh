#!/bin/bash
# ============================================================
# 安装 Omnia systemd 服务
# 运行一次即可，之后用 systemctl 管理
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
SERVICE_FILE="$PROJECT_ROOT/omnia.service"
SYSTEMD_PATH="/etc/systemd/system/omnia.service"

echo -e "${YELLOW}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║        安装 Omnia systemd 服务                          ║${NC}"
echo -e "${YELLOW}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================
# 第一步：停止手动启动的旧进程
# ============================================================
echo -e "${BLUE}[1/4] 停止手动启动的旧进程...${NC}"

# 停止 start-fastapi.sh 启动的进程
if [ -f "$HOME/.omnia/omnia-main.pid" ]; then
    OLD_PID=$(cat "$HOME/.omnia/omnia-main.pid")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo -e "  → 停止旧主应用 (PID: $OLD_PID)"
        kill "$OLD_PID" 2>/dev/null || true
        sleep 1
    fi
    rm -f "$HOME/.omnia/omnia-main.pid"
fi

# 杀死所有残留的 uvicorn 进程
pids=$(pgrep -f "uvicorn.*src.omnia.main" 2>/dev/null || true)
if [ -n "$pids" ]; then
    echo -e "  → 清理残留 uvicorn 进程: $pids"
    echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 1
fi

echo -e "${GREEN}  ✓ 旧进程已清理${NC}"
echo ""

# ============================================================
# 第二步：创建日志目录
# ============================================================
echo -e "${BLUE}[2/4] 确保日志目录存在...${NC}"
mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$HOME/.omnia"
echo -e "${GREEN}  ✓ 日志目录就绪${NC}"
echo ""

# ============================================================
# 第三步：安装 systemd 服务文件
# ============================================================
echo -e "${BLUE}[3/4] 安装 systemd 服务文件...${NC}"

# 备份旧文件（如果存在）
if [ -f "$SYSTEMD_PATH" ]; then
    sudo cp "$SYSTEMD_PATH" "${SYSTEMD_PATH}.bak.$(date +%Y%m%d%H%M%S)"
    echo -e "  → 已备份旧服务文件"
fi

sudo cp "$SERVICE_FILE" "$SYSTEMD_PATH"
sudo systemctl daemon-reload
echo -e "${GREEN}  ✓ 服务文件已安装到 $SYSTEMD_PATH${NC}"
echo ""

# ============================================================
# 第四步：启动并设置开机自启
# ============================================================
echo -e "${BLUE}[4/4] 启动服务并设置开机自启...${NC}"

sudo systemctl enable omnia.service
sudo systemctl start omnia.service

sleep 2

# 检查状态
if systemctl is-active --quiet omnia.service; then
    echo -e "${GREEN}  ✓ Omnia 服务已启动${NC}"
else
    echo -e "${RED}  ✗ 服务启动失败，查看日志:${NC}"
    echo -e "    journalctl -u omnia.service -n 20 --no-pager"
    exit 1
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        安装完成!                                        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${YELLOW}常用命令:${NC}"
echo -e "    systemctl status omnia     # 查看状态"
echo -e "    systemctl restart omnia    # 重启"
echo -e "    systemctl stop omnia       # 停止"
echo -e "    journalctl -u omnia -f     # 实时日志"
echo ""
echo -e "  ${YELLOW}验证:${NC}"
echo -e "    curl -s http://127.0.0.1:8765/health"
echo ""
