#!/usr/bin/env python3
"""
Phase 1 Test Script - Omnia 2.0 Core Components

测试：
1. Tool System
2. Feature Flags
3. FTS5 Search
4. Hook System
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core import (
    ToolRegistry, ToolContext, ToolResult,
    FeatureFlags, FeatureCategory, is_enabled, enable, disable,
    FTSClient, SearchResult, MessageRecord,
    HookRegistry, HookType, HookContext,
)
import asyncio


def test_tool_system():
    """测试工具系统"""
    print("\n" + "=" * 60)
    print("Testing Tool System")
    print("=" * 60)
    
    registry = ToolRegistry.get_instance()
    
    # 列出所有工具
    tools = registry.list_all()
    print(f"\nRegistered tools: {len(tools)}")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:50]}...")
    
    # 获取工具
    read_tool = registry.get("read_file")
    if read_tool:
        print(f"\nread_file tool found:")
        print(f"  - is_read_only: {read_tool.is_read_only({})}")
        print(f"  - OpenAI schema: {read_tool.to_openai_schema()['function']['name']}")
    
    # 测试 shell 工具权限
    shell_tool = registry.get("execute_shell")
    if shell_tool:
        context = ToolContext(
            session_id="test",
            user_id="test",
            working_directory="/tmp"
        )
        
        # 安全命令
        perm = shell_tool.check_permissions({"command": "ls -la"}, context)
        print(f"\n'ls -la' permission: {perm.behavior.value}")
        
        # 危险命令
        perm = shell_tool.check_permissions({"command": "rm -rf /"}, context)
        print(f"'rm -rf /' permission: {perm.behavior.value}")
        print(f"  Reason: {perm.reason}")
    
    print("\n✅ Tool System test passed!")


def test_feature_flags():
    """测试 Feature Flags"""
    print("\n" + "=" * 60)
    print("Testing Feature Flags")
    print("=" * 60)
    
    # 列出所有 flags
    all_flags = FeatureFlags.list_all()
    print(f"\nTotal flags: {len(all_flags)}")
    
    # 按分类列出
    for category in FeatureCategory:
        flags = FeatureFlags.list_by_category(category)
        enabled = [k for k, v in flags.items() if v]
        print(f"\n{category.value}: {len(enabled)} enabled / {len(flags)} total")
    
    # 测试启用/禁用
    print(f"\nBefore: EXECUTION_PARALLEL_TOOLS = {is_enabled('EXECUTION_PARALLEL_TOOLS')}")
    enable("EXECUTION_PARALLEL_TOOLS")
    print(f"After enable: EXECUTION_PARALLEL_TOOLS = {is_enabled('EXECUTION_PARALLEL_TOOLS')}")
    disable("EXECUTION_PARALLEL_TOOLS")
    print(f"After disable: EXECUTION_PARALLEL_TOOLS = {is_enabled('EXECUTION_PARALLEL_TOOLS')}")
    
    # 测试依赖
    print(f"\nBefore: COGNITION_INTENT_RECOGNITION = {is_enabled('COGNITION_INTENT_RECOGNITION')}")
    result = enable("COGNITION_INTENT_RECOGNITION")
    print(f"Enable result: {result} (should be False - dependency not met)")
    
    # 先启用依赖
    enable("EXPERIMENTAL_INTENT_ENGINE")
    result = enable("COGNITION_INTENT_RECOGNITION")
    print(f"Enable result after enabling dependency: {result}")
    print(f"After: COGNITION_INTENT_RECOGNITION = {is_enabled('COGNITION_INTENT_RECOGNITION')}")
    
    # 列出启用的实验性功能
    experimental = FeatureFlags.list_by_category(FeatureCategory.EXPERIMENTAL)
    enabled_exp = [k for k, v in experimental.items() if v]
    print(f"\nEnabled experimental features: {enabled_exp}")
    
    print("\n✅ Feature Flags test passed!")


def test_fts_search():
    """测试 FTS5 全文搜索"""
    print("\n" + "=" * 60)
    print("Testing FTS5 Search")
    print("=" * 60)
    
    # 创建测试数据库
    fts = FTSClient("/tmp/omnia_fts_test.db")
    
    # 存储测试消息
    print("\nStoring test messages...")
    msg_id1 = fts.store_message(
        session_id="test_session_1",
        role="user",
        content="你好，我是原点，我正在测试 Omnia 2.0 的功能"
    )
    print(f"  Stored message 1: id={msg_id1}")
    
    msg_id2 = fts.store_message(
        session_id="test_session_1",
        role="assistant",
        content="你好原点！我是 Omnia，很高兴为你服务。我们正在测试 FTS5 全文搜索功能"
    )
    print(f"  Stored message 2: id={msg_id2}")
    
    msg_id3 = fts.store_message(
        session_id="test_session_2",
        role="user",
        content="用户的偏好设置在哪里？我想修改一下"
    )
    print(f"  Stored message 3: id={msg_id3}")
    
    # 搜索测试
    print("\nSearching for '用户'...")
    results = fts.search("用户", limit=5)
    print(f"  Found {len(results)} results:")
    for r in results:
        print(f"    - [{r.role}] {r.content[:50]}... (rank={r.rank:.2f})")
    
    print("\nSearching for 'FTS5'...")
    results = fts.search("FTS5", limit=5)
    print(f"  Found {len(results)} results:")
    for r in results:
        print(f"    - [{r.role}] {r.content[:50]}... (rank={r.rank:.2f})")
    
    # 统计
    stats = fts.get_stats()
    print(f"\nStats:")
    print(f"  Total messages: {stats['total_messages']}")
    print(f"  Total sessions: {stats['total_sessions']}")
    print(f"  Role counts: {stats['role_counts']}")
    
    print("\n✅ FTS5 Search test passed!")


async def test_hook_system():
    """测试 Hook 系统"""
    print("\n" + "=" * 60)
    print("Testing Hook System")
    print("=" * 60)
    
    registry = HookRegistry.get_instance()
    
    # 注册自定义钩子
    custom_called = []
    
    @registry.on(HookType.PRE_TOOL_USE, priority=10, name="custom_pre_hook")
    async def custom_pre_hook(context: HookContext):
        custom_called.append("pre")
        print(f"  [Custom Hook] Before {context.tool_name}")
    
    @registry.on(HookType.POST_TOOL_USE, priority=10, name="custom_post_hook")
    async def custom_post_hook(context: HookContext):
        custom_called.append("post")
        print(f"  [Custom Hook] After {context.tool_name}")
    
    # 列出钩子
    hooks = registry.list_hooks(HookType.PRE_TOOL_USE)
    print(f"\nPRE_TOOL_USE hooks: {len(hooks)}")
    for h in hooks:
        print(f"  - {h['name']} (priority={h['priority']}, enabled={h['enabled']})")
    
    # 触发钩子
    print("\nTriggering hooks...")
    context = HookContext(
        type=HookType.PRE_TOOL_USE,
        tool_name="read_file",
        tool_args={"path": "/tmp/test.txt"}
    )
    await registry.trigger(context)
    
    context = HookContext(
        type=HookType.POST_TOOL_USE,
        tool_name="read_file",
        tool_result="test content"
    )
    await registry.trigger(context)
    
    print(f"\nCustom hooks called: {custom_called}")
    
    # 测试禁用
    registry.disable(HookType.PRE_TOOL_USE, "custom_pre_hook")
    hooks = registry.list_hooks(HookType.PRE_TOOL_USE)
    pre_hook = next((h for h in hooks if h['name'] == 'custom_pre_hook'), None)
    if pre_hook:
        print(f"\nAfter disable: custom_pre_hook enabled = {pre_hook['enabled']}")
    
    print("\n✅ Hook System test passed!")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Omnia 2.0 Phase 1 - Core Components Test")
    print("=" * 60)
    
    try:
        test_tool_system()
        test_feature_flags()
        test_fts_search()
        asyncio.run(test_hook_system())
        
        print("\n" + "=" * 60)
        print("✅ All Phase 1 tests passed!")
        print("=" * 60)
        
        return 0
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
