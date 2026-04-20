#!/usr/bin/env python3
"""
飞书机器人增强版 - 集成 URL 检测和中断功能
"""

import os
import sys
import json
import time
import threading
import lark_oapi as lark

# 添加项目路径
sys.path.insert(0, '/home/shan/.openclaw/workspace/omnia-os')

# 导入 URL 检测模块
from src.omnia.url_detector import extract_urls, is_url_message, get_primary_url, get_url_type

# 导入中断管理模块
from src.omnia.interrupt_manager import set_interrupt, clear_interrupt, check_interrupt, init_interrupt_system

# ==================== 配置 ====================
APP_ID = os.getenv("FEISHU_APP_ID", "cli_a95407a7b7f8500d")
APP_SECRET = os.getenv("FEISHU_APP_SECRET", "lqBZvLbCJUfBqHl9hYz4NbFgMjRkMpTn")

# 飞书客户端
client = None

# ==================== 初始化 ====================
init_interrupt_system()

# ==================== 消息处理器 ====================
@lark.ws.def_handler
def handle_message(event: lark.ws.event.Event):
    """处理接收到的消息"""
    try:
        # 检查是否是中断指令
        if check_interrupt_command(event):
            return
        
        # 获取消息内容
        message = event.message
        content = json.loads(message.content) if message.content else {}
        
        # 获取文本内容
        text = content.get("text", "") if isinstance(content, dict) else ""
        
        print(f"\n{'='*50}")
        print(f"📨 收到消息:")
        print(f"  发送者: {message.sender_id}")
        print(f"  消息类型: {message.message_type}")
        print(f"  内容: {text}")
        
        # 检测 URL
        if is_url_message(text):
            urls = extract_urls(text)
            primary_url = get_primary_url(text)
            url_type = get_url_type(primary_url) if primary_url else "未知"
            
            print(f"\n🔗 检测到 URL:")
            print(f"  URL: {primary_url}")
            print(f"  类型: {url_type}")
            
            # 回复用户
            reply_text = f"检测到你发送了链接：\n\n{primary_url}\n\n类型：{url_type}\n\n我可以帮你：\n1. 查看网页内容\n2. 搜索相关信息\n\n请告诉我你想做什么？"
            send_reply(message.chat_id, reply_text)
        else:
            # 普通消息处理
            print(f"\n💬 普通消息")
            handle_normal_message(message.chat_id, text)
        
    except Exception as e:
        print(f"❌ 处理消息失败: {e}")
        import traceback
        traceback.print_exc()


def check_interrupt_command(event: lark.ws.event.Event) -> bool:
    """检查是否是中断指令"""
    try:
        message = event.message
        content = json.loads(message.content) if message.content else {}
        text = content.get("text", "") if isinstance(content, dict) else ""
        
        # 检查是否以 "/" 开头
        if text.strip().startswith("/"):
            command = text.strip()[1:].strip()  # 移除 "/"
            
            if command in ["stop", "终止", "取消", "cancel"]:
                print(f"\n⏹️ 收到中断指令: {text}")
                set_interrupt("用户请求终止")
                send_reply(message.chat_id, "✅ 已终止当前任务")
                return True
            else:
                print(f"\n❓ 未知指令: {command}")
                send_reply(message.chat_id, f"未知指令: /{command}\n\n可用指令:\n/stop - 终止任务\n/cancel - 取消操作")
                return True
        
        return False
    except Exception as e:
        print(f"❌ 检查中断指令失败: {e}")
        return False


def handle_normal_message(chat_id: str, text: str):
    """处理普通消息"""
    # 这里可以集成 Omnia 的聊天处理逻辑
    # 暂时返回简单回复
    reply_text = f"收到你的消息：{text}\n\n我是 Omnia 助手，我可以：\n1. 打开并查看网页（发送 URL）\n2. 使用 /stop 终止任务\n\n更多功能正在开发中..."
    send_reply(chat_id, reply_text)


def send_reply(chat_id: str, text: str):
    """发送回复消息"""
    global client
    
    try:
        # 构造消息请求
        request = lark.api.im.v1.message.create.request_builder() \
            .receive_id_type("chat_id") \
            .request_body(lark.api.im.v1.message.create.request_body_builder()
                .receive_id(chat_id)
                .msg_type("text")
                .content(json.dumps({"text": text}))
                .build()) \
            .build()
        
        # 发送消息
        response = client.im.v1.message.create(request)
        
        if response.success():
            print(f"✅ 消息已发送")
        else:
            print(f"❌ 发送失败: {response.code} - {response.msg}")
            
    except Exception as e:
        print(f"❌ 发送消息异常: {e}")
        import traceback
        traceback.print_exc()


# ==================== 主函数 ====================
def main():
    """启动飞书机器人"""
    global client
    
    print("="*60)
    print("🤖 飞书机器人增强版启动中...")
    print("="*60)
    print(f"App ID: {APP_ID}")
    print(f"功能: URL 检测 + 中断指令")
    print("="*60)
    
    # 创建飞书客户端
    client = lark.Client.builder() \
        .app_id(APP_ID) \
        .app_secret(APP_SECRET) \
        .log_level(lark.LogLevel.ERROR) \
        .build()
    
    print("\n✅ 飞书客户端已创建")
    
    # 创建 WebSocket 客户端
    ws_client = lark.ws.Client(
        app_id=APP_ID,
        app_secret=APP_SECRET,
        event_handler=handle_message,
        log_level=lark.LogLevel.INFO
    )
    
    print("✅ WebSocket 客户端已创建")
    print("🔗 正在连接飞书服务器...\n")
    
    # 启动 WebSocket 连接
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
