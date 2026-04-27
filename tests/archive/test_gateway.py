#!/usr/bin/env python3
"""测试 Omnia Gateway 架构"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.gateway.runner import GatewayRunner, ChannelType
from gateway.webchat_adapter import WebChatAdapter


async def test_gateway():
    """测试 Gateway 基本功能"""
    
    print("=== Omnia Gateway 测试 ===\n")
    
    # 1. 创建 Gateway Runner
    print("1. 创建 Gateway Runner...")
    runner = GatewayRunner.get_instance()
    print("   ✓ Gateway Runner 已创建\n")
    
    # 2. 创建 WebChat Adapter
    print("2. 创建 WebChat Adapter...")
    webchat = WebChatAdapter()
    await webchat.start()
    print("   ✓ WebChat Adapter 已启动\n")
    
    # 3. 注册 Adapter
    print("3. 注册 WebChat Adapter...")
    await runner.register_adapter(webchat)  # 只需要 adapter 对象
    print("   ✓ WebChat Adapter 已注册\n")
    
    # 4. 模拟接收消息
    print("4. 模拟接收消息...")
    
    async def handle_message(event):
        print(f"   收到消息:")
        print(f"   - Channel: {event.channel.value}")
        print(f"   - User ID: {event.user_id}")
        print(f"   - Content: {event.content}")
    
    webchat._on_message = handle_message
    
    await webchat.receive_message(
        user_id="test_user",
        chat_id="test_chat",
        content="你好，Omnia！"
    )
    print("   ✓ 消息处理完成\n")
    
    # 5. 清理
    print("5. 清理...")
    await webchat.stop()
    print("   ✓ WebChat Adapter 已停止\n")
    
    print("=== 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(test_gateway())
