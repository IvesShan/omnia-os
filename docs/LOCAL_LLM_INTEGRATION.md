# 本地模型集成指南

## 概述

Omnia 现已支持本地 GPU 加速模型，实现：
- ✅ 快速响应（本地 GPU 推理）
- ✅ 零 Token 成本
- ✅ 隐私保护（数据不出本地）
- ✅ 自动降级（本地不可用时切换云端）

## 硬件配置

| 项目 | 配置 |
|------|------|
| GPU | AMD Radeon RX 6800/6900 XT (16GB) |
| 模型 | Gemma 4 4B (Q8_0) |
| 显存占用 | ~5.5GB |
| 推理速度 | ~20-30 tokens/s |

## 快速开始

### 1. 启动本地模型服务

```bash
# 使用管理脚本
bash scripts/local_llm.sh start

# 或手动启动
llama-server --model ~/AI_Models/gemma-4-E4B-it-OBLITERATED-Q8_0.gguf \
    --port 8080 --n-gpu-layers 99 --ctx-size 32768
```

### 2. 检查服务状态

```bash
bash scripts/local_llm.sh status
```

### 3. 测试 API

```bash
bash scripts/local_llm.sh test
```

## 使用方式

### 方式 1: 直接使用 LocalLLMClient

```python
from core.providers.local_client import LocalLLMClient

async def chat():
    client = LocalLLMClient()
    
    response = await client.chat([
        {"role": "user", "content": "你好"}
    ])
    
    print(response['content'])
```

### 方式 2: 使用智能路由器（推荐）

```python
from core.providers.smart_router import smart_chat

async def chat():
    # 自动选择本地/云端模型
    response = await smart_chat([
        {"role": "user", "content": "你好"}
    ])
    
    print(response['content'])
```

### 方式 3: 通过 Provider 系统

```python
from core.providers import ProviderResolver

resolver = ProviderResolver()
client = resolver.get_client("local/gemma-4-4b")

response = await client.chat([
    {"role": "user", "content": "你好"}
])
```

## 智能路由策略

SmartModelRouter 会自动选择最佳模型：

1. **简单任务** → 本地模型（快速、免费）
2. **复杂任务** → 云端模型（更智能）
3. **本地不可用** → 自动降级到云端

```python
# 查看选择的模型
router = SmartModelRouter()
model_id, tier = await router.select_model(messages)

print(f"选择模型: {model_id}")
print(f"层级: {tier.value}")  # local / cloud_fast / cloud_smart
```

## 配置选项

### .env 配置

```bash
# 本地模型
LOCAL_LLM_ENABLED=true
LOCAL_LLM_BASE_URL=http://localhost:8080
LOCAL_LLM_MODEL=gemma-4-E4B-it-OBLITERATED-Q8_0.gguf
LOCAL_LLM_GPU=true

# 云端模型（Fallback）
QIANFAN_API_KEY=your_key
```

### config/local_llm.yaml

```yaml
default_model: "local/gemma-4-4b"

models:
  gemma-4-4b:
    model_id: "gemma-4-E4B-it-OBLITERATED-Q8_0.gguf"
    context_window: 32768
    max_output: 4096
    
api:
  base_url: "http://localhost:8080"
  timeout: 300
```

## 管理命令

```bash
# 启动服务
bash scripts/local_llm.sh start

# 停止服务
bash scripts/local_llm.sh stop

# 重启服务
bash scripts/local_llm.sh restart

# 查看状态
bash scripts/local_llm.sh status

# 查看日志
bash scripts/local_llm.sh logs

# 测试 API
bash scripts/local_llm.sh test
```

## 性能优化

### GPU 加速

确保 ROCm 驱动正确安装：

```bash
# 检查 GPU
rocm-smi

# 检查 HIP 支持
python3 -c "import torch; print(torch.cuda.is_available())"
```

### 编译优化

llama.cpp 编译时启用 HIPBLAS：

```bash
cd ~/AI_Models/llama.cpp
cmake -B build -DGGML_HIP=ON
cmake --build build --config Release -j$(nproc)
```

## 故障排除

### 服务无法启动

1. 检查 GPU 驱动：`rocm-smi`
2. 检查端口占用：`lsof -i :8080`
3. 查看日志：`tail -f /tmp/llama_server.log`

### API 响应慢

1. 检查 GPU 显存：`rocm-smi --showmeminfo vram`
2. 减少 GPU 层数：`--n-gpu-layers 50`
3. 减小上下文：`--ctx-size 16384`

### 内存不足

1. 使用量化模型（Q4/Q5）
2. 减少 GPU 层数
3. 使用更小的模型

## 文件结构

```
omnia-os/
├── config/
│   └── local_llm.yaml          # 本地模型配置
├── scripts/
│   └── local_llm.sh            # 服务管理脚本
├── src/core/providers/
│   ├── __init__.py             # Provider 注册表
│   ├── local_client.py         # 本地模型客户端
│   └── smart_router.py         # 智能路由器
└── test_local_llm.py           # 集成测试
```

## 下一步

- [ ] 添加更多本地模型支持
- [ ] 实现 RAG + 本地模型
- [ ] 优化流式输出性能
- [ ] 添加模型热切换功能
