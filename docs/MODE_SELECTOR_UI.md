# 模型模式选择器 - UI 面板

## 概述

在 Omnia 前端 HUD 面板中，新增了可视化的模型模式选择器，支持一键切换本地/云端/智能模式。

---

## 功能特性

### 🎯 三种模式

| 模式 | 图标 | 说明 | 适用场景 |
|------|------|------|----------|
| **本地** | 🏠 | 只使用本地 GPU | 隐私优先、无网络、节省 Token |
| **云端** | ☁️ | 只使用云端 API | 复杂任务、需要最强模型 |
| **智能** | 🧠 | 自动选择最优 | 平衡性能与成本（默认） |

### 📊 实时状态显示

- **本地状态**: 在线/离线/检查中
- **云端状态**: 在线/离线/检查中
- **当前模式**: 高亮显示激活模式

---

## 使用方法

### 方式 1: UI 面板点击（推荐）

1. 打开 Omnia Web UI (`http://127.0.0.1:5001`)
2. 找到右侧面板的 **"模型模式"** 面板
3. 点击三个按钮之一：
   - 🏠 **本地** - 只用本地 GPU
   - ☁️ **云端** - 只用云端
   - 🧠 **智能** - 自动选择

### 方式 2: 斜杠命令

在聊天框输入：
```
/model
```
系统会滚动到模型选择面板并高亮提示。

### 方式 3: 命令行

```bash
# 切换到本地模式
bash scripts/model_mode.sh local

# 切换到云端模式
bash scripts/model_mode.sh cloud

# 切换到智能模式
bash scripts/model_mode.sh auto

# 查看当前状态
bash scripts/model_mode.sh status
```

### 方式 4: Python API

```python
from core.providers.smart_router import set_model_mode, smart_chat

# 切换模式
set_model_mode("local_only")  # 或 "cloud_only" 或 "smart"

# 发送请求（自动使用当前模式）
response = await smart_chat([
    {"role": "user", "content": "你好"}
])
```

---

## 技术实现

### 前端组件

- **HTML**: `web/index.html` - 模型模式面板
- **CSS**: `web/styles.css` - 按钮样式与动画
- **JS**: `web/app.js` - 交互逻辑

### 后端 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/model/status` | GET | 检查本地/云端服务状态 |
| `/api/model/mode` | POST | 设置模型模式 |

### 状态持久化

- **前端**: `localStorage.omnia_model_mode`
- **后端**: `os.environ.OMNIA_MODEL_MODE`
- **配置**: `.env` 文件（可选永久设置）

---

## 界面预览

```
┌─────────────────────────┐
│ MODEL.MODE    模型模式   │
├─────────────────────────┤
│ 当前模式: 本地           │
│                         │
│  ┌─────┐ ┌─────┐ ┌─────┐│
│  │ 🏠  │ │ ☁️  │ │ 🧠  ││
│  │本地 │ │云端 │ │智能 ││
│  │GPU  │ │Token│ │自动 ││
│  └─────┘ └─────┘ └─────┘│
│                         │
│ 本地状态: 在线           │
│ 云端状态: 在线           │
└─────────────────────────┘
```

---

## 故障排查

### 问题: 点击按钮无反应

**检查**:
1. 浏览器控制台是否有错误
2. 后端服务是否运行 (`curl http://127.0.0.1:5001/api/model/status`)

### 问题: 状态显示"离线"

**本地离线**:
```bash
# 检查 Ollama 服务
curl http://127.0.0.1:11434/api/tags

# 启动 Ollama
ollama serve
```

**云端离线**:
```bash
# 检查 API 密钥
cat .env | grep KIMI_API_KEY
```

---

## 更新日志

**2026-04-21**
- ✅ 新增 HUD 面板模型选择器
- ✅ 支持三种模式一键切换
- ✅ 实时显示服务状态
- ✅ 添加后端 API 端点
- ✅ 状态持久化到 localStorage

---

## 相关文档

- [模型模式指南](MODEL_MODE_GUIDE.md)
- [智能路由器](../src/core/providers/smart_router.py)
- [示例代码](../examples/model_mode_usage.py)
