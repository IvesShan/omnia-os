"""
LLM 客户端
支持多个 Provider 的异步调用
"""

import json
from typing import AsyncGenerator, Dict, List, Optional

import httpx
import yaml

from src.omnia.config import settings


class LLMClient:
    """LLM 客户端 - 支持异步调用"""
    
    def __init__(self):
        self.timeout = settings.request_timeout
        self._load_providers()
    
    def _load_providers(self):
        """加载 Provider 配置"""
        self.providers = {}
        
        # 加载本地模型配置
        if settings.local_llm_config.exists():
            try:
                with open(settings.local_llm_config) as f:
                    config = yaml.safe_load(f)
                    self.providers["local"] = config
            except Exception as e:
                print(f"[WARNING] Failed to load local LLM config: {e}")
        
        # 从环境变量加载 API keys
        if settings.openai_api_key:
            self.providers["openai"] = {
                "api_key": settings.openai_api_key,
                "base_url": "https://api.openai.com/v1"
            }
        
        if settings.deepseek_api_key:
            self.providers["deepseek"] = {
                "api_key": settings.deepseek_api_key,
                "base_url": "https://api.deepseek.com/v1"
            }
        
        if settings.moonshot_api_key:
            self.providers["moonshot"] = {
                "api_key": settings.moonshot_api_key,
                "base_url": "https://api.moonshot.cn/v1"
            }
        
        if settings.zhipu_api_key:
            self.providers["zhipu"] = {
                "api_key": settings.zhipu_api_key,
                "base_url": "https://open.bigmodel.cn/api/paas/v4"
            }
    
    async def call(
        self,
        provider: str,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict:
        """
        调用 LLM（非流式）
        
        Args:
            provider: Provider 名称
            messages: 消息列表
            tools: 工具列表
            stream: 是否流式
            **kwargs: 其他参数
        
        Returns:
            响应结果
        """
        if provider == "local":
            return await self._call_local(messages, tools, stream, **kwargs)
        else:
            return await self._call_api(provider, messages, tools, stream, **kwargs)
    
    async def stream(
        self,
        provider: str,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        流式调用 LLM
        
        Args:
            provider: Provider 名称
            messages: 消息列表
            tools: 工具列表
            **kwargs: 其他参数
        
        Yields:
            流式响应块
        """
        if provider == "local":
            async for chunk in self._stream_local(messages, tools, **kwargs):
                yield chunk
        else:
            async for chunk in self._stream_api(provider, messages, tools, **kwargs):
                yield chunk
    
    async def _call_local(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict:
        """调用本地模型"""
        url = f"{settings.local_llm_base_url}/v1/chat/completions"
        
        payload = {
            "model": settings.local_llm_model,
            "messages": messages,
            "stream": stream,
            **kwargs
        }
        
        if tools:
            payload["tools"] = tools
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    
    async def _stream_local(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式调用本地模型"""
        url = f"{settings.local_llm_base_url}/v1/chat/completions"
        
        payload = {
            "model": settings.local_llm_model,
            "messages": messages,
            "stream": True,
            **kwargs
        }
        
        if tools:
            payload["tools"] = tools
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        yield line
    
    async def _call_api(
        self,
        provider: str,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict:
        """调用云端 API"""
        if provider not in self.providers:
            raise ValueError(f"Provider {provider} not configured")
        
        config = self.providers[provider]
        url = f"{config['base_url']}/chat/completions"
        
        payload = {
            "model": kwargs.get("model", self._get_default_model(provider)),
            "messages": messages,
            "stream": stream,
            **kwargs
        }
        
        if tools:
            payload["tools"] = tools
        
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def _stream_api(
        self,
        provider: str,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式调用云端 API"""
        if provider not in self.providers:
            raise ValueError(f"Provider {provider} not configured")
        
        config = self.providers[provider]
        url = f"{config['base_url']}/chat/completions"
        
        payload = {
            "model": kwargs.get("model", self._get_default_model(provider)),
            "messages": messages,
            "stream": True,
            **kwargs
        }
        
        if tools:
            payload["tools"] = tools
        
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        yield line
    
    def _get_default_model(self, provider: str) -> str:
        """获取 Provider 的默认模型"""
        defaults = {
            "openai": "gpt-4o-mini",
            "deepseek": "deepseek-chat",
            "moonshot": "moonshot-v1-8k",
            "zhipu": "glm-4-flash"
        }
        return defaults.get(provider, "gpt-4o-mini")
    
    def get_available_providers(self) -> List[str]:
        """获取可用的 Provider 列表"""
        return list(self.providers.keys())
