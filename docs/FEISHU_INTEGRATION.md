# 飞书集成指南

## 已完成

1. ✅ 添加 FEISHU/LARK 通道类型
2. ✅ 创建 FeishuAdapter 适配器
3. ✅ 添加 Webhook 端点 `/webhook/feishu`
4. ✅ 配置文件 `config/feishu.json`

## 配置步骤

### 1. 在飞书开放平台配置

1. 打开 [飞书开放平台](https://open.feishu.cn/)
2. 进入应用 → 事件订阅
3. 添加事件订阅地址：
   ```
   http://你的服务器地址/webhook/feishu
   ```
4. 添加事件：`im.message.receive_v1`（接收消息）

### 2. 启动 Omnia Web Server

```bash
cd ~//home/shan/omnia-os
python3 src/omnia/web_server.py
```

### 3. 测试 Webhook

```bash
# 模拟飞书 URL 验证
curl -X POST http://localhost:5001/webhook/feishu \
  -H "Content-Type: application/json" \
  -d '{"type":"url_verification","challenge":"test123"}'
# 应返回: {"challenge":"test123"}

# 模拟消息事件
curl -X POST http://localhost:5001/webhook/feishu \
  -H "Content-Type: application/json" \
  -d '{
    "header": {"event_type": "im.message.receive_v1"},
    "event": {
      "sender": {"sender_id": {"open_id": "ou_test123"}},
      "message": {
        "chat_id": "oc_test123",
        "message_type": "text",
        "content": "{\"text\": \"你好 Omnia\"}"
      }
    }
  }'
# 应返回: {"code":0}
```

### 4. 检查日志

消息会打印在控制台：
```
[Feishu] ou_test123: 你好 Omnia
```

## 使用 FeishuAdapter 发送消息

```python
from core.gateway.feishu_adapter import FeishuAdapter

adapter = FeishuAdapter(
    app_id="cli_a92d57c4c5b95cc8",
    app_secret="jzm6pUrSUKDx6NbptHsiWXyz6whvnoSL",
)

# 发送文本
await adapter.send("ou_user123", "你好，这是来自 Omnia 的消息")

# 发送卡片
await adapter.send("ou_user123", json.dumps({
    "type": "template",
    "data": {
        "template_id": "xxx",
        "template_variable": {}
    }
}))
```

## 连接模式

### Webhook 模式（默认）
- 飞书主动推送事件到 Omnia
- 需要公网可访问的 HTTP 端点
- 适合生产环境

### WebSocket 模式
- Omnia 主动连接飞书
- 不需要公网端点
- 适合本地开发

修改 `config/feishu.json`:
```json
{
  "connection_mode": "websocket"
}
```

## 下一步

- [ ] 集成到 Gateway Runner
- [ ] 实现消息自动回复
- [ ] 支持卡片消息模板
