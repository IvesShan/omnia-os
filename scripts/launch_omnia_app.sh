#!/bin/bash
# Omnia 应用启动脚本
# 自动启动后端服务，然后启动 Tauri 应用

set -e

OMNIA_DIR="/home/shan/.openclaw/workspace/omnia-os"
LOG_DIR="$OMNIA_DIR/logs"
PID_DIR="$OMNIA_DIR/.pids"

# 创建必要的目录
mkdir -p "$LOG_DIR" "$PID_DIR"

echo "=== 启动 Omnia ==="
echo ""

# 1. 启动 Persona Daemon（如果未运行）
if pgrep -f "start_daemon.py" > /dev/null; then
    echo "✓ Persona Daemon 已在运行"
else
    echo "启动 Persona Daemon..."
    cd "$OMNIA_DIR"
    nohup python3 scripts/start_daemon.py > "$LOG_DIR/daemon.log" 2>&1 &
    echo $! > "$PID_DIR/daemon.pid"
    sleep 2
    echo "✓ Persona Daemon 已启动 (PID: $(cat $PID_DIR/daemon.pid))"
fi

# 2. 启动 Web Server（如果未运行）
if pgrep -f "web_server.py" > /dev/null; then
    echo "✓ Web Server 已在运行"
else
    echo "启动 Web Server..."
    cd "$OMNIA_DIR"
    nohup python3 src/omnia/web_server.py > "$LOG_DIR/webserver.log" 2>&1 &
    echo $! > "$PID_DIR/webserver.pid"
    sleep 2
    echo "✓ Web Server 已启动 (PID: $(cat $PID_DIR/webserver.pid))"
fi

echo ""
echo "后端服务已就绪！"
echo ""

# 3. 启动 Tauri 应用
TAURI_APP="$OMNIA_DIR/src-tauri/target/release/omnia-desktop"

if [ -f "$TAURI_APP" ]; then
    echo "启动 Omnia 应用..."
    exec "$TAURI_APP"
else
    echo "⚠ Tauri 应用尚未构建完成"
    echo "运行以下命令构建："
    echo "  cd $OMNIA_DIR && npm run tauri build"
    exit 1
fi
