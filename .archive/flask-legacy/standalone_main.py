#!/usr/bin/env python3
"""
Omnia Backend - Standalone Entry Point
用于 PyInstaller 打包的独立入口

功能：
- API 代理（支持多家 AI 服务商）
- Memory Palace 管理
- 人格系统（从 seeds 加载基础人格）
- 配置管理
- 健康检查
"""

import os
import sys
import json
import logging
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from typing import Dict, Any, Optional

# ============ 路径配置 ============

# 获取应用根目录（打包后和开发时不同）
def get_app_root():
    """获取应用根目录"""
    # 打包后：可执行文件所在目录
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    # 开发时：backend 目录的父目录
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
    
    # 默认配置
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
        
        # 解析 SOUL.md（简单的键值对格式）
        persona = {
            "name": persona_name,
            "soul": content,
            "loaded_at": datetime.now().isoformat()
        }
        
        # 加载记忆（如果有）
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

# ============ API 路由 ============

@app.route('/health')
def health():
    """健康检查"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "1.1.0"
    })

@app.route('/api/config', methods=['GET'])
def get_config():
    """获取配置"""
    config = load_config()
    # 不返回敏感信息
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
    personas = get_all_personas()
    return jsonify({
        "personas": personas,
        "count": len(personas)
    })

@app.route('/api/personas/<name>', methods=['GET'])
def get_persona(name):
    """获取指定人格"""
    persona = load_persona(name)
    if persona:
        return jsonify(persona)
    return jsonify({"error": "Persona not found"}), 404

@app.route('/api/chat', methods=['POST'])
def chat():
    """聊天 API - 代理到 AI 服务"""
    data = request.json
    message = data.get('message', '')
    config = load_config()
    
    # TODO: 实现实际的 AI 调用
    # 根据 config['api_provider'] 调用对应的服务
    
    if not config.get('api_key'):
        return jsonify({
            "error": "API key not configured",
            "hint": "Please configure your API key in settings"
        }), 400
    
    # 临时响应
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
    
    return jsonify({
        "app_root": str(APP_ROOT),
        "user_data_dir": str(USER_DATA_DIR),
        "seeds_dir": str(SEEDS_DIR),
        "seeds_exists": SEEDS_DIR.exists(),
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
    args = parser.parse_args()
    
    # 显示启动信息
    print("\n" + "="*50)
    print("  Omnia AIOS Backend v1.1.0")
    print("="*50)
    print(f"  App Root:  {APP_ROOT}")
    print(f"  User Data: {USER_DATA_DIR}")
    print(f"  Seeds:     {SEEDS_DIR}")
    print(f"  Port:      {args.port}")
    print("="*50 + "\n")
    
    # 加载人格
    personas = get_all_personas()
    print(f"✓ Loaded {len(personas)} personas:")
    for p in personas:
        print(f"  - {p['name']}")
    print()
    
    # 启动服务
    logger.info(f"Starting Omnia Backend on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)

if __name__ == '__main__':
    main()
