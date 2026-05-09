"""
LLM 客户端 - 异步版本
支持：多 Provider、流式输出、工具调用
"""
import os
import json
import httpx
from typing import AsyncGenerator, Optional, List
from pathlib import Path

from src.omnia.config import settings


class LLMClient:
    """异步 LLM 客户端"""
    
    # Provider 配置
    PROVIDER_URLS = {
        "deepseek": "https://api.deepseek.com/v1/chat/completions",
        "kimi": "https://api.moonshot.cn/v1/chat/completions",
        "xiaomi": "https://api.maimemo.com/v1/chat/completions",
        "openai": "https://api.openai.com/v1/chat/completions",
        "qianfan": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions",
    }
    
    PROVIDER_MODELS = {
        "deepseek": "deepseek-v4-flash",
        "kimi": "K2.6-code-preview",
        "xiaomi": "mimo-v2.5-pro",
        "openai": "gpt-4o",
        "qianfan": "baiduqianfancodingplan/qianfan-code-latest",
    }
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
    
    def _load_api_key(self, provider: str) -> str | None:
        """加载 API Key"""
        env_keys = {
            "deepseek": "DEEPSEEK_API_KEY",
            "kimi": "MOONSHOT_API_KEY",
            "xiaomi": "MIMO_API_KEY",
            "openai": "OPENAI_API_KEY",
            "qianfan": "QIANFAN_API_KEY",
        }
        
        env_key = env_keys.get(provider)
        if not env_key:
            return None
        
        # 优先从环境变量加载
        api_key = os.environ.get(env_key)
        if api_key:
            return api_key
        
        # 从 .env 文件加载
        env_file = settings.project_root / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith(f"{env_key}="):
                    return line.split("=", 1)[1].strip()
        
        return None
    
    def _build_headers(self, api_key: str, provider: str) -> dict:
        """构建请求头"""
        headers = {"Content-Type": "application/json"}
        
        if provider == "xiaomi":
            headers["api-key"] = api_key
        else:
            headers["Authorization"] = f"Bearer {api_key}"
        
        return headers
    
    def _get_model(self, provider: str) -> str:
        """获取模型名称"""
        # 优先从环境变量读取
        env_model = os.environ.get(f"{provider.upper()}_MODEL")
        if env_model:
            return env_model
        
        # 使用默认模型
        return self.PROVIDER_MODELS.get(provider, "unknown")
    
    async def chat(
        self,
        messages: List[dict],
        provider: str = "deepseek",
        tools: List[dict] = None,
        stream: bool = False
    ) -> dict:
        """
        非流式聊天
        
        Args:
            messages: 消息列表
            provider: Provider 名称
            tools: 工具列表
            stream: 是否流式（此方法固定为 False）
        
        Returns:
            {"content": str, "usage": dict}
        """
        # 加载 API Key
        api_key = self._load_api_key(provider)
        if not api_key:
            raise ValueError(f"No API key configured for provider: {provider}")
        
        # 构建请求
        url = self.PROVIDER_URLS.get(provider)
        if not url:
            raise ValueError(f"Unknown provider: {provider}")
        
        model = self._get_model(provider)
        headers = self._build_headers(api_key, provider)
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "stream": False,
        }
        
        # 添加工具
        if tools:
            payload["tools"] = tools
        
        # 发送请求
        response = await self.client.post(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            raise ValueError(f"API error {response.status_code}: {response.text[:500]}")
        
        data = response.json()
        
        # 解析响应
        content = ""
        usage = {}
        
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0].get("message", {}).get("content", "")
        
        if "usage" in data:
            usage = data["usage"]
        
        return {"content": content, "usage": usage}
    
    async def stream_chat(
        self,
        messages: List[dict],
        provider: str = "deepseek",
        tools: List[dict] = None
    ) -> AsyncGenerator[dict, None]:
        """
        流式聊天
        
        Yields:
            {"type": "token", "content": str}
            {"type": "tool_call", "name": str, "arguments": dict}
            {"type": "tool_result", "name": str, "content": str}
            {"type": "done", "full_content": str}
            {"type": "error", "message": str}
        """
        # 加载 API Key
        api_key = self._load_api_key(provider)
        if not api_key:
            yield {"type": "error", "message": f"No API key configured for provider: {provider}"}
            return
        
        # 构建请求
        url = self.PROVIDER_URLS.get(provider)
        if not url:
            yield {"type": "error", "message": f"Unknown provider: {provider}"}
            return
        
        model = self._get_model(provider)
        headers = self._build_headers(api_key, provider)
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "stream": True,
        }
        
        # 添加工具
        if tools:
            payload["tools"] = tools
        
        # 发送流式请求
        async with self.client.stream("POST", url, headers=headers, json=payload) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                yield {"type": "error", "message": f"API error {response.status_code}: {error_text[:500]}"}
                return
            
            # 解析流式响应
            full_content = ""
            
            async for line in response.aiter_lines():
                if not line:
                    continue
                
                if line.startswith("data: "):
                    data_str = line[6:]
                    
                    if data_str == "[DONE]":
                        break
                    
                    try:
                        data = json.loads(data_str)
                        
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            
                            # 文本内容
                            if "content" in delta and delta["content"]:
                                content = delta["content"]
                                full_content += content
                                yield {"type": "token", "content": content}
                            
                            # 思考内容（DeepSeek V4 / Gemma 3）
                            if "reasoning_content" in delta and delta["reasoning_content"]:
                                yield {"type": "thinking", "content": delta["reasoning_content"]}
                        
                    except json.JSONDecodeError:
                        continue
            
            # 发送完成事件
            yield {"type": "done", "full_content": full_content}


# 全局客户端实例
_client: Optional[LLMClient] = None


async def get_llm_client() -> LLMClient:
    """获取 LLM 客户端实例（依赖注入）"""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
