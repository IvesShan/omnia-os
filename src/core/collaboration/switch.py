"""协作开关配置

定义何时启用协作功能
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import re


class CollaborationMode(Enum):
    """协作模式"""
    OFF = "off"                    # 关闭协作
    ON_DEMAND = "on_demand"        # 按需启用（需要明确触发）
    AUTO = "auto"                  # 自动协作（智能判断）


@dataclass
class CollaborationConfig:
    """协作配置"""
    mode: CollaborationMode = CollaborationMode.OFF
    trigger_keywords: List[str] = None  # 触发关键词
    auto_delegate: bool = False          # 自动委托
    
    def __post_init__(self):
        if self.trigger_keywords is None:
            # 默认触发关键词
            self.trigger_keywords = [
                "@协作", "@collab", "@合作",
                "让Omnia", "委托给Omnia", "本地执行",
                "两边合作", "协作完成", "共同完成"
            ]
    
    def should_trigger_collaboration(self, message: str) -> bool:
        """判断是否应该触发协作"""
        if self.mode == CollaborationMode.OFF:
            return False
        
        if self.mode == CollaborationMode.AUTO:
            # 自动模式：智能判断
            return self._smart_detect(message)
        
        # 按需模式：检查关键词
        return any(kw in message for kw in self.trigger_keywords)
    
    def _smart_detect(self, message: str) -> bool:
        """智能检测是否需要协作（AUTO模式）"""
        # 需要双方配合的任务特征
        patterns = [
            r"同时.*(本地|云端|文件|API)",
            r"先.*再.*然后",
            r"两边.*(完成|执行|合作)",
            r"(本地|文件).*(分析|上传|部署)",
        ]
        return any(re.search(p, message) for p in patterns)


# 全局配置
_config: Optional[CollaborationConfig] = None

def get_collaboration_config() -> CollaborationConfig:
    """获取协作配置"""
    global _config
    if _config is None:
        _config = CollaborationConfig(mode=CollaborationMode.ON_DEMAND)
    return _config

def set_collaboration_mode(mode: CollaborationMode):
    """设置协作模式"""
    global _config
    if _config is None:
        _config = CollaborationConfig()
    _config.mode = mode
