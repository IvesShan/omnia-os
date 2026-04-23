#!/bin/bash
# Omnia 本地模型服务 - GPU 加速版（已修复）

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

# 停止旧服务
if pgrep -f "llama-server.*$PORT" > /dev/null; then
    log_warn "停止旧服务..."
    pkill -f "llama-server.*$PORT"
    sleep 2
fi

# 检查模型
if [ ! -f "$MODEL" ]; then
    log_error "模型文件不存在: $MODEL"
    exit 1
fi

log_info "🚀 启动 GPU 加速本地模型服务..."
log_info "模型: $(basename $MODEL)"
log_info "端口: $PORT"

# 设置 GPU 环境变量（关键！）
export HSA_OVERRIDE_GFX_VERSION=10.3.0
export HIP_VISIBLE_DEVICES=0
export HSA_ENABLE_SDMA=0
export CUDA_VISIBLE_DEVICES=-1  # 禁用 CUDA，只用 ROCm

# 设置 ROCm 库路径
export ROCm_PATH=/opt/rocm-6.2.0
export LD_LIBRARY_PATH=$ROCm_PATH/lib:$LLAMA_DIR:$LD_LIBRARY_PATH

# 高性能参数
nohup "$LLAMA_DIR/llama-server" \
    --model "$MODEL" \
    --port $PORT \
    --host 0.0.0.0 \
    --n-gpu-layers 99 \
    --ctx-size 32768 \
    --threads 8 \
    --batch-size 512 \
    --ubatch-size 256 \
    > "$LOG" 2>&1 &

PID=$!
log_info "进程 PID: $PID"

# 等待启动
log_info "等待服务初始化..."
sleep 15

# 检查进程
if kill -0 $PID 2>/dev/null; then
    log_info "✅ 服务启动成功!"
    log_info "API: http://localhost:$PORT"
    log_info "日志: $LOG"
    
    # 测试 API
    sleep 5
    if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
        log_info "✅ API 健康检查通过"
        
        # 检查 GPU 是否启用
        if grep -q "no usable GPU" "$LOG" 2>/dev/null; then
            log_error "❌ GPU 未启用，请检查日志"
            log_warn "日志内容:"
            head -20 "$LOG"
        else
            log_info "✅ GPU 加速已启用"
        fi
        
        # 显示性能指标
        log_info "📊 性能配置:"
        log_info "  - GPU: AMD Radeon RX 6800 (16GB)"
        log_info "  - GPU 层数: 99 (全 GPU 加速)"
        log_info "  - 上下文: 32768 tokens"
        log_info "  - 线程: 8"
        log_info "  - 批处理: 512"
    else
        log_warn "⚠️ API 尚未就绪，请检查日志: $LOG"
    fi
else
    log_error "❌ 服务启动失败"
    log_error "日志内容:"
    tail -50 "$LOG"
    exit 1
fi
