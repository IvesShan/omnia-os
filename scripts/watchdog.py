#!/usr/bin/env python3
"""
Omnia Watchdog - 监控守护进程和 Web Server 健康状态

功能：
1. 定期检查进程存活
2. 检查 API 响应
3. 异常时自动重启
4. 记录健康日志
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from core.config import OMNIA_HOME

PID_FILE = OMNIA_HOME / "daemon.pid"
WEB_PID_FILE = OMNIA_HOME / "web_server.pid"
HEALTH_LOG = OMNIA_HOME / "watchdog.log"
STATE_FILE = OMNIA_HOME / "watchdog_state.json"

# 检查间隔（秒）
CHECK_INTERVAL = 30
# 最大无响应次数
MAX_FAILURES = 3
# API 健康检查超时
API_TIMEOUT = 5


def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(HEALTH_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "daemon_failures": 0,
        "web_failures": 0,
        "last_check": None,
        "restarts": 0,
    }


def save_state(state: dict):
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception:
        pass


def check_process(pid: int) -> bool:
    """检查进程是否存活"""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def check_api_health(port: int = 5001) -> bool:
    """检查 API 是否响应"""
    try:
        import urllib.request
        url = f"http://localhost:{port}/api/status"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=API_TIMEOUT) as resp:
            return resp.status == 200
    except Exception:
        return False


def restart_daemon():
    """重启守护进程"""
    log("🔄 重启守护进程...")
    try:
        # 停止旧进程
        if PID_FILE.exists():
            old_pid = int(PID_FILE.read_text().strip())
            try:
                os.kill(old_pid, signal.SIGTERM)
                time.sleep(2)
                try:
                    os.kill(old_pid, signal.SIGKILL)
                except OSError:
                    pass
            except OSError:
                pass
            PID_FILE.unlink(missing_ok=True)
        
        # 启动新进程
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "start_daemon.py")],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            log("✅ 守护进程重启成功")
            return True
        else:
            log(f"❌ 守护进程重启失败: {result.stderr}")
            return False
    except Exception as e:
        log(f"❌ 重启异常: {e}")
        return False


def restart_web_server():
    """重启 Web Server"""
    log("🔄 重启 Web Server...")
    try:
        # 停止旧进程
        if WEB_PID_FILE.exists():
            old_pid = int(WEB_PID_FILE.read_text().strip())
            try:
                os.kill(old_pid, signal.SIGTERM)
                time.sleep(2)
            except OSError:
                pass
            WEB_PID_FILE.unlink(missing_ok=True)
        
        # 启动新进程
        subprocess.Popen(
            [sys.executable, str(PROJECT_ROOT / "src" / "omnia" / "web_server.py")],
            stdout=open(OMNIA_HOME / "web_server.log", "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        time.sleep(3)
        log("✅ Web Server 重启成功")
        return True
    except Exception as e:
        log(f"❌ Web Server 重启失败: {e}")
        return False


def main():
    # 系统启动时等待 Web 服务完全就绪，避免与 systemd 并行启动冲突
    time.sleep(10)
    log("启动延迟结束，开始健康检查")
    log("=" * 60)
    log("🐕 Omnia Watchdog 启动")
    log(f"检查间隔: {CHECK_INTERVAL}s, 最大失败次数: {MAX_FAILURES}")
    log("=" * 60)
    
    state = load_state()
    
    while True:
        try:
            state["last_check"] = datetime.now().isoformat()
            
            # 检查守护进程
            daemon_healthy = False
            if PID_FILE.exists():
                pid = int(PID_FILE.read_text().strip())
                daemon_healthy = check_process(pid)
            
            if daemon_healthy:
                state["daemon_failures"] = 0
                log("✅ 守护进程正常")
            else:
                state["daemon_failures"] += 1
                log(f"⚠️ 守护进程无响应 ({state['daemon_failures']}/{MAX_FAILURES})")
                
                if state["daemon_failures"] >= MAX_FAILURES:
                    if restart_daemon():
                        state["daemon_failures"] = 0
                        state["restarts"] += 1
            
            # 检查 Web Server
            web_healthy = check_api_health()
            if web_healthy:
                state["web_failures"] = 0
                log("✅ Web Server 正常")
            else:
                state["web_failures"] += 1
                log(f"⚠️ Web Server 无响应 ({state['web_failures']}/{MAX_FAILURES})")
                
                if state["web_failures"] >= MAX_FAILURES:
                    if restart_web_server():
                        state["web_failures"] = 0
                        state["restarts"] += 1
            
            save_state(state)
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            log("👋 Watchdog 停止")
            break
        except Exception as e:
            log(f"❌ 检查异常: {e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
