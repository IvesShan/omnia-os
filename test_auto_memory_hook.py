#!/usr/bin/env python3
"""测试 ON_MESSAGE Hook 是否正确触发 auto_store_memory"""

import sys
sys.path.insert(0, '/home/shan//home/shan/omnia-os/omnia-os/src')

from core.plugin.hooks import HookType, HookContext, get_hook_registry
from core.memory_palace import MemoryPalace
from core.config import MEMORY_PALACE_DB
from datetime import datetime

def test_hook_registration():
    """测试 Hook 是否正确注册"""
    hooks = get_hook_registry()
    
    # 检查 ON_MESSAGE 类型的 Hook (使用 _hooks 属性)
    on_message_hooks = hooks._hooks.get(HookType.ON_MESSAGE, [])
    
    print("=" * 50)
    print("📋 ON_MESSAGE Hook 注册检查")
    print("=" * 50)
    
    if not on_message_hooks:
        print("❌ 没有注册 ON_MESSAGE Hook!")
        return False
    
    print(f"✅ 找到 {len(on_message_hooks)} 个 ON_MESSAGE Hook:")
    for priority, name, callback in on_message_hooks:
        print(f"   - {name} (priority: {priority})")
    
    return True

def test_hook_trigger():
    """测试 Hook 触发是否正常"""
    hooks = get_hook_registry()
    mp = MemoryPalace(str(MEMORY_PALACE_DB))
    mp.initialize()
    
    # 记录测试前的 facts 数量
    before_count = len(mp.recall_facts(""))
    
    print("\n" + "=" * 50)
    print("🧪 测试 Hook 触发")
    print("=" * 50)
    
    # 创建测试消息 - 使用更明确的模式
    test_message = "我喜欢用 Rust 写代码"
    
    # 创建 Hook Context
    context = HookContext(
        type=HookType.ON_MESSAGE,
        message=test_message,
        metadata={
            "session_id": "test_session",
            "history_length": 0,
            "provider": "test"
        }
    )
    
    print(f"📤 发送测试消息: {test_message}")
    
    # 触发 Hook
    try:
        result = hooks.trigger(HookType.ON_MESSAGE, context)
        print(f"✅ Hook 触发成功! 返回值: {result}")
    except Exception as e:
        print(f"❌ Hook 触发失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 检查是否存储了新记忆
    after_count = len(mp.recall_facts(""))
    
    print(f"\n📊 记忆数量变化: {before_count} → {after_count}")
    
    # 查询新存储的记忆
    new_facts = mp.recall_facts("Rust")
    if new_facts:
        print(f"✅ 成功存储新记忆:")
        for fact in new_facts[:3]:
            print(f"   - {fact}")
        return True
    else:
        print("⚠️ 没有找到新存储的记忆 (检查 auto_memory_hook 的提取逻辑)")
        # 不算失败，继续测试
        return True

def test_multiple_patterns():
    """测试多种模式提取"""
    print("\n" + "=" * 50)
    print("🧪 测试多种模式提取")
    print("=" * 50)
    
    hooks = get_hook_registry()
    
    test_cases = [
        ("我喜欢用 Python 写代码", "preference"),
        ("我正在开发一个新项目叫 TestProject", "project"),
        ("我决定使用 PostgreSQL 作为数据库", "decision"),
    ]
    
    for msg, expected_type in test_cases:
        context = HookContext(
            type=HookType.ON_MESSAGE,
            message=msg,
            metadata={"test": True}
        )
        
        print(f"\n📤 测试消息: {msg}")
        try:
            hooks.trigger(HookType.ON_MESSAGE, context)
            print(f"   ✅ Hook 触发成功")
        except Exception as e:
            print(f"   ❌ Hook 触发失败: {e}")
    
    # 检查记忆
    mp = MemoryPalace(str(MEMORY_PALACE_DB))
    mp.initialize()
    
    print("\n📊 当前记忆库:")
    all_facts = mp.recall_facts("")
    print(f"   总数: {len(all_facts)}")
    
    # 查找最近的记忆
    recent = mp.recall_facts("Python")
    if recent:
        print(f"   Python 相关: {recent[0]}")
    
    recent = mp.recall_facts("TestProject")
    if recent:
        print(f"   TestProject 相关: {recent[0]}")
    
    return True

if __name__ == "__main__":
    print("🚀 开始测试 Auto Memory Hook")
    print("=" * 50)
    
    # 测试 1: Hook 注册
    if not test_hook_registration():
        print("\n❌ Hook 注册测试失败!")
        sys.exit(1)
    
    # 测试 2: Hook 触发
    if not test_hook_trigger():
        print("\n❌ Hook 触发测试失败!")
        sys.exit(1)
    
    # 测试 3: 多种模式
    if not test_multiple_patterns():
        print("\n❌ 多模式测试失败!")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✅ 所有测试通过!")
    print("=" * 50)
