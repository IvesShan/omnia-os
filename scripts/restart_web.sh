#!/bin/bash
# 重启 Omnia Web Server

set -e

PROJECT_ROOT="/home/shan/omnia-os"
PID_FILE="$PROJECT_ROOT/.omnia/web_server.pid"
LOG_FILE="$PROJECT_ROOT/.omnia/web_server.log"

echo "🔄 Restarting Omnia Web Server..."

# 检查当前进程
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "  Stopping old process (PID: $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null || true
        sleep 2
        
        # 强制杀死
        if ps -p "$OLD_PID" > /dev/null 2>&1; then
            echo "  Force killing..."
            kill -9 "$OLD_PID" 2>/dev/null || true
            sleep 1
        fi
    fi
    rm -f "$PID_FILE"
fi

# 启动新进程
echo "  Starting new process..."
cd "$PROJECT_ROOT"

nohup python3 src/omnia/web_server.py > "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo $NEW_PID > "$PID_FILE"

echo "  ✅ Started (PID: $NEW_PID)"
echo ""

# 等待启动
echo "  Waiting for server to be ready..."
sleep 3

# 检查健康状态
if curl -s http://localhost:5001/api/status > /dev/null 2>&1; then
    echo "  ✅ Server is healthy"
else
    echo "  ⚠️  Server may not be ready yet, check logs:"
    echo "      tail -50 $LOG_FILE"
fi

echo ""
echo "📊 Logs: $LOG_FILE"
echo "🌐 URL: http://localhost:5001"
