#!/bin/bash
# 启动 Omnia Neural Graph API

cd /home/shan/omnia-os/omnia-os

# 激活虚拟环境
source .venv/bin/activate

# 启动 API 服务
python -m uvicorn src.core.memory.neural_api:app --host 0.0.0.0 --port 8765 --reload
