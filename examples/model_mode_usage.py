#!/usr/bin/env python3
"""
模型模式使用示例

演示三种方式切换模型模式：
1. 环境变量
2. 命令行工具
3. Python 代码
"""

import asyncio
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.providers.smart_router import (
    SmartModelRouter,
    set_model_mode,
    get_model_mode,
    smart_chat
)


async def demo_mode_switching():
    """演示模式切换"""
    
    print("=" * 60)
    print("Omnia 模型模式使用示例")
    print("=" * 60)
    print()
    
    # 方式1：查看当前模式
    print("【方式1】查看当前模式")
    print(f"  当前模式: {get_model_mode()}")
    print()
    
    # 方式2：Python 代码切换
    print("【方式2】Python 代码切换")
    
    print("\n切换到本地模式...")
    set_model_mode("local_only")
    print(f"  当前模式: {get_model_mode()}")
    
    print("\n切换到云端模式...")
    set_model_mode("cloud_only")
    print(f"  当前模式: {get_model_mode()}")
    
    print("\n切换回自动模式...")
    set_model_mode("auto")
    print(f"  当前模式: {get_model_mode()}")
    print()
    
    # 方式3：单次请求指定模式
    print("【方式3】单次请求指定模式")
    print("  smart_chat(messages, mode='local_only')  # 这次只用本地")
    print("  smart_chat(messages, mode='cloud_only')  # 这次只用云端")
    print()
    
    # 方式4：环境变量
    print("【方式4】环境变量（启动前设置）")
    print("  export OMNIA_MODEL_MODE=local_only")
    print("  export OMNIA_MODEL_MODE=cloud_only")
    print("  export OMNIA_MODEL_MODE=auto")
    print()
    
    # 方式5：命令行工具
    print("【方式5】命令行工具")
    print("  bash scripts/model_mode.sh local  # 只用本地")
    print("  bash scripts/model_mode.sh cloud  # 只用云端")
    print("  bash scripts/model_mode.sh auto   # 智能选择")
    print("  bash scripts/model_mode.sh status # 查看状态")
    print()
    
    # 测试本地模型
    print("=" * 60)
    print("测试本地模型")
    print("=" * 60)
    
    set_model_mode("local_only")
    
    messages = [
        {"role": "user", "content": "你好，请用一句话介绍你自己"}
    ]
    
    try:
        print("\n发送请求到本地模型...")
        response = await smart_chat(messages)
        print(f"\n响应: {response}")
    except Exception as e:
        print(f"\n错误: {e}")
        print("请确保本地服务已启动: bash scripts/local_llm.sh start")


if __name__ == "__main__":
    asyncio.run(demo_mode_switching())
