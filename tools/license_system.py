#!/usr/bin/env python3
"""
Omnia 授权系统 - 机器码绑定 + 卡密验证
用于商业版保护
"""

import os
import sys
import json
import hashlib
import platform
import subprocess
import uuid
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class MachineID:
    """机器唯一标识生成器"""
    
    @staticmethod
    def get_machine_id() -> str:
        """获取机器唯一标识"""
        info = ""
        
        # 1. 获取平台信息
        info += platform.platform()
        info += platform.processor()
        info += platform.machine()
        
        # 2. 获取系统特定标识
        system = platform.system()
        
        if system == "Windows":
            info += MachineID._get_windows_id()
        elif system == "Darwin":
            info += MachineID._get_macos_id()
        elif system == "Linux":
            info += MachineID._get_linux_id()
        
        # 3. 获取MAC地址
        mac = uuid.getnode()
        info += str(mac)
        
        # 4. 生成哈希
        return hashlib.sha256(info.encode()).hexdigest()[:32]
    
    @staticmethod
    def _get_windows_id() -> str:
        """获取Windows机器ID"""
        try:
            result = subprocess.run(
                ["wmic", "csproduct", "get", "UUID"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip().split('\n')[-1].strip()
        except:
            return ""
    
    @staticmethod
    def _get_macos_id() -> str:
        """获取macOS机器ID"""
        try:
            result = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split('\n'):
                if 'IOPlatformUUID' in line:
                    return line.split('"')[-2]
        except:
            return ""
        return ""
    
    @staticmethod
    def _get_linux_id() -> str:
        """获取Linux机器ID"""
        # 尝试读取 /etc/machine-id
        machine_id_paths = [
            "/etc/machine-id",
            "/var/lib/dbus/machine-id",
            "/proc/sys/kernel/random/boot_id"
        ]
        
        for path in machine_id_paths:
            try:
                with open(path, 'r') as f:
                    return f.read().strip()
            except:
                continue
        
        return ""


class LicenseManager:
    """授权管理器"""
    
    # 授权类型
    LICENSE_TRIAL = "trial"        # 试用版
    LICENSE_MONTHLY = "monthly"    # 月卡
    LICENSE_QUARTERLY = "quarterly"  # 季卡
    LICENSE_YEARLY = "yearly"      # 年卡
    LICENSE_PERPETUAL = "perpetual"  # 终身版
    
    # 有效期（天）
    DURATION = {
        LICENSE_TRIAL: 3,
        LICENSE_MONTHLY: 30,
        LICENSE_QUARTERLY: 90,
        LICENSE_YEARLY: 365,
        LICENSE_PERPETUAL: 36500,  # 100年
    }
    
    def __init__(self, db_path: Optional[str] = None):
        """初始化授权管理器"""
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path.home() / ".omnia" / "license.db"
        
        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._init_db()
        
        # 获取机器码
        self.machine_id = MachineID.get_machine_id()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建授权表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                key TEXT PRIMARY KEY,
                license_type TEXT NOT NULL,
                machine_id TEXT,
                activated_at TEXT,
                expires_at TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建激活记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT,
                machine_id TEXT,
                activated_at TEXT,
                ip_address TEXT,
                FOREIGN KEY (license_key) REFERENCES licenses(key)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def generate_license_key(self, license_type: str) -> str:
        """
        生成授权码
        
        Args:
            license_type: 授权类型 (trial/monthly/quarterly/yearly/perpetual)
        
        Returns:
            授权码字符串
        """
        # 生成随机前缀
        prefix = license_type[:3].upper()
        
        # 生成随机数据
        random_data = os.urandom(16)
        hash_data = hashlib.sha256(random_data).hexdigest()[:20].upper()
        
        # 格式化授权码: OMNIA-XXXX-XXXX-XXXX-XXXX
        key = f"OMNIA-{hash_data[:4]}-{hash_data[4:8]}-{hash_data[8:12]}-{hash_data[12:16]}"
        
        # 存储到数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO licenses (key, license_type, created_at)
            VALUES (?, ?, ?)
        ''', (key, license_type, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return key
    
    def activate(self, license_key: str) -> Dict[str, Any]:
        """
        激活授权
        
        Args:
            license_key: 授权码
        
        Returns:
            激活结果
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查授权码是否存在
        cursor.execute('SELECT * FROM licenses WHERE key = ?', (license_key,))
        license_data = cursor.fetchone()
        
        if not license_data:
            conn.close()
            return {
                "success": False,
                "error": "授权码无效"
            }
        
        # 检查是否已激活到其他机器
        if license_data[2] and license_data[2] != self.machine_id:
            conn.close()
            return {
                "success": False,
                "error": "授权码已绑定到其他设备"
            }
        
        # 计算过期时间
        license_type = license_data[1]
        duration_days = self.DURATION.get(license_type, 30)
        activated_at = datetime.now()
        expires_at = activated_at + timedelta(days=duration_days)
        
        # 更新授权记录
        cursor.execute('''
            UPDATE licenses 
            SET machine_id = ?, activated_at = ?, expires_at = ?
            WHERE key = ?
        ''', (
            self.machine_id,
            activated_at.isoformat(),
            expires_at.isoformat(),
            license_key
        ))
        
        # 记录激活日志
        cursor.execute('''
            INSERT INTO activations (license_key, machine_id, activated_at)
            VALUES (?, ?, ?)
        ''', (license_key, self.machine_id, activated_at.isoformat()))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "license_type": license_type,
            "expires_at": expires_at.isoformat(),
            "days_remaining": duration_days
        }
    
    def check_license(self) -> Dict[str, Any]:
        """
        检查当前授权状态
        
        Returns:
            授权状态信息
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 查找当前机器的有效授权
        cursor.execute('''
            SELECT * FROM licenses 
            WHERE machine_id = ? AND is_active = 1
            ORDER BY expires_at DESC
            LIMIT 1
        ''', (self.machine_id,))
        
        license_data = cursor.fetchone()
        conn.close()
        
        if not license_data:
            return {
                "valid": False,
                "status": "未授权",
                "message": "请购买授权码"
            }
        
        # 检查是否过期
        expires_at = datetime.fromisoformat(license_data[4])
        now = datetime.now()
        
        if now > expires_at:
            return {
                "valid": False,
                "status": "已过期",
                "message": "授权已过期，请续费",
                "expired_at": expires_at.isoformat()
            }
        
        # 计算剩余天数
        days_remaining = (expires_at - now).days
        
        return {
            "valid": True,
            "status": "已授权",
            "license_type": license_data[1],
            "expires_at": expires_at.isoformat(),
            "days_remaining": days_remaining,
            "machine_id": self.machine_id
        }
    
    def get_trial_license(self) -> Dict[str, Any]:
        """
        获取试用授权
        
        Returns:
            试用授权信息
        """
        # 检查是否已有试用记录
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM licenses 
            WHERE license_type = 'trial' AND machine_id = ?
        ''', (self.machine_id,))
        
        existing = cursor.fetchone()
        conn.close()
        
        if existing:
            return {
                "success": False,
                "error": "试用期已使用",
                "message": "每个设备只能试用一次"
            }
        
        # 生成试用授权
        trial_key = self.generate_license_key("trial")
        result = self.activate(trial_key)
        
        if result["success"]:
            result["message"] = "试用期3天"
        
        return result
    
    def deactivate(self, license_key: str) -> Dict[str, Any]:
        """
        停用授权（用于设备迁移）
        
        Args:
            license_key: 授权码
        
        Returns:
            停用结果
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE licenses 
            SET machine_id = NULL, activated_at = NULL, expires_at = NULL
            WHERE key = ? AND machine_id = ?
        ''', (license_key, self.machine_id))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if affected > 0:
            return {"success": True, "message": "授权已停用，可在其他设备激活"}
        
        return {"success": False, "error": "授权码不存在或未绑定到当前设备"}


def main():
    """命令行工具"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Omnia 授权管理工具")
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # 生成授权码
    gen_parser = subparsers.add_parser("generate", help="生成授权码")
    gen_parser.add_argument("type", choices=["trial", "monthly", "quarterly", "yearly", "perpetual"])
    gen_parser.add_argument("--count", type=int, default=1, help="生成数量")
    
    # 激活授权
    activate_parser = subparsers.add_parser("activate", help="激活授权")
    activate_parser.add_argument("key", help="授权码")
    
    # 检查状态
    subparsers.add_parser("status", help="检查授权状态")
    
    # 获取机器码
    subparsers.add_parser("machine-id", help="获取机器码")
    
    # 获取试用
    subparsers.add_parser("trial", help="获取试用授权")
    
    args = parser.parse_args()
    
    manager = LicenseManager()
    
    if args.command == "generate":
        for _ in range(args.count):
            key = manager.generate_license_key(args.type)
            print(key)
    
    elif args.command == "activate":
        result = manager.activate(args.key)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "status":
        result = manager.check_license()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "machine-id":
        print(f"机器码: {manager.machine_id}")
    
    elif args.command == "trial":
        result = manager.get_trial_license()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
