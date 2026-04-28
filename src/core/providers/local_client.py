"""
from core.logging_config import get_logger

logger = get_logger(__name__)

Local LLM Client - llama.cpp server 客户端

支持 llama.cpp 的 HTTP API，兼容 OpenAI 格式
"""

import aiohttp
import asyncio
from typing import AsyncGenerator
from dataclasses import dataclass


@dataclass
class LocalModelConfig:
    """本地模型配置"""
    base_url: str = "http://localhost:8080"
    model_id: str = "gemma-4-E4B-it-OBLITERATED-Q8_0.gguf"
    context_window: int = 32768
    max_output: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    timeout: int = 300


class LocalLLMClient:
    """本地模型客户端 - 连接 llama.cpp server"""
    
    def __init__(self, config: LocalModelConfig | None = None):
        self.config = config or LocalModelConfig()
        self.base_url = self.config.base_url.rstrip('/')
        
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs
    ) -> dict:
        """
        发送聊天请求
        
        llama.cpp server 使用 OpenAI 兼容格式
        """
        url = f"{self.base_url}/v1/chat/completions"
        
        payload = {
            "model": self.config.model_id,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_output),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "stream": False,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise Exception(f"Local LLM error: {resp.status} - {error_text}")
                    
                    data = await resp.json()
                    
            # 解析 OpenAI 格式响应
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            
            return {
                "content": message.get("content", ""),
                "tool_calls": None,  # 本地模型暂不支持工具调用
                "usage": {
                    "input": data.get("usage", {}).get("prompt_tokens", 0),
                    "output": data.get("usage", {}).get("completion_tokens", 0),
                },
                "model": data.get("model", self.config.model_id),
            }
            
        except asyncio.TimeoutError:
            raise Exception("Local LLM timeout - model may be loading or GPU memory exhausted")
        except aiohttp.ClientError as e:
            raise Exception(f"Local LLM connection error: {e}")
    
    async def stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式聊天"""
        url = f"{self.base_url}/v1/chat/completions"
        
        payload = {
            "model": self.config.model_id,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_output),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "stream": True,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise Exception(f"Local LLM error: {resp.status} - {error_text}")
                    
                    async for line in resp.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data_str = line[6:]
                            if data_str == '[DONE]':
                                break
                            try:
                                import json
                                data = json.loads(data_str)
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
                                
        except aiohttp.ClientError as e:
            raise Exception(f"Local LLM connection error: {e}")
    
    async def health_check(self) -> bool:
        """检查服务是否可用"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False
    
    async def get_model_info(self) -> dict:
        """获取模型信息"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/props",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception:
            pass
        return {}


# 便捷函数
async def test_local_llm():
    """测试本地模型"""
    client = LocalLLMClient()
    
    # 健康检查
    if not await client.health_check():
        logger.info("❌ Local LLM 服务不可用")
        return False
    
    logger.info("✅ Local LLM 服务正常")
    
    # 测试聊天
    response = await client.chat([
        {"role": "user", "content": "你好，请用一句话介绍自己"}
    ])
    
    print(f"📝 响应: {response['content'][:100]}...")
    print(f"📊 Token: {response['usage']}")
    
    return True


if __name__ == "__main__":
    asyncio.run(test_local_llm())
