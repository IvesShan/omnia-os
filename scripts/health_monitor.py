#!/usr/bin/env python3
"""
Omnia 健康监控脚本

监控进程状态、内存使用、自动恢复异常进程。
"""

import os
import sys
import time
import json
import psutil
import subprocess
from pathlib import Path
from datetime import datetime

# 配置
OMNIA_HOME = Path.home() / ".omnia"
LOG_FILE = OMNIA_HOME / "logs" / "health_monitor.log"
STATE_FILE = OMNIA_HOME / "health_state.json"
ALERT_THRESHOLD_MEMORY_MB = 500  # 内存超过此值触发警告
CRITICAL_THRESHOLD_MEMORY_MB = 1000  # 内存超过此值触发重启
CHECK_INTERVAL_SECONDS = 60


def log(message: str, level: str = "INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}\n"
    
    # 确保日志目录存在
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line)
    
    print(log_line.strip())


def get_omnia_processes() -> list:
    """获取所有 Omnia 相关进程"""
    processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            
            # 检查是否是 Omnia 进程
            if any(keyword in cmdline.lower() for keyword in ['omnia', 'web_server', 'daemon_runner', 'neuro_center']):
                processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'cmdline': cmdline[:100],  # 截断
                    'memory_mb': proc.info['memory_info'].rss / 1024 / 1024,
                    'cpu_percent': proc.cpu_percent(interval=0.1),
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return processes


def check_process_health(processes: list) -> dict:
    """检查进程健康状态"""
    health = {
        'status': 'healthy',
        'warnings': [],
        'critical': [],
        'processes': processes,
    }
    
    for proc in processes:
        # 检查内存使用
        if proc['memory_mb'] > CRITICAL_THRESHOLD_MEMORY_MB:
            health['critical'].append(f"进程 {proc['pid']} 内存使用过高: {proc['memory_mb']:.1f}MB")
            health['status'] = 'critical'
        elif proc['memory_mb'] > ALERT_THRESHOLD_MEMORY_MB:
            health['warnings'].append(f"进程 {proc['pid']} 内存使用较高: {proc['memory_mb']:.1f}MB")
            if health['status'] == 'healthy':
                health['status'] = 'warning'
    
    return health


def save_state(health: dict):
    """保存健康状态"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    state = {
        'timestamp': datetime.now().isoformat(),
        'health': health,
    }
    
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def send_alert(message: str, level: str = "WARNING"):
    """发送告警（可以扩展为邮件、微信等）"""
    log(message, level)
    
    # TODO: 集成告警系统
    # - 发送邮件
    # - 发送微信消息
    # - 写入系统通知


def restart_service(service_name: str):
    """重启服务"""
    log(f"正在重启服务: {service_name}", "WARNING")
    
    try:
        # 使用 systemctl 重启
        result = subprocess.run(
            ['systemctl', '--user', 'restart', service_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            log(f"服务 {service_name} 重启成功", "INFO")
        else:
            log(f"服务 {service_name} 重启失败: {result.stderr}", "ERROR")
    except Exception as e:
        log(f"重启服务异常: {e}", "ERROR")


def monitor_loop():
    """监控循环"""
    log("健康监控启动")
    
    while True:
        try:
            # 获取进程
            processes = get_omnia_processes()
            
            # 检查健康状态
            health = check_process_health(processes)
            
            # 保存状态
            save_state(health)
            
            # 记录状态
            log(f"健康检查: {health['status']}, 进程数: {len(processes)}")
            
            # 处理告警
            if health['warnings']:
                for warning in health['warnings']:
                    send_alert(warning, "WARNING")
            
            if health['critical']:
                for critical in health['critical']:
                    send_alert(critical, "CRITICAL")
                
                # 自动重启（谨慎使用）
                # restart_service('omnia.service')
            
            # 等待下次检查
            time.sleep(CHECK_INTERVAL_SECONDS)
            
        except KeyboardInterrupt:
            log("健康监控停止", "INFO")
            break
        except Exception as e:
            log(f"监控异常: {e}", "ERROR")
            time.sleep(10)


def check_once():
    """单次检查（用于测试）"""
    processes = get_omnia_processes()
    health = check_process_health(processes)
    save_state(health)
    
    print(json.dumps(health, indent=2, ensure_ascii=False))
    return health


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # 单次检查模式
        check_once()
    else:
        # 持续监控模式
        monitor_loop()
