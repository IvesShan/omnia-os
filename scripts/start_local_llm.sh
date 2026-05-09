#!/bin/bash
# 启动本地 LLM 推理服务器 (Qwen3-8B)

export OMNIA_MODEL_MODE=local
export LOCAL_LLM_URL=http://localhost:8080/v1/chat/completions
export LOCAL_LLM_MODEL=Qwen3-8B

echo "[start_local_llm] Starting vLLM server with Qwen3-8B..."
echo "[start_local_llm] Model path: /home/shan/models/Qwen3-8B"
echo "[start_local_llm] Port: 8080"

# 使用系统 Python（vLLM 安装在这里）
python3 -m vllm.entrypoints.openai.api_server \
    --model /home/shan/models/Qwen3-8B \
    --host 0.0.0.0 \
    --port 8080 \
    --gpu-memory-utilization 0.9 \
    --max-model-len 8192 \
    --trust-remote-code
