"""
Omnia 授权验证模块
用途：验证卡密、保存/读取本地许可证
版本：v2.1 - 修复异步问题
"""

import asyncio
import hashlib
import json
import os
import platform
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

# ============================================================
# 签名密钥
# ============================================================
MASTER_KEY = "Omnia-Commercial-License-2025-SecretKey-Change-Me!"

# 授权类型及其天数
LICENSE_TYPES: Dict[str, Dict[str, Any]] = {
    "M": {"type": "monthly", "days": 30, "label": "月卡"},
    "Q": {"type": "quarterly", "days": 90, "label": "季卡"},
    "Y": {"type": "yearly", "days": 365, "label": "年卡"},
}

# 许可证文件路径
LICENSE_FILE = Path.home() / ".omnia" / "license.dat"


def get_machine_id() -> str:
    """获取机器唯一标识"""
    try:
        if platform.system() == "Windows":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography"
            )
            machine_guid = winreg.QueryValueEx(key, "MachineGuid")[0]
            winreg.CloseKey(key)
            return machine_guid
        elif platform.system() == "Darwin":
            import subprocess
            result = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split('\n'):
                if 'IOPlatformUUID' in line:
                    return line.split('"')[-2]
        else:
            machine_id_files = [
                Path("/etc/machine-id"),
                Path("/var/lib/dbus/machine-id"),
            ]
            for f in machine_id_files:
                if f.exists():
                    return f.read_text().strip()
        
        return str(uuid.getnode())
    except Exception as e:
        print(f"[License] 获取 machine_id 失败: {e}")
        return str(uuid.getnode())


def parse_license_key(key: str) -> Optional[Tuple[str, str, str]]:
    """解析卡密"""
    try:
        clean_key = key.strip().upper().replace("-", "").replace(" ", "")
        
        if len(clean_key) != 16:
            return None
        
        random_part = clean_key[:8]
        type_char = clean_key[8]
        signature = clean_key[9:]
        
        if type_char not in LICENSE_TYPES:
            return None
        
        return type_char, random_part, signature
    except Exception:
        return None


def verify_license_key(key: str) -> Tuple[bool, str, dict]:
    """验证卡密"""
    result = parse_license_key(key)
    
    if result is None:
        return False, "卡密格式无效（需要16位）", {}
    
    type_char, random_part, signature = result
    license_info = LICENSE_TYPES[type_char]
    
    expected_sig_data = f"{random_part}{type_char}{MASTER_KEY}"
    expected_sig = hashlib.sha256(expected_sig_data.encode()).hexdigest()[:10].upper()
    
    if not signature.startswith(expected_sig[:4]):
        return False, "卡密签名无效", {}
    
    activate_time = datetime.now()
    expire_time = activate_time + timedelta(days=license_info["days"])
    
    return True, "卡密验证成功", {
        "type": license_info["type"],
        "type_label": license_info["label"],
        "activate_time": activate_time.strftime("%Y-%m-%d %H:%M:%S"),
        "expire_time": expire_time.strftime("%Y-%m-%d %H:%M:%S"),
        "machine_id": get_machine_id(),
    }


def save_license(license_data: dict) -> bool:
    """保存许可证到本地"""
    try:
        LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
        license_data["machine_id"] = get_machine_id()
        
        data_str = json.dumps(license_data, sort_keys=True)
        license_data["checksum"] = hashlib.sha256(
            (data_str + MASTER_KEY).encode()
        ).hexdigest()
        
        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            json.dump(license_data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"[License] 保存许可证失败: {e}")
        return False


def load_license() -> Optional[dict]:
    """加载本地许可证"""
    try:
        if not LICENSE_FILE.exists():
            return None
        
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            license_data = json.load(f)
        
        saved_checksum = license_data.pop("checksum", None)
        if saved_checksum is None:
            return None
        
        data_str = json.dumps(license_data, sort_keys=True)
        expected_checksum = hashlib.sha256(
            (data_str + MASTER_KEY).encode()
        ).hexdigest()
        
        if saved_checksum != expected_checksum:
            return None
        
        if license_data.get("machine_id") != get_machine_id():
            return None
        
        return license_data
    except Exception as e:
        print(f"[License] 加载许可证失败: {e}")
        return None


async def check_license_status() -> Tuple[bool, str, Optional[dict]]:
    """检查许可证状态（异步）"""
    try:
        license_data = await asyncio.wait_for(
            asyncio.to_thread(load_license),
            timeout=5.0
        )
        
        if license_data is None:
            return False, "未激活", None
        
        expire_time = datetime.strptime(
            license_data["expire_time"], 
            "%Y-%m-%d %H:%M:%S"
        )
        
        if datetime.now() > expire_time:
            return False, "已过期", license_data
        
        remaining = (expire_time - datetime.now()).days
        return True, f"有效 (剩余 {remaining} 天)", license_data
    except asyncio.TimeoutError:
        print("[License] 检查状态超时")
        return False, "检查超时", None
    except Exception as e:
        print(f"[License] 检查状态异常: {e}")
        return False, f"检查失败: {str(e)}", None


async def activate_license(key: str) -> Tuple[bool, str]:
    """激活许可证（异步）"""
    try:
        is_valid, message, license_info = await asyncio.wait_for(
            asyncio.to_thread(verify_license_key, key),
            timeout=5.0
        )
        
        if not is_valid:
            return False, message
        
        success = await asyncio.wait_for(
            asyncio.to_thread(save_license, license_info),
            timeout=5.0
        )
        
        if success:
            return True, f"激活成功！授权类型: {license_info['type_label']}, 过期时间: {license_info['expire_time']}"
        else:
            return False, "许可证保存失败"
    except asyncio.TimeoutError:
        return False, "激活超时，请重试"
    except Exception as e:
        return False, f"激活失败: {str(e)}"


async def get_license_display() -> str:
    """获取许可证显示信息（异步）"""
    try:
        is_valid, status, license_data = await check_license_status()
        
        if not is_valid:
            if license_data and status == "已过期":
                return f"⚠️ 授权已过期 (过期时间: {license_data['expire_time']})"
            return "❌ 未激活"
        
        return f"✅ {status} | 类型: {license_data['type_label']} | 过期: {license_data['expire_time']}"
    except Exception as e:
        return f"❌ 检查失败: {str(e)}"


if __name__ == "__main__":
    print("Omnia 授权验证模块 v2.1")
    print(f"机器ID: {get_machine_id()}")
    print(f"许可证文件: {LICENSE_FILE}")
    
    is_valid, status, data = asyncio.run(check_license_status())
    print(f"当前状态: {status}")
    
    if data:
        print(f"授权详情: {json.dumps(data, indent=2, ensure_ascii=False)}")
