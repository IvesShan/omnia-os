"""
Omnia 日志配置
统一的日志管理模块
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "omnia",
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    log_format: Optional[str] = None
) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径（可选）
        log_format: 日志格式（可选）
    
    Returns:
        配置好的日志记录器
    """
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 默认日志格式
    if log_format is None:
        log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（可选）
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
    
    Returns:
        日志记录器
    """
    return logging.getLogger(name)


# 默认日志记录器
default_logger = setup_logger()


# 便捷函数
def info(message: str, *args, **kwargs):
    """记录信息日志"""
    default_logger.info(message, *args, **kwargs)


def error(message: str, *args, **kwargs):
    """记录错误日志"""
    default_logger.error(message, *args, **kwargs)


def warning(message: str, *args, **kwargs):
    """记录警告日志"""
    default_logger.warning(message, *args, **kwargs)


def debug(message: str, *args, **kwargs):
    """记录调试日志"""
    default_logger.debug(message, *args, **kwargs)


def exception(message: str, *args, **kwargs):
    """记录异常日志（包含堆栈跟踪）"""
    default_logger.exception(message, *args, **kwargs)
