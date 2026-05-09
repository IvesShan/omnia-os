#!/bin/bash
# Omnia FastAPI 启动脚本

cd /home/shan/omnia-os

# 激活虚拟环境
source venv/bin/activate

# 启动 FastAPI 服务
python3 -m uvicorn src.omnia.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload
