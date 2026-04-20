#!/usr/bin/env python3
"""
飞书机器人 - WebSocket 长连接模式
不需要公网 URL，通过 SDK 与飞书建立 WebSocket 连接接收消息
"""

import os
import sys
import json
import lark_oapi as lark
from lark_oapi.event import BaseEventHandler
from lark_oapi.api.im.v1 import *

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 飞书配置
APP_ID = "cli_a9540774f0b8dcc4"
APP_SECRET = "C4AOjmYuoRrcgFNm9XoHahwOzEoqgsyR"

class MessageHandler(BaseEventHandler):
    """消息事件处理器"""
    
    def handle(self, event):
        """处理接收到的消息"""
        try:
            # 解析事件数据
            event_data = event.event
            message = event_data.message
            
            msg_type = message.message_type
            msg_content = message.content
            chat_id = message.chat_id
            sender_id = event_data.sender.sender_id.user_id
            
            print(f"\n收到消息:")
            print(f"  发送者: {sender_id}")
            print(f"  群组: {chat_id}")
            print(f"  类型: {msg_type}")
            print(f"  内容: {msg_content}")
            
            # 处理文本消息
            if msg_type == "text":
                content_json = json.loads(msg_content)
                text = content_json.get("text", "")
                print(f"  文本: {text}")
                
                # 简单的回复逻辑
                response = self.process_message(text, sender_id)
                if response:
                    self.send_message(chat_id, response)
            
            return {}
            
        except Exception as e:
            print(f"处理消息错误: {e}")
            return {}
    
    def process_message(self, text, user_id):
        """处理消息内容，返回回复"""
        text = text.strip().lower()
        
        # 简单的命令处理
        if text in ["你好", "hi", "hello"]:
            return "你好！我是 Omnia 的飞书助手 👋"
        
        elif text in ["时间", "几点"]:
            from datetime import datetime
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return f"现在时间是：{now}"
        
        elif text == "help":
            return """可用命令：
- 你好：打招呼
- 时间：查询当前时间
- help：显示帮助信息
- 其他消息会转发给 Omnia 处理"""
        
        else:
            # TODO: 对接 Omnia 后端处理
            return f"收到你的消息：{text}\n\n（我是 Omnia 的飞书助手，更多功能正在开发中...）"
    
    def send_message(self, chat_id, text):
        """发送消息到飞书"""
        try:
            client = create_client()
            
            # 构建请求
            request = CreateMessageRequest.builder() \
                .receive_id_type("chat_id") \
                .request_body(CreateMessageRequestBody.builder() \
                    .receive_id(chat_id) \
                    .msg_type("text") \
                    .content(json.dumps({"text": text})) \
                    .build()) \
                .build()
            
            # 发送
            response = client.im.v1.message.create(request)
            
            if response.success():
                print(f"  ✓ 消息已发送")
            else:
                print(f"  ✗ 发送失败: {response.msg}")
                
        except Exception as e:
            print(f"  发送消息错误: {e}")


def create_client():
    """创建飞书客户端"""
    return lark.Client.builder() \
        .app_id(APP_ID) \
        .app_secret(APP_SECRET) \
        .log_level(lark.LogLevel.DEBUG) \
        .build()


def start_longpoll_bot():
    """启动长连接机器人"""
    print("=" * 60)
    print("飞书机器人 - WebSocket 长连接模式")
    print("=" * 60)
    print(f"App ID: {APP_ID}")
    print(f"正在连接飞书开放平台...")
    print("-" * 60)
    
    # 创建客户端
    client = create_client()
    
    # 注册事件处理器
    dispatcher = lark.EventDispatcher.builder() \
        .register_p2_im_message_receive_v1(MessageHandler()) \
        .build()
    
    # 创建长连接客户端
    ws_client = lark.ws.Client(
        APP_ID,
        APP_SECRET,
        event_dispatcher=dispatcher,
        log_level=lark.LogLevel.DEBUG
    )
    
    print("✓ 长连接已建立")
    print("✓ 正在监听消息...")
    print("-" * 60)
    print("提示：在飞书中给机器人发消息试试！")
    print("按 Ctrl+C 退出")
    print("=" * 60)
    
    # 启动长连接
    ws_client.start()


def test_connection():
    """测试飞书连接"""
    print("测试飞书连接...")
    
    try:
        client = create_client()
        
        # 获取机器人信息
        request = GetBotInfoRequest.builder().build()
        response = client.im.v1.bot_info.get(request)
        
        if response.success():
            bot = response.data
            print(f"✓ 连接成功！")
            print(f"  机器人名称: {bot.bot_info.app_name}")
            print(f"  Open ID: {bot.bot_info.open_id}")
            return True
        else:
            print(f"✗ 连接失败: {response.msg}")
            return False
            
    except Exception as e:
        print(f"✗ 连接错误: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="飞书机器人")
    parser.add_argument("--test", action="store_true", help="测试连接")
    args = parser.parse_args()
    
    if args.test:
        test_connection()
    else:
        start_longpoll_bot()
