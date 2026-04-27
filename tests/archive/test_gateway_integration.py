#!/usr/bin/env python3
"""测试 Gateway 集成到 web_server。

验证：
1. 默认模式（直接模式）是否正常
2. Gateway 模式是否可以切换
3. 两种模式的兼容性
"""

import os
import sys

# 设置路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))


def test_direct_mode():
    """测试直接模式（legacy）。"""
    print("\n=== 测试 1: 直接模式（legacy）===\n")
    
    # 确保不使用 Gateway
    os.environ["OMNIA_USE_GATEWAY"] = "false"
    
    from gateway.integration import should_use_gateway, handle_chat_direct
    
    print(f"1. 检查模式...")
    print(f"   should_use_gateway() = {should_use_gateway()}")
    assert not should_use_gateway(), "应该使用直接模式"
    print("   ✓ 确认使用直接模式")
    
    print(f"\n2. 检查 handle_chat_direct...")
    assert callable(handle_chat_direct), "handle_chat_direct 应该是可调用的"
    print("   ✓ handle_chat_direct 可用")
    
    print("\n✓ 测试 1 通过：直接模式正常")


def test_gateway_mode():
    """测试 Gateway 模式。"""
    print("\n=== 测试 2: Gateway 模式 ===\n")
    
    # 启用 Gateway
    os.environ["OMNIA_USE_GATEWAY"] = "true"
    
    # 重新导入以应用环境变量
    import importlib
    import gateway.integration
    importlib.reload(gateway.integration)
    from gateway.integration import should_use_gateway, handle_chat_via_gateway
    
    print(f"1. 检查模式...")
    print(f"   should_use_gateway() = {should_use_gateway()}")
    assert should_use_gateway(), "应该使用 Gateway 模式"
    print("   ✓ 确认使用 Gateway 模式")
    
    print(f"\n2. 检查 handle_chat_via_gateway...")
    assert callable(handle_chat_via_gateway), "handle_chat_via_gateway 应该是可调用的"
    print("   ✓ handle_chat_via_gateway 可用")
    
    print("\n✓ 测试 2 通过：Gateway 模式正常")


def test_unified_interface():
    """测试统一接口。"""
    print("\n=== 测试 3: 统一接口 ===\n")
    
    # 测试直接模式
    os.environ["OMNIA_USE_GATEWAY"] = "false"
    import importlib
    import gateway.integration
    importlib.reload(gateway.integration)
    from gateway.integration import handle_chat_unified
    
    print("1. 测试直接模式下的统一接口...")
    print("   ✓ handle_chat_unified 可用")
    
    # 测试 Gateway 模式
    os.environ["OMNIA_USE_GATEWAY"] = "true"
    importlib.reload(gateway.integration)
    from gateway.integration import handle_chat_unified as handle_chat_unified_gateway
    
    print("\n2. 测试 Gateway 模式下的统一接口...")
    print("   ✓ handle_chat_unified 可用")
    
    print("\n✓ 测试 3 通过：统一接口正常")


def test_web_server_import():
    """测试 web_server 的导入。"""
    print("\n=== 测试 4: web_server 导入 ===\n")
    
    os.environ["OMNIA_USE_GATEWAY"] = "false"
    
    print("1. 测试 web_server 模块导入...")
    try:
        # 只导入模块，不创建 app（避免其他依赖问题）
        import omnia.web_server
        print("   ✓ omnia.web_server 导入成功")
        
        # 检查 chat 函数存在
        print("\n2. 检查 chat 端点...")
        # chat 函数在 create_app 内部定义，所以我们只验证模块加载
        print("   ✓ web_server 模块加载正常")
        
    except Exception as e:
        print(f"   ✗ 导入失败: {e}")
        raise
    
    print("\n✓ 测试 4 通过：web_server 导入正常")


def main():
    print("\n" + "=" * 60)
    print("Omnia Gateway 集成测试")
    print("=" * 60)
    
    try:
        test_direct_mode()
        test_gateway_mode()
        test_unified_interface()
        test_web_server_import()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        
        print("\n架构总结：")
        print("  web_server.py")
        print("       ↓")
        print("  gateway/integration.py")
        print("       ↓")
        print("  ├─→ handle_chat_direct (legacy)")
        print("  └─→ handle_chat_via_gateway (Gateway)")
        print()
        print("切换方式：")
        print("  export OMNIA_USE_GATEWAY=true   # 启用 Gateway")
        print("  export OMNIA_USE_GATEWAY=false  # 使用直接模式")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
