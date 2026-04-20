#!/usr/bin/env python3
"""
启动 Omnia Gateway - 统一消息入口

用法：
    python3 scripts/start_omnia_gateway.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.gateway.runner import GatewayRunner
from gateway.webchat_adapter import WebChatAdapter
from gateway.chat_handler_wrapper import ChatHandlerWrapper


async def main():
    """启动 Omnia Gateway"""
    print("=" * 60)
    print("Omnia Gateway 启动中...")
    print("=" * 60)
    
    # 1. 创建 Gateway Runner
    print("\n[1/4] 创建 Gateway Runner...")
    runner = GatewayRunner.get_instance()
    print("      ✓ Gateway Runner 已创建")
    
    # 2. 创建 WebChat Adapter
    print("\n[2/4] 创建 WebChat Adapter...")
    webchat = WebChatAdapter()
    await webchat.start()
    print("      ✓ WebChat Adapter 已启动")
    
    # 3. 注册 Adapter
    print("\n[3/4] 注册 WebChat Adapter...")
    await runner.register_adapter(webchat)
    print("      ✓ WebChat Adapter 已注册")
    
    # 4. 启动 Gateway
    print("\n[4/4] 启动 Gateway...")
    await runner.start()
    print("      ✓ Gateway 已启动")
    
    print("\n" + "=" * 60)
    print("✓ Omnia Gateway 运行中！")
    print("=" * 60)
    print("\n支持的通道：")
    print("  - WebChat (http://127.0.0.1:5001)")
    print("\n按 Ctrl+C 停止...")
    
    try:
        # 保持运行
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\n正在停止...")
        await webchat.stop()
        await runner.stop()
        print("✓ 已停止")


if __name__ == "__main__":
    asyncio.run(main())
