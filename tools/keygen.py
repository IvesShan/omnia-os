#!/usr/bin/env python3
"""
Omnia 商业版卡密生成器 v3.0
===========================
使用统一的授权系统生成卡密

用法：
  python keygen.py --type monthly --count 10
  python keygen.py --type monthly --count 10 --output keys.txt
"""

import argparse
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from omnia.license import generate_license_key, LICENSE_TYPES


def main():
    parser = argparse.ArgumentParser(description="Omnia 商业版卡密生成器 v3.0")
    parser.add_argument(
        "--type", "-t",
        choices=["trial", "monthly", "quarterly", "yearly", "perpetual"],
        required=True,
        help="授权类型"
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=1,
        help="生成数量 (默认: 1)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="输出文件 (默认: 直接输出到控制台)"
    )

    args = parser.parse_args()

    # 映射类型名到类型字符
    type_map = {
        "trial": "T",
        "monthly": "M",
        "quarterly": "Q",
        "yearly": "Y",
        "perpetual": "P",
    }

    type_char = type_map[args.type]
    type_info = LICENSE_TYPES[type_char]

    print(f"\n{'='*60}")
    print(f"  Omnia 卡密生成器 v3.0")
    print(f"{'='*60}")
    print(f"  类型: {type_info['label']} ({type_info['days']}天)")
    print(f"  数量: {args.count}")
    print(f"  格式: OMNI-XXXX-XXXX-XXXX-XXXX")
    print(f"{'='*60}\n")

    keys = []
    for i in range(args.count):
        key = generate_license_key(type_char)
        keys.append(key)
        print(f"  [{i+1:3d}] {key}")

    print(f"\n{'='*60}")
    print(f"  ✅ 已生成 {args.count} 个卡密")
    print(f"{'='*60}\n")

    # 输出到文件
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(f"Omnia 商业版卡密\n")
            f.write(f"类型: {type_info['label']}\n")
            f.write(f"数量: {args.count}\n")
            f.write(f"{'='*40}\n\n")
            for key in keys:
                f.write(f"{key}\n")
        print(f"  📁 已保存到: {args.output}")


if __name__ == "__main__":
    main()
