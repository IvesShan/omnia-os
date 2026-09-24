"""Omnia CLI entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def _load_dotenv():
    """轻量加载项目根目录 .env 到环境变量（不覆盖已存在的变量）。"""
    env_file = PROJECT_ROOT / ".env"
    if not env_file.is_file():
        return
    try:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except OSError:
        pass


import os
_load_dotenv()

from src.core.neuro_center import PersonaDaemon, DaemonConfig
from src.core.neuro_center.notification_queue import pop_notifications_for_session
from omnia.wake import assemble_wake_prompt
from omnia.chat import chat
from core.settings import get_settings

# 全局 settings（cmd_status 等用到）
settings = get_settings()


def cmd_wake(args):
    message = " ".join(args.message) if args.message else None
    prompt = assemble_wake_prompt(message)
    print(prompt)


def cmd_chat(args):
    message = " ".join(args.message)
    if not message:
        print("Usage: omnia chat <message>")
        return
    chat(message)


def cmd_status(args):
    workspace_root = PROJECT_ROOT.parent
    db_file = settings.memory_palace_db
    queue_file = settings.omnia_home / "notifications.jsonl"

    print("=" * 60)
    print("Omnia Status (FastAPI)")
    print("=" * 60)

    # FastAPI Server
    import urllib.request
    try:
        req = urllib.request.Request("http://localhost:8765/api/status", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                print("\nFastAPI Server: running (http://localhost:8765)")
            else:
                print(f"\nFastAPI Server: returned status {resp.status}")
    except Exception as e:
        print(f"\nFastAPI Server: not reachable ({e})")

    # Memory palace
    if db_file.exists():
        import sqlite3
        with sqlite3.connect(str(db_file)) as conn:
            cursor = conn.cursor()
            counts = {}
            for table in ["facts", "relations", "habits", "timeline"]:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
        print("\nMemory Palace:")
        for k, v in counts.items():
            print(f"  {k}: {v}")
    else:
        print("\nMemory Palace: not initialized")

    # Pending notifications
    pulse = pop_notifications_for_session(queue_file)
    if pulse:
        print(f"\nPending notifications:{pulse}")
    else:
        print("\nPending notifications: none")

    print("\n" + "=" * 60)


def cmd_doctor(args):
    from omnia.doctor import print_doctor
    cfg = getattr(args, "config", None)
    s = get_settings(cfg) if cfg else settings
    code = print_doctor(s)
    sys.exit(code)

def cmd_serve(args):
    """启动 Omnia 主服务（FastAPI/uvicorn）。

    默认前台运行（Ctrl+C 停止）。生产环境建议用 systemd（omnia.service），
    本命令面向开发/自托管快速启动：omnia serve
    """
    cfg = getattr(args, "config", None)
    s = get_settings(cfg) if cfg else settings
    host = args.host or s.server_host
    port = args.port or s.server_port
    app = args.app or "src.omnia.main:app"

    # 端口占用预检
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host if host != "0.0.0.0" else "127.0.0.1", port))
        except OSError:
            print(f"❌ 端口 {port} 已被占用。先停止已有服务（omnia stop / systemctl），或换 --port")
            sys.exit(1)

    print("=" * 56)
    print("Omnia Serve")
    print("=" * 56)
    print(f"  app : {app}")
    print(f"  addr: http://{host}:{port}")
    print(f"  conf: {s.config_path or '(默认/env)'}")
    print("  按 Ctrl+C 停止。生产环境建议: systemctl --user start omnia.service")
    print("=" * 56)

    try:
        import uvicorn
    except ImportError:
        print("❌ 未安装 uvicorn，请先: pip install uvicorn fastapi")
        sys.exit(1)

    uvicorn.run(app, host=host, port=port, log_level=args.log_level)

def cmd_config(args):
    from core.settings import Settings, find_config_file
    sub = args.config_action
    if sub == "validate":
        path = find_config_file(getattr(args, "config", None))
        if not path:
            print("❌ 未找到 omnia.yaml")
            sys.exit(1)
        s = Settings(str(path))
        issues = s.validate()
        if issues:
            print(f"❌ {path} 存在 {len(issues)} 个问题：")
            for i in issues:
                print(f"  - {i}")
            sys.exit(1)
        print(f"✅ {path} 校验通过")
    elif sub == "init":
        target = Path.home() / ".omnia" / "omnia.yaml"
        if target.exists() and not getattr(args, "force", False):
            print(f"⚠️  {target} 已存在（用 --force 覆盖）")
            sys.exit(1)
        src = PROJECT_ROOT / "omnia.yaml.example"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"✅ 已生成 {target}")
        print("   下一步：编辑该文件填入你的 API key，或确保 .env 中有对应环境变量")
        print("   然后运行: omnia doctor")


def main():
    parser = argparse.ArgumentParser(prog="omnia", description="Omnia Agent OS")
    parser.add_argument("--config", help="指定 omnia.yaml 配置文件路径")
    subparsers = parser.add_subparsers(dest="command", required=True)

    wake_parser = subparsers.add_parser("wake", help="Run the full wake cycle and print system prompt")
    wake_parser.add_argument("message", nargs="*", help="Optional user message to plan against")
    wake_parser.set_defaults(func=cmd_wake)

    chat_parser = subparsers.add_parser("chat", help="Chat with Omnia in the terminal")
    chat_parser.add_argument("message", nargs="+", help="Your message to Omnia")
    chat_parser.set_defaults(func=cmd_chat)

    status_parser = subparsers.add_parser("status", help="Show Omnia system status")
    status_parser.set_defaults(func=cmd_status)

    doctor_parser = subparsers.add_parser("doctor", help="系统自检：配置/依赖/端口/LLM/数据库")
    doctor_parser.set_defaults(func=cmd_doctor)

    serve_parser = subparsers.add_parser("serve", help="启动 Omnia 主服务（FastAPI/uvicorn）")
    serve_parser.add_argument("--host", help="监听地址（默认读配置 server.host）")
    serve_parser.add_argument("--port", type=int, help="监听端口（默认读配置 server.port）")
    serve_parser.add_argument("--app", help="ASGI app（默认 src.omnia.main:app）")
    serve_parser.add_argument("--log-level", default="info", help="日志级别（默认 info）")
    serve_parser.set_defaults(func=cmd_serve)

    config_parser = subparsers.add_parser("config", help="配置管理")
    config_sub = config_parser.add_subparsers(dest="config_action", required=True)
    cv = config_sub.add_parser("validate", help="校验 omnia.yaml 配置")
    cv.set_defaults(func=cmd_config)
    ci = config_sub.add_parser("init", help="从模板生成 ~/.omnia/omnia.yaml")
    ci.add_argument("--force", action="store_true", help="覆盖已存在的配置")
    ci.set_defaults(func=cmd_config)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
