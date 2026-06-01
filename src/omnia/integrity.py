"""
Omnia 代码完整性校验模块
======================
用于检测关键文件是否被篡改（防逆向修改）
使用 HMAC-SHA256 签名校验
"""

import hashlib
import hmac
import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional

# 校验密钥（与 MASTER_KEY 不同）
INTEGRITY_KEY = "Omnia-Integrity-Check-2026-Secret-v1"

# 需要保护的关键文件列表
PROTECTED_FILES = [
    "src/omnia/license.py",
    "src/omnia/config.py",
    "backend/standalone_main.py",
]


def compute_file_hash(file_path: str) -> str:
    """计算文件的 HMAC-SHA256 签名"""
    try:
        content = Path(file_path).read_bytes()
        return hmac.new(
            INTEGRITY_KEY.encode(),
            content,
            hashlib.sha256
        ).hexdigest()
    except Exception:
        return ""


def compute_code_hash() -> str:
    """计算所有受保护文件的综合签名"""
    hashes = []
    for f in PROTECTED_FILES:
        h = compute_file_hash(f)
        if h:
            hashes.append(f"{f}:{h}")
    
    combined = "|".join(sorted(hashes))
    return hmac.new(
        INTEGRITY_KEY.encode(),
        combined.encode(),
        hashlib.sha256
    ).hexdigest()


def get_signatures_file() -> Path:
    """获取签名文件路径"""
    root = Path(__file__).parent.parent.parent
    return root / ".integrity.json"


def save_signatures():
    """保存当前文件签名（打包前调用）"""
    signatures = {}
    for f in PROTECTED_FILES:
        h = compute_file_hash(f)
        if h:
            signatures[f] = h
    
    sig_file = get_signatures_file()
    sig_file.write_text(json.dumps(signatures, indent=2))
    print(f"✅ 签名已保存到 {sig_file}")
    return signatures


def verify_integrity() -> tuple[bool, list[str]]:
    """
    验证文件完整性
    返回：(all_valid, list_of_tampered_files)
    """
    sig_file = get_signatures_file()
    if not sig_file.exists():
        return True, []  # 无签名文件时跳过验证
    
    try:
        saved = json.loads(sig_file.read_text())
    except Exception:
        return False, ["签名文件损坏"]
    
    tampered = []
    for file_path, expected_hash in saved.items():
        current_hash = compute_file_hash(file_path)
        if current_hash != expected_hash:
            tampered.append(file_path)
    
    return len(tampered) == 0, tampered


def check_and_warn():
    """检查完整性并打印警告（应用启动时调用）"""
    is_valid, tampered = verify_integrity()
    if not is_valid:
        print("\n" + "!" * 60)
        print("⚠️  警告：检测到文件被篡改！")
        print("!" * 60)
        for f in tampered:
            print(f"  ❌ {f}")
        print()
        print("  此版本可能已被修改，存在安全风险。")
        print("  请从官方渠道重新下载。")
        print("!" * 60 + "\n")
    return is_valid


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "sign":
        save_signatures()
    elif len(sys.argv) > 1 and sys.argv[1] == "verify":
        ok, tampered = verify_integrity()
        if ok:
            print("✅ 所有文件完整性验证通过")
        else:
            print("❌ 以下文件被篡改：")
            for f in tampered:
                print(f"  - {f}")
    else:
        print("用法：")
        print("  python integrity.py sign    # 保存签名（打包前）")
        print("  python integrity.py verify  # 验证签名")
