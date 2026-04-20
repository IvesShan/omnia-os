"""
任务中断管理器
支持通过 "/" 快捷指令终止正在进行的任务
"""

import os
import json
import time
from pathlib import Path
from typing import Optional

# 中断标志文件路径
INTERRUPT_DIR = Path.home() / ".openclaw" / "workspace" / "omnia-os" / ".tmp"
INTERRUPT_FILE = INTERRUPT_DIR / "interrupt.flag"


def init_interrupt_system():
    """初始化中断系统"""
    INTERRUPT_DIR.mkdir(parents=True, exist_ok=True)
    clear_interrupt()


def set_interrupt(reason: str = "user_request"):
    """设置中断标志"""
    data = {
        "interrupted": True,
        "reason": reason,
        "timestamp": time.time()
    }
    with open(INTERRUPT_FILE, 'w') as f:
        json.dump(data, f)


def clear_interrupt():
    """清除中断标志"""
    if INTERRUPT_FILE.exists():
        INTERRUPT_FILE.unlink()


def check_interrupt() -> bool:
    """检查是否收到中断信号"""
    if not INTERRUPT_FILE.exists():
        return False
    
    try:
        with open(INTERRUPT_FILE, 'r') as f:
            data = json.load(f)
            return data.get("interrupted", False)
    except:
        return False


def get_interrupt_info() -> Optional[dict]:
    """获取中断信息"""
    if not INTERRUPT_FILE.exists():
        return None
    
    try:
        with open(INTERRUPT_FILE, 'r') as f:
            return json.load(f)
    except:
        return None


class InterruptibleTask:
    """可中断的任务上下文管理器"""
    
    def __init__(self, task_name: str = "unnamed"):
        self.task_name = task_name
        self.interrupted = False
    
    def __enter__(self):
        clear_interrupt()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if check_interrupt():
            self.interrupted = True
            print(f"\n[中断] 任务 '{self.task_name}' 已被用户终止")
            return True  # 抑制异常
        return False
    
    def check(self) -> bool:
        """检查是否应该中断，返回 True 表示应该停止"""
        if check_interrupt():
            self.interrupted = True
            return True
        return False
