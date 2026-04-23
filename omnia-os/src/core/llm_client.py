"""
Omnia LLM Client - 统一的 LLM API 客户端

支持：
- 千帆 (Baidu Qianfan) - 默认
- Kimi (Moonshot)
- DeepSeek
- OpenAI 兼容 API
"""

import os
import json
import httpx
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = "qianfan"
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 2000


class LLMClient:
    """
    统一的 LLM 客户端
    
    使用方式：
    
    ```python
    client = LLMClient()
    response = await client.chat(
        messages=[{"role": "user", "content": "你好"}]
    )
    ```
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or self._load_config()
        self.client = httpx.AsyncClient(timeout=60.0)
    
    def _load_config(self) -> LLMConfig:
        """从环境变量加载配置"""
        
        # 1. 尝试从 .env 文件加载（Omnia 根目录）
        env_path = "/home/shan/omnia-os/omnia-os/.env"
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('QIANFAN_API_KEY='):
                        os.environ['QIANFAN_API_KEY'] = line.split('=', 1)[1]
                    elif line.startswith('KIMI_API_KEY='):
                        os.environ['KIMI_API_KEY'] = line.split('=', 1)[1]
                    elif line.startswith('DEEPSEEK_API_KEY='):
                        os.environ['DEEPSEEK_API_KEY'] = line.split('=', 1)[1]
        
        # 2. 优先使用千帆
        qianfan_key = os.getenv("QIANFAN_API_KEY", "")
        if qianfan_key:
            return LLMConfig(
                provider="qianfan",
                api_key=qianfan_key,
                base_url="https://qianfan.baidubce.com/v2/coding",
                model="qianfan-code-latest"
            )
        
        # 3. 其次使用 Kimi
        kimi_key = os.getenv("KIMI_API_KEY", "")
        if kimi_key:
            return LLMConfig(
                provider="kimi",
                api_key=kimi_key,
                base_url="https://api.moonshot.cn/v1",
                model="moonshot-v1-8k"
            )
        
        # 4. 最后使用 DeepSeek
        deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        if deepseek_key:
            return LLMConfig(
                provider="deepseek",
                api_key=deepseek_key,
                base_url="https://api.deepseek.com/v1",
                model="deepseek-chat"
            )
        
        # 5. 默认配置（无 API key）
        return LLMConfig(
            provider="qianfan",
            api_key="",
            base_url="https://qianfan.baidubce.com/v2/coding",
            model="qianfan-code-latest"
        )
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
        
        Returns:
            API 响应
        """
        
        # 根据提供商选择不同的调用方式
        if self.config.provider == "qianfan":
            return await self._chat_qianfan(messages, temperature, max_tokens)
        elif self.config.provider == "kimi":
            return await self._chat_openai_compatible(messages, temperature, max_tokens)
        elif self.config.provider == "deepseek":
            return await self._chat_openai_compatible(messages, temperature, max_tokens)
        else:
            return await self._chat_openai_compatible(messages, temperature, max_tokens)
    
    async def _chat_qianfan(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """千帆 API 调用"""
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens
        }
        
        try:
            response = await self.client.post(
                f"{self.config.base_url}/chat/completions",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            
            # 标准化响应格式
            return {
                "provider": "qianfan",
                "choices": result.get("choices", []),
                "usage": result.get("usage", {}),
                "model": result.get("model", self.config.model)
            }
        except Exception as e:
            return {
                "error": str(e),
                "provider": "qianfan",
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": f"千帆 API 调用失败: {e}"
                    }
                }]
            }
    
    async def _chat_openai_compatible(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """OpenAI 兼容 API 调用（Kimi、DeepSeek）"""
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens
        }
        
        try:
            response = await self.client.post(
                f"{self.config.base_url}/chat/completions",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            
            # 标准化响应格式
            return {
                "provider": self.config.provider,
                "choices": result.get("choices", []),
                "usage": result.get("usage", {}),
                "model": result.get("model", self.config.model)
            }
        except Exception as e:
            return {
                "error": str(e),
                "provider": self.config.provider,
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": f"{self.config.provider} API 调用失败: {e}"
                    }
                }]
            }
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# 便捷函数
def create_llm_client(config: Optional[LLMConfig] = None) -> LLMClient:
    """创建 LLM 客户端实例"""
    return LLMClient(config)
