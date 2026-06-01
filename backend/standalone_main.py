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

# ============ 🔐 授权系统（统一使用 src/omnia/license.py）===========

# 添加 src 到 sys.path，确保可以导入统一的授权模块
_src_path = str(APP_ROOT / "src")
if _src_path not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from src.omnia.license import (
    get_machine_id,
    verify_license_key,
    save_license,
    load_license,
    check_license_status,
    activate_trial,
    is_trial_used,
    get_full_status,
    encrypt_api_key,
    decrypt_api_key,
    get_api_key_masked,
    activate_online,
    deactivate_online,
    start_background_verifier,
    get_update_info,
    is_online_verified,
    LICENSE_FILE,
    LICENSE_DB,
)

def init_trial_if_needed():
    """首次运行时自动创建试用许可（调用统一授权模块）"""
    is_valid, status, _ = check_license_status()
    if is_valid:
        return  # 已有有效许可
    if not is_trial_used():
        success, msg = activate_trial()
        if success:
            logger.info(f"✅ {msg}")
        else:
            logger.info(f"试用激活失败: {msg}")
    else:
        logger.info("试用期已使用过，需要购买授权")


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
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", sans-serif;
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
        .api-key-section { margin-top: 24px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1); }
        .api-key-section h3 { font-size: 14px; color: #aaa; margin-bottom: 12px; }
        .provider-select {
            width: 100%;
            padding: 10px 12px;
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 8px;
            color: #fff;
            font-size: 14px;
            margin-bottom: 12px;
            outline: none;
        }
        .provider-select option { background: #1a1a3e; color: #fff; }
        .btn-sm {
            padding: 10px 20px;
            font-size: 14px;
            width: auto;
            display: inline-block;
        }
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
                <input type="text" id="licenseKey" placeholder="OMNI-XXXX-XXXX-XXXX-XXXX" maxlength="24" autocomplete="off" />
            </div>
            <button class="btn btn-primary" onclick="activate()">激活授权</button>
            <button class="btn btn-trial" onclick="startTrial()">免费试用 1 天</button>
        </div>

        <div class="api-key-section" id="apiKeySection">
            <h3>🔑 AI 服务商配置</h3>
            <select class="provider-select" id="providerSelect">
                <option value="kimi">Kimi (Moonshot)</option>
                <option value="deepseek">DeepSeek</option>
                <option value="openai">OpenAI</option>
                <option value="claude">Claude (Anthropic)</option>
                <option value="qwen">通义千问 (阿里)</option>
                <option value="zhipu">智谱 AI (GLM)</option>
            </select>
            <div class="input-group">
                <label>API Key</label>
                <input type="password" id="apiKeyInput" placeholder="sk-..." autocomplete="off" />
            </div>
            <button class="btn btn-primary btn-sm" onclick="saveApiKey()">保存 API Key</button>
            <div id="apiKeyStatus" style="font-size: 12px; color: #888; margin-top: 8px; text-align: center;"></div>
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
                    setTimeout(() => { checkStatus(); window.location.href = '/'; }, 2000);
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
                    setTimeout(() => { checkStatus(); window.location.href = '/'; }, 2000);
                } else {
                    showMsg(data.message, 'error');
                }
            } catch(e) {
                showMsg('请求失败', 'error');
            }
        }

        async function saveApiKey() {
            const provider = document.getElementById('providerSelect').value;
            const apiKey = document.getElementById('apiKeyInput').value.trim();
            if (!apiKey) { showMsg('请输入 API Key', 'error'); return; }
            try {
                const resp = await fetch('/api/config/api-key', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({provider: provider, api_key: apiKey})
                });
                const data = await resp.json();
                if (data.success) {
                    document.getElementById('apiKeyStatus').textContent = '✅ API Key 已安全保存 (' + (data.masked || '****') + ')';
                    document.getElementById('apiKeyInput').value = '';
                } else {
                    showMsg(data.message || '保存失败', 'error');
                }
            } catch(e) {
                showMsg('保存失败', 'error');
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
            // OMNI- 前缀
            if (v.startsWith('OMNI')) {
                parts.push('OMNI');
                v = v.substring(4);
            }
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

        // 检查 API Key 状态
        fetch('/api/config').then(r=>r.json()).then(d=>{
            if (d.has_api_key) {
                document.getElementById('apiKeyStatus').textContent = '✅ 已配置 API Key';
            }
        });
    </script>
</body>
</html>
"""

@app.route('/api/license/status')
def license_status_api():
    """获取授权状态"""
    status = get_full_status()
    if not status.get("is_valid"):
        return jsonify({
            "is_valid": False,
            "status": "expired" if status.get("status") == "已过期" else "inactive",
            "message": status.get("status", "未激活"),
            "expire_time": status.get("expire_time"),
            "type_label": status.get("type_label"),
        })
    return jsonify({
        "is_valid": True,
        "status": "active",
        "message": status.get("status"),
        "type": status.get("type"),
        "type_label": status.get("type_label"),
        "activate_time": status.get("activate_time"),
        "expire_time": status.get("expire_time"),
        "remaining_days": status.get("remaining_days", 0),
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
    """获取试用许可（调用统一授权模块）"""
    is_valid, _, _ = check_license_status()
    if is_valid:
        return jsonify({"success": False, "message": "您已有有效授权，无需试用"})
    if is_trial_used():
        return jsonify({"success": False, "message": "试用期已使用，请购买授权"})
    success, msg = activate_trial()
    return jsonify({"success": success, "message": msg})


@app.route('/api/license/machine-id')
def license_machine_id_api():
    """获取机器码"""
    return jsonify({"machine_id": get_machine_id()})


@app.route('/license')
def license_page():
    """授权激活页面"""
    return render_template_string(LICENSE_PAGE_HTML)


@app.route('/api/config/api-key', methods=['POST'])
def save_api_key_api():
    """安全存储 API Key（加密存储）"""
    try:
        body = request.json
        api_key = body.get("api_key", "").strip()
        if not api_key:
            return jsonify({"success": False, "message": "请输入 API Key"})
        if encrypt_api_key(api_key):
            return jsonify({"success": True, "masked": get_api_key_masked()})
        else:
            return jsonify({"success": False, "message": "API Key 存储失败"})
    except Exception as e:
        return jsonify({"success": False, "message": f"存储失败: {str(e)}"})


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
            # 启动后台在线验证 + 自动更新检测
            start_background_verifier()
            logger.info("🔄 后台验证线程已启动")
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
    
    # 显示更新信息
    update_info = get_update_info()
    if update_info:
        print(f"\n🆕 新版本可用: v{update_info['version']}")
        print(f"   下载地址: {update_info['url']}\n")
    
    app.run(host=args.host, port=args.port, debug=False, threaded=True)

if __name__ == '__main__':
    main()
