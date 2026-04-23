# Omnia Gateway 集成方案

## 背景

当前 Omnia 通过 OpenClaw Gateway 接收消息，但这违反了 Omnia 的独立性原则。

**问题：**
- Omnia 的代码修改会影响 OpenClaw
- Omnia 不是完全独立的系统

**目标：**
- Omnia 拥有自己的 Gateway
- OpenClaw 只是 Omnia 的一个可选通道

---

## 架构对比

### 当前架构（依赖 OpenClaw）

```
用户 → OpenClaw Gateway → Omnia Daemon → 无限
         ↓
    OpenClaw 的网关
    Omnia 被动接收
```

### 目标架构（Omnia 独立）

```
用户 → Omnia Gateway → 通道适配器 → Omnia 核心 → 无限
         ↓
    ├─ WebChat Adapter
    ├─ Feishu Adapter
    ├─ CLI Adapter
    └─ OpenClaw Adapter（可选）
```

---

## 实现步骤

### 第一阶段：创建 Gateway 架构

✅ **已完成**
- `src/core/gateway/runner.py` — GatewayRunner
- `src/core/gateway/feishu_adapter.py` — 飞书适配器
- `src/gateway/webchat_adapter.py` — WebChat 适配器
- `test_gateway.py` — 测试脚本

### 第二阶段：集成到 web_server.py

**修改 `src/omnia/web_server.py`：**

1. 在 `create_app()` 中初始化 Gateway
2. 创建 WebChatAdapter
3. 修改 `/api/chat` 端点，通过 Gateway 接收消息

**代码示例：**

```python
from gateway import GatewayRunner, WebChatAdapter

# 在 create_app() 中
gateway = GatewayRunner.get_instance()
webchat_adapter = WebChatAdapter()

# 设置消息处理器
async def handle_omnia_message(event):
    # 调用 Omnia 核心处理消息
    from omnia.chat_handler import handle_chat
    result = handle_chat(event.content, ...)
    return result

webchat_adapter._on_message = handle_omnia_message

# 注册到 Gateway
await gateway.register_adapter(webchat_adapter)

# 修改 /api/chat 端点
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message")
    user_id = data.get("user_id", "web_user")
    chat_id = data.get("chat_id", "default")
    
    # 通过 Gateway 接收消息
    asyncio.run(webchat_adapter.receive_message(
        user_id=user_id,
        chat_id=chat_id,
        content=message,
    ))
    
    # 返回结果
    return jsonify(result)
```

### 第三阶段：创建独立 Gateway 服务

**创建 `scripts/start_gateway.py`：**

```python
#!/usr/bin/env python3
"""启动 Omnia Gateway 服务"""

import asyncio
from gateway import GatewayRunner, WebChatAdapter, FeishuAdapter

async def main():
    runner = GatewayRunner()
    
    # 注册所有适配器
    await runner.register_adapter(WebChatAdapter())
    await runner.register_adapter(FeishuAdapter(...))
    
    # 启动 Gateway
    await runner.start()
    print("Omnia Gateway 已启动")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 优势

### 独立性
- Omnia 不依赖 OpenClaw
- 可以独立部署、独立运行

### 扩展性
- 轻松添加新通道（Discord、Telegram、Slack 等）
- 统一的消息格式

### 可维护性
- 通道适配器独立开发
- 核心逻辑与通道解耦

---

## 兼容性

### 保持 OpenClaw 支持

OpenClaw 可以作为 Omnia 的一个通道：

```python
# 创建 OpenClaw Adapter
class OpenClawAdapter(ChannelAdapter):
    channel_type = ChannelType.API
    
    async def receive_from_openclaw(self, message):
        # 将 OpenClaw 的消息转换为 MessageEvent
        event = MessageEvent(...)
        await self._on_message(event)
```

---

## 测试

```bash
# 测试 Gateway 架构
python3 test_gateway.py

# 测试 web_server.py 集成
python3 src/omnia/web_server.py
```

---

## 时间线

- [x] 2026-04-19: 创建 Gateway 架构
- [ ] 2026-04-19: 集成到 web_server.py
- [ ] 2026-04-20: 创建独立 Gateway 服务
- [ ] 2026-04-21: 添加更多通道适配器

---

## 参考

- OpenClaw Gateway 设计
- Hermes Gateway 架构
- Omnia 设计原则：Sovereignty Over Lock-in
