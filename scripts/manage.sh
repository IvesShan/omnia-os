#!/usr/bin/env bash
# ============================================================
#  Omnia 一键管理脚本 — 跨平台 (Linux/macOS)
#  用法: bash scripts/manage.sh [命令]
# ============================================================

set -e

OMNIA_HOME="$(cd "$(dirname "$0")/.." && pwd)"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ----- 检测操作系统 -----
OS_TYPE=""
case "$(uname)" in
    Linux)  OS_TYPE="linux"  ;;
    Darwin) OS_TYPE="macos"  ;;
    *)
        echo -e "${RED}❌ 不支持的操作系统: $(uname)${NC}"
        exit 1
        ;;
esac

# ----- launchd 标签（macOS）-----
LAUNCH_LABELS=("com.omnia.web" "com.omnia.daemon" "com.omnia.watchdog")
LAUNCH_NAMES=("omnia (web)" "omnia-daemon" "omnia-watchdog")

# ----- systemd 服务名（Linux）-----
SYSTEMD_SERVICES=("omnia" "omnia-daemon" "omnia-watchdog")

# ---------- 辅助函数 ----------
status_color() {
    case "$1" in
        active|running)   echo -e "${GREEN}✅ $1${NC}" ;;
        inactive|dead)    echo -e "${RED}❌ $1${NC}" ;;
        failed)           echo -e "${RED}💀 $1 (失败)${NC}" ;;
        *)                echo -e "${YELLOW}⚠️  $1${NC}" ;;
    esac
}

enabled_color() {
    case "$1" in
        enabled)  echo -e "${GREEN}✅ 是${NC}" ;;
        disabled) echo -e "${RED}❌ 否${NC}" ;;
        *)        echo -e "${YELLOW}⚠️  $1${NC}" ;;
    esac
}

print_banner() {
    echo ""
    echo "  ██████╗ ███╗   ███╗███╗   ██╗██╗ █████╗ "
    echo " ██╔═══██╗████╗ ████║████╗  ██║██║██╔══██╗"
    echo " ██║   ██║██╔████╔██║██╔██╗ ██║██║███████║"
    echo " ██║   ██║██║╚██╔╝██║██║╚██╗██║██║██╔══██║"
    echo " ╚██████╔╝██║ ╚═╝ ██║██║ ╚████║██║██║  ██║"
    echo "  ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝"
    echo "  管理脚本  |  $(basename "$0") [命令]"
    echo ""
}

# ---------- Linux: systemd 实现 ----------
linux_service_status() {
    local s=$1
    local active=$(systemctl --user is-active "$s" 2>/dev/null || echo "unknown")
    local enabled=$(systemctl --user is-enabled "$s" 2>/dev/null || echo "unknown")
    echo -e "${CYAN}$s${NC}"
    echo "  状态: $(status_color "$active")"
    echo "  开机: $(enabled_color "$enabled")"
    echo ""
}

linux_check_port() {
    if ss -tlnp 2>/dev/null | grep -q ":5001"; then
        echo -e "  Web 服务 (5001):  ${GREEN}✅ 监听中${NC}"
    else
        echo -e "  Web 服务 (5001):  ${RED}❌ 未监听${NC}"
    fi
}

# ---------- macOS: launchd 实现 ----------
macos_service_status() {
    local i=$1
    local label="${LAUNCH_LABELS[$i]}"
    local name="${LAUNCH_NAMES[$i]}"
    local out
    out=$(launchctl list "$label" 2>/dev/null || echo "NOT_LOADED")
    
    echo -e "${CYAN}$name${NC}"
    if [ "$out" = "NOT_LOADED" ]; then
        echo -e "  状态: ${RED}❌ 未加载${NC}"
        echo -e "  开机: ${YELLOW}⚠️  否${NC}"
    else
        local pid=$(echo "$out" | awk 'NR==2{print $1}')
        local last_exit=$(echo "$out" | awk 'NR==2{print $2}')
        if [ "$pid" = "-1" ]; then
            echo -e "  状态: ${RED}❌ 已退出 (exit=$last_exit)${NC}"
            echo -e "  开机: ${GREEN}✅ 是（将自动重启）${NC}"
        else
            echo -e "  状态: ${GREEN}✅ 运行中 (PID: $pid)${NC}"
            echo -e "  开机: ${GREEN}✅ 是${NC}"
        fi
    fi
    echo ""
}

macos_check_port() {
    if lsof -i :5001 -P -n 2>/dev/null | grep -q LISTEN; then
        echo -e "  Web 服务 (5001):  ${GREEN}✅ 监听中${NC}"
    else
        echo -e "  Web 服务 (5001):  ${RED}❌ 未监听${NC}"
    fi
}

# ---------- 进程检查（通用）----------
check_processes() {
    echo "🔄  进程健康"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    for proc in "web_server.py" "_daemon_runner" "watchdog.py"; do
        if pgrep -f "$proc" > /dev/null 2>&1; then
            echo -e "  $proc:  ${GREEN}✅ 运行中${NC}"
        else
            echo -e "  $proc:  ${RED}❌ 未运行${NC}"
        fi
    done
    echo ""
}

# ---------- 命令 ----------
cmd_status() {
    print_banner
    echo "📊  Omnia 服务状态"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo -e "系统: ${CYAN}$OS_TYPE${NC}"
    echo ""

    if [ "$OS_TYPE" = "linux" ]; then
        for s in "${SYSTEMD_SERVICES[@]}"; do
            linux_service_status "$s"
        done
    else
        for i in "${!LAUNCH_LABELS[@]}"; do
            macos_service_status "$i"
        done
    fi

    echo "🌐  端口监听"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if [ "$OS_TYPE" = "linux" ]; then
        linux_check_port
    else
        macos_check_port
    fi
    echo ""

    check_processes
}

cmd_start() {
    echo "▶️  启动所有 Omnia 服务..."
    if [ "$OS_TYPE" = "linux" ]; then
        for s in "${SYSTEMD_SERVICES[@]}"; do
            systemctl --user start "$s" 2>/dev/null && \
                echo -e "  ${GREEN}✅${NC} $s 已启动" || \
                echo -e "  ${YELLOW}⚠️${NC} $s 启动失败（可能已在运行）"
        done
    else
        for label in "${LAUNCH_LABELS[@]}"; do
            launchctl load "$HOME/Library/LaunchAgents/$label.plist" 2>/dev/null && \
                echo -e "  ${GREEN}✅${NC} $label 已启动" || \
                echo -e "  ${YELLOW}⚠️${NC} $label 启动失败（可能已在运行）"
        done
    fi
    echo "⏳ 等待 3 秒确认状态..."
    sleep 3
    cmd_status
}

cmd_stop() {
    echo -e "${YELLOW}⏹️  正在停止所有 Omnia 服务...${NC}"
    if [ "$OS_TYPE" = "linux" ]; then
        systemctl --user stop omnia-watchdog 2>/dev/null && echo -e "  ${GREEN}✅${NC} omnia-watchdog 已停止" || true
        systemctl --user stop omnia-daemon 2>/dev/null && echo -e "  ${GREEN}✅${NC} omnia-daemon 已停止" || true
        systemctl --user stop omnia 2>/dev/null && echo -e "  ${GREEN}✅${NC} omnia (web) 已停止" || true
    else
        # 反向顺序停止：watchdog → daemon → web
        for label in "com.omnia.watchdog" "com.omnia.daemon" "com.omnia.web"; do
            launchctl unload "$HOME/Library/LaunchAgents/$label.plist" 2>/dev/null && \
                echo -e "  ${GREEN}✅${NC} $label 已停止" || true
        done
    fi
    echo -e "${GREEN}✅ 所有服务已停止${NC}"
}

cmd_restart() {
    echo -e "${YELLOW}🔄  重启所有 Omnia 服务...${NC}"
    cmd_stop
    sleep 2
    cmd_start
}

cmd_logs() {
    local service="${2:-all}"
    case "$service" in
        web|omnia|"")
            echo "📋 Web 服务日志 (Ctrl+C 退出)..."
            if [ "$OS_TYPE" = "linux" ]; then
                journalctl --user -u omnia.service -f --no-hostname -o cat 2>/dev/null || \
                    tail -f "$OMNIA_HOME/logs/web_server.log" 2>/dev/null || \
                    echo -e "${RED}❌ 无日志可用${NC}"
            else
                tail -f "$OMNIA_HOME/logs/web_server.log" 2>/dev/null || \
                    echo -e "${RED}❌ 无日志可用${NC}"
            fi
            ;;
        daemon)
            echo "📋 守护进程日志 (Ctrl+C 退出)..."
            tail -f "$OMNIA_HOME/logs/daemon.log" 2>/dev/null || \
                echo -e "${RED}❌ 无日志可用${NC}"
            ;;
        watchdog)
            echo "📋 看门狗日志 (Ctrl+C 退出)..."
            tail -f "$OMNIA_HOME/logs/watchdog.log" 2>/dev/null || \
                echo -e "${RED}❌ 无日志可用${NC}"
            ;;
        *)
            echo -e "${RED}❌ 未知服务: $service${NC}"
            echo "  可用: web, daemon, watchdog"
            ;;
    esac
}

cmd_recent_logs() {
    echo "📋  最近日志摘要"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    for logfile in "$OMNIA_HOME/logs/"*.log; do
        if [ -f "$logfile" ]; then
            local name=$(basename "$logfile")
            echo -e "\n${CYAN}▶ $name${NC}"
            tail -n 10 "$logfile" 2>/dev/null | sed 's/^/  /' || echo "  (空)"
        fi
    done
}

# ---------- 日志轮转命令 ----------
cmd_logs_rotate() {
    echo "🔄 轮转日志文件..."
    python3 "$OMNIA_HOME/scripts/log_rotator.py" --force
}

cmd_logs_clean() {
    echo "🧹 清理过期日志..."
    python3 "$OMNIA_HOME/scripts/log_rotator.py" --clean
}

cmd_logs_status() {
    python3 "$OMNIA_HOME/scripts/log_rotator.py" --status
}

cmd_help() {
    print_banner
    echo "用法: $(basename "$0") [命令]"
    echo ""
    echo "📌  常用命令"
    echo "  status          查看所有服务状态（默认）"
    echo "  start           启动所有服务"
    echo "  stop            停止所有服务"
    echo "  restart         重启所有服务"
    echo "  logs [服务]     实时查看日志 (web|daemon|watchdog)"
    echo "  logs-recent     查看最近日志摘要"
    echo ""
    echo "📌  日志管理"
    echo "  logs-status     查看日志文件状态和大小"
    echo "  logs-rotate     手动轮转日志文件"
    echo "  logs-clean      清理过期日志文件"
    echo ""
    echo "📌  平台命令对照"
    if [ "$OS_TYPE" = "linux" ]; then
        echo "  systemctl --user status omnia       查看单个服务"
        echo "  journalctl --user -u omnia -f       查看 Web 日志"
    else
        echo "  launchctl list com.omnia.web        查看单个服务"
        echo "  tail -f logs/web_server.log         查看 Web 日志"
    fi
    echo ""
}

# ---------- 入口 ----------
case "${1:-status}" in
    status|s)         cmd_status ;;
    start|up)         cmd_start ;;
    stop|down)        cmd_stop ;;
    restart|reload)   cmd_restart ;;
    logs|l)           cmd_logs "$@" ;;
    logs-recent|lr)   cmd_recent_logs ;;
    logs-status)      cmd_logs_status ;;
    logs-rotate)      cmd_logs_rotate ;;
    logs-clean)       cmd_logs_clean ;;
    help|--help|-h)   cmd_help ;;
    *)
        echo -e "${RED}❌ 未知命令: $1${NC}"
        cmd_help
        exit 1
        ;;
esac
