#!/usr/bin/env python3
"""
Omnia 商业版卡密生成器
用途：生成月卡、季卡、年卡卡密
运行：python keygen.py --type monthly --count 10
"""

import argparse
import hashlib
import hmac
import json
import os
import secrets
import string
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
# 🔐 签名密钥 - 请修改为你自己的密钥！
# 这个密钥必须与 license.py 中的完全一致
# ============================================================
MASTER_KEY = "Omnia-Commercial-License-2025-SecretKey-Change-Me!"

# 授权类型
LICENSE_TYPES = {
    "monthly": {"days": 30, "label": "月卡", "price": 88},
    "quarterly": {"days": 90, "label": "季卡", "price": 198},
    "yearly": {"days": 365, "label": "年卡", "price": 398},
}


def generate_license_key(license_type: str, expire_date: datetime) -> str:
    """
    生成卡密
    格式：XXXX-XXXX-XXXX-XXXX (16位，不含易混淆字符)
    """
    # 只用不易混淆的字符
    charset = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    
    # 生成随机部分 (8位)
    random_part = ''.join(secrets.choice(charset) for _ in range(8))
    
    # 构造卡密数据
    data = {
        "type": license_type,
        "expire": expire_date.strftime("%Y-%m-%d"),
        "random": random_part,
    }
    
    # 计算 HMAC 签名
    data_str = json.dumps(data, sort_keys=True)
    signature = hmac.new(
        MASTER_KEY.encode(),
        data_str.encode(),
        hashlib.sha256
    ).hexdigest()[:8].upper()
    
    # 组合卡密：随机部分 + 类型标识 + 签名
    # 类型标识: M=月卡, Q=季卡, Y=年卡
    type_char = {"monthly": "M", "quarterly": "Q", "yearly": "Y"}[license_type]
    
    # 最终卡密格式：8位随机 + 1位类型 + 3位签名 + 4位补充
    key = f"{random_part[:4]}-{random_part[4:]}-{type_char}{signature[:2]}-{signature[2:]}"
    
    return key


def save_license_data(key: str, license_type: str, expire_date: datetime, output_file: str):
    """保存卡密及其元数据"""
    data = {
        "key": key,
        "type": license_type,
        "type_label": LICENSE_TYPES[license_type]["label"],
        "expire": expire_date.strftime("%Y-%m-%d"),
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "price": LICENSE_TYPES[license_type]["price"],
    }
    
    # 追加到文件
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(f"{key}  |  {data['type_label']}  |  过期: {data['expire']}  |  ¥{data['price']}\n")
    
    return data


def main():
    parser = argparse.ArgumentParser(description="Omnia 商业版卡密生成器")
    parser.add_argument(
        "--type", "-t",
        choices=["monthly", "quarterly", "yearly"],
        required=True,
        help="授权类型: monthly(月卡), quarterly(季卡), yearly(年卡)"
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=1,
        help="生成数量 (默认: 1)"
    )
    parser.add_argument(
        "--output", "-o",
        default="licenses.txt",
        help="输出文件 (默认: licenses.txt)"
    )
    parser.add_argument(
        "--expire-from-now",
        action="store_true",
        help="从现在开始计算过期时间 (默认从激活时开始)"
    )
    
    args = parser.parse_args()
    
    license_type = args.type
    count = args.count
    output_file = args.output
    
    print(f"\n{'='*60}")
    print(f"  Omnia 卡密生成器")
    print(f"{'='*60}")
    print(f"  类型: {LICENSE_TYPES[license_type]['label']}")
    print(f"  数量: {count}")
    print(f"  输出: {output_file}")
    print(f"{'='*60}\n")
    
    # 如果文件不存在，写入表头
    if not os.path.exists(output_file):
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"{'='*60}\n")
            f.write(f"  Omnia 商业版卡密 - 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*60}\n\n")
            f.write(f"{'卡密':<25} | {'类型':<8} | {'过期日期':<15} | {'价格'}\n")
            f.write(f"{'-'*25}-+-{'-'*8}-+-{'-'*15}-+-{'-'*6}\n")
    
    generated_keys = []
    
    for i in range(count):
        if args.expire_from_now:
            # 从现在开始计算
            expire_date = datetime.now() + timedelta(days=LICENSE_TYPES[license_type]["days"])
        else:
            # 卡密本身不包含激活时间，过期时间在激活时计算
            # 这里用一个占位日期
            expire_date = datetime(2099, 12, 31)
        
        key = generate_license_key(license_type, expire_date)
        data = save_license_data(key, license_type, expire_date, output_file)
        
        generated_keys.append(key)
        print(f"  [{i+1}/{count}] {key}")
    
    print(f"\n{'='*60}")
    print(f"  ✅ 已生成 {count} 个卡密，保存到: {output_file}")
    print(f"{'='*60}\n")
    
    # 同时输出到控制台方便复制
    print("生成的卡密:")
    print("-" * 30)
    for key in generated_keys:
        print(key)
    print("-" * 30)


if __name__ == "__main__":
    main()
