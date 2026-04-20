#!/usr/bin/env python3
"""
飞书机器人 - 使用官方 larksdk-oapi WebSocket 长连接
"""

import os
import sys
import json
import lark_oapi as lark
from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
from lark_oapi.ws import Client as WSClient

# 加载 .env 文件
def load_env():
    """加载环境变量"""
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

# 从环境变量获取配置
APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
ENCRYPT_KEY = os.environ.get("FEISHU_ENCRYPT_KEY", "")
VERIFICATION_TOKEN = os.environ.get("FEISHU_VERIFICATION_TOKEN", "")

if not APP_ID or not APP_SECRET:
    print("❌ 错误: 请设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
    sys.exit(1)

# 创建 REST 客户端（用于发送消息）
client = lark.Client.builder() \
    .app_id(APP_ID) \
    .app_secret(APP_SECRET) \
    .build()

def handle_message(event):
    """处理消息事件"""
    print(f"\n{'='*50}")
    print("📨 收到消息！")
    print(f"{'='*50}")
    
    try:
        # event 是一个对象，包含 header 和 body
        header = event.header if hasattr(event, 'header') else {}
        body = event.body if hasattr(event, 'body') else {}
        
        print(f"Event Type: {header.event_type if hasattr(header, 'event_type') else 'unknown'}")
        
        # 解析消息
        event_data = body.get("event", {}) if isinstance(body, dict) else {}
        message = event_data.get("message", {})
        
        if message:
            content_str = message.get("content", "{}")
            content = json.loads(content_str) if isinstance(content_str, str) else content_str
            
            msg_type = message.get("message_type")
            chat_id = message.get("chat_id")
            sender = event_data.get("sender", {}).get("sender_id", {})
            open_id = sender.get("open_id")
            
            print(f"\n消息类型: {msg_type}")
            print(f"聊天ID: {chat_id}")
            print(f"发送者: {open_id}")
            print(f"内容: {content}")
            
            # 回复消息
            if msg_type == "text":
                text = content.get("text", "")
                print(f"\n准备回复...")
                send_message(chat_id, f"收到你的消息: {text}")
            
    except Exception as e:
        print(f"\n❌ 处理消息出错: {e}")
        import traceback
        traceback.print_exc()

def send_message(chat_id, text):
    """发送消息"""
    try:
        request = lark.api.im.message.CreateMessageRequest.builder() \
            .receive_id_type(lark.api.im.message.ReceiveIdTypeEnum.CHAT_ID) \
            .request_body(lark.api.im.message.CreateMessageRequestBody.builder() \
                .receive_id(chat_id) \
                .msg_type("text") \
                .content(json.dumps({"text": text})) \
                .build()) \
            .build()
        
        response = client.im.message.create(request)
        
        if response.code == 0:
            print(f"✓ 消息发送成功")
        else:
            print(f"✗ 消息发送失败: {response.code} - {response.msg}")
            
    except Exception as e:
        print(f"❌ 发送消息出错: {e}")
        import traceback
        traceback.print_exc()

def main():
    """启动飞书 WebSocket 长连接"""
    print("=" * 60)
    print("🤖 飞书机器人启动中...")
    print("=" * 60)
    print(f"APP_ID: {APP_ID}")
    print(f"APP_SECRET: {'*' * 8}")
    print("=" * 60)
    
    # 创建事件处理器
    event_handler = EventDispatcherHandler.builder(
        ENCRYPT_KEY, 
        VERIFICATION_TOKEN
    ) \
    .register_p2_im_message_receive_v1(handle_message) \
    .build()
    
    print("✓ 事件处理器创建成功")
    
    # 创建 WebSocket 客户端
    ws_client = WSClient(
        app_id=APP_ID,
        app_secret=APP_SECRET,
        event_handler=event_handler,
        log_level=lark.LogLevel.INFO
    )
    
    print("✓ WebSocket 客户端创建成功")
    print("\n📡 开始监听飞书消息...")
    print("   按 Ctrl+C 停止\n")
    
    # 启动监听（阻塞）
    ws_client.start()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 机器人已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
