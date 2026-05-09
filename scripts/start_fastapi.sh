#!/bin/bash
# Omnia FastAPI 启动脚本
# 使用冷门端口 8765，避免冲突

cd /home/shan/omnia-os

# 检查是否已运行
if pgrep -f "uvicorn.*8765" > /dev/null; then
    echo "⚠️  FastAPI 已在运行 (端口 8765)"
    echo "   停止命令: pkill -f 'uvicorn.*8765'"
    exit 1
fi

# 检查 Python 环境
PYTHON_EXE=""
if [ -f "$HOME/pytorch_env/bin/python3" ]; then
    PYTHON_EXE="$HOME/pytorch_env/bin/python3"
    echo "✓ 使用 pytorch_env"
elif [ -f "venv/bin/python3" ]; then
    PYTHON_EXE="venv/bin/python3"
    echo "✓ 使用 venv"
else
    PYTHON_EXE="python3"
    echo "⚠ 使用系统 Python"
fi

# 检查依赖
if ! $PYTHON_EXE -c "import fastapi" 2>/dev/null; then
    echo "安装 FastAPI 依赖..."
    $PYTHON_EXE -m pip install fastapi uvicorn python-multipart -q
fi

# 启动服务
echo ""
echo "🚀 启动 Omnia FastAPI..."
echo "📍 地址: http://localhost:8765"
echo "📚 API 文档: http://localhost:8765/docs"
echo "📖 ReDoc: http://localhost:8765/redoc"
echo ""

if [ "$1" == "--daemon" ]; then
    # 后台运行
    nohup $PYTHON_EXE -m uvicorn src.omnia.main:app \
        --host 0.0.0.0 \
        --port 8765 \
        > /tmp/omnia_fastapi.log 2>&1 &
    
    echo $! > /tmp/omnia_fastapi.pid
    echo "✓ FastAPI 已在后台启动 (PID: $!)"
    echo "   日志: /tmp/omnia_fastapi.log"
else
    # 前台运行（开发模式）
    $PYTHON_EXE -m uvicorn src.omnia.main:app \
        --host 0.0.0.0 \
        --port 8765 \
        --reload
fi
