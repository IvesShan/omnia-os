"""
Omnia 统一授权系统 v4.0
=====================
统一的卡密验证 + 试用期 + 机器绑定 + API Key 加密存储
+ 在线验证 + 离线宽限期 + 自动更新检测

卡密格式：OMNI-XXXX-XXXX-XXXX-XXXX (20位，不含易混淆字符)
试用期：1 天
机器绑定：基于 machine-id / IOPlatformUUID / Registry
在线验证：每 24 小时向激活服务器验证一次
离线宽限期：7 天（超过后需要联网验证）
"""

import hashlib
import json
import os
import platform
import secrets
import sqlite3
import subprocess
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

# ============================================================
# 🔐 配置常量
# ============================================================

MASTER_KEY = "Omnia-Commercial-License-2026-SecretKey-v3"
USER_DATA_DIR = Path.home() / ".omnia"
LICENSE_FILE = USER_DATA_DIR / "license.dat"
LICENSE_DB = USER_DATA_DIR / "license.db"
CONFIG_DIR = USER_DATA_DIR / "config"
API_KEY_FILE = CONFIG_DIR / "api_key.enc"

# 在线激活服务器
ACTIVATION_SERVER = os.getenv("OMNIA_ACTIVATION_SERVER", "https://activate.omnia-ai.com")
VERIFY_INTERVAL = 3600 * 24  # 24 小时验证一次
OFFLINE_GRACE_DAYS = 7  # 离线宽限期

# 自动更新
UPDATE_CHECK_INTERVAL = 3600 * 6  # 6 小时检查一次
UPDATE_CHECK_URL = os.getenv("OMNIA_UPDATE_URL", "https://api.github.com/repos/omnia-ai/omnia/releases/latest")

# 授权类型
LICENSE_TYPES = {
    "T": {"type": "trial",      "days": 1,    "label": "试用版",  "price": 0},
    "M": {"type": "monthly",    "days": 30,   "label": "月卡",    "price": 68},
    "Q": {"type": "quarterly",  "days": 90,   "label": "季卡",    "price": 168},
    "Y": {"type": "yearly",     "days": 365,  "label": "年卡",    "price": 388},
    "P": {"type": "perpetual",  "days": 36500,"label": "终身版",  "price": 888},
}

# 不易混淆的字符集（排除 0/O/1/I/l）
CHARSET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


# ============================================================
# 🔧 工具函数
# ============================================================

def get_machine_id() -> str:
    """获取机器唯一标识（跨平台）"""
    try:
        system = platform.system()

        if system == "Windows":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography"
            )
            machine_guid = winreg.QueryValueEx(key, "MachineGuid")[0]
            winreg.CloseKey(key)
            return machine_guid

        elif system == "Darwin":
            result = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split('\n'):
                if 'IOPlatformUUID' in line:
                    return line.split('"')[-2]

        else:  # Linux
            for path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
                if Path(path).exists():
                    return Path(path).read_text().strip()

        return str(uuid.getnode())
    except Exception:
        return str(uuid.getnode())


def _ensure_dirs():
    """确保必要目录存在"""
    for d in [USER_DATA_DIR, CONFIG_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# ============================================================
# 🔑 卡密生成
# ============================================================

def generate_license_key(license_type: str) -> str:
    """
    生成卡密
    格式：OMNI-XXXX-XXXX-XXXX-XXXX
    """
    if license_type not in LICENSE_TYPES:
        raise ValueError(f"无效的授权类型: {license_type}")

    type_char = license_type
    random_part = ''.join(secrets.choice(CHARSET) for _ in range(12))
    sig_data = f"{random_part}{type_char}{MASTER_KEY}"
    signature = hashlib.sha256(sig_data.encode()).hexdigest()[:3].upper()

    key_body = f"{random_part}{type_char}{signature}"
    # 分段：4-4-4-4
    key = f"OMNI-{key_body[:4]}-{key_body[4:8]}-{key_body[8:12]}-{key_body[12:16]}"

    return key


# ============================================================
# 🔒 卡密验证
# ============================================================

def parse_license_key(key: str) -> Optional[Tuple[str, str, str]]:
    """
    解析卡密
    返回：(type_char, random_part, signature) 或 None
    """
    try:
        # 去掉前缀 OMNI- 和所有分隔符
        clean = key.strip().upper()
        if clean.startswith("OMNI-"):
            clean = clean[5:]
        clean = clean.replace("-", "").replace(" ", "")

        if len(clean) != 16:
            return None

        random_part = clean[:12]
        type_char = clean[12]
        signature = clean[13:]

        if type_char not in LICENSE_TYPES:
            return None

        return type_char, random_part, signature
    except Exception:
        return None


def verify_license_key(key: str) -> Tuple[bool, str, dict]:
    """
    验证卡密
    返回：(is_valid, message, license_info)
    """
    result = parse_license_key(key)

    if result is None:
        return False, "卡密格式无效（需要 OMNI-XXXX-XXXX-XXXX-XXXX 格式）", {}

    type_char, random_part, signature = result
    license_info = LICENSE_TYPES[type_char]

    # 验证签名
    expected_sig_data = f"{random_part}{type_char}{MASTER_KEY}"
    expected_sig = hashlib.sha256(expected_sig_data.encode()).hexdigest()[:3].upper()

    if signature != expected_sig:
        return False, "卡密签名无效", {}

    activate_time = datetime.now()
    expire_time = activate_time + timedelta(days=license_info["days"])

    return True, "卡密验证成功", {
        "type": license_info["type"],
        "type_label": license_info["label"],
        "days": license_info["days"],
        "activate_time": activate_time.strftime("%Y-%m-%d %H:%M:%S"),
        "expire_time": expire_time.strftime("%Y-%m-%d %H:%M:%S"),
        "machine_id": get_machine_id(),
    }


# ============================================================
# 💾 许可证存储
# ============================================================

def save_license(license_data: dict) -> bool:
    """保存许可证到本地（带校验和）"""
    try:
        _ensure_dirs()
        license_data["machine_id"] = get_machine_id()
        license_data["saved_at"] = datetime.now().isoformat()

        data_str = json.dumps(license_data, sort_keys=True)
        license_data["checksum"] = hashlib.sha256(
            (data_str + MASTER_KEY).encode()
        ).hexdigest()

        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            json.dump(license_data, f, indent=2, ensure_ascii=False)

        return True
    except Exception:
        return False


def load_license() -> Optional[dict]:
    """加载本地许可证（验证校验和 + 机器绑定）"""
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
    except Exception:
        return None


def check_license_status() -> Tuple[bool, str, Optional[dict]]:
    """
    检查许可证状态
    返回：(is_valid, status_msg, license_data)
    """
    license_data = load_license()

    if license_data is None:
        return False, "未激活", None

    try:
        expire_time = datetime.strptime(
            license_data["expire_time"],
            "%Y-%m-%d %H:%M:%S"
        )
    except Exception:
        return False, "许可证数据损坏", None

    if datetime.now() > expire_time:
        return False, "已过期", license_data

    remaining = (expire_time - datetime.now()).days
    return True, f"有效 (剩余 {remaining} 天)", license_data


# ============================================================
# 🆓 试用期管理
# ============================================================

def _init_trial_db():
    """初始化试用记录数据库"""
    _ensure_dirs()
    try:
        conn = sqlite3.connect(LICENSE_DB)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trial_used (
                machine_id TEXT PRIMARY KEY,
                used_at TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception:
        pass


def is_trial_used() -> bool:
    """检查试用期是否已使用"""
    _init_trial_db()
    try:
        conn = sqlite3.connect(LICENSE_DB)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM trial_used WHERE machine_id = ?",
            (get_machine_id(),)
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


def activate_trial() -> Tuple[bool, str]:
    """
    激活试用期（1 天）
    返回：(success, message)
    """
    # 检查是否已有有效授权
    is_valid, _, _ = check_license_status()
    if is_valid:
        return False, "您已有有效授权，无需试用"

    # 检查试用是否已使用
    if is_trial_used():
        return False, "试用期已使用，请购买授权"

    # 创建试用许可
    trial_info = LICENSE_TYPES["T"]
    activate_time = datetime.now()
    expire_time = activate_time + timedelta(days=trial_info["days"])

    trial_data = {
        "type": trial_info["type"],
        "type_label": trial_info["label"],
        "days": trial_info["days"],
        "activate_time": activate_time.strftime("%Y-%m-%d %H:%M:%S"),
        "expire_time": expire_time.strftime("%Y-%m-%d %H:%M:%S"),
        "machine_id": get_machine_id(),
    }

    if save_license(trial_data):
        # 记录已使用试用
        try:
            _init_trial_db()
            conn = sqlite3.connect(LICENSE_DB)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO trial_used (machine_id, used_at) VALUES (?, ?)",
                (get_machine_id(), datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

        return True, f"试用许可已激活，有效期至 {expire_time.strftime('%Y-%m-%d %H:%M:%S')}"

    return False, "试用许可创建失败"


# ============================================================
# 🔐 API Key 加密存储
# ============================================================

def encrypt_api_key(api_key: str) -> bool:
    """加密存储 API Key"""
    try:
        _ensure_dirs()
        # 使用机器ID作为加密密钥的一部分
        key_material = f"{get_machine_id()}{MASTER_KEY}"
        enc_key = hashlib.sha256(key_material.encode()).digest()[:16]

        # 简单的 XOR 加密（对于API Key足够）
        key_bytes = api_key.encode('utf-8')
        encrypted = bytes(
            b ^ enc_key[i % len(enc_key)]
            for i, b in enumerate(key_bytes)
        )

        # 存储为 hex
        data = {
            "encrypted": encrypted.hex(),
            "hash": hashlib.sha256(api_key.encode()).hexdigest()[:16],
            "created_at": datetime.now().isoformat()
        }

        with open(API_KEY_FILE, "w") as f:
            json.dump(data, f)

        return True
    except Exception:
        return False


def decrypt_api_key() -> Optional[str]:
    """解密读取 API Key"""
    try:
        if not API_KEY_FILE.exists():
            return None

        with open(API_KEY_FILE, "r") as f:
            data = json.load(f)

        encrypted = bytes.fromhex(data["encrypted"])

        key_material = f"{get_machine_id()}{MASTER_KEY}"
        enc_key = hashlib.sha256(key_material.encode()).digest()[:16]

        decrypted = bytes(
            b ^ enc_key[i % len(enc_key)]
            for i, b in enumerate(encrypted)
        )

        api_key = decrypted.decode('utf-8')

        # 验证完整性
        if hashlib.sha256(api_key.encode()).hexdigest()[:16] != data["hash"]:
            return None

        return api_key
    except Exception:
        return None


def get_api_key_masked() -> Optional[str]:
    """获取脱敏的 API Key（用于显示）"""
    api_key = decrypt_api_key()
    if not api_key:
        return None
    if len(api_key) <= 8:
        return "****"
    return f"{api_key[:4]}****{api_key[-4:]}"


# ============================================================
# 🚫 授权停用（设备迁移）
# ============================================================

def deactivate_license() -> Tuple[bool, str]:
    """停用当前设备的授权（用于设备迁移）"""
    try:
        if LICENSE_FILE.exists():
            LICENSE_FILE.unlink()
        return True, "授权已停用，卡密可在其他设备激活"
    except Exception as e:
        return False, f"停用失败: {str(e)}"


# ============================================================
# 📊 综合状态
# ============================================================

def get_full_status() -> dict:
    """获取完整的授权状态信息"""
    is_valid, status_msg, license_data = check_license_status()

    result = {
        "is_valid": is_valid,
        "status": status_msg,
        "machine_id": get_machine_id(),
        "license_file": str(LICENSE_FILE),
        "trial_used": is_trial_used(),
        "has_api_key": decrypt_api_key() is not None,
        "api_key_masked": get_api_key_masked(),
    }

    if license_data:
        result.update({
            "type": license_data.get("type"),
            "type_label": license_data.get("type_label"),
            "activate_time": license_data.get("activate_time"),
            "expire_time": license_data.get("expire_time"),
        })

        try:
            expire_time = datetime.strptime(
                license_data["expire_time"],
                "%Y-%m-%d %H:%M:%S"
            )
            result["remaining_days"] = max(0, (expire_time - datetime.now()).days)
        except Exception:
            result["remaining_days"] = 0

    return result


# ============================================================
# 🌐 在线激活
# ============================================================

def activate_online(license_key: str) -> Tuple[bool, str]:
    """
    在线激活卡密
    向激活服务器发送激活请求，成功后本地保存许可证
    """
    import urllib.request
    import urllib.error

    try:
        url = f"{ACTIVATION_SERVER}/api/v1/activate"
        payload = json.dumps({
            "license_key": license_key.strip().upper(),
            "machine_id": get_machine_id(),
            "machine_name": platform.node(),
            "os_type": platform.system(),
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if data.get("success"):
            # 保存本地许可证
            license_data = {
                "license_key": license_key.strip().upper(),
                "type": data.get("type"),
                "type_label": data.get("type_label"),
                "expire_time": data.get("expire_at"),
                "activate_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "machine_id": get_machine_id(),
                "online_verified": True,
                "last_verify": datetime.now().isoformat(),
            }
            save_license(license_data)
            _save_license_key(license_key.strip().upper())
            return True, data.get("message", "激活成功")

        return False, data.get("detail", "激活失败")

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(body).get("detail", body)
        except Exception:
            detail = body
        return False, f"服务器错误: {detail}"
    except urllib.error.URLError:
        return False, "无法连接激活服务器，请检查网络"
    except Exception as e:
        return False, f"激活失败: {str(e)}"


def verify_online(license_key: str) -> Tuple[bool, str, Optional[dict]]:
    """
    在线验证授权状态
    向激活服务器发送验证请求
    """
    import urllib.request
    import urllib.error

    try:
        url = f"{ACTIVATION_SERVER}/api/v1/verify"
        payload = json.dumps({
            "license_key": license_key,
            "machine_id": get_machine_id(),
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        return data.get("valid", False), data.get("message", ""), data

    except Exception:
        return False, "在线验证失败", None


def deactivate_online(license_key: str) -> Tuple[bool, str]:
    """
    在线停用授权（设备迁移）
    """
    import urllib.request

    try:
        url = f"{ACTIVATION_SERVER}/api/v1/deactivate"
        payload = json.dumps({
            "license_key": license_key,
            "machine_id": get_machine_id(),
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if data.get("success"):
            # 清除本地许可证
            deactivate_license()

        return data.get("success", False), data.get("message", "")

    except Exception as e:
        return False, f"停用失败: {str(e)}"


def _save_license_key(key: str):
    """保存卡密到本地（用于在线验证）"""
    try:
        _ensure_dirs()
        key_file = CONFIG_DIR / "license_key.dat"
        key_file.write_text(key, encoding="utf-8")
    except Exception:
        pass


def _load_license_key() -> Optional[str]:
    """读取本地保存的卡密"""
    try:
        key_file = CONFIG_DIR / "license_key.dat"
        if key_file.exists():
            return key_file.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return None


# ============================================================
# ⏰ 后台验证线程
# ============================================================

class _BackgroundVerifier:
    """后台定期在线验证 + 自动更新检测"""

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._update_info: Optional[dict] = None
        self._last_verify_ok = True
        self._verify_fail_count = 0

    @property
    def update_info(self) -> Optional[dict]:
        return self._update_info

    @property
    def last_verify_ok(self) -> bool:
        return self._last_verify_ok

    def start(self):
        """启动后台验证线程"""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="omnia-verifier")
        self._thread.start()

    def stop(self):
        """停止后台验证"""
        self._stop_event.set()

    def _run(self):
        """线程主循环"""
        while not self._stop_event.is_set():
            try:
                self._do_verify()
                self._do_update_check()
            except Exception:
                pass
            # 每小时检查一次
            self._stop_event.wait(3600)

    def _do_verify(self):
        """执行在线验证"""
        license_key = _load_license_key()
        if not license_key:
            return

        is_valid, message, data = verify_online(license_key)

        if is_valid:
            self._last_verify_ok = True
            self._verify_fail_count = 0
            # 更新本地许可证信息
            if data and data.get("expire_at"):
                license_data = load_license()
                if license_data:
                    license_data["expire_time"] = data["expire_at"]
                    license_data["last_verify"] = datetime.now().isoformat()
                    license_data["online_verified"] = True
                    save_license(license_data)
        else:
            self._verify_fail_count += 1
            if self._verify_fail_count >= 3:
                self._last_verify_ok = False

    def _do_update_check(self):
        """检查是否有新版本"""
        try:
            import urllib.request
            req = urllib.request.Request(UPDATE_CHECK_URL, headers={"User-Agent": "Omnia-Client/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            remote_tag = data.get("tag_name", "").lstrip("v")
            if remote_tag and remote_tag != _get_current_version():
                self._update_info = {
                    "version": remote_tag,
                    "url": data.get("html_url", ""),
                    "body": data.get("body", "")[:500],
                    "published_at": data.get("published_at", ""),
                }
            else:
                self._update_info = None
        except Exception:
            pass


def _get_current_version() -> str:
    """获取当前版本号"""
    try:
        ver_file = Path(__file__).parent.parent.parent / "VERSION"
        if ver_file.exists():
            return ver_file.read_text().strip()
    except Exception:
        pass
    return "2.0.0"


# 全局单例
_verifier = _BackgroundVerifier()


def start_background_verifier():
    """启动后台验证（应用启动时调用）"""
    _verifier.start()


def stop_background_verifier():
    """停止后台验证"""
    _verifier.stop()


def get_update_info() -> Optional[dict]:
    """获取更新信息"""
    return _verifier.update_info


def is_online_verified() -> bool:
    """是否通过在线验证"""
    return _verifier.last_verify_ok


# ============================================================
# 🔧 兼容层（供 standalone_main.py 使用）
# ============================================================

def init_trial_if_needed():
    """首次运行时自动创建试用许可（兼容旧代码）"""
    is_valid, _, _ = check_license_status()
    if is_valid:
        return
    if not is_trial_used():
        activate_trial()


# ============================================================
# 🧪 命令行工具
# ============================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Omnia 授权系统 v3.0")
        print(f"机器ID: {get_machine_id()}")
        print(f"许可证: {LICENSE_FILE}")
        print()
        status = get_full_status()
        print(f"授权状态: {status['status']}")
        if status.get('type_label'):
            print(f"授权类型: {status['type_label']}")
        if status.get('remaining_days') is not None:
            print(f"剩余天数: {status['remaining_days']}")
        print(f"API Key: {'已配置' if status['has_api_key'] else '未配置'}")
        print()
        print("用法:")
        print("  python license.py status          # 查看状态")
        print("  python license.py activate KEY    # 激活卡密")
        print("  python license.py trial           # 试用1天")
        print("  python license.py deactivate      # 停用授权")
        print("  python license.py generate TYPE   # 生成卡密")
        print("  python license.py set-key KEY     # 设置API Key")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "status":
        status = get_full_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))

    elif cmd == "activate":
        if len(sys.argv) < 3:
            print("用法: python license.py activate YOUR-KEY")
            sys.exit(1)
        key = sys.argv[2]
        is_valid, msg, info = verify_license_key(key)
        if is_valid:
            if save_license(info):
                print(f"✅ {msg}")
                print(f"   类型: {info['type_label']}")
                print(f"   有效期至: {info['expire_time']}")
            else:
                print("❌ 许可证保存失败")
        else:
            print(f"❌ {msg}")

    elif cmd == "trial":
        success, msg = activate_trial()
        print(f"{'✅' if success else '❌'} {msg}")

    elif cmd == "deactivate":
        success, msg = deactivate_license()
        print(f"{'✅' if success else '❌'} {msg}")

    elif cmd == "generate":
        if len(sys.argv) < 3:
            print("用法: python license.py generate [T|M|Q|Y|P]")
            print("  T=试用(1天) M=月卡(30天) Q=季卡(90天) Y=年卡(365天) P=终身版")
            sys.exit(1)
        type_char = sys.argv[2].upper()
        if type_char not in LICENSE_TYPES:
            print(f"无效类型: {type_char}")
            sys.exit(1)
        count = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        info = LICENSE_TYPES[type_char]
        print(f"\n生成 {count} 个 {info['label']} 卡密:")
        print("-" * 40)
        for _ in range(count):
            key = generate_license_key(type_char)
            print(key)

    elif cmd == "set-key":
        if len(sys.argv) < 3:
            print("用法: python license.py set-key YOUR-API-KEY")
            sys.exit(1)
        api_key = sys.argv[2]
        if encrypt_api_key(api_key):
            print("✅ API Key 已加密存储")
            print(f"   脱敏显示: {get_api_key_masked()}")
        else:
            print("❌ API Key 存储失败")

    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)
