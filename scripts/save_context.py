#!/usr/bin/env python3
"""保存当前会话上下文

使用方法:
    python scripts/save_context.py "DJI诊断工具开发" "完成了USB通信模块，测试成功" --project "DJI诊断系统" --files "dji_knowledge_base.md" --next "完善Web界面" --next "测试更多设备"
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.context_manager import save_current_context


def main():
    parser = argparse.ArgumentParser(description="保存当前会话上下文")
    parser.add_argument("topic", help="会话主题")
    parser.add_argument("summary", help="会话摘要")
    parser.add_argument("--project", help="活跃项目名称")
    parser.add_argument("--files", nargs="*", help="活跃文件列表")
    parser.add_argument("--decisions", nargs="*", help="关键决策")
    parser.add_argument("--next", nargs="*", help="下一步计划")
    parser.add_argument("--conversation", help="原始对话内容（文件路径）")
    
    args = parser.parse_args()
    
    # 读取原始对话（如果提供了文件）
    raw_conversation = None
    if args.conversation:
        conv_path = Path(args.conversation)
        if conv_path.exists():
            raw_conversation = conv_path.read_text(encoding='utf-8')
    
    # 保存上下文
    save_current_context(
        topic=args.topic,
        summary=args.summary,
        active_project=args.project,
        active_files=args.files,
        key_decisions=args.decisions,
        next_steps=args.next,
        raw_conversation=raw_conversation,
    )
    
    print("✅ 上下文已保存")
    print(f"   主题: {args.topic}")
    print(f"   摘要: {args.summary}")
    if args.project:
        print(f"   项目: {args.project}")
    if args.next:
        print(f"   下一步: {', '.join(args.next)}")


if __name__ == "__main__":
    main()
