#!/bin/bash
# Omnia 一键启动脚本（FastAPI 版本）
# 启动 FastAPI Server（端口 8765）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OMNIA_HOME="$HOME/.omnia"

echo "========================================"
echo "🚀 Omnia FastAPI 启动中..."
echo "========================================"

# 创建必要目录
mkdir -p "$OMNIA_HOME"

# 启动 FastAPI Server（如果未运行）
FASTAPI_PID_FILE="$OMNIA_HOME/fastapi.pid"
if [ -f "$FASTAPI_PID_FILE" ]; then
    OLD_PID=$(cat "$FASTAPI_PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "✅ FastAPI Server 已运行 (PID: $OLD_PID)"
    else
        rm -f "$FASTAPI_PID_FILE"
        echo "⚠️  清理过期 PID 文件"
    fi
fi

if [ ! -f "$FASTAPI_PID_FILE" ]; then
    echo "🌐 启动 FastAPI Server..."
    cd "$PROJECT_ROOT"
    nohup python3 -m uvicorn src.omnia.main:app --host 0.0.0.0 --port 8765 > "$OMNIA_HOME/fastapi.log" 2>&1 &
    FASTAPI_PID=$!
    echo $FASTAPI_PID > "$FASTAPI_PID_FILE"
    sleep 3
    echo "✅ FastAPI Server 已启动 (PID: $FASTAPI_PID)"
fi

echo ""
echo "========================================"
echo "✅ Omnia FastAPI 启动完成！"
echo "========================================"
echo ""
echo "📊 状态："
echo "  - FastAPI Server: $(cat $OMNIA_HOME/fastapi.pid 2>/dev/null || echo '未知')"
echo ""
echo "🌐 访问: http://localhost:8765"
echo "📖 API 文档: http://localhost:8765/docs"
echo "📝 日志: $OMNIA_HOME/fastapi.log"
echo ""
