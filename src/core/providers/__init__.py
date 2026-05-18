"""
Provider Abstraction - Omnia 2.0

参考：Hermes 的 18+ Provider 支持
目的：统一模型调用接口，支持多提供商切换和降级

支持 Provider:
- OpenAI (GPT-4, GPT-4o, GPT-3.5)
- Anthropic (Claude 3.5 Sonnet, Claude 3 Opus)
- Google (Gemini Pro, Gemini Ultra)
- Moonshot (Kimi)
- Baidu (Qianfan)
- Zhipu (GLM)
- Alibaba (Qwen)
- DeepSeek
- Xiaomi (MiMo)
- Ollama (本地模型)
- vLLM (本地部署)
- Custom (自定义端点)

Usage:
    from core.providers import ProviderResolver, ModelClient
    
    resolver = ProviderResolver()
    client = resolver.get_client("xiaomi/mimo-v2.5-pro")
    response = await client.chat(messages, tools)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable
import os


class ProviderType(Enum):
    """提供商类型"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MOONSHOT = "moonshot"
    KIMI = "kimi"
    QIANFAN = "qianfan"
    ZHIPU = "zhipu"
    QWEN = "qwen"
    DEEPSEEK = "deepseek"
    XIAOMI = "xiaomi"
    OLLAMA = "ollama"
    VLLM = "vllm"
    CUSTOM = "custom"


@dataclass
class ModelConfig:
    """模型配置"""
    provider: ProviderType
    model_id: str
    display_name: str
    context_window: int = 128_000
    max_output: int = 4_096
    supports_vision: bool = False
    supports_tools: bool = True
    supports_streaming: bool = True
    api_format: str = "openai"  # openai, anthropic, codex
    base_url: str | None = None
    auth_header: str = "Authorization"  # 认证头类型: Authorization, api-key
    auth_prefix: str = "Bearer "       # 认证头前缀: "Bearer ", "" 等
    default_params: dict = field(default_factory=dict)


# ============================================================================
# Predefined Models
# ============================================================================

MODEL_REGISTRY: dict[str, ModelConfig] = {
    # === OpenAI ===
    "openai/gpt-4o": ModelConfig(
        provider=ProviderType.OPENAI,
        model_id="gpt-4o",
        display_name="GPT-4o",
        context_window=128_000,
        max_output=16_384,
        supports_vision=True,
        supports_tools=True,
    ),
    "openai/gpt-4-turbo": ModelConfig(
        provider=ProviderType.OPENAI,
        model_id="gpt-4-turbo",
        display_name="GPT-4 Turbo",
        context_window=128_000,
        max_output=4_096,
        supports_vision=True,
        supports_tools=True,
    ),
    "openai/gpt-3.5-turbo": ModelConfig(
        provider=ProviderType.OPENAI,
        model_id="gpt-3.5-turbo",
        display_name="GPT-3.5 Turbo",
        context_window=16_384,
        max_output=4_096,
        supports_tools=True,
    ),
    
    # === Anthropic ===
    "anthropic/claude-3-5-sonnet": ModelConfig(
        provider=ProviderType.ANTHROPIC,
        model_id="claude-3-5-sonnet-20241022",
        display_name="Claude 3.5 Sonnet",
        context_window=200_000,
        max_output=8_192,
        supports_vision=True,
        supports_tools=True,
        api_format="anthropic",
    ),
    "anthropic/claude-3-opus": ModelConfig(
        provider=ProviderType.ANTHROPIC,
        model_id="claude-3-opus-20240229",
        display_name="Claude 3 Opus",
        context_window=200_000,
        max_output=4_096,
        supports_vision=True,
        supports_tools=True,
        api_format="anthropic",
    ),
    
    # === Google ===
    "google/gemini-pro": ModelConfig(
        provider=ProviderType.GOOGLE,
        model_id="gemini-1.5-pro",
        display_name="Gemini 1.5 Pro",
        context_window=1_000_000,
        max_output=8_192,
        supports_vision=True,
        supports_tools=True,
    ),
    
    # === Moonshot / Kimi ===
    "moonshot/kimi-code": ModelConfig(
        provider=ProviderType.MOONSHOT,
        model_id="kimi-code",
        display_name="Kimi Code",
        context_window=128_000,
        max_output=8_192,
        supports_tools=True,
        base_url="https://api.moonshot.cn/v1",
    ),
    "kimi/kimi-code": ModelConfig(
        provider=ProviderType.KIMI,
        model_id="kimi-code",
        display_name="Kimi Code",
        context_window=128_000,
        max_output=8_192,
        supports_tools=True,
        base_url="https://api.kimi.com/coding/v1",
    ),
    
    # === Baidu Qianfan ===
    "qianfan/qianfan-code": ModelConfig(
        provider=ProviderType.QIANFAN,
        model_id="qianfan-code-latest",
        display_name="Qianfan Code",
        context_window=128_000,
        max_output=8_192,
        supports_tools=True,
        base_url="https://qianfan.baidubce.com/v2/coding",
        api_format="openai",
    ),
    
    # === Zhipu GLM ===
    "zhipu/glm-4": ModelConfig(
        provider=ProviderType.ZHIPU,
        model_id="glm-4",
        display_name="GLM-4",
        context_window=128_000,
        max_output=8_192,
        supports_tools=True,
        base_url="https://open.bigmodel.cn/api/paas/v4",
    ),
    
    # === Alibaba Qwen ===
    "qwen/qwen-max": ModelConfig(
        provider=ProviderType.QWEN,
        model_id="qwen-max",
        display_name="Qwen Max",
        context_window=32_000,
        max_output=8_192,
        supports_tools=True,
        base_url="https://dashscope.aliyuncs.com/api/v1",
    ),
    
    # === DeepSeek ===
    "deepseek/deepseek-coder": ModelConfig(
        provider=ProviderType.DEEPSEEK,
        model_id="deepseek-coder",
        display_name="DeepSeek Coder",
        context_window=16_000,
        max_output=4_096,
        supports_tools=True,
        base_url="https://api.deepseek.com/v1",
    ),
    "deepseek/deepseek-v4-pro": ModelConfig(
        provider=ProviderType.DEEPSEEK,
        model_id="deepseek-v4-pro",
        display_name="DeepSeek V4 Pro",
        context_window=128_000,
        max_output=32_768,
        supports_tools=True,
        base_url="https://api.deepseek.com/v1",
    ),
    "deepseek/deepseek-v4-flash": ModelConfig(
        provider=ProviderType.DEEPSEEK,
        model_id="deepseek-v4-flash",
        display_name="DeepSeek V4 Flash",
        context_window=128_000,
        max_output=32_768,
        supports_tools=True,
        base_url="https://api.deepseek.com/v1",
    ),
    
    # === Xiaomi MiMo (Token Plan + 计费 API) ===
    "xiaomi/mimo-v2.5-pro": ModelConfig(
        provider=ProviderType.XIAOMI,
        model_id="mimo-v2.5-pro",
        display_name="MiMo V2.5 Pro",
        context_window=128_000,
        max_output=131_072,
        supports_vision=True,
        supports_tools=True,
        base_url="https://token-plan-cn.xiaomimimo.com/v1",
        auth_header="api-key",
        auth_prefix="",
    ),
    "xiaomi/mimo-v2.5": ModelConfig(
        provider=ProviderType.XIAOMI,
        model_id="mimo-v2.5",
        display_name="MiMo V2.5",
        context_window=128_000,
        max_output=32_768,
        supports_vision=True,
        supports_tools=True,
        base_url="https://token-plan-cn.xiaomimimo.com/v1",
        auth_header="api-key",
        auth_prefix="",
    ),
    "xiaomi/mimo-v2-pro": ModelConfig(
        provider=ProviderType.XIAOMI,
        model_id="mimo-v2-pro",
        display_name="MiMo V2 Pro",
        context_window=128_000,
        max_output=131_072,
        supports_vision=True,
        supports_tools=True,
        base_url="https://token-plan-cn.xiaomimimo.com/v1",
        auth_header="api-key",
        auth_prefix="",
    ),
    "xiaomi/mimo-v2-omni": ModelConfig(
        provider=ProviderType.XIAOMI,
        model_id="mimo-v2-omni",
        display_name="MiMo V2 Omni",
        context_window=128_000,
        max_output=32_768,
        supports_vision=True,
        supports_tools=True,
        base_url="https://token-plan-cn.xiaomimimo.com/v1",
        auth_header="api-key",
        auth_prefix="",
    ),
    "xiaomi/mimo-v2-flash": ModelConfig(
        provider=ProviderType.XIAOMI,
        model_id="mimo-v2-flash",
        display_name="MiMo V2 Flash",
        context_window=128_000,
        max_output=65_536,
        supports_tools=True,
        base_url="https://token-plan-cn.xiaomimimo.com/v1",
        auth_header="api-key",
        auth_prefix="",
    ),
    
    # === Ollama (Local) ===
    "ollama/llama3": ModelConfig(
        provider=ProviderType.OLLAMA,
        model_id="llama3",
        display_name="Llama 3 (Local)",
        context_window=8_000,
        max_output=4_096,
        supports_tools=False,
        base_url="http://localhost:11434/v1",
    ),
    "ollama/codellama": ModelConfig(
        provider=ProviderType.OLLAMA,
        model_id="codellama",
        display_name="CodeLlama (Local)",
        context_window=16_000,
        max_output=4_096,
        supports_tools=False,
        base_url="http://localhost:11434/v1",
    ),
    # === Local LLM (llama.cpp server) ===
    "local/gemma-4-4b": ModelConfig(
        provider=ProviderType.CUSTOM,
        model_id="gemma-4-E4B-it-OBLITERATED-Q8_0.gguf",
        display_name="Gemma 4 4B (Local GPU)",
        context_window=32_768,
        max_output=4_096,
        supports_vision=False,
        supports_tools=False,
        supports_streaming=True,
        base_url="http://localhost:8080",
    ),
    "local/qwen-7b": ModelConfig(
        provider=ProviderType.CUSTOM,
        model_id="qwen-7b",
        display_name="Qwen 7B (Local GPU)",
        context_window=32_768,
        max_output=4_096,
        supports_vision=False,
        supports_tools=False,
        supports_streaming=True,
        base_url="http://localhost:8080",
    ),

}


# ============================================================================
# Provider Base Class
# ============================================================================

class ModelClient(ABC):
    """模型客户端基类"""
    
    def __init__(self, config: ModelConfig, api_key: str | None = None):
        self.config = config
        self.api_key = api_key
    
    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs
    ) -> dict:
        """
        发送聊天请求
        
        Returns:
            {
                "content": str,
                "tool_calls": list | None,
                "usage": {"input": int, "output": int},
                "model": str,
            }
        """
        pass
    
    @abstractmethod
    async def stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs
    ):
        """流式聊天"""
        pass


# ============================================================================
# OpenAI-compatible Client
# ============================================================================

class OpenAIClient(ModelClient):
    """OpenAI 兼容客户端"""
    
    def _build_headers(self) -> dict:
        """构建请求头"""
        headers = {
            "Content-Type": "application/json",
        }
        
        if self.api_key:
            auth_value = f"{self.config.auth_prefix}{self.api_key}"
            headers[self.config.auth_header] = auth_value
        
        return headers
    
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs
    ) -> dict:
        import aiohttp
        
        base_url = self.config.base_url or "https://api.openai.com/v1"
        url = f"{base_url}/chat/completions"
        
        headers = self._build_headers()
        
        payload = {
            "model": self.config.model_id,
            "messages": messages,
            **self.config.default_params,
            **kwargs
        }
        
        if tools:
            payload["tools"] = tools
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                data = await resp.json()
        
        choice = data["choices"][0]
        message = choice["message"]
        
        return {
            "content": message.get("content", ""),
            "tool_calls": message.get("tool_calls"),
            "usage": {
                "input": data.get("usage", {}).get("prompt_tokens", 0),
                "output": data.get("usage", {}).get("completion_tokens", 0),
            },
            "model": data.get("model", self.config.model_id),
        }
    
    async def stream(self, messages: list[dict], tools: list[dict] | None = None, **kwargs):
        """流式聊天 - SSE 流式响应"""
        import json as _json
        
        # 如果底层支持流式调用
        try:
            result = await self.chat(messages, tools, **kwargs)
            content = result.get("content", "")
            
            # 按块发送，模拟 SSE 流式效果
            chunk_size = max(1, len(content) // max(1, len(content) // 10))
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i+chunk_size]
                yield {
                    "choices": [{
                        "delta": {"content": chunk},
                        "finish_reason": None,
                    }],
                    "model": result.get("model", "unknown"),
                }
            
            # 发送结束标记
            yield {
                "choices": [{
                    "delta": {},
                    "finish_reason": "stop",
                }],
                "model": result.get("model", "unknown"),
                "usage": result.get("usage", {}),
            }
        except Exception as e:
            yield {
                "choices": [{
                    "delta": {"content": f"[Stream Error: {e}]"},
                    "finish_reason": "stop",
                }],
            }


# ============================================================================
# Anthropic Client
# ============================================================================

class AnthropicClient(ModelClient):
    """Anthropic 客户端"""
    
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs
    ) -> dict:
        import aiohttp
        
        url = "https://api.anthropic.com/v1/messages"
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        
        # 转换消息格式
        system = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system += msg["content"] + "\n"
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        payload = {
            "model": self.config.model_id,
            "max_tokens": self.config.max_output,
            "system": system,
            "messages": anthropic_messages,
            **kwargs
        }
        
        if tools:
            payload["tools"] = self._convert_tools(tools)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                data = await resp.json()
        
        content_blocks = data.get("content", [])
        text_content = ""
        tool_use = []
        
        for block in content_blocks:
            if block["type"] == "text":
                text_content += block["text"]
            elif block["type"] == "tool_use":
                tool_use.append(block)
        
        return {
            "content": text_content,
            "tool_calls": tool_use if tool_use else None,
            "usage": {
                "input": data.get("usage", {}).get("input_tokens", 0),
                "output": data.get("usage", {}).get("output_tokens", 0),
            },
            "model": data.get("model", self.config.model_id),
        }
    
    def _convert_tools(self, openai_tools: list[dict]) -> list[dict]:
        """转换 OpenAI 工具格式到 Anthropic 格式"""
        anthropic_tools = []
        for tool in openai_tools:
            fn = tool.get("function", {})
            anthropic_tools.append({
                "name": fn.get("name"),
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object"})
            })
        return anthropic_tools
    
    async def stream(self, messages: list[dict], tools: list[dict] | None = None, **kwargs):
        """流式聊天"""
        result = await self.chat(messages, tools, **kwargs)
        yield result["content"]


# ============================================================================
# Provider Resolver
# ============================================================================

class ProviderResolver:
    """
    Provider 解析器
    
    功能：
    - 根据模型 ID 解析 Provider
    - 获取 API Key
    - 创建客户端实例
    - 支持降级和轮询
    """
    
    # API Key 环境变量映射
    ENV_KEY_MAP = {
        ProviderType.OPENAI: "OPENAI_API_KEY",
        ProviderType.ANTHROPIC: "ANTHROPIC_API_KEY",
        ProviderType.GOOGLE: "GOOGLE_API_KEY",
        ProviderType.MOONSHOT: "MOONSHOT_API_KEY",
        ProviderType.KIMI: "KIMI_API_KEY",
        ProviderType.QIANFAN: "QIANFAN_API_KEY",
        ProviderType.ZHIPU: "ZHIPU_API_KEY",
        ProviderType.QWEN: "QWEN_API_KEY",
        ProviderType.DEEPSEEK: "DEEPSEEK_API_KEY",
        ProviderType.XIAOMI: "MIMO_API_KEY",
    }
    
    def __init__(self, api_keys: dict[str, str] | None = None):
        """
        Args:
            api_keys: 手动传入的 API Keys {provider: key}
        """
        self.api_keys = api_keys or {}
    
    def get_config(self, model_id: str) -> ModelConfig | None:
        """获取模型配置"""
        return MODEL_REGISTRY.get(model_id)
    
    def get_api_key(self, provider: ProviderType) -> str | None:
        """获取 API Key"""
        # 1. 手动传入的 key
        if provider.value in self.api_keys:
            return self.api_keys[provider.value]
        
        # 2. 环境变量
        env_key = self.ENV_KEY_MAP.get(provider)
        if env_key:
            return os.environ.get(env_key)
        
        return None
    
    def get_client(self, model_id: str, api_key: str | None = None) -> ModelClient:
        """
        获取模型客户端
        
        Args:
            model_id: 模型 ID (e.g., "openai/gpt-4o" or "xiaomi/mimo-v2.5-pro")
            api_key: 可选的 API Key（覆盖默认）
        
        Returns:
            ModelClient 实例
        """
        config = self.get_config(model_id)
        if not config:
            raise ValueError(f"Unknown model: {model_id}")
        
        # 获取 API Key
        final_key = api_key or self.get_api_key(config.provider)
        
        # 根据类型创建客户端
        if config.api_format == "anthropic":
            return AnthropicClient(config, final_key)
        else:
            return OpenAIClient(config, final_key)
    
    def list_available(self) -> list[str]:
        """列出可用的模型（有 API Key）"""
        available = []
        for model_id, config in MODEL_REGISTRY.items():
            if self.get_api_key(config.provider):
                available.append(model_id)
        return available
    
    def get_fallback_chain(self, model_id: str) -> list[str]:
        """
        获取降级链
        
        例如：openai/gpt-4o -> openai/gpt-3.5-turbo -> moonshot/kimi-code
        """
        config = self.get_config(model_id)
        if not config:
            return []
        
        chain = [model_id]
        provider = config.provider
        
        # 同 provider 的其他模型
        for mid, cfg in MODEL_REGISTRY.items():
            if cfg.provider == provider and mid != model_id:
                if self.get_api_key(provider):
                    chain.append(mid)
        
        # 其他 provider 的模型
        for mid, cfg in MODEL_REGISTRY.items():
            if cfg.provider != provider and mid not in chain:
                if self.get_api_key(cfg.provider):
                    chain.append(mid)
        
        return chain[:5]  # 最多 5 个降级选项


# ============================================================================
# Convenience Functions
# ============================================================================

def get_client(model_id: str, api_key: str | None = None) -> ModelClient:
    """快捷函数：获取模型客户端"""
    resolver = ProviderResolver()
    return resolver.get_client(model_id, api_key)


def list_available_models() -> list[str]:
    """快捷函数：列出可用模型"""
    resolver = ProviderResolver()
    return resolver.list_available()
