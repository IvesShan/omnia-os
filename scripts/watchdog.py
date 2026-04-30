#!/usr/bin/env python3
"""
Omnia Watchdog - 监控守护进程和 Web Server 健康状态

功能：
1. 定期检查进程存活
2. 检查 API 响应
3. 异常时通过 systemd 自动重启
4. 记录健康日志
5. 重启速率限制，避免重启风暴

依赖：
  - systemd --user 管理 omnia.service, omnia-daemon.service
  - 本 watchdog 作为 omnia-watchdog.service 运行
"""

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from core.config import OMNIA_HOME

PID_FILE = OMNIA_HOME / "daemon.pid"
HEALTH_LOG = OMNIA_HOME / "watchdog.log"
STATE_FILE = OMNIA_HOME / "watchdog_state.json"

# 检查间隔（秒）
CHECK_INTERVAL = 30
# 最大无响应次数
MAX_FAILURES = 3
# API 健康检查超时
API_TIMEOUT = 5

# systemd 服务名
SYSTEMD_SERVICES = {
    "web": "omnia.service",
    "daemon": "omnia-daemon.service",
}

# 重启速率限制：N 秒内最多重启 M 次
RESTART_RATE_WINDOW = 120  # 2 分钟窗口
RESTART_RATE_MAX = 2       # 窗口内最多重启 2 次

# 日志轮转配置
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5


def setup_logger():
    """Setup rotating logger for watchdog"""
    OMNIA_HOME.mkdir(parents=True, exist_ok=True)
    
    handler = RotatingFileHandler(
        HEALTH_LOG,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    
    logger = logging.getLogger('watchdog')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    
    return logger


# 初始化 logger
logger = setup_logger()


def log(msg: str):
    """Log message to both console and rotating file"""
    print(msg)
    logger.info(msg)


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
        "restart_timestamps": [],
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


def check_systemd_service_active(service_name: str) -> bool:
    """检查 systemd 服务是否正在运行"""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", service_name],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() == "active"
    except Exception:
        return False


def check_systemd_service_failed(service_name: str) -> bool:
    """检查 systemd 服务是否处于 failed 状态"""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-failed", service_name],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() == "failed"
    except Exception:
        return False


def _is_restart_allowed(state: dict, service_key: str) -> bool:
    """检查重启速率限制"""
    now = time.time()
    timestamps = state.get("restart_timestamps", [])
    # 清理过期的时间戳
    timestamps = [t for t in timestamps if now - t < RESTART_RATE_WINDOW]
    state["restart_timestamps"] = timestamps
    
    if len(timestamps) >= RESTART_RATE_MAX:
        log(f"  ⛔ 重启速率限制：{RESTART_RATE_WINDOW}s 内已重启 {len(timestamps)} 次（上限 {RESTART_RATE_MAX}）")
        return False
    return True


def _systemctl_restart(service_name: str, state: dict) -> bool:
    """通过 systemd --user 重启服务（带速率限制）"""
    try:
        # 先检查是否已经 active
        if check_systemd_service_active(service_name):
            log(f"  ℹ️ {service_name} 已经在运行，跳过重启")
            return True
        
        # 检查速率限制
        if not _is_restart_allowed(state, service_name):
            return False
        
        log(f"  → 执行: systemctl --user restart {service_name}")
        result = subprocess.run(
            ["systemctl", "--user", "restart", service_name],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            log(f"  ✅ systemd 重启 {service_name} 成功")
            state.setdefault("restart_timestamps", []).append(time.time())
            # 等待服务就绪
            time.sleep(5)
            return True
        else:
            err = result.stderr.strip()
            log(f"  ❌ systemd 重启失败: {err}")
            # 如果是 rate-limit-hit，尝试 reset-failed 后重试
            if "start-limit-hit" in err or "rate" in err.lower():
                log(f"  → 检测到 rate-limit，执行 reset-failed...")
                subprocess.run(
                    ["systemctl", "--user", "reset-failed", service_name],
                    capture_output=True, text=True, timeout=10,
                )
                time.sleep(5)
                retry = subprocess.run(
                    ["systemctl", "--user", "restart", service_name],
                    capture_output=True, text=True, timeout=60,
                )
                if retry.returncode == 0:
                    log(f"  ✅ reset-failed 后重启成功")
                    state.setdefault("restart_timestamps", []).append(time.time())
                    return True
                else:
                    log(f"  ❌ reset-failed 后仍然失败: {retry.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        log(f"  ❌ systemd 重启超时 (60s)")
        return False
    except FileNotFoundError:
        log(f"  ❌ systemctl 命令未找到 — 不在 systemd 环境中？")
        return False
    except Exception as e:
        log(f"  ❌ systemd 重启异常: {e}")
        return False


def restart_daemon(state: dict):
    """通过 systemd 重启守护进程"""
    log("🔄 重启守护进程 (omnia-daemon.service)...")
    return _systemctl_restart(SYSTEMD_SERVICES["daemon"], state)


def restart_web_server(state: dict):
    """通过 systemd 重启 Web Server"""
    log("🔄 重启 Web Server (omnia.service)...")
    return _systemctl_restart(SYSTEMD_SERVICES["web"], state)


def main():
    log("=" * 60)
    log("🐕 Omnia Watchdog 启动")
    log(f"检查间隔: {CHECK_INTERVAL}s, 最大失败次数: {MAX_FAILURES}")
    log(f"日志轮转: {MAX_LOG_SIZE // 1024 // 1024} MB max, {BACKUP_COUNT} backups")
    log(f"重启速率限制: {RESTART_RATE_MAX}次/{RESTART_RATE_WINDOW}s")
    log(f"使用 systemd 管理重启: {', '.join(SYSTEMD_SERVICES.values())}")
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
                    if restart_daemon(state):
                        state["daemon_failures"] = 0
                        state["restarts"] += 1
            
            # 检查 Web Server（通过 API 健康检查）
            web_healthy = check_api_health()
            if web_healthy:
                state["web_failures"] = 0
                log("✅ Web Server 正常")
            else:
                state["web_failures"] += 1
                log(f"⚠️ Web Server 无响应 ({state['web_failures']}/{MAX_FAILURES})")
                
                if state["web_failures"] >= MAX_FAILURES:
                    if restart_web_server(state):
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
