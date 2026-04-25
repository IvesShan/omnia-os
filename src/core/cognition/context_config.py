"""
上下文管理配置

这个文件允许用户自定义上下文管理的行为，包括：
- 不同模型的上下文窗口大小
- Token 估算参数
- 压缩策略
- 历史加载策略
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ContextConfig:
    """上下文管理配置"""
    
    # ========== Token 估算参数 ==========
    # 中文 token 估算：多少字符 = 1 token
    chinese_chars_per_token: int = 2
    
    # 英文 token 估算：多少字符 = 1 token
    english_chars_per_token: int = 4
    
    # 其他字符 token 估算
    other_chars_per_token: int = 3
    
    # 消息格式开销（每条消息额外的 token 数）
    message_format_overhead: int = 4
    
    # 格式开销比例（额外增加的比例）
    format_overhead_ratio: float = 0.1
    
    # ========== 上下文窗口配置 ==========
    # 上下文利用率阈值（超过此值触发压缩）
    context_utilization_threshold: float = 0.7
    
    # 安全边际（使用上下文窗口的比例）
    safety_margin: float = 0.9
    
    # 预留输出 token 比例
    output_token_ratio: float = 0.3
    
    # 预留系统提示词 token 比例
    system_prompt_token_ratio: float = 0.1
    
    # ========== 历史加载策略 ==========
    # 前端历史最小条数（低于此值从数据库加载）
    min_frontend_history: int = 10
    
    # 数据库加载历史条数
    db_history_limit: int = 40
    
    # 合并后最大历史条数
    max_merged_history: int = 80
    
    # 根据上下文窗口动态调整：每多少 tokens 允许 1 条消息
    tokens_per_message: int = 500
    
    # 最小历史消息数
    min_history_messages: int = 20
    
    # 最大历史消息数
    max_history_messages: int = 100
    
    # ========== 压缩策略 ==========
    # 保留最近消息数（不压缩）
    preserve_recent_messages: int = 5
    
    # 最小保留消息数（紧急压缩时）
    min_preserve_messages: int = 3
    
    # 是否启用摘要压缩
    enable_summary_compression: bool = True
    
    # 是否启用滑动窗口
    enable_sliding_window: bool = True
    
    # ========== 调试选项 ==========
    # 是否打印 token 统计信息
    verbose: bool = True
    
    # 是否记录压缩日志
    log_compression: bool = True


# 默认配置
DEFAULT_CONFIG = ContextConfig()


# 模型特定配置
MODEL_SPECIFIC_CONFIGS: Dict[str, ContextConfig] = {
    # Kimi 模型 - 大上下文窗口，可以保留更多历史
    "kimi": ContextConfig(
        context_utilization_threshold=0.8,  # 更高的利用率
        db_history_limit=60,  # 加载更多历史
        max_merged_history=120,  # 允许更多历史
        preserve_recent_messages=10,  # 保留更多最近消息
    ),
    
    # Qianfan - 小上下文窗口，需要更激进的压缩
    "qianfan": ContextConfig(
        context_utilization_threshold=0.6,  # 更低的阈值
        db_history_limit=20,  # 加载较少历史
        max_merged_history=40,  # 限制历史条数
        preserve_recent_messages=3,  # 保留较少最近消息
    ),
    
    # 本地模型 - 通常上下文窗口较小
    "local": ContextConfig(
        context_utilization_threshold=0.5,  # 更保守的阈值
        db_history_limit=15,
        max_merged_history=30,
        preserve_recent_messages=3,
    ),
}


def get_config(model: str) -> ContextConfig:
    """
    获取指定模型的配置
    
    Args:
        model: 模型名称
        
    Returns:
        ContextConfig 实例
    """
    # 精确匹配
    if model in MODEL_SPECIFIC_CONFIGS:
        return MODEL_SPECIFIC_CONFIGS[model]
    
    # 模糊匹配
    model_lower = model.lower()
    for key, config in MODEL_SPECIFIC_CONFIGS.items():
        if key.lower() in model_lower or model_lower in key.lower():
            return config
    
    # 默认配置
    return DEFAULT_CONFIG


# ========== 用户自定义配置 ==========
# 用户可以创建 ~/.omnia/context_config.py 来自定义配置

def load_user_config() -> Optional[ContextConfig]:
    """
    加载用户自定义配置
    
    查找路径：
    1. ~/.omnia/context_config.py
    2. 项目根目录/.omnia/context_config.py
    
    Returns:
        用户自定义的 ContextConfig，如果不存在则返回 None
    """
    from pathlib import Path
    import importlib.util
    
    # 查找配置文件
    config_paths = [
        Path.home() / ".omnia" / "context_config.py",
        Path.cwd() / ".omnia" / "context_config.py",
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            try:
                spec = importlib.util.spec_from_file_location("user_context_config", config_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, "CONTEXT_CONFIG"):
                        return module.CONTEXT_CONFIG
            except Exception as e:
                print(f"[ContextConfig] Failed to load user config: {e}")
    
    return None


# 缓存用户配置
_user_config_cache: Optional[ContextConfig] = None


def get_effective_config(model: str) -> ContextConfig:
    """
    获取有效配置（合并默认配置、模型特定配置和用户自定义配置）
    
    Args:
        model: 模型名称
        
    Returns:
        有效的 ContextConfig 实例
    """
    global _user_config_cache
    
    # 获取基础配置
    base_config = get_config(model)
    
    # 加载用户配置（只加载一次）
    if _user_config_cache is None:
        _user_config_cache = load_user_config()
    
    # 如果没有用户配置，返回基础配置
    if _user_config_cache is None:
        return base_config
    
    # 合并配置（用户配置覆盖基础配置）
    # 这里简单返回用户配置，实际可以实现更复杂的合并逻辑
    return _user_config_cache


# ========== 示例：用户自定义配置 ==========
"""
# 保存到 ~/.omnia/context_config.py

from core.cognition.context_config import ContextConfig

CONTEXT_CONFIG = ContextConfig(
    # 更激进的压缩策略
    context_utilization_threshold=0.6,
    
    # 加载更多历史
    db_history_limit=50,
    max_merged_history=100,
    
    # 保留更多最近消息
    preserve_recent_messages=8,
    
    # 启用详细日志
    verbose=True,
)
"""
