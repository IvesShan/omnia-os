#!/bin/bash
# Omnia Local LLM - 128K 超大上下文配置
# 针对 AMD RX 6800 16GB + 6核CPU 的极致优化

set -e

echo "========================================="
echo "  Omnia LLM - 128K 超大上下文"
echo "========================================="

# 环境变量 - ROCm GPU 检测修复
export HSA_OVERRIDE_GFX_VERSION=10.3.0
export HIP_VISIBLE_DEVICES=0
export HSA_ENABLE_SDMA=0
export CUDA_VISIBLE_DEVICES=-1

# 路径配置
LLAMA_BIN="/home/shan/llama.cpp/build/bin/llama-server"
MODEL_PATH="/home/shan/models/gemma-4-e4b-obliterated/hf/OBLITERATUS-gemma-4-E4B-it-OBLITERATED/gemma-4-E4B-it-OBLITERATED-Q8_0.gguf"

# 停止旧服务
echo "🛑 停止旧服务..."
pkill -f "llama-server.*8080" 2>/dev/null || true
sleep 2

# 检查端口
if lsof -i :8080 >/dev/null 2>&1; then
    echo "⚠️  端口 8080 仍被占用，强制清理..."
    lsof -ti :8080 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

echo "🚀 启动 128K 超大上下文服务..."

# 128K 超大上下文配置
exec "$LLAMA_BIN" \
    --model "$MODEL_PATH" \
    --port 8080 \
    --host 0.0.0.0 \
    \
    `# === GPU 加速 ===` \
    --n-gpu-layers 99 \
    \
    `# === 128K 超大上下文 ===` \
    --ctx-size 131072 \
    \
    `# === 批处理优化 ===` \
    --batch-size 1024 \
    --ubatch-size 512 \
    \
    `# === Flash Attention ===` \
    --flash-attn on \
    \
    `# === KV Cache 优化 ===` \
    --cache-type-k q8_0 \
    --cache-type-v q8_0 \
    \
    `# === CPU 优化 ===` \
    --threads 6 \
    --threads-batch 6 \
    \
    `# === 并发优化：2个槽位，每个64K ===` \
    --parallel 2 \
    --cont-batching \
    \
    `# === 内存优化 ===` \
    --mlock
