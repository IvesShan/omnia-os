#!/usr/bin/env python3
"""
Token 管理测试

测试 token 估算、上下文窗口查询和压缩功能。
"""

import sys
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.cognition.token_manager import (
    estimate_tokens,
    estimate_messages_tokens,
    get_model_context_window,
    check_context_overflow,
    smart_compress_history,
    trim_messages_to_fit,
)


def test_estimate_tokens():
    """测试 token 估算"""
    print("\n" + "="*60)
    print("测试 1: Token 估算")
    print("="*60)
    
    test_cases = [
        ("Hello, world!", "英文短句"),
        ("你好，世界！", "中文短句"),
        ("Hello 你好 World 世界", "中英混合"),
        ("def hello():\n    print('Hello')", "代码"),
        ("这是一个很长的中文句子，包含了很多字符，用来测试 token 估算的准确性。", "长中文"),
        ("This is a long English sentence that contains many words to test the accuracy of token estimation.", "长英文"),
    ]
    
    for text, desc in test_cases:
        tokens = estimate_tokens(text)
        print(f"\n{desc}:")
        print(f"  文本: {text[:50]}{'...' if len(text) > 50 else ''}")
        print(f"  字符数: {len(text)}")
        print(f"  估算 tokens: {tokens}")
        print(f"  平均每 token 字符数: {len(text)/tokens:.1f}")


def test_estimate_messages():
    """测试消息 token 估算"""
    print("\n" + "="*60)
    print("测试 2: 消息列表 Token 估算")
    print("="*60)
    
    messages = [
        {"role": "system", "content": "你是一个有帮助的 AI 助手。"},
        {"role": "user", "content": "你好，请问你能做什么？"},
        {"role": "assistant", "content": "你好！我可以帮助你回答问题、编写代码、分析数据等。有什么我可以帮助你的吗？"},
        {"role": "user", "content": "帮我写一个 Python 函数，计算斐波那契数列。"},
        {"role": "assistant", "content": "好的，这是一个计算斐波那契数列的 Python 函数：\n\ndef fibonacci(n):\n    if n <= 0:\n        return []\n    elif n == 1:\n        return [0]\n    elif n == 2:\n        return [0, 1]\n    \n    fib = [0, 1]\n    for i in range(2, n):\n        fib.append(fib[i-1] + fib[i-2])\n    return fib\n\n使用方法：\nprint(fibonacci(10))  # 输出: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]"},
    ]
    
    total_tokens = estimate_messages_tokens(messages)
    
    print(f"\n消息数量: {len(messages)}")
    print(f"总 tokens: {total_tokens}")
    print(f"\n各消息 tokens:")
    
    for i, msg in enumerate(messages):
        msg_tokens = estimate_messages_tokens([msg])
        print(f"  [{i}] {msg['role']}: {msg_tokens} tokens")


def test_context_windows():
    """测试模型上下文窗口查询"""
    print("\n" + "="*60)
    print("测试 3: 模型上下文窗口")
    print("="*60)
    
    models = [
        "kimi",
        "K2.6-code-preview",
        "qianfan",
        "qianfan-code-latest",
        "gpt-4o",
        "gpt-3.5-turbo",
        "deepseek-chat",
        "local",
        "unknown-model",
    ]
    
    print("\n模型上下文窗口大小：")
    for model in models:
        window = get_model_context_window(model)
        print(f"  {model:25s} -> {window:>7,} tokens")


def test_context_overflow():
    """测试上下文溢出检测"""
    print("\n" + "="*60)
    print("测试 4: 上下文溢出检测")
    print("="*60)
    
    # 创建一个很长的消息列表
    long_messages = []
    for i in range(100):
        long_messages.append({
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"这是第 {i} 条消息。" * 50  # 每条消息约 300 字符
        })
    
    # 测试不同模型
    models = ["kimi", "qianfan", "local"]
    
    for model in models:
        overflow = check_context_overflow(long_messages, model)
        print(f"\n模型: {model}")
        print(f"  当前 tokens: {overflow['current_tokens']:,}")
        print(f"  最大 tokens: {overflow['max_tokens']:,}")
        print(f"  利用率: {overflow['utilization']:.1%}")
        print(f"  是否溢出: {'⚠️ 是' if overflow['overflow'] else '✅ 否'}")


def test_smart_compress():
    """测试智能压缩"""
    print("\n" + "="*60)
    print("测试 5: 智能压缩")
    print("="*60)
    
    # 创建一个很长的消息列表
    messages = [
        {"role": "system", "content": "你是一个有帮助的 AI 助手。"},
    ]
    
    for i in range(50):
        messages.append({
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"这是第 {i} 条消息，包含一些内容。" * 20
        })
    
    print(f"\n原始消息数: {len(messages)}")
    print(f"原始 tokens: {estimate_messages_tokens(messages):,}")
    
    # 测试压缩
    models = ["qianfan", "kimi"]
    
    for model in models:
        print(f"\n压缩模型: {model}")
        compressed, stats = smart_compress_history(messages, model)
        
        print(f"  压缩后消息数: {len(compressed)}")
        print(f"  压缩后 tokens: {stats['final_tokens']:,}")
        print(f"  压缩率: {stats['compression_ratio']:.1%}")
        print(f"  节省 tokens: {stats['original_tokens'] - stats['final_tokens']:,}")


def test_trim_messages():
    """测试消息裁剪"""
    print("\n" + "="*60)
    print("测试 6: 消息裁剪")
    print("="*60)
    
    # 创建消息列表
    messages = [{"role": "system", "content": "系统提示词"}]
    
    for i in range(30):
        messages.append({
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"消息 {i}: " + "这是一段较长的内容，用来测试裁剪功能。" * 10
        })
    
    print(f"\n原始消息数: {len(messages)}")
    print(f"原始 tokens: {estimate_messages_tokens(messages):,}")
    
    # 裁剪到适应 Qianfan 的上下文窗口
    trimmed, tokens = trim_messages_to_fit(
        messages,
        model="qianfan",
        max_output_tokens=2000,
        system_prompt_tokens=500,
        preserve_recent=5,
    )
    
    print(f"\n裁剪后消息数: {len(trimmed)}")
    print(f"裁剪后 tokens: {tokens:,}")
    
    # 显示保留的消息
    print(f"\n保留的消息:")
    for i, msg in enumerate(trimmed):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")[:50]
        print(f"  [{i}] {role}: {content}...")


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Token 管理测试套件")
    print("="*60)
    
    try:
        test_estimate_tokens()
        test_estimate_messages()
        test_context_windows()
        test_context_overflow()
        test_smart_compress()
        test_trim_messages()
        
        print("\n" + "="*60)
        print("✅ 所有测试完成！")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
