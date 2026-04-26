#!/usr/bin/env python3
"""
Token 管理功能测试

测试：
- Token 估算
- 上下文溢出检测
- 智能压缩
- API 端点
"""

import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.cognition.token_manager import (
    estimate_text_tokens,
    estimate_messages_tokens,
    check_context_overflow,
    smart_compress_history,
    get_model_context_window,
    get_token_stats,
    MODEL_CONTEXT_WINDOWS
)


def test_token_estimation():
    """测试 Token 估算"""
    print("\n" + "="*60)
    print("📊 Token 估算测试")
    print("="*60)
    
    # 测试文本
    texts = [
        "Hello, world!",
        "你好，世界！这是一段中文测试文本。",
        "def hello():\n    print('Hello, world!')\n    return True",
        "这是一个混合文本 Mixed text with 中文 and English."
    ]
    
    for text in texts:
        tokens = estimate_text_tokens(text)
        print(f"\n文本: {text[:50]}...")
        print(f"  字符数: {len(text)}")
        print(f"  Token 数: {tokens}")
        print(f"  比例: {len(text)/tokens:.2f} 字符/token")


def test_context_overflow():
    """测试上下文溢出检测"""
    print("\n" + "="*60)
    print("🔍 上下文溢出检测测试")
    print("="*60)
    
    # 创建不同长度的消息列表
    short_messages = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮你的吗？"}
    ]
    
    long_messages = []
    for i in range(100):
        long_messages.append({"role": "user", "content": f"这是第 {i} 条消息，包含一些内容来增加 token 数量。"})
        long_messages.append({"role": "assistant", "content": f"收到第 {i} 条消息，这是回复内容，也包含一些文字来增加 token 数量。"})
    
    # 测试不同模型
    models = ["kimi", "qianfan", "gpt-4o", "local"]
    
    print("\n短消息列表 (2 条):")
    for model in models:
        result = check_context_overflow(short_messages, model)
        print(f"  {model:15} - 利用率: {result['utilization']*100:5.1f}%, 溢出: {result['overflow']}")
    
    print("\n长消息列表 (200 条):")
    for model in models:
        result = check_context_overflow(long_messages, model)
        print(f"  {model:15} - 利用率: {result['utilization']*100:6.1f}%, 溢出: {result['overflow']}, 警告: {result['warning']}")


def test_smart_compression():
    """测试智能压缩"""
    print("\n" + "="*60)
    print("🗜️ 智能压缩测试")
    print("="*60)
    
    # 创建需要压缩的消息列表
    messages = []
    for i in range(50):
        messages.append({
            "role": "user",
            "content": f"用户消息 {i}: 这是一条比较长的用户消息，包含足够的内容来测试压缩效果。"
        })
        messages.append({
            "role": "assistant",
            "content": f"助手回复 {i}: 这是一条比较长的助手回复，同样包含足够的内容来测试压缩效果。"
        })
    
    # 添加一条系统消息
    messages.insert(0, {"role": "system", "content": "你是一个智能助手。"})
    
    print(f"\n原始消息数: {len(messages)}")
    print(f"原始 Token 数: {estimate_messages_tokens(messages)}")
    
    # 测试不同模型的压缩效果
    for model in ["kimi", "qianfan"]:
        print(f"\n--- 模型: {model} ---")
        compressed, stats = smart_compress_history(messages, model, preserve_recent=10)
        
        print(f"压缩后消息数: {len(compressed)}")
        print(f"压缩后 Token 数: {estimate_messages_tokens(compressed)}")
        print(f"压缩统计: {stats}")


def test_model_context_windows():
    """测试模型上下文窗口配置"""
    print("\n" + "="*60)
    print("📋 模型上下文窗口配置")
    print("="*60)
    
    print(f"\n支持的模型数量: {len(MODEL_CONTEXT_WINDOWS)}")
    print("\n模型列表:")
    print("-" * 60)
    
    for name, config in MODEL_CONTEXT_WINDOWS.items():
        print(f"  {name:20} | 上下文: {config.context_window:8,} tokens | "
              f"输出: {config.max_output:5,} | 推荐利用率: {config.recommended_utilization*100:.0f}%")


def test_token_stats():
    """测试 Token 统计"""
    print("\n" + "="*60)
    print("📈 Token 统计测试")
    print("="*60)
    
    messages = [
        {"role": "system", "content": "你是一个智能助手。"},
        {"role": "user", "content": "你好，请问今天天气怎么样？"},
        {"role": "assistant", "content": "你好！抱歉，我无法获取实时天气信息。建议你查看天气预报应用或网站。"},
        {"role": "user", "content": "好的，谢谢。"},
        {"role": "assistant", "content": "不客气！还有什么可以帮你的吗？"}
    ]
    
    stats = get_token_stats(messages, "kimi")
    
    print(f"\n总 Token 数: {stats['total_tokens']}")
    print(f"消息数: {stats['message_count']}")
    print(f"模型: {stats['model']}")
    print(f"上下文窗口: {stats['context_window']:,}")
    print(f"利用率: {stats['utilization']*100:.2f}%")
    print(f"剩余 Token: {stats['remaining_tokens']:,}")
    
    print("\n按角色统计:")
    for role, info in stats['role_breakdown'].items():
        print(f"  {role:10} - 消息数: {info['count']:3}, Tokens: {info['tokens']:5}")


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🚀 Token 管理功能测试")
    print("="*60)
    
    try:
        test_token_estimation()
        test_context_overflow()
        test_smart_compression()
        test_model_context_windows()
        test_token_stats()
        
        print("\n" + "="*60)
        print("✅ 所有测试通过！")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
