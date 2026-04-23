#!/bin/bash
# Omnia 本地模型服务启动脚本

set -e

# 配置
LLAMA_DIR="/home/shan/llama.cpp/build/bin"
MODEL="/home/shan/models/gemma-4-e4b-obliterated/hf/OBLITERATUS-gemma-4-E4B-it-OBLITERATED/gemma-4-E4B-it-OBLITERATED-Q8_0.gguf"
PORT=8080
LOG="/tmp/llama_server.log"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查是否已运行
if pgrep -f "llama-server.*$PORT" > /dev/null; then
    log_warn "服务已在运行 (端口 $PORT)"
    log_info "API: http://localhost:$PORT"
    exit 0
fi

# 检查模型
if [ ! -f "$MODEL" ]; then
    log_error "模型文件不存在: $MODEL"
    exit 1
fi

log_info "启动本地模型服务..."
log_info "模型: $(basename $MODEL)"
log_info "端口: $PORT"
log_info "GPU: AMD ROCm (99 layers)"

# 设置库路径并启动
export LD_LIBRARY_PATH="$LLAMA_DIR:$LD_LIBRARY_PATH"

nohup "$LLAMA_DIR/llama-server" \
    --model "$MODEL" \
    --port $PORT \
    --host 0.0.0.0 \
    --n-gpu-layers 99 \
    --ctx-size 32768 \
    --threads 8 \
    > "$LOG" 2>&1 &

PID=$!
log_info "进程 PID: $PID"

# 等待启动
sleep 10

# 检查进程
if kill -0 $PID 2>/dev/null; then
    log_info "✅ 服务启动成功!"
    log_info "API: http://localhost:$PORT"
    log_info "日志: $LOG"
    
    # 测试 API
    sleep 3
    if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
        log_info "✅ API 健康检查通过"
    else
        log_warn "⚠️ API 尚未就绪，请稍后检查"
    fi
else
    log_error "❌ 服务启动失败"
    log_error "日志内容:"
    tail -30 "$LOG"
    exit 1
fi
