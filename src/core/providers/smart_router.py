"""
Smart Model Router - 智能模型路由器（v2）

支持三种模式：
1. LOCAL_ONLY - 只用本地模型
2. CLOUD_ONLY - 只用云端模型
3. AUTO - 智能选择（默认）

配置方式（优先级从高到低）：
- 代码传入：SmartModelRouter(mode_override="local_only")
- 环境变量：export OMNIA_MODEL_MODE=local_only
- 默认值：RouterConfig.default_mode（auto）

修复历史：
- v2: 修复重复变量赋值、按需初始化本地客户端、支持 mode_override、
      provider 注册表、chat 双重 fallback、健康检查缓存
"""

from __future__ import annotations

from core.logging_config import get_logger

logger = get_logger(__name__)

import os
import time
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from .local_client import LocalLLMClient, LocalModelConfig


class ModelMode(Enum):
    """模型使用模式"""
    LOCAL_ONLY = "local_only"
    CLOUD_ONLY = "cloud_only"
    AUTO = "auto"


class ModelTier(Enum):
    """模型层级"""
    LOCAL = "local"
    CLOUD_FAST = "cloud_fast"
    CLOUD_SMART = "cloud_smart"


def _parse_mode(s: Optional[str]) -> Optional[ModelMode]:
    """解析模式字符串，返回 None 表示无效/未指定"""
    if not s:
        return None
    s = s.strip().lower()
    return {
        "local_only": ModelMode.LOCAL_ONLY,
        "local": ModelMode.LOCAL_ONLY,
        "cloud_only": ModelMode.CLOUD_ONLY,
        "cloud": ModelMode.CLOUD_ONLY,
        "auto": ModelMode.AUTO,
    }.get(s)


@dataclass
class RouterConfig:
    """路由配置"""
    default_mode: ModelMode = ModelMode.AUTO
    local_model: str = "gemma-4-E4B-it-OBLITERATED-Q8_0.gguf"
    cloud_fast_model: str = "qianfan"
    cloud_smart_model: str = "kimi"

    # AUTO 模式参数
    prefer_local: bool = True
    complexity_threshold: int = 1000  # 超过此 token 数切换云端
    auto_fallback: bool = True        # 本地不可用时自动降级


class SmartModelRouter:
    """
    智能模型路由器（全局单例）

    优先级：mode_override 构造参数 > OMNIA_MODEL_MODE 环境变量 > config.default_mode
    """

    _instance: Optional["SmartModelRouter"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        config: Optional[RouterConfig] = None,
        mode_override: Optional[str] = None,
    ):
        if self._initialized:
            return

        self.config = config or RouterConfig()

        # 解析模式：优先级 mode_override > 环境变量 > config.default_mode
        parsed = (
            _parse_mode(mode_override)
            or _parse_mode(os.getenv("OMNIA_MODEL_MODE"))
            or self.config.default_mode
        )
        self._mode: ModelMode = parsed

        # 本地客户端：按需延迟初始化
        self._local_client: Optional[LocalLLMClient] = None
        self._local_available: Optional[bool] = None
        self._last_health_check: float = 0.0
        self._health_check_interval: float = 60.0  # 秒

        # provider 注册表（运行时可注册额外 provider）
        self._provider_registry: dict[str, object] = {}

        # 如果当前模式需要本地，立即初始化
        if self._need_local():
            self._ensure_local_client()

        self._initialized = True
        logger.info(
            f"[SmartRouter] Initialized: mode={self._mode.value}, "
            f"local_client={'ready' if self._local_client else 'deferred'}"
        )

    # ─────────────────────────────────────────────
    # 内部辅助
    # ─────────────────────────────────────────────

    def _need_local(self) -> bool:
        """判断当前模式是否可能需要本地模型"""
        if self._mode == ModelMode.LOCAL_ONLY:
            return True
        if self._mode == ModelMode.AUTO and self.config.prefer_local:
            return True
        return False

    def _ensure_local_client(self):
        """按需初始化本地客户端，避免云端模式下无谓初始化"""
        if self._local_client is not None:
            return
        try:
            self._local_client = LocalLLMClient(
                LocalModelConfig(model_id=self.config.local_model)
            )
            # 注册到 provider 表（接口兼容 ModelClient）
            self._provider_registry.setdefault("local", self._local_client)
            logger.info(f"[SmartRouter] Local client initialized: {self.config.local_model}")
        except Exception as e:
            logger.warning(f"[SmartRouter] Failed to init local client: {e}")
            self._local_client = None

    def _select_cloud_provider(self) -> str:
        """选择一个可用的云端 provider"""
        import os as _os
        # 优先小米 → DeepSeek → 千帆 → Kimi（Kimi key 已失效，放最后）
        if _os.getenv("MIMO_API_KEY"):
            return "xiaomi"
        if _os.getenv("DEEPSEEK_API_KEY"):
            return "deepseek"
        if _os.getenv("QIANFAN_API_KEY") or _os.getenv("BAIDU_API_KEY"):
            return "qianfan"
        if _os.getenv("MOONSHOT_API_KEY") or _os.getenv("KIMI_API_KEY"):
            return "kimi"
        # 从注册表里找一个非 local 的
        for name in self._provider_registry:
            if name != "local":
                return name
        return "xiaomi"  # 默认返回小米，让调用方报错也更合理
    # ─────────────────────────────────────────────
    # 模式切换
    # ─────────────────────────────────────────────

    @property
    def mode(self) -> ModelMode:
        return self._mode

    def set_mode(self, mode: str | ModelMode):
        """运行时切换模式"""
        if isinstance(mode, str):
            parsed = _parse_mode(mode)
            if parsed is None:
                raise ValueError(
                    f"无效模式: {mode}，支持: local_only, cloud_only, auto"
                )
            self._mode = parsed
        else:
            self._mode = mode

        # 如果切换到需要本地的模式，确保本地客户端已初始化
        if self._need_local():
            self._ensure_local_client()

        logger.info(f"[SmartRouter] Mode changed to: {self._mode.value}")

    # ─────────────────────────────────────────────
    # 健康检查（带缓存）
    # ─────────────────────────────────────────────

    async def is_local_available(self, force: bool = False) -> bool:
        """检查本地模型是否可用（60 秒缓存）"""
        if not self._need_local():
            return False

        self._ensure_local_client()
        if self._local_client is None:
            return False

        now = time.time()
        if (
            not force
            and self._local_available is not None
            and (now - self._last_health_check) < self._health_check_interval
        ):
            return self._local_available

        try:
            self._local_available = await self._local_client.health_check()
        except Exception:
            self._local_available = False

        self._last_health_check = time.time()
        return self._local_available

    # ─────────────────────────────────────────────
    # 复杂度估算
    # ─────────────────────────────────────────────

    def estimate_complexity(self, messages: list[dict]) -> int:
        """估算对话复杂度（token 数）"""
        total = 0
        for msg in messages:
            content = msg.get("content") or ""
            total += max(1, len(content) // 2)
        return total

    # ─────────────────────────────────────────────
    # provider 注册
    # ─────────────────────────────────────────────

    def register_provider(self, name: str, client):
        """注册外部 provider（可选）"""
        self._provider_registry[name] = client
        logger.info(f"[SmartRouter] Registered provider: {name}")

    # ─────────────────────────────────────────────
    # 核心：选择 provider
    # ─────────────────────────────────────────────

    def _choose_provider(self, messages: list[dict], mode: Optional[str] = None):
        """
        选择 provider 和 tier

        Returns:
            (provider_name, ModelTier)
        """
        use_mode = _parse_mode(mode) or self._mode

        # ── LOCAL_ONLY ──
        if use_mode == ModelMode.LOCAL_ONLY:
            return "local", ModelTier.LOCAL

        # ── CLOUD_ONLY ──
        if use_mode == ModelMode.CLOUD_ONLY:
            return self._select_cloud_provider(), ModelTier.CLOUD_SMART

        # ── AUTO ──
        if self.config.prefer_local:
            return "local", ModelTier.LOCAL
        return self._select_cloud_provider(), ModelTier.CLOUD_FAST

    # ─────────────────────────────────────────────
    # 核心：调用 provider
    # ─────────────────────────────────────────────

    async def _call_provider(
        self, provider: str, messages: list[dict], **kwargs
    ) -> dict:
        """调用指定 provider 的 chat 方法"""
        client = self._provider_registry.get(provider)
        if client is None:
            raise RuntimeError(f"Provider '{provider}' not registered")
        return await client.chat(messages, **kwargs)

    async def _try_chat(
        self, provider: str, messages: list[dict], **kwargs
    ) -> Optional[dict]:
        """尝试调用，失败返回 None（用于 fallback）"""
        try:
            return await self._call_provider(provider, messages, **kwargs)
        except (ConnectionError, OSError, TimeoutError) as e:
            logger.warning(f"[SmartRouter] Network error ({provider}): {e}")
            return None
        except Exception as e:
            logger.warning(f"[SmartRouter] Provider error ({provider}): {e}")
            return None

    # ─────────────────────────────────────────────
    # 公开接口：chat
    # ─────────────────────────────────────────────

    async def chat(
        self,
        messages: list[dict],
        mode: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        发送对话请求（自动选择模型 + fallback）

        Args:
            messages: 对话消息
            mode: 临时覆盖模式（"local_only" | "cloud_only" | "auto"）
            **kwargs: 传递给底层 provider 的额外参数

        Returns:
            模型响应内容（str）

        Raises:
            RuntimeError: 所有 provider 均不可用
        """
        provider, tier = self._choose_provider(messages, mode)

        # ── 本地模式：检查可用性，必要时 fallback ──
        if provider == "local":
            avail = await self.is_local_available()
            if not avail:
                if self.config.auto_fallback:
                    provider = self._select_cloud_provider()
                    tier = ModelTier.CLOUD_FAST
                    logger.info("[SmartRouter] Local unavailable, fallback to cloud")
                else:
                    raise RuntimeError(
                        "本地模型不可用。请启动: bash scripts/local_llm.sh start"
                    )

        # ── 第一次尝试 ──
        result = await self._try_chat(provider, messages, **kwargs)
        if result is not None:
            return result.get("content", "")

        # ── 第二次尝试（fallback） ──
        if self.config.auto_fallback:
            fallback = (
                self._select_cloud_provider() if provider == "local" else "local"
            )
            # 确保 fallback 的 provider 已注册
            if fallback == "local":
                self._ensure_local_client()
                avail = await self.is_local_available()
                if not avail:
                    # 云端 fallback 失败 → 尝试另一个云端
                    fallback = self._select_cloud_provider()

            result = await self._try_chat(fallback, messages, **kwargs)
            if result is not None:
                return result.get("content", "")

        raise RuntimeError(
            f"All providers failed. Tried: {provider} + fallback. "
            f"Check API keys or local model server."
        )


# ─────────────────────────────────────────────
# 全局单例 + 便捷函数
# ─────────────────────────────────────────────

_router: Optional[SmartModelRouter] = None


def get_router() -> SmartModelRouter:
    """获取全局路由器"""
    global _router
    if _router is None:
        _router = SmartModelRouter()
    return _router


def reset_router():
    """重置全局路由器（用于测试）"""
    global _router
    SmartModelRouter._instance = None
    _router = None


async def smart_chat(
    messages: list[dict],
    mode: Optional[str] = None,
    **kwargs,
) -> str:
    """智能对话（自动选择模型）"""
    router = get_router()
    return await router.chat(messages, mode=mode, **kwargs)


def set_model_mode(mode: str):
    """全局设置模型模式"""
    router = get_router()
    router.set_mode(mode)


def get_model_mode() -> str:
    """获取当前模型模式"""
    router = get_router()
    return router.mode.value
