"""
from core.logging_config import get_logger

logger = get_logger(__name__)

Smart Model Router - 智能模型路由器

支持三种模式：
1. LOCAL_ONLY - 只用本地模型
2. CLOUD_ONLY - 只用云端模型  
3. AUTO - 智能选择（默认）

使用方式：
    # 方式1：环境变量
    export OMNIA_MODEL_MODE=local_only
    
    # 方式2：代码中设置
    router = SmartModelRouter()
    router.set_mode("local_only")
    
    # 方式3：单次请求指定
    await router.chat(messages, mode="cloud_only")
"""

import os
from typing import Optional, Literal
from dataclasses import dataclass
from enum import Enum

from .local_client import LocalLLMClient, LocalModelConfig


class ModelMode(Enum):
    """模型使用模式"""
    LOCAL_ONLY = "local_only"    # 只用本地
    CLOUD_ONLY = "cloud_only"    # 只用云端
    AUTO = "auto"                # 智能选择（默认）


class ModelTier(Enum):
    """模型层级"""
    LOCAL = "local"              # 本地模型
    CLOUD_FAST = "cloud_fast"    # 云端快速模型
    CLOUD_SMART = "cloud_smart"  # 云端智能模型


@dataclass
class RouterConfig:
    """路由配置"""
    # 模型选择
    default_mode: ModelMode = ModelMode.AUTO
    local_model: str = "gemma-4-E4B-it-OBLITERATED-Q8_0.gguf"
    cloud_fast_model: str = "qianfan"
    cloud_smart_model: str = "kimi"
    
    # AUTO 模式参数
    prefer_local: bool = True
    complexity_threshold: int = 1000  # 超过此 token 数切换云端
    auto_fallback: bool = True        # 本地不可用时自动降级


class SmartModelRouter:
    """智能模型路由器"""
    
    _instance = None  # 单例
    
    def __new__(cls, config: Optional[RouterConfig] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: Optional[RouterConfig] = None):
        if self._initialized:
            return
            
        # 从环境变量读取模式
        env_mode = os.getenv("OMNIA_MODEL_MODE", "auto").lower()
        
        self.config = config or RouterConfig()
        self._mode = self._parse_mode(env_mode) or self.config.default_mode
        
        # 初始化本地客户端（仅在 local 模式下）
        env_mode = os.getenv("OMNIA_MODEL_MODE", "auto").lower()
        if env_mode in ("local", "local_only"):
            self.local_client = LocalLLMClient(LocalModelConfig(
                model_id=self.config.local_model
            ))
        else:
            # 云端模式下不初始化本地客户端，避免连接 localhost:8080
            self.local_client = None
            logger.info(f"[SmartRouter] Cloud mode: local client disabled")
        
        self._local_available: Optional[bool] = None
        self._last_check: float = 0
        self._initialized = True
    
    def _parse_mode(self, mode_str: str) -> Optional[ModelMode]:
        """解析模式字符串"""
        mode_map = {
            "local_only": ModelMode.LOCAL_ONLY,
            "local": ModelMode.LOCAL_ONLY,
            "cloud_only": ModelMode.CLOUD_ONLY,
            "cloud": ModelMode.CLOUD_ONLY,
            "auto": ModelMode.AUTO,
        }
        return mode_map.get(mode_str.lower())
    
    @property
    def mode(self) -> ModelMode:
        """当前模式"""
        return self._mode
    
    def set_mode(self, mode: str | ModelMode):
        """
        设置模式
        
        Args:
            mode: "local_only" | "cloud_only" | "auto" | ModelMode
        """
        if isinstance(mode, str):
            parsed = self._parse_mode(mode)
            if parsed is None:
                raise ValueError(f"无效模式: {mode}，支持: local_only, cloud_only, auto")
            self._mode = parsed
        else:
            self._mode = mode
    
    async def is_local_available(self) -> bool:
        """检查本地模型是否可用"""
        # 如果本地客户端未初始化，直接返回 False
        if self.local_client is None:
            return False
        
        import time
        now = time.time()
        
        # 缓存 60 秒
        if self._local_available is not None and (now - self._last_check) < 60:
            return self._local_available
        
        self._local_available = await self.local_client.health_check()
        self._last_check = now
        return self._local_available
    
    def estimate_complexity(self, messages: list[dict]) -> int:
        """估算对话复杂度（token 数）"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            # 简单估算：中文约 1.5 字/token，英文约 4 字符/token
            total += len(content) // 2
        return total
    
    async def select_model(
        self,
        messages: list[dict],
        mode: Optional[str] = None
    ) -> tuple[str, ModelTier]:
        """
        选择最佳模型
        
        Args:
            messages: 对话消息
            mode: 临时覆盖模式
            
        Returns:
            (model_id, tier)
        """
        # 确定使用的模式
        use_mode = self._mode
        if mode:
            parsed = self._parse_mode(mode)
            if parsed:
                use_mode = parsed
        
        # LOCAL_ONLY 模式
        if use_mode == ModelMode.LOCAL_ONLY:
            if await self.is_local_available():
                return (f"local/{self.config.local_model}", ModelTier.LOCAL)
            else:
                raise RuntimeError("本地模型不可用，请先启动服务: bash scripts/local_llm.sh start")
        
        # CLOUD_ONLY 模式
        if use_mode == ModelMode.CLOUD_ONLY:
            return (self.config.cloud_smart_model, ModelTier.CLOUD_SMART)
        
        # AUTO 模式
        if self.config.prefer_local and await self.is_local_available():
            complexity = self.estimate_complexity(messages)
            
            if complexity <= self.config.complexity_threshold:
                return (f"local/{self.config.local_model}", ModelTier.LOCAL)
            else:
                return (self.config.cloud_smart_model, ModelTier.CLOUD_SMART)
        
        # 降级到云端
        if self.config.auto_fallback:
            return (self.config.cloud_fast_model, ModelTier.CLOUD_FAST)
        
        raise RuntimeError("无可用模型")
    
    async def chat(
        self,
        messages: list[dict],
        mode: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        发送对话请求
        
        Args:
            messages: 对话消息
            mode: 临时覆盖模式（"local_only" | "cloud_only" | "auto"）
            **kwargs: 其他参数
            
        Returns:
            模型响应
        """
        model_id, tier = await self.select_model(messages, mode)
        
        if tier == ModelTier.LOCAL:
            # 使用本地模型
            response = await self.local_client.chat(messages, **kwargs)
            return response
        else:
            # 使用云端模型（通过现有的 provider 系统）
            # TODO: 集成到 Omnia 的 provider 系统
            raise NotImplementedError(
                f"云端模型 {model_id} 尚未集成。"
                f"请使用 mode='local_only' 或启动本地服务。"
            )


# 全局单例
_router: Optional[SmartModelRouter] = None


def get_router() -> SmartModelRouter:
    """获取全局路由器"""
    global _router
    if _router is None:
        _router = SmartModelRouter()
    return _router


# 便捷函数
async def smart_chat(
    messages: list[dict],
    mode: Optional[str] = None,
    **kwargs
) -> str:
    """
    智能对话（自动选择模型）
    
    Args:
        messages: 对话消息
        mode: 可选模式覆盖
        
    Returns:
        模型响应
    """
    router = get_router()
    return await router.chat(messages, mode=mode, **kwargs)


def set_model_mode(mode: str):
    """
    全局设置模型模式
    
    Args:
        mode: "local_only" | "cloud_only" | "auto"
    """
    router = get_router()
    router.set_mode(mode)


def get_model_mode() -> str:
    """获取当前模型模式"""
    router = get_router()
    return router.mode.value


# =========================================
# 健康检查函数
# =========================================

async def check_local_health() -> bool:
    """
    检查本地模型是否在线
    
    Returns:
        True 如果本地模型服务可用
    """
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:8080/health",
                timeout=aiohttp.ClientTimeout(total=3)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("status") == "ok"
                return False
    except (TimeoutError, ConnectionError) as e:
        return False


async def check_cloud_health() -> bool:
    """
    检查云端模型是否可用
    
    Returns:
        True 如果至少有一个云端 API 配置正确
    """
    import os
    
    # 检查 Kimi API
    kimi_key = os.getenv("MOONSHOT_API_KEY") or os.getenv("KIMI_API_KEY")
    if kimi_key:
        return True
    
    # 检查百度千帆
    baidu_key = os.getenv("BAIDU_API_KEY") or os.getenv("QIANFAN_API_KEY")
    if baidu_key:
        return True
    
    # 检查 DeepSeek
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    if deepseek_key:
        return True
    
    return False
