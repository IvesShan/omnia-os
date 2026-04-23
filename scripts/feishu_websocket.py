#!/usr/bin/env python3
"""
飞书 WebSocket 长连接机器人
使用官方 SDK 的 WebSocket 客户端，无需公网服务器
"""

import json
import lark_oapi as lark
from lark_oapi.ws.client import Client as WSClient
from lark_oapi.event.dispatcher_handler import EventDispatcherHandler

# 加载配置
CONFIG_PATH = "/home/shan//home/shan/omnia-os/omnia-os/config/feishu.json"

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

config = load_config()

# 创建普通客户端（用于发送消息）
client = lark.Client.builder() \
    .app_id(config['app_id']) \
    .app_secret(config['app_secret']) \
    .log_level(lark.LogLevel.INFO) \
    .build()

# 消息处理回调
def on_message_receive(data):
    """处理接收到的消息事件"""
    try:
        print(f"\n{'='*50}")
        
        # data 是事件对象
        event = data.event
        message = event.message
        sender = event.sender
        
        msg_type = message.message_type
        content = message.content
        chat_id = message.chat_id
        sender_id = sender.sender_id.user_id
        
        print(f"📨 收到消息")
        print(f"  发送者: {sender_id}")
        print(f"  群聊: {chat_id}")
        print(f"  类型: {msg_type}")
        print(f"  内容: {content}")
        
        # 如果是文本消息，调用 Omnia 聊天
        if msg_type == "text":
            content_json = json.loads(content)
            text = content_json.get('text', '')
            
            # 调用 Omnia API
            reply_text = call_omnia_chat(text, chat_id, sender_id)
            send_text_message(chat_id, reply_text)
        
    except Exception as e:
        print(f"❌ 处理消息失败: {e}")
        import traceback
        traceback.print_exc()

def call_omnia_chat(message, chat_id, user_id):
    """调用 Omnia 聊天 API"""
    import requests
    
    try:
        # 调用本地 Omnia API
        response = requests.post(
            "http://127.0.0.1:5001/api/chat",
            json={
                "message": message,
                "history": []
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("reply", "抱歉，我暂时无法回复")
        else:
            return f"Omnia API 错误: {response.status_code}"
            
    except Exception as e:
        return f"连接 Omnia 失败: {e}"

def send_text_message(chat_id, text):
    """发送文本消息"""
    try:
        from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody
        
        req = CreateMessageRequest.builder() \
            .receive_id_type("chat_id") \
            .request_body(CreateMessageRequestBody.builder()
                .receive_id(chat_id)
                .msg_type("text")
                .content(json.dumps({"text": text}))
                .build()) \
            .build()
        
        resp = client.im.v1.message.create(req)
        
        if resp.success():
            print(f"✅ 消息发送成功")
        else:
            print(f"❌ 消息发送失败: {resp.code} - {resp.msg}")
            
    except Exception as e:
        print(f"❌ 发送消息异常: {e}")

def main():
    print("=" * 60)
    print("🤖 飞书 WebSocket 长连接机器人")
    print("=" * 60)
    print(f"App ID: {config['app_id']}")
    print()
    
    # 创建事件处理器
    event_handler = EventDispatcherHandler.builder(
        encrypt_key="",  # 长连接模式不需要
        verification_token="",  # 长连接模式不需要
        level=lark.LogLevel.INFO
    ).register_p2_im_message_receive_v1(on_message_receive) \
     .build()
    
    # 创建 WebSocket 客户端
    print("正在建立 WebSocket 长连接...")
    
    ws_client = WSClient(
        app_id=config['app_id'],
        app_secret=config['app_secret'],
        log_level=lark.LogLevel.INFO,
        event_handler=event_handler
    )
    
    print("✅ WebSocket 连接已建立")
    print()
    print("🤖 机器人已就绪，等待消息...")
    print("   在飞书中给机器人发消息试试吧！")
    print()
    print("   按 Ctrl+C 退出")
    print("=" * 60)
    
    # 启动 WebSocket 客户端（阻塞运行）
    try:
        ws_client.start()
    except KeyboardInterrupt:
        print("\n\n👋 机器人已停止")

if __name__ == "__main__":
    main()
