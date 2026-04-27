#!/bin/bash
# ============================================================
#  Omnia 一键管理脚本
#  用法: ./scripts/manage.sh [命令]
#  或:   bash scripts/manage.sh [命令]
# ============================================================

set -e

OMNIA_HOME="$(cd "$(dirname "$0")/.." && pwd)"
SERVICES=("omnia" "omnia-daemon" "omnia-watchdog")
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ---------- 辅助函数 ----------
service_status() {
    local s=$1
    local active=$(systemctl --user is-active "$s" 2>/dev/null)
    local enabled=$(systemctl --user is-enabled "$s" 2>/dev/null)
    echo -e "${CYAN}$s${NC}"
    echo "  状态: $(status_color "$active")"
    echo "  开机: $(enabled_color "$enabled")"
    echo ""
}

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

# ---------- 命令 ----------
cmd_status() {
    print_banner
    echo "📊  Omnia 服务状态"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    for s in "${SERVICES[@]}"; do
        service_status "$s"
    done

    # 检查端口
    echo "🌐  端口监听"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if ss -tlnp 2>/dev/null | grep -q ":5001"; then
        echo -e "  Web 服务 (5001):  ${GREEN}✅ 监听中${NC}"
    else
        echo -e "  Web 服务 (5001):  ${RED}❌ 未监听${NC}"
    fi
    echo ""

    # 检查进程
    echo "🔄  进程健康"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if pgrep -f "web_server.py" > /dev/null 2>&1; then
        echo -e "  web_server.py:   ${GREEN}✅ 运行中${NC}"
    else
        echo -e "  web_server.py:   ${RED}❌ 未运行${NC}"
    fi
    if pgrep -f "_daemon_runner" > /dev/null 2>&1; then
        echo -e "  _daemon_runner:  ${GREEN}✅ 运行中${NC}"
    else
        echo -e "  _daemon_runner:  ${RED}❌ 未运行${NC}"
    fi
    if pgrep -f "watchdog.py" > /dev/null 2>&1; then
        echo -e "  watchdog:        ${GREEN}✅ 运行中${NC}"
    else
        echo -e "  watchdog:        ${RED}❌ 未运行${NC}"
    fi
    echo ""
}

cmd_start() {
    echo "▶️  启动所有 Omnia 服务..."
    for s in "${SERVICES[@]}"; do
        systemctl --user start "$s" 2>/dev/null && \
            echo -e "  ${GREEN}✅${NC} $s 已启动" || \
            echo -e "  ${YELLOW}⚠️${NC} $s 启动失败（可能已在运行）"
    done
    echo "⏳ 等待 3 秒确认状态..."
    sleep 3
    cmd_status
}

cmd_stop() {
    echo -e "${YELLOW}⏹️  正在停止所有 Omnia 服务...${NC}"
    # 按依赖顺序停止: watchdog -> daemon -> web
    systemctl --user stop omnia-watchdog 2>/dev/null && echo -e "  ${GREEN}✅${NC} omnia-watchdog 已停止" || true
    systemctl --user stop omnia-daemon 2>/dev/null && echo -e "  ${GREEN}✅${NC} omnia-daemon 已停止" || true
    systemctl --user stop omnia 2>/dev/null && echo -e "  ${GREEN}✅${NC} omnia (web) 已停止" || true
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
            journalctl --user -u omnia.service -f --no-hostname -o cat 2>/dev/null || \
                tail -f /tmp/omnia.log 2>/dev/null || \
                echo -e "${RED}❌ 无日志可用${NC}"
            ;;
        daemon)
            echo "📋 守护进程日志 (Ctrl+C 退出)..."
            tail -f "$OMNIA_HOME/logs/daemon.log" 2>/dev/null || \
                journalctl --user -u omnia-daemon.service -f --no-hostname 2>/dev/null || \
                echo -e "${RED}❌ 无日志可用${NC}"
            ;;
        watchdog)
            echo "📋 看门狗日志 (Ctrl+C 退出)..."
            journalctl --user -u omnia-watchdog.service -f --no-hostname -o cat 2>/dev/null || \
                echo -e "${RED}❌ 无日志可用${NC}"
            ;;
        *)
            echo -e "${RED}❌ 未知服务: $service${NC}"
            echo "  可用: web, daemon, watchdog"
            ;;
    esac
}

cmd_recent_logs() {
    echo "📋  最近 30 条日志（所有服务）"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    for s in "${SERVICES[@]}"; do
        echo -e "\n${CYAN}▶ $s${NC}"
        journalctl --user -u "$s.service" --no-hostname -o cat -n 10 2>/dev/null | \
            sed 's/^/  /' || echo "  (无日志)"
    done
}

cmd_help() {
    print_banner
    echo "用法: $(basename "$0") [命令]"
    echo ""
    echo "📌  常用命令"
    echo "  status        查看所有服务状态（默认）"
    echo "  start         启动所有服务"
    echo "  stop          停止所有服务"
    echo "  restart       重启所有服务"
    echo "  logs [服务]   实时查看日志 (web|daemon|watchdog)"
    echo "  logs-recent   查看最近日志摘要"
    echo "  help          显示此帮助"
    echo ""
    echo "📌  你也可以直接用:"
    echo "  systemctl --user status omnia"
    echo "  systemctl --user restart omnia-daemon"
    echo ""
}

# ---------- 入口 ----------
case "${1:-status}" in
    status|s)       cmd_status ;;
    start|up)       cmd_start ;;
    stop|down)      cmd_stop ;;
    restart|reload) cmd_restart ;;
    logs|l)         cmd_logs "$@" ;;
    logs-recent|lr) cmd_recent_logs ;;
    help|--help|-h) cmd_help ;;
    *)
        echo -e "${RED}❌ 未知命令: $1${NC}"
        cmd_help
        exit 1
        ;;
esac
