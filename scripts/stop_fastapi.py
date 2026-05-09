#!/usr/bin/env python3
"""Stop Omnia FastAPI server."""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.config import OMNIA_HOME

PID_FILE = OMNIA_HOME / "fastapi.pid"


def main():
    if not PID_FILE.exists():
        print("⚠️  FastAPI 未运行 (PID 文件不存在)")
        
        # 尝试通过进程名查找
        import subprocess
        result = subprocess.run(
            ["pgrep", "-f", "uvicorn.*8765"],
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            print(f"   找到 {len(pids)} 个相关进程:")
            for pid in pids:
                print(f"   - PID {pid}")
            print(f"   强制停止: kill {' '.join(pids)}")
        else:
            print("   未找到相关进程")
        return

    pid = PID_FILE.read_text().strip()
    
    try:
        pid_int = int(pid)
        os.kill(pid_int, 15)  # SIGTERM
        print(f"✓ 已发送停止信号 (pid={pid})")
        
        # 等待进程结束
        import time
        for i in range(10):
            try:
                os.kill(pid_int, 0)
                time.sleep(0.5)
            except OSError:
                # 进程已结束
                PID_FILE.unlink(missing_ok=True)
                print(f"✓ FastAPI 已停止")
                return
        
        # 强制结束
        print(f"⚠️  进程未响应，强制结束...")
        os.kill(pid_int, 9)  # SIGKILL
        PID_FILE.unlink(missing_ok=True)
        print(f"✓ FastAPI 已强制停止")
        
    except (OSError, ValueError) as e:
        print(f"⚠️  进程不存在或已停止: {e}")
        PID_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
