#!/usr/bin/env python3
"""Restart Omnia FastAPI server."""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

def main():
    print("重启 FastAPI...")
    
    # 停止
    stop_script = PROJECT_ROOT / "scripts" / "stop_fastapi.py"
    subprocess.run([sys.executable, str(stop_script)])
    
    # 等待
    import time
    time.sleep(1)
    
    # 启动
    start_script = PROJECT_ROOT / "scripts" / "start_fastapi.py"
    subprocess.run([sys.executable, str(start_script)])


if __name__ == "__main__":
    main()
