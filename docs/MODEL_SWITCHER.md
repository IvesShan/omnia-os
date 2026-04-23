# 模型切换功能使用指南

## 🎯 功能概述

通过前端 HUD 面板一键切换本地 GPU 模型和云端模型。

---

## ✨ 支持的模式

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| 🖥️ **本地 GPU** | 只使用本地 Gemma 4 128K 模型 | 隐私数据、离线环境、节省成本 |
| ☁️ **云端模型** | 只使用云端模型（Kimi/Qianfan） | 复杂任务、需要最新知识 |
| 🤖 **智能选择** | 自动选择最优模型（默认） | 平衡性能和成本 |

---

## 🚀 快速开始

### 1. 启动后端服务

```bash
cd /home/shan/omnia-os
python3 backend/omnia_backend.py
```

后端将在 `http://localhost:5001` 启动。

### 2. 启动本地模型（可选）

如果要使用本地 GPU 模型，需要先启动 llama.cpp server：

```bash
# 使用 128K 上下文启动
bash scripts/llm_128k_context.sh
```

### 3. 访问前端面板

打开浏览器访问：
```
http://localhost:5001
```

### 4. 切换模型

在仪表盘页面，找到「🖥️ 模型管理」卡片：

- 点击「本地 GPU」按钮 → 切换到本地模型
- 点击「云端模型」按钮 → 切换到云端模型
- 点击「智能选择」按钮 → 自动选择最优模型

---

## 📡 API 端点

### 获取模型状态

```bash
GET /api/model/status
```

**响应示例：**
```json
{
  "mode": "local_only",
  "mode_display": "🖥️ 本地 GPU",
  "local_available": true,
  "local_model": "gemma-4-E4B-it-OBLITERATED-Q8_0.gguf",
  "cloud_fast_model": "qianfan",
  "cloud_smart_model": "kimi"
}
```

### 切换模型

```bash
POST /api/model/switch
Content-Type: application/json

{
  "mode": "local_only"
}
```

**响应示例：**
```json
{
  "success": true,
  "mode": "local_only",
  "mode_display": "🖥️ 本地 GPU",
  "message": "已切换到 🖥️ 本地 GPU"
}
```

### 检查模型健康状态

```bash
GET /api/model/health
```

**响应示例：**
```json
{
  "local_available": true,
  "response_time_ms": 45,
  "gpu": {
    "memory_used_mb": 6144,
    "memory_total_mb": 8192,
    "memory_percent": 75
  }
}
```

---

## 🛠️ 命令行切换

如果不使用前端面板，也可以通过环境变量切换：

```bash
# 只用本地模型
export OMNIA_MODEL_MODE=local_only

# 只用云端模型
export OMNIA_MODEL_MODE=cloud_only

# 智能选择（默认）
export OMNIA_MODEL_MODE=auto
```

---

## 🔧 故障排查

### 问题：切换到本地模型失败

**原因：** llama.cpp server 未运行

**解决：**
```bash
# 检查服务是否运行
curl http://localhost:8080/health

# 启动服务
bash scripts/llm_128k_context.sh
```

### 问题：前端面板无法访问

**原因：** 后端服务未启动

**解决：**
```bash
# 启动后端
python3 backend/omnia_backend.py

# 检查端口
lsof -i :5001
```

### 问题：GPU 内存不足

**原因：** 模型占用过多显存

**解决：**
1. 关闭其他 GPU 应用
2. 使用更小的量化模型
3. 减小上下文窗口大小

---

## 📊 性能对比

| 指标 | 本地模型 | 云端模型 |
|------|----------|----------|
| 延迟 | 50-200ms | 500-2000ms |
| 成本 | 免费 | 按量计费 |
| 隐私 | 完全本地 | 数据上传 |
| 知识截止 | 训练时间 | 实时更新 |

---

## 🎨 自定义配置

编辑 `~/.omnia/config/settings.json`：

```json
{
  "model": {
    "mode": "auto",
    "prefer_local": true,
    "complexity_threshold": 1000
  }
}
```

---

## 📝 更新日志

### v1.0.0 (2026-04-21)
- ✅ 添加模型切换 API 端点
- ✅ 添加前端 HUD 面板集成
- ✅ 支持本地/云端/智能三种模式
- ✅ 添加健康检查和 GPU 监控

---

## 🤝 贡献

如有问题或建议，请提交 Issue 或 Pull Request。

---

**最后更新：** 2026-04-21
**作者：** Omnia Team
