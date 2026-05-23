#!/usr/bin/env python3
"""
Omnia Backend - Standalone Entry Point
用于 Nuitka 打包的独立入口

功能：
- API 代理（支持多家 AI 服务商）
- Memory Palace 管理
- 人格系统（从 seeds 加载基础人格）
- 配置管理
- 健康检查
- 🔐 授权验证系统（卡密激活 + 试用期）
"""

import os
import sys
import json
import logging
import hashlib
import hmac
import platform
import uuid
import sqlite3
import secrets
from pathlib import Path
from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# ============ 路径配置 ============

def get_app_root():
    """获取应用根目录"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent

APP_ROOT = get_app_root()
DEFAULT_PORT = 5001

# 用户数据目录
USER_DATA_DIR = Path.home() / ".omnia"
CONFIG_DIR = USER_DATA_DIR / "config"
DATA_DIR = USER_DATA_DIR / "data"
LOG_DIR = USER_DATA_DIR / "logs"
MEMORY_DIR = USER_DATA_DIR / "memory"

# 应用内资源目录
SEEDS_DIR = APP_ROOT / "seeds"

# 确保用户目录存在
for d in [CONFIG_DIR, DATA_DIR, LOG_DIR, MEMORY_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ============ 日志配置 ============

log_file = LOG_DIR / "backend.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info(f"Omnia Backend starting...")
logger.info(f"App root: {APP_ROOT}")
logger.info(f"User data: {USER_DATA_DIR}")
logger.info(f"Seeds dir: {SEEDS_DIR}")

# ============ 🔐 授权系统 ============

# 签名密钥（与 tools/keygen.py 和 src/omnia/license.py 保持一致）
LICENSE_MASTER_KEY = "Omnia-Commercial-License-2025-SecretKey-Change-Me!"

# 授权类型
LICENSE_TYPES = {
    "M": {"type": "monthly", "days": 30, "label": "月卡"},
    "Q": {"type": "quarterly", "days": 90, "label": "季卡"},
    "Y": {"type": "yearly", "days": 365, "label": "年卡"},
    "T": {"type": "trial", "days": 3, "label": "试用"},
}

LICENSE_FILE = USER_DATA_DIR / "license.dat"
LICENSE_DB = USER_DATA_DIR / "license.db"


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
        logger.warning(f"获取 machine_id 失败: {e}")
        return str(uuid.getnode())


def verify_license_key(key: str) -> tuple:
    """验证卡密，返回 (is_valid, message, info_dict)"""
    try:
        clean_key = key.strip().upper().replace("-", "").replace(" ", "")
        if len(clean_key) != 16:
            return False, "卡密格式无效（需要16位）", {}

        random_part = clean_key[:8]
        type_char = clean_key[8]
        signature = clean_key[9:]

        if type_char not in LICENSE_TYPES:
            return False, "卡密类型无效", {}

        license_info = LICENSE_TYPES[type_char]

        # 验证签名
        expected_sig_data = f"{random_part}{type_char}{LICENSE_MASTER_KEY}"
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
    except Exception as e:
        return False, f"验证失败: {str(e)}", {}


def save_license(license_data: dict) -> bool:
    """保存许可证到本地"""
    try:
        LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
        license_data["machine_id"] = get_machine_id()
        data_str = json.dumps(license_data, sort_keys=True)
        license_data["checksum"] = hashlib.sha256(
            (data_str + LICENSE_MASTER_KEY).encode()
        ).hexdigest()
        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            json.dump(license_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"保存许可证失败: {e}")
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
            (data_str + LICENSE_MASTER_KEY).encode()
        ).hexdigest()
        if saved_checksum != expected_checksum:
            return None
        if license_data.get("machine_id") != get_machine_id():
            return None
        return license_data
    except Exception as e:
        logger.error(f"加载许可证失败: {e}")
        return None


def check_license_status() -> tuple:
    """检查许可证状态，返回 (is_valid, status_msg, license_data)"""
    license_data = load_license()
    if license_data is None:
        return False, "未激活", None
    try:
        expire_time = datetime.strptime(license_data["expire_time"], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return False, "许可证数据损坏", None
    if datetime.now() > expire_time:
        return False, "已过期", license_data
    remaining = (expire_time - datetime.now()).days
    return True, f"有效 (剩余 {remaining} 天)", license_data


def init_trial_if_needed():
    """首次运行时自动创建试用许可"""
    is_valid, status, _ = check_license_status()
    if is_valid:
        return  # 已有有效许可

    # 检查是否已经用过试用
    try:
        if LICENSE_DB.exists():
            conn = sqlite3.connect(LICENSE_DB)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM trial_used WHERE machine_id = ?",
                (get_machine_id(),)
            )
            count = cursor.fetchone()[0]
            conn.close()
            if count > 0:
                logger.info("试用期已使用过，需要购买授权")
                return
    except Exception:
        pass

    # 创建试用许可
    logger.info("首次运行，创建3天试用许可...")
    trial_type = LICENSE_TYPES["T"]
    activate_time = datetime.now()
    expire_time = activate_time + timedelta(days=trial_type["days"])

    trial_data = {
        "type": trial_type["type"],
        "type_label": trial_type["label"],
        "activate_time": activate_time.strftime("%Y-%m-%d %H:%M:%S"),
        "expire_time": expire_time.strftime("%Y-%m-%d %H:%M:%S"),
        "machine_id": get_machine_id(),
    }

    if save_license(trial_data):
        # 记录已使用试用
        try:
            LICENSE_DB.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(LICENSE_DB)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trial_used (
                    machine_id TEXT PRIMARY KEY,
                    used_at TEXT
                )
            """)
            cursor.execute(
                "INSERT OR IGNORE INTO trial_used (machine_id, used_at) VALUES (?, ?)",
                (get_machine_id(), datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"记录试用状态失败: {e}")
        logger.info(f"✅ 试用许可已创建，有效期至 {expire_time.strftime('%Y-%m-%d %H:%M:%S')}")


# ============ Flask 应用 ============

app = Flask(__name__)
CORS(app)

# ============ 配置管理 ============

config_file = CONFIG_DIR / "settings.json"

def load_config() -> Dict[str, Any]:
    """加载用户配置"""
    if config_file.exists():
        try:
            with open(config_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
    return {
        "api_provider": "kimi",
        "api_key": "",
        "model_name": "moonshot-v1-8k",
        "backend_port": DEFAULT_PORT,
        "log_level": "info",
        "auto_start_backend": True,
        "first_run": True
    }

def save_config(config: Dict[str, Any]):
    """保存用户配置"""
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    logger.info("Config saved")

# ============ 人格系统 ============

def load_persona(persona_name: str) -> Optional[Dict[str, Any]]:
    """从 seeds 加载人格设定"""
    soul_file = SEEDS_DIR / persona_name / "SOUL.md"
    if not soul_file.exists():
        logger.warning(f"Persona not found: {persona_name}")
        return None
    try:
        with open(soul_file, encoding='utf-8') as f:
            content = f.read()
        persona = {
            "name": persona_name,
            "soul": content,
            "loaded_at": datetime.now().isoformat()
        }
        memory_dir = SEEDS_DIR / persona_name / "memory"
        if memory_dir.exists():
            persona["memory_seeds"] = []
            for mem_file in memory_dir.glob("*.md"):
                with open(mem_file, encoding='utf-8') as f:
                    persona["memory_seeds"].append({
                        "file": mem_file.name,
                        "content": f.read()
                    })
        logger.info(f"Persona loaded: {persona_name}")
        return persona
    except Exception as e:
        logger.error(f"Failed to load persona {persona_name}: {e}")
        return None

def get_all_personas() -> list:
    """获取所有可用人格"""
    personas = []
    if not SEEDS_DIR.exists():
        logger.warning(f"Seeds directory not found: {SEEDS_DIR}")
        return personas
    for persona_dir in SEEDS_DIR.iterdir():
        if persona_dir.is_dir() and (persona_dir / "SOUL.md").exists():
            persona = load_persona(persona_dir.name)
            if persona:
                personas.append(persona)
    return personas

# ============ 🔐 授权 API 路由 ============

LICENSE_PAGE_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Omnia - 授权激活</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3e 50%, #0a0a2a 100%);
            color: #e0e0e0;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            background: rgba(20, 20, 50, 0.9);
            border: 1px solid rgba(100, 100, 255, 0.2);
            border-radius: 16px;
            padding: 40px;
            max-width: 480px;
            width: 90%;
            backdrop-filter: blur(10px);
        }
        .logo {
            text-align: center;
            font-size: 32px;
            font-weight: bold;
            background: linear-gradient(135deg, #64b5f6, #ba68c8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        .subtitle {
            text-align: center;
            color: #888;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .status-box {
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 20px;
            text-align: center;
        }
        .status-active { border-left: 4px solid #4caf50; }
        .status-expired { border-left: 4px solid #ff9800; }
        .status-inactive { border-left: 4px solid #f44336; }
        .input-group { margin-bottom: 16px; }
        .input-group label {
            display: block;
            margin-bottom: 6px;
            font-size: 13px;
            color: #aaa;
        }
        .input-group input {
            width: 100%;
            padding: 12px 16px;
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 8px;
            color: #fff;
            font-size: 16px;
            letter-spacing: 2px;
            text-align: center;
            outline: none;
            transition: border-color 0.3s;
        }
        .input-group input:focus { border-color: rgba(100, 150, 255, 0.6); }
        .btn {
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 10px;
        }
        .btn-primary {
            background: linear-gradient(135deg, #5c6bc0, #7c4dff);
            color: #fff;
        }
        .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(124,77,255,0.4); }
        .btn-trial {
            background: transparent;
            border: 1px solid rgba(255,255,255,0.2);
            color: #aaa;
        }
        .btn-trial:hover { border-color: rgba(255,255,255,0.4); color: #fff; }
        .message {
            text-align: center;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 16px;
            display: none;
        }
        .message.success { display: block; background: rgba(76,175,80,0.15); color: #81c784; }
        .message.error { display: block; background: rgba(244,67,54,0.15); color: #e57373; }
        .info { font-size: 12px; color: #666; text-align: center; margin-top: 16px; }
        .machine-id { font-family: monospace; font-size: 11px; color: #555; word-break: break-all; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">✦ Omnia</div>
        <div class="subtitle">AI Operating System · 授权激活</div>

        <div id="statusBox" class="status-box">
            <div id="statusText">正在检查授权状态...</div>
        </div>

        <div id="msg" class="message"></div>

        <div id="activateForm">
            <div class="input-group">
                <label>请输入授权卡密</label>
                <input type="text" id="licenseKey" placeholder="XXXX-XXXX-XXXX-XXXX" maxlength="19" autocomplete="off" />
            </div>
            <button class="btn btn-primary" onclick="activate()">激活授权</button>
            <button class="btn btn-trial" onclick="startTrial()">免费试用 3 天</button>
        </div>

        <div class="info">
            <p>购买授权请联系管理员</p>
            <p class="machine-id" id="machineId"></p>
        </div>
    </div>

    <script>
        async function checkStatus() {
            try {
                const resp = await fetch('/api/license/status');
                const data = await resp.json();
                const box = document.getElementById('statusBox');
                const text = document.getElementById('statusText');

                if (data.is_valid) {
                    box.className = 'status-box status-active';
                    text.innerHTML = '✅ <strong>' + data.type_label + '</strong> · 剩余 ' + data.remaining_days + ' 天<br><small>过期时间: ' + data.expire_time + '</small>';
                    document.getElementById('activateForm').style.display = 'none';
                } else if (data.status === 'expired') {
                    box.className = 'status-box status-expired';
                    text.innerHTML = '⚠️ 授权已过期<br><small>过期时间: ' + (data.expire_time || '') + '</small>';
                } else {
                    box.className = 'status-box status-inactive';
                    text.innerHTML = '❌ ' + (data.message || '未激活');
                }
            } catch(e) {
                document.getElementById('statusText').textContent = '无法连接服务器';
            }
        }

        async function activate() {
            const key = document.getElementById('licenseKey').value.trim();
            if (!key) { showMsg('请输入卡密', 'error'); return; }
            try {
                const resp = await fetch('/api/license/activate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({key: key})
                });
                const data = await resp.json();
                if (data.success) {
                    showMsg(data.message, 'success');
                    setTimeout(() => checkStatus(), 1000);
                } else {
                    showMsg(data.message, 'error');
                }
            } catch(e) {
                showMsg('激活请求失败', 'error');
            }
        }

        async function startTrial() {
            try {
                const resp = await fetch('/api/license/trial', {method: 'POST'});
                const data = await resp.json();
                if (data.success) {
                    showMsg(data.message, 'success');
                    setTimeout(() => checkStatus(), 1000);
                } else {
                    showMsg(data.message, 'error');
                }
            } catch(e) {
                showMsg('请求失败', 'error');
            }
        }

        function showMsg(text, type) {
            const msg = document.getElementById('msg');
            msg.textContent = text;
            msg.className = 'message ' + type;
        }

        // 自动格式化卡密输入
        document.getElementById('licenseKey').addEventListener('input', function(e) {
            let v = e.target.value.replace(/[^A-Za-z0-9]/g, '').toUpperCase();
            let parts = [];
            for (let i = 0; i < v.length && i < 16; i += 4) {
                parts.push(v.substring(i, Math.min(i+4, v.length)));
            }
            e.target.value = parts.join('-');
        });

        // 初始化
        checkStatus();
        document.getElementById('machineId').textContent = 'Machine ID: loading...';
        fetch('/api/license/machine-id').then(r=>r.json()).then(d=>{
            document.getElementById('machineId').textContent = 'Machine ID: ' + d.machine_id;
        });
    </script>
</body>
</html>
"""

@app.route('/api/license/status')
def license_status_api():
    """获取授权状态"""
    is_valid, status, license_data = check_license_status()
    if license_data is None:
        return jsonify({"is_valid": False, "status": "inactive", "message": status})
    if not is_valid:
        return jsonify({
            "is_valid": False,
            "status": "expired" if status == "已过期" else "inactive",
            "message": status,
            "expire_time": license_data.get("expire_time"),
            "type_label": license_data.get("type_label"),
        })
    try:
        expire_time = datetime.strptime(license_data["expire_time"], "%Y-%m-%d %H:%M:%S")
        remaining_days = (expire_time - datetime.now()).days
    except Exception:
        remaining_days = 0
    return jsonify({
        "is_valid": True,
        "status": "active",
        "message": status,
        "type": license_data.get("type"),
        "type_label": license_data.get("type_label"),
        "activate_time": license_data.get("activate_time"),
        "expire_time": license_data.get("expire_time"),
        "remaining_days": remaining_days,
    })


@app.route('/api/license/activate', methods=['POST'])
def license_activate_api():
    """激活授权"""
    try:
        body = request.json
        key = body.get("key", "").strip()
        if not key:
            return jsonify({"success": False, "message": "请输入卡密"})
        is_valid, message, license_info = verify_license_key(key)
        if not is_valid:
            return jsonify({"success": False, "message": message})
        if save_license(license_info):
            return jsonify({"success": True, "message": f"激活成功！{license_info['type_label']}，有效期至 {license_info['expire_time']}"})
        else:
            return jsonify({"success": False, "message": "许可证保存失败"})
    except Exception as e:
        return jsonify({"success": False, "message": f"激活失败: {str(e)}"})


@app.route('/api/license/trial', methods=['POST'])
def license_trial_api():
    """获取试用许可"""
    # 检查是否已有有效许可
    is_valid, _, _ = check_license_status()
    if is_valid:
        return jsonify({"success": False, "message": "您已有有效授权，无需试用"})

    # 检查试用是否已使用
    try:
        if LICENSE_DB.exists():
            conn = sqlite3.connect(LICENSE_DB)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM trial_used WHERE machine_id = ?",
                (get_machine_id(),)
            )
            count = cursor.fetchone()[0]
            conn.close()
            if count > 0:
                return jsonify({"success": False, "message": "试用期已使用，请购买授权"})
    except Exception:
        pass

    # 创建试用
    trial_type = LICENSE_TYPES["T"]
    activate_time = datetime.now()
    expire_time = activate_time + timedelta(days=trial_type["days"])
    trial_data = {
        "type": trial_type["type"],
        "type_label": trial_type["label"],
        "activate_time": activate_time.strftime("%Y-%m-%d %H:%M:%S"),
        "expire_time": expire_time.strftime("%Y-%m-%d %H:%M:%S"),
        "machine_id": get_machine_id(),
    }
    if save_license(trial_data):
        try:
            LICENSE_DB.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(LICENSE_DB)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trial_used (
                    machine_id TEXT PRIMARY KEY,
                    used_at TEXT
                )
            """)
            cursor.execute(
                "INSERT OR IGNORE INTO trial_used (machine_id, used_at) VALUES (?, ?)",
                (get_machine_id(), datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"记录试用状态失败: {e}")
        return jsonify({"success": True, "message": f"试用许可已激活，有效期至 {expire_time.strftime('%Y-%m-%d %H:%M:%S')}"})
    else:
        return jsonify({"success": False, "message": "试用许可创建失败"})


@app.route('/api/license/machine-id')
def license_machine_id_api():
    """获取机器码"""
    return jsonify({"machine_id": get_machine_id()})


@app.route('/license')
def license_page():
    """授权激活页面"""
    return render_template_string(LICENSE_PAGE_HTML)


# ============ 原有 API 路由 ============

@app.route('/health')
def health():
    """健康检查"""
    is_valid, status, _ = check_license_status()
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "1.2.0",
        "license": {
            "valid": is_valid,
            "status": status
        }
    })

@app.route('/api/config', methods=['GET'])
def get_config():
    """获取配置"""
    config = load_config()
    safe_config = {k: v for k, v in config.items() if k != 'api_key'}
    safe_config['has_api_key'] = bool(config.get('api_key'))
    return jsonify(safe_config)

@app.route('/api/config', methods=['POST'])
def update_config():
    """更新配置"""
    config = request.json
    save_config(config)
    return jsonify({"status": "saved"})

@app.route('/api/personas', methods=['GET'])
def list_personas():
    """列出所有人格"""
    # 检查授权
    is_valid, _, _ = check_license_status()
    if not is_valid:
        return jsonify({"error": "unauthorized", "message": "请先激活授权", "redirect": "/license"}), 401
    personas = get_all_personas()
    return jsonify({"personas": personas, "count": len(personas)})

@app.route('/api/personas/<name>', methods=['GET'])
def get_persona(name):
    """获取指定人格"""
    is_valid, _, _ = check_license_status()
    if not is_valid:
        return jsonify({"error": "unauthorized", "message": "请先激活授权"}), 401
    persona = load_persona(name)
    if persona:
        return jsonify(persona)
    return jsonify({"error": "Persona not found"}), 404

@app.route('/api/chat', methods=['POST'])
def chat():
    """聊天 API - 代理到 AI 服务"""
    # 检查授权
    is_valid, status, _ = check_license_status()
    if not is_valid:
        return jsonify({"error": "unauthorized", "message": "请先激活授权", "redirect": "/license"}), 401

    data = request.json
    message = data.get('message', '')
    config = load_config()
    if not config.get('api_key'):
        return jsonify({
            "error": "API key not configured",
            "hint": "Please configure your API key in settings"
        }), 400
    return jsonify({
        "response": f"[Omnia] 收到你的消息：{message}",
        "timestamp": datetime.now().isoformat(),
        "model": config.get('model_name', 'unknown')
    })

@app.route('/api/memory/status', methods=['GET'])
def memory_status():
    """记忆系统状态"""
    memory_db = MEMORY_DIR / "memory_palace.db"
    return jsonify({
        "initialized": True,
        "db_exists": memory_db.exists(),
        "db_path": str(memory_db),
        "layers": ["facts", "relations", "habits", "timeline"]
    })

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """获取日志"""
    lines = request.args.get('lines', 100, type=int)
    if log_file.exists():
        with open(log_file) as f:
            all_lines = f.readlines()
        return jsonify(all_lines[-lines:])
    return jsonify([])

@app.route('/api/diagnostics', methods=['GET'])
def diagnostics():
    """系统诊断"""
    config = load_config()
    is_valid, license_status, _ = check_license_status()
    return jsonify({
        "app_root": str(APP_ROOT),
        "user_data_dir": str(USER_DATA_DIR),
        "seeds_dir": str(SEEDS_DIR),
        "seeds_exists": SEEDS_DIR.exists(),
        "license": {
            "valid": is_valid,
            "status": license_status,
            "machine_id": get_machine_id(),
        },
        "config": {
            "provider": config.get('api_provider'),
            "model": config.get('model_name'),
            "has_api_key": bool(config.get('api_key')),
            "first_run": config.get('first_run', True)
        },
        "directories": {
            "config": str(CONFIG_DIR),
            "data": str(DATA_DIR),
            "logs": str(LOG_DIR),
            "memory": str(MEMORY_DIR)
        },
        "timestamp": datetime.now().isoformat()
    })

# ============ 主程序 ============

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Omnia Backend')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Port to run on')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--skip-license', action='store_true', help='跳过授权检查（开发用）')
    args = parser.parse_args()

    # 🔐 初始化授权检查
    if not args.skip_license:
        init_trial_if_needed()
        is_valid, status, _ = check_license_status()
        if not is_valid:
            logger.warning(f"⚠️ 授权状态: {status}")
            logger.warning("访问 http://127.0.0.1:{}/license 进行激活".format(args.port))
        else:
            logger.info(f"✅ 授权状态: {status}")
    else:
        logger.info("🔓 授权检查已跳过（开发模式）")

    # 显示启动信息
    print("\n" + "="*50)
    print("  Omnia AIOS Backend v1.2.0")
    print("="*50)
    print(f"  App Root:  {APP_ROOT}")
    print(f"  User Data: {USER_DATA_DIR}")
    print(f"  Seeds:     {SEEDS_DIR}")
    print(f"  Port:      {args.port}")
    is_valid, lic_status, _ = check_license_status()
    print(f"  License:   {lic_status}")
    print("="*50 + "\n")

    # 加载人格
    if is_valid:
        personas = get_all_personas()
        print(f"✓ Loaded {len(personas)} personas:")
        for p in personas:
            print(f"  - {p['name']}")
        print()
    else:
        print("⚠️ 未授权，人格系统已锁定")
        print(f"   请访问: http://127.0.0.1:{args.port}/license")
        print()

    # 启动服务
    logger.info(f"Starting Omnia Backend on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)

if __name__ == '__main__':
    main()
