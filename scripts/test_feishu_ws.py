#!/usr/bin/env python3
"""
飞书 WebSocket 长连接测试
"""
import lark_oapi as lark
from lark_oapi.ws import Client
from lark_oapi.event.dispatcher_handler import EventDispatcherHandler

# 配置
APP_ID = "cli_a9540774f0b8dcc4"
APP_SECRET = "**********"

def handle_message(event):
    """处理消息事件"""
    print(f"\n{'='*60}")
    print(f"收到消息事件!")
    print(f"事件类型: {event.header.event_type}")
    print(f"事件数据: {event.event}")
    
    # 提取消息内容
    try:
        message = event.event.message
        content = message.content
        chat_id = message.chat_id
        msg_type = message.message_type
        
        print(f"消息类型: {msg_type}")
        print(f"聊天ID: {chat_id}")
        print(f"消息内容: {content}")
        
        # TODO: 回复消息
        # reply_to_message(chat_id, content)
        
    except Exception as e:
        print(f"解析消息失败: {e}")
    
    print(f"{'='*60}\n")

def main():
    print("飞书 WebSocket 长连接测试")
    print("=" * 60)
    
    # 创建事件处理器
    event_handler = (
        EventDispatcherHandler.builder("", "", lark.LogLevel.DEBUG)
        .register_p2_im_message_receive_v1(handle_message)
        .build()
    )
    
    print("事件处理器已创建")
    print("已注册: im.message.receive_v1 事件")
    
    # 创建 WebSocket 客户端
    client = Client(
        app_id=APP_ID,
        app_secret=APP_SECRET,
        log_level=lark.LogLevel.DEBUG,
        event_handler=event_handler
    )
    
    print("WebSocket 客户端已创建")
    print("正在启动连接...")
    print("=" * 60)
    
    # 启动连接（阻塞）
    client.start()

if __name__ == "__main__":
    main()
