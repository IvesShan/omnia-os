#!/bin/bash
# Omnia 一键启动脚本
# 同时启动守护进程、Web Server 和 Watchdog

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OMNIA_HOME="$HOME/.omnia"

echo "========================================"
echo "🚀 Omnia 启动中..."
echo "========================================"

# 创建必要目录
mkdir -p "$OMNIA_HOME"

# 1. 启动守护进程
echo ""
echo "📦 启动守护进程..."
python3 "$SCRIPT_DIR/start_daemon.py"

# 2. 启动 Web Server（如果未运行）
WEB_PID_FILE="$OMNIA_HOME/web_server.pid"
if [ -f "$WEB_PID_FILE" ]; then
    OLD_PID=$(cat "$WEB_PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "✅ Web Server 已运行 (PID: $OLD_PID)"
    else
        rm -f "$WEB_PID_FILE"
        echo "⚠️ 清理过期 PID 文件"
    fi
fi

if [ ! -f "$WEB_PID_FILE" ]; then
    echo "🌐 启动 Web Server..."
    nohup python3 "$PROJECT_ROOT/src/omnia/web_server.py" > "$OMNIA_HOME/web_server.log" 2>&1 &
    WEB_PID=$!
    echo $WEB_PID > "$WEB_PID_FILE"
    sleep 2
    echo "✅ Web Server 已启动 (PID: $WEB_PID)"
fi

# 3. 启动 Watchdog（后台运行）
WATCHDOG_PID_FILE="$OMNIA_HOME/watchdog.pid"
if [ -f "$WATCHDOG_PID_FILE" ]; then
    OLD_PID=$(cat "$WATCHDOG_PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "✅ Watchdog 已运行 (PID: $OLD_PID)"
    else
        rm -f "$WATCHDOG_PID_FILE"
    fi
fi

if [ ! -f "$WATCHDOG_PID_FILE" ]; then
    echo "🐕 启动 Watchdog..."
    nohup python3 "$SCRIPT_DIR/watchdog.py" > "$OMNIA_HOME/watchdog_output.log" 2>&1 &
    WATCHDOG_PID=$!
    echo $WATCHDOG_PID > "$WATCHDOG_PID_FILE"
    sleep 1
    echo "✅ Watchdog 已启动 (PID: $WATCHDOG_PID)"
fi

echo ""
echo "========================================"
echo "✅ Omnia 全部启动完成！"
echo "========================================"
echo ""
echo "📊 状态："
echo "  - 守护进程: $(cat $OMNIA_HOME/daemon.pid 2>/dev/null || echo '未知')"
echo "  - Web Server: $(cat $OMNIA_HOME/web_server.pid 2>/dev/null || echo '未知')"
echo "  - Watchdog: $(cat $OMNIA_HOME/watchdog.pid 2>/dev/null || echo '未知')"
echo ""
echo "🌐 访问: http://localhost:5200"
echo "📝 日志目录: $OMNIA_HOME"
echo ""
