#!/usr/bin/env python3
"""Flask Daemon 已移除。请使用 systemd 管理 FastAPI 服务。"""

import sys

def main():
    print("[INFO] Flask Persona Daemon 已移除。")
    print("[INFO] FastAPI 服务由 systemd 管理: omnia-fastapi.service")
    print("[INFO] 启动: systemctl --user start omnia-fastapi.service")
    print("[INFO] 状态: systemctl --user status omnia-fastapi.service")
    sys.exit(0)

if __name__ == '__main__':
    main()
