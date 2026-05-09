#!/usr/bin/env python3
"""Start Omnia FastAPI server (background daemon mode)."""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.config import OMNIA_HOME

PID_FILE = OMNIA_HOME / "fastapi.pid"
LOG_FILE = OMNIA_HOME / "fastapi.log"
PORT = 8765


def main():
    # 检查是否已运行
    if PID_FILE.exists():
        old_pid = PID_FILE.read_text().strip()
        try:
            pid_int = int(old_pid)
            os.kill(pid_int, 0)
            print(f"⚠️  FastAPI 已在运行 (pid={old_pid}, port={PORT})")
            print(f"   停止命令: python3 scripts/stop_fastapi.py")
            return
        except (OSError, ValueError):
            # 进程不存在，继续启动
            PID_FILE.unlink(missing_ok=True)

    # 选择 Python 环境
    pytorch_python = Path.home() / "pytorch_env" / "bin" / "python3"
    omnia_venv_python = PROJECT_ROOT / ".venv" / "bin" / "python3"
    
    if pytorch_python.exists():
        python_exe = str(pytorch_python)
        print("✓ 使用 pytorch_env")
    elif omnia_venv_python.exists():
        python_exe = str(omnia_venv_python)
        print("✓ 使用 omnia venv")
    else:
        python_exe = sys.executable
        print("⚠ 使用系统 Python")

    # 确保日志目录存在
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # 启动 FastAPI
    log_fd = open(LOG_FILE, 'a', encoding='utf-8')
    
    proc = subprocess.Popen(
        [
            python_exe, "-m", "uvicorn",
            "src.omnia.main:app",
            "--host", "0.0.0.0",
            "--port", str(PORT),
        ],
        stdout=log_fd,
        stderr=log_fd,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    
    log_fd.close()
    PID_FILE.write_text(str(proc.pid))
    
    print(f"✓ FastAPI 已启动 (pid={proc.pid})")
    print(f"   地址: http://localhost:{PORT}")
    print(f"   API 文档: http://localhost:{PORT}/docs")
    print(f"   日志: {LOG_FILE}")


if __name__ == "__main__":
    main()
