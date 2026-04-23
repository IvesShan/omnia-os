# 模型模式切换指南

Omnia 支持三种模型使用模式，你可以根据需求灵活切换。

---

## 📊 三种模式对比

| 模式 | 说明 | 优点 | 缺点 |
|------|------|------|------|
| **local_only** | 只用本地 GPU 模型 | 免费、隐私、快速 | 能力有限、需显存 |
| **cloud_only** | 只用云端模型 | 强大、无需显存 | 消耗 Token |
| **auto** | 智能选择 | 兼顾成本和能力 | 需配置阈值 |

---

## 🚀 快速切换

### 方式1：命令行（推荐）

```bash
# 只用本地（免费）
bash scripts/model_mode.sh local

# 只用云端（强大）
bash scripts/model_mode.sh cloud

# 智能选择（默认）
bash scripts/model_mode.sh auto

# 查看当前状态
bash scripts/model_mode.sh status
```

### 方式2：环境变量

在 `.env` 文件中设置：

```bash
# 只用本地
OMNIA_MODEL_MODE=local_only

# 只用云端
OMNIA_MODEL_MODE=cloud_only

# 智能选择
OMNIA_MODEL_MODE=auto
```

### 方式3：Python 代码

```python
from core.providers.smart_router import set_model_mode, get_model_mode

# 切换模式
set_model_mode("local_only")  # 只用本地
set_model_mode("cloud_only")  # 只用云端
set_model_mode("auto")        # 智能选择

# 查看当前模式
print(get_model_mode())
```

### 方式4：单次请求指定

```python
from core.providers.smart_router import smart_chat

messages = [{"role": "user", "content": "你好"}]

# 这次只用本地
response = await smart_chat(messages, mode="local_only")

# 这次只用云端
response = await smart_chat(messages, mode="cloud_only")
```

---

## 💡 使用场景

### 场景1：省钱模式（local_only）

适合：
- 日常对话
- 简单问答
- 隐私敏感内容
- Token 配额紧张

```bash
bash scripts/model_mode.sh local
```

### 场景2：最强模式（cloud_only）

适合：
- 复杂推理
- 代码生成
- 长文本处理
- 需要最准确回答

```bash
bash scripts/model_mode.sh cloud
```

### 场景3：智能模式（auto，默认）

适合：
- 混合使用场景
- 平衡成本与质量
- 不确定任务复杂度

```bash
bash scripts/model_mode.sh auto
```

---

## ⚙️ AUTO 模式配置

AUTO 模式会根据任务复杂度自动选择：

```python
# 在 smart_router.py 中配置
RouterConfig(
    prefer_local=True,           # 优先本地
    complexity_threshold=1000,   # 超过 1000 token 用云端
    auto_fallback=True,          # 本地不可用时自动降级
)
```

---

## 🔧 管理本地服务

```bash
# 启动本地服务
bash scripts/local_llm.sh start

# 停止服务
bash scripts/local_llm.sh stop

# 查看状态
bash scripts/local_llm.sh status

# 测试 API
bash scripts/local_llm.sh test
```

---

## 📝 完整示例

```python
import asyncio
from core.providers.smart_router import smart_chat, set_model_mode

async def main():
    # 设置为本地模式
    set_model_mode("local_only")
    
    messages = [
        {"role": "user", "content": "介绍一下你自己"}
    ]
    
    # 使用本地模型
    response = await smart_chat(messages)
    print(response)

asyncio.run(main())
```

---

## ❓ 常见问题

### Q: 切换模式后需要重启吗？
A: 不需要，立即生效。

### Q: local_only 模式下本地服务没启动怎么办？
A: 会抛出错误，提示启动服务。运行 `bash scripts/local_llm.sh start`

### Q: AUTO 模式如何判断复杂度？
A: 根据消息长度估算 token 数，超过阈值就用云端。

### Q: 可以同时用多个模式吗？
A: 可以，用单次请求指定模式覆盖全局设置。

---

**推荐配置**：日常用 `auto`，省钱用 `local`，重要任务用 `cloud`。
