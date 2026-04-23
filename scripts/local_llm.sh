#!/bin/bash
# Omnia 本地模型服务管理脚本

set -e

# 配置
MODEL_DIR="/home/shan/AI_Models"
MODEL_NAME="gemma-4-E4B-it-OBLITERATED-Q8_0.gguf"
PORT=8080
GPU_LAYERS=99

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查 llama.cpp
check_llama_cpp() {
    if ! command -v llama-server &> /dev/null; then
        log_error "llama-server 未找到"
        log_info "请先编译 llama.cpp: cd ~/AI_Models/llama.cpp && cmake -B build -DGGML_HIP=ON && cmake --build build --config Release"
        exit 1
    fi
}

# 检查模型
check_model() {
    if [ ! -f "$MODEL_DIR/$MODEL_NAME" ]; then
        log_error "模型文件不存在: $MODEL_DIR/$MODEL_NAME"
        exit 1
    fi
}

# 启动服务
start() {
    if pgrep -f "llama-server.*$PORT" > /dev/null; then
        log_warn "服务已在运行 (端口 $PORT)"
        return 0
    fi
    
    check_llama_cpp
    check_model
    
    log_info "启动本地模型服务..."
    log_info "模型: $MODEL_NAME"
    log_info "端口: $PORT"
    log_info "GPU 层数: $GPU_LAYERS"
    
    nohup llama-server \
        --model "$MODEL_DIR/$MODEL_NAME" \
        --port $PORT \
        --host 0.0.0.0 \
        --n-gpu-layers $GPU_LAYERS \
        --ctx-size 32768 \
        --threads 8 \
        > /tmp/llama_server.log 2>&1 &
    
    sleep 3
    
    if pgrep -f "llama-server.*$PORT" > /dev/null; then
        log_info "✅ 服务启动成功"
        log_info "API 端点: http://localhost:$PORT"
        log_info "日志文件: /tmp/llama_server.log"
    else
        log_error "❌ 服务启动失败"
        tail -20 /tmp/llama_server.log
        exit 1
    fi
}

# 停止服务
stop() {
    if pgrep -f "llama-server.*$PORT" > /dev/null; then
        log_info "停止服务..."
        pkill -f "llama-server.*$PORT"
        sleep 2
        log_info "✅ 服务已停止"
    else
        log_warn "服务未运行"
    fi
}

# 重启服务
restart() {
    stop
    start
}

# 查看状态
status() {
    if pgrep -f "llama-server.*$PORT" > /dev/null; then
        log_info "✅ 服务运行中 (端口 $PORT)"
        
        # 测试 API
        if curl -s "http://localhost:$PORT/health" > /dev/null; then
            log_info "✅ API 健康检查通过"
        else
            log_warn "⚠️ API 健康检查失败"
        fi
        
        # GPU 使用情况
        if command -v rocm-smi &> /dev/null; then
            echo ""
            rocm-smi --showmeminfo vram 2>/dev/null | head -10 || true
        fi
    else
        log_warn "服务未运行"
    fi
}

# 查看日志
logs() {
    tail -f /tmp/llama_server.log
}

# 测试 API
test_api() {
    log_info "测试本地模型 API..."
    
    response=$(curl -s -X POST "http://localhost:$PORT/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -d '{
            "model": "'$MODEL_NAME'",
            "messages": [{"role": "user", "content": "你好，请用一句话介绍自己"}],
            "max_tokens": 100
        }')
    
    if [ $? -eq 0 ]; then
        echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    else
        log_error "API 测试失败"
    fi
}

# 帮助
help() {
    echo "Omnia 本地模型服务管理"
    echo ""
    echo "用法: $0 {start|stop|restart|status|logs|test}"
    echo ""
    echo "命令:"
    echo "  start    启动服务"
    echo "  stop     停止服务"
    echo "  restart  重启服务"
    echo "  status   查看状态"
    echo "  logs     查看日志"
    echo "  test     测试 API"
    echo ""
    echo "配置:"
    echo "  模型: $MODEL_NAME"
    echo "  端口: $PORT"
    echo "  目录: $MODEL_DIR"
}

# 主入口
case "$1" in
    start)   start ;;
    stop)    stop ;;
    restart) restart ;;
    status)  status ;;
    logs)    logs ;;
    test)    test_api ;;
    *)       help ;;
esac
