"""
Omnia 统一日志配置

Usage:
    from core.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("Hello, Omnia!")
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


# 日志目录 - 使用 ~/.omnia/logs
LOG_DIR = Path.home() / ".omnia" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    获取配置好的 logger
    
    Args:
        name: 模块名（通常使用 __name__）
        level: 日志级别
    
    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    
    # 避免重复配置
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # 文件处理器（按日期）
    log_file = LOG_DIR / f"omnia_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    return logger


# 全局配置函数
def configure_logging(level: int = logging.INFO):
    """配置全局日志"""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 移除默认处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)
    
    # 添加文件处理器
    log_file = LOG_DIR / f"omnia_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)


# 便捷函数
def log_info(message: str):
    """快速记录 INFO 日志"""
    get_logger("omnia").info(message)


def log_error(message: str):
    """快速记录 ERROR 日志"""
    get_logger("omnia").error(message)


def log_debug(message: str):
    """快速记录 DEBUG 日志"""
    get_logger("omnia").debug(message)


def log_warning(message: str):
    """快速记录 WARNING 日志"""
    get_logger("omnia").warning(message)
