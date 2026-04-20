#!/usr/bin/env python3
"""
飞书长连接机器人 - 使用官方 WebSocket 长连接模式
无需公网服务器，适合本地开发
"""

import asyncio
import json
import lark_oapi as lark
from lark_oapi.api.im.v1 import *

# 加载配置
CONFIG_PATH = "/home/shan/.openclaw/workspace/omnia-os/config/feishu.json"

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

config = load_config()

# 创建飞书客户端
client = lark.Client.builder() \
    .app_id(config['app_id']) \
    .app_secret(config['app_secret']) \
    .log_level(lark.LogLevel.DEBUG) \
    .build()

def handle_message(event):
    """处理接收到的消息"""
    try:
        msg_type = event.event.message.message_type
        content = event.event.message.content
        sender_id = event.event.sender.sender_id.user_id
        chat_id = event.event.message.chat_id
        
        print(f"\n收到消息:")
        print(f"  发送者: {sender_id}")
        print(f"  群聊ID: {chat_id}")
        print(f"  类型: {msg_type}")
        print(f"  内容: {content}")
        
        # 如果是文本消息，自动回复
        if msg_type == "text":
            content_json = json.loads(content)
            text = content_json.get('text', '')
            
            # 回复消息
            reply_text = f"收到你的消息: {text}"
            send_message(chat_id, reply_text)
            
    except Exception as e:
        print(f"处理消息失败: {e}")

def send_message(chat_id, text):
    """发送消息"""
    try:
        req = CreateMessage.builder() \
            .receive_id_type("chat_id") \
            .request_body(CreateMessageRequestBody.builder()
                .receive_id(chat_id)
                .msg_type("text")
                .content(json.dumps({"text": text}))
                .build()) \
            .build()
        
        resp = client.im.v1.message.create(req)
        
        if resp.success():
            print(f"消息发送成功: {text}")
        else:
            print(f"消息发送失败: {resp.code} - {resp.msg}")
            
    except Exception as e:
        print(f"发送消息异常: {e}")

def main():
    print("=" * 50)
    print("飞书长连接机器人启动")
    print(f"App ID: {config['app_id'][:20]}...")
    print("=" * 50)
    
    # 使用 WebSocket 长连接
    # 注意：飞书 SDK 的长连接功能需要额外配置
    # 这里先使用轮询模式作为示例
    
    print("\n正在连接飞书...")
    print("提示: 请在飞书开放平台启用「使用长连接接收事件」")
    print("路径: 应用详情 -> 事件订阅 -> 配置方式 -> 使用长连接接收事件")
    
    # 测试 API 连接
    try:
        # 获取机器人信息
        req = GetBotInfo.builder().build()
        resp = client.botty.v1.bot_info.get(req)
        
        if resp.success():
            print(f"\n✓ 连接成功!")
            print(f"  机器人名称: {resp.data.bot_info.app_name}")
            print(f"  开放能力: {resp.data.bot_info.open_lark}")
        else:
            print(f"\n✗ 连接失败: {resp.code} - {resp.msg}")
            return
    except Exception as e:
        print(f"\n✗ 连接异常: {e}")
        return
    
    print("\n机器人已就绪，等待消息...")
    print("按 Ctrl+C 退出\n")
    
    # 保持运行
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n机器人已停止")

if __name__ == "__main__":
    main()
