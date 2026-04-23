"""
Qianfan LLM Client - 百度千帆 API 客户端

支持千帆 Coding Plan API
"""

import os
import requests
from typing import Dict, List, Optional, Any
from pathlib import Path


class QianfanClient:
    """千帆 API 客户端"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "qianfan-code-latest"):
        """
        初始化千帆客户端
        
        Args:
            api_key: API key，如果不提供则从环境变量或 .env 文件读取
            model: 模型名称
        """
        self.api_key = api_key or self._load_api_key()
        self.model = model
        self.base_url = "https://qianfan.baidubce.com/v2/coding"
        
        if not self.api_key:
            raise ValueError("Qianfan API key not found. Set QIANFAN_API_KEY in .env or environment.")
    
    def _load_api_key(self) -> Optional[str]:
        """加载 API key，优先从 .env 文件读取"""
        # 优先级 1: 环境变量
        api_key = os.environ.get("QIANFAN_API_KEY")
        if api_key:
            return api_key
        
        # 优先级 2: .env 文件
        env_file = Path(__file__).parent.parent.parent.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    if key == "QIANFAN_API_KEY":
                        return val.strip().strip('"').strip("'")
        
        return None
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表
            tools: 工具列表（可选）
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            API 响应
        """
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        if tools:
            payload["tools"] = tools
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=300)
            
            if response.status_code != 200:
                error_text = response.text
                raise RuntimeError(f"Qianfan API error {response.status_code}: {error_text}")
            
            data = response.json()
            
            # 提取内容
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            
            # 如果 content 为空但有 reasoning_content，使用它
            if not content and "reasoning_content" in message:
                content = message["reasoning_content"]
            
            return {
                "content": content,
                "tool_calls": message.get("tool_calls"),
                "usage": {
                    "input": data.get("usage", {}).get("prompt_tokens", 0),
                    "output": data.get("usage", {}).get("completion_tokens", 0),
                },
                "model": data.get("model", self.model),
                "raw_response": data,
            }
            
        except requests.exceptions.Timeout:
            raise RuntimeError("Qianfan API timeout")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Qianfan API request error: {e}")
    
    def simple_call(self, prompt: str, context: Optional[Dict] = None) -> str:
        """
        简单调用接口（用于循环推理引擎）
        
        Args:
            prompt: 提示文本
            context: 上下文（可选）
            
        Returns:
            模型响应文本
        """
        messages = [{"role": "user", "content": prompt}]
        
        result = self.chat(messages)
        
        return result["content"]


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("Qianfan Client Test")
    print("=" * 60)
    
    try:
        client = QianfanClient()
        print(f"✅ Client initialized")
        print(f"   Model: {client.model}")
        print(f"   API Key: {client.api_key[:20]}...")
        
        # 测试简单调用
        print("\n📝 Testing simple call...")
        response = client.simple_call("你好，请简单介绍一下你自己。")
        print(f"✅ Response: {response[:200]}...")
        
        # 测试聊天接口
        print("\n📝 Testing chat interface...")
        messages = [
            {"role": "system", "content": "你是一个友好的助手。"},
            {"role": "user", "content": "今天天气怎么样？"}
        ]
        result = client.chat(messages)
        print(f"✅ Content: {result['content'][:200]}...")
        print(f"   Usage: {result['usage']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
