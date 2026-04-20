#!/usr/bin/env python3
"""
飞书机器人 WebSocket 长连接 - 修复版
"""
import os
import sys
import json
import logging
import requests
from pathlib import Path

# 设置详细日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import lark_oapi as lark
from lark_oapi.api.im.v1 import P2ImMessageReceiveV1, CreateMessageRequest, CreateMessageRequestBody

# 配置
APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")

# Omnia API 地址
OMNIA_API = "http://127.0.0.1:5001"

print(f"[配置] APP_ID: {APP_ID}")
print(f"[配置] APP_SECRET: {APP_SECRET[:10]}..." if APP_SECRET else "[配置] APP_SECRET 未设置")

# 创建客户端
client = lark.Client.builder() \
    .app_id(APP_ID) \
    .app_secret(APP_SECRET) \
    .log_level(lark.LogLevel.INFO) \
    .build()

def call_omnia_chat(message: str, user_id: str = None) -> str:
    """调用 Omnia 聊天 API"""
    try:
        response = requests.post(
            f"{OMNIA_API}/api/chat",
            json={
                "message": message,
                "history": [],
                "user_id": user_id
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("reply", "抱歉，我暂时无法回复")
        else:
            return f"Omnia API 错误: {response.status_code}"
            
    except requests.exceptions.ConnectionError:
        return "⚠️ Omnia 服务未启动，请先启动 Omnia"
    except Exception as e:
        return f"连接 Omnia 失败: {e}"

def handle_message(event: P2ImMessageReceiveV1):
    """处理消息事件"""
    print("\n" + "="*50)
    print("[收到消息]")
    print(f"  事件类型: {event.header.event_type}")
    print(f"  消息类型: {event.event.message.message_type}")
    print(f"  消息内容: {event.event.message.content}")
    print(f"  发送者: {event.event.sender.sender_id.open_id}")
    print("="*50 + "\n")
    
    try:
        # 解析消息内容
        content = json.loads(event.event.message.content)
        text = content.get("text", "")
        print(f"[解析] 文本内容: {text}")
        
        # 调用 Omnia
        reply_text = call_omnia_chat(text, event.event.sender.sender_id.open_id)
        
        # 发送回复
        send_reply(
            event.event.sender.sender_id.open_id,
            reply_text
        )
        
    except Exception as e:
        print(f"[错误] {e}")
        import traceback
        traceback.print_exc()

def send_reply(open_id: str, text: str):
    """发送回复消息"""
    try:
        request = CreateMessageRequest.builder() \
            .receive_id_type("open_id") \
            .request_body(CreateMessageRequestBody.builder()
                .receive_id(open_id)
                .msg_type("text")
                .content(json.dumps({"text": text}))
                .build()) \
            .build()
        
        response = client.im.v1.message.create(request)
        
        if response.success():
            print(f"[回复] 成功")
        else:
            print(f"[回复] 失败: {response.code} - {response.msg}")
            
    except Exception as e:
        print(f"[错误] 发送消息失败: {e}")

def main():
    print("\n" + "="*50)
    print("飞书机器人启动")
    print("="*50)
    
    if not APP_ID or not APP_SECRET:
        print("[错误] 缺少配置")
        return
    
    # 创建事件处理器
    event_handler = lark.EventDispatcherHandler.builder(
        encrypt_key="",
        verification_token="",
        level=lark.LogLevel.INFO
    ).register_p2_im_message_receive_v1(handle_message).build()
    
    print("[事件] 已注册消息处理器")
    
    # 创建 WebSocket 客户端
    ws_client = lark.ws.Client(
        app_id=APP_ID,
        app_secret=APP_SECRET,
        event_handler=event_handler,
        log_level=lark.LogLevel.INFO
    )
    
    print("[WebSocket] 开始连接...")
    print(f"[Omnia] API 地址: {OMNIA_API}")
    
    # 启动
    try:
        ws_client.start()
    except KeyboardInterrupt:
        print("\n[停止] 收到中断信号")
    except Exception as e:
        print(f"[错误] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
