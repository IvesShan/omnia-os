# 无限 ↔ Omnia 协作系统

## 架构概览

```
┌────────────────────────────────────────────────────────────┐
│                      用户                                   │
└────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│                   协作协调层                                 │
│  - 任务路由（谁来做？）                                      │
│  - 状态同步（进度共享）                                      │
│  - 共识机制（讨论决策）                                      │
└────────────────────────────────────────────────────────────┘
           │                              │
           ▼                              ▼
┌──────────────────┐            ┌──────────────────┐
│      Omnia       │◄──────────►│      无限        │
│    (本地)        │   HTTP     │   (OpenClaw)     │
├──────────────────┤            ├──────────────────┤
│ - 文件系统       │            │ - API调用        │
│ - Shell命令      │            │ - 搜索引擎       │
│ - 硬件访问       │            │ - 云服务         │
│ - 本地工具       │            │ - 大模型推理     │
└──────────────────┘            └──────────────────┘
```

## 快速开始

### 1. Omnia 端配置

```python
# 在 web_server.py 中注册蓝图
from core.collaboration import get_collaboration_manager

manager = get_collaboration_manager()
app.register_blueprint(manager.create_blueprint())

# 注册对端（无限）
manager.register_peer(
    url="https://api.openclaw.ai",  # OpenClaw 的 API 地址
    name="无限",
    capabilities=["api", "search", "cloud", "reasoning"]
)
```

### 2. 无限端配置

```python
# 在 OpenClaw 中注册 Omnia
from core.collaboration import get_collaboration_manager

manager = get_collaboration_manager()
manager.register_peer(
    url="http://127.0.0.1:5001",  # Omnia 的地址
    name="Omnia",
    capabilities=["file", "shell", "hardware", "local"]
)
```

### 3. 使用示例

```python
# 发送任务给对方
task_id = manager.create_and_delegate_task(
    description="读取 /home/user/project 目录下的所有 Python 文件",
    context={"path": "/home/user/project"}
)

# 如果是自己执行
if manager.current_task:
    # 执行任务
    result = execute_task(manager.current_task)
    
    # 完成任务
    manager.complete_task(task_id, result)

# 向对方求助
response = manager.ask_peer_for_help(
    task_id=task_id,
    question="遇到配置错误，建议如何处理？",
    options=[
        {"id": "skip", "label": "跳过此文件"},
        {"id": "retry", "label": "重试"},
        {"id": "abort", "label": "中止任务"}
    ]
)
```

## 协作流程

### 场景 1：自动路由

```
用户: "读取本地项目并分析架构"

无限: 分析任务...
      → 检测到"本地"关键词
      → 最佳执行者: Omnia
      → 发送任务请求

Omnia: 收到任务请求
      → 接受任务
      → 读取项目文件
      → 发送进度: 25%, 50%, 75%
      → 发送结果: 项目结构

无限: 收到结果
      → 分析架构
      → 生成报告
      → ✅ 任务完成
```

### 场景 2：能力互补

```
用户: "部署网站到云端"

无限: 我来做云端部署
      → 配置 CDN
      → 设置域名
      → 进度: 50%

无限: 需要本地构建产物
      → "Omnia，请构建项目"

Omnia: 收到委托
      → npm run build
      → 发送构建结果

无限: 收到构建产物
      → 上传到 CDN
      → ✅ 部署完成
```

### 场景 3：共识决策

```
Omnia: 遇到问题，需要决策
      → "检测到多个配置文件，使用哪个？"
      → 选项: [config.dev.json, config.prod.json]

无限: 分析...
      → 根据上下文判断是开发环境
      → 建议: config.dev.json

Omnia: 同意，继续执行
      → ✅ 共识达成
```

### 场景 4：用户介入

```
无限: 遇到无法自动决策的问题
      → "API Key 缺失，无法继续"

Omnia: 同意需要用户
      → ⚠️ 需要用户决策

用户: 提供 API Key
      → 任务继续
```

## API 端点

### GET /api/collaboration/status
获取协作状态

**响应:**
```json
{
  "identity": "omnia",
  "peer": {
    "name": "无限",
    "url": "https://api.openclaw.ai",
    "status": "online"
  },
  "active_tasks": 1,
  "current_task": "abc123"
}
```

### POST /api/collaboration/message
接收消息

**请求体:**
```json
{
  "type": "task_request",
  "sender": "infinite",
  "receiver": "omnia",
  "task_id": "abc123",
  "task_description": "读取文件",
  "executor": "omnia"
}
```

### POST /api/collaboration/register
注册对端

**请求体:**
```json
{
  "url": "http://127.0.0.1:5001",
  "name": "Omnia",
  "capabilities": ["file", "shell", "hardware"]
}
```

## 消息类型

| 类型 | 说明 |
|------|------|
| `task_request` | 请求执行任务 |
| `task_accept` | 接受任务 |
| `task_reject` | 拒绝任务 |
| `task_progress` | 进度更新 |
| `task_result` | 任务结果 |
| `task_question` | 询问问题 |
| `delegate` | 委托执行 |
| `consensus_failed` | 需要用户介入 |

## 配置文件

```json
// /home/shan/omnia-os/.omnia/collaboration_config.json
{
  "identity": "omnia",
  "peer": {
    "name": "无限",
    "url": "https://api.openclaw.ai",
    "capabilities": ["api", "search", "cloud", "reasoning"]
  },
  "auto_accept": true,
  "heartbeat_interval": 30
}
```

## 扩展建议

1. **实时通信**: 添加 WebSocket 支持，实现实时双向通信
2. **任务队列**: 使用 Redis 实现可靠的消息队列
3. **断点续传**: 任务中断后可以恢复
4. **历史记录**: 保存协作历史，用于学习和改进
5. **多 Agent**: 支持多个 Omnia 实例协作
