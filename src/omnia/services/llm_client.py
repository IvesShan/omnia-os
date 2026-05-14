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
    
    # Provider 配置（与 Flask 版本对齐）
    PROVIDER_URLS = {
        "deepseek": "https://api.deepseek.com/v1/chat/completions",
        "kimi": "https://api.kimi.com/coding/v1/messages",  # Anthropic 格式
        "xiaomi": "https://token-plan-cn.xiaomimimo.com/v1/chat/completions",
        "openai": "https://api.openai.com/v1/chat/completions",
        "qianfan": "https://qianfan.baidubce.com/v2/coding/chat/completions",  # 千帆 Coding Plan
    }
    
    PROVIDER_MODELS = {
        "deepseek": "deepseek-v4-pro",
        "kimi": "kimi-code",
        "xiaomi": "mimo-v2.5-pro",
        "openai": "gpt-4o",
        "qianfan": "qianfan-code-latest",  # 千帆 Coding Plan 模型名
    }
    
    # 支持 API 级工具调用的 Provider
    API_TOOL_PROVIDERS = {"deepseek", "openai", "xiaomi", "qianfan"}
    
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
            # Xiaomi MiMo Token Plan - 使用 api-key 头（非 Bearer）
            headers["api-key"] = api_key
        elif provider == "kimi":
            # Kimi Coding API - 使用 Bearer token
            headers["Authorization"] = f"Bearer {api_key}"
        else:
            # DeepSeek, OpenAI, Qianfan 等使用 Bearer token
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
            {"content": str, "usage": dict, "tool_calls": list, "reasoning_content": str}
        """
        # 加载 API Key
        api_key = self._load_api_key(provider)
        if not api_key:
            return {"content": f"❌ 未配置 {provider} API Key", "error": "missing_api_key"}
        
        # 获取 URL 和模型
        url = self.PROVIDER_URLS.get(provider)
        model = self._get_model(provider)
        
        if not url:
            return {"content": f"❌ 不支持的 Provider: {provider}", "error": "unsupported_provider"}
        
        # 构建请求体
        body = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        
        # 添加工具（如果支持）
        if tools and provider in self.API_TOOL_PROVIDERS:
            body["tools"] = tools
        
        # 构建请求头
        headers = self._build_headers(api_key, provider)
        
        try:
            print(f"[LLMClient] Calling {provider} API: model={model}, url={url}")
            response = await self.client.post(url, json=body, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            # 解析响应
            if provider == "kimi":
                # Kimi 使用 Anthropic 格式
                return self._parse_kimi_response(data)
            else:
                # OpenAI 格式（DeepSeek、OpenAI、Xiaomi、Qianfan）
                return self._parse_openai_response(data)
                
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.text
            except:
                error_detail = str(e)
            
            print(f"[LLMClient] HTTP Error: {e.response.status_code} - {error_detail}")
            return {
                "content": f"❌ API 调用失败: {e.response.status_code}",
                "error": error_detail,
                "status_code": e.response.status_code
            }
        except Exception as e:
            print(f"[LLMClient] Error: {e}")
            return {"content": f"❌ 请求异常: {str(e)}", "error": str(e)}
    
    def _parse_openai_response(self, data: dict) -> dict:
        """解析 OpenAI 格式响应"""
        choices = data.get("choices", [])
        if not choices:
            return {"content": "", "error": "empty_choices"}
        
        choice = choices[0]
        message = choice.get("message", {})
        
        content = message.get("content") or ""
        tool_calls = message.get("tool_calls") or []
        reasoning_content = message.get("reasoning_content") or ""
        
        # 解析工具调用
        parsed_tool_calls = []
        for tc in tool_calls:
            function = tc.get("function", {})
            arguments = function.get("arguments", "{}")
            
            # 解析参数
            try:
                if isinstance(arguments, str):
                    parsed_args = json.loads(arguments)
                else:
                    parsed_args = arguments
            except json.JSONDecodeError:
                parsed_args = {}
            
            parsed_tool_calls.append({
                "id": tc.get("id", ""),
                "name": function.get("name", ""),
                "arguments": parsed_args
            })
        
        return {
            "content": content,
            "tool_calls": parsed_tool_calls,
            "reasoning_content": reasoning_content,
            "usage": data.get("usage", {})
        }
    
    def _parse_kimi_response(self, data: dict) -> dict:
        """解析 Kimi (Anthropic 格式) 响应"""
        content_blocks = data.get("content", [])
        text_parts = []
        tool_calls = []
        
        for block in content_blocks:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append({
                    "id": block.get("id", ""),
                    "name": block.get("name", ""),
                    "arguments": block.get("input", {})
                })
        
        return {
            "content": "\n".join(text_parts),
            "tool_calls": tool_calls,
            "reasoning_content": "",
            "usage": data.get("usage", {})
        }
    
    async def stream_chat(
        self,
        messages: List[dict],
        provider: str = "deepseek",
        tools: List[dict] = None
    ) -> AsyncGenerator[dict, None]:
        """
        流式聊天
        
        Args:
            messages: 消息列表
            provider: Provider 名称
            tools: 工具列表
        
        Yields:
            {"type": "token|thinking|tool_call|tool_call_end|error|done", ...}
        """
        # 加载 API Key
        api_key = self._load_api_key(provider)
        if not api_key:
            yield {"type": "error", "data": f"未配置 {provider} API Key"}
            return
        
        # 获取 URL 和模型
        url = self.PROVIDER_URLS.get(provider)
        model = self._get_model(provider)
        
        if not url:
            yield {"type": "error", "data": f"不支持的 Provider: {provider}"}
            return
        
        # 构建请求体
        body = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        
        # 添加工具（如果支持）
        if tools and provider in self.API_TOOL_PROVIDERS:
            body["tools"] = tools
        
        # 构建请求头
        headers = self._build_headers(api_key, provider)
        
        # 工具调用累积器
        pending_tool_calls = {}
        full_content = ""
        full_reasoning = ""
        
        try:
            print(f"[LLMClient] Streaming {provider} API: model={model}, url={url}")
            
            async with self.client.stream("POST", url, json=body, headers=headers) as response:
                response.raise_for_status()
                
                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    
                    # 处理 SSE 数据
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        
                        if not line or line.startswith(":"):
                            continue
                        
                        if line.startswith("data: "):
                            data_str = line[6:]
                            
                            if data_str == "[DONE]":
                                # 发送累积的工具调用
                                if pending_tool_calls:
                                    parsed = []
                                    for idx in sorted(pending_tool_calls.keys()):
                                        tc = pending_tool_calls[idx]
                                        args_str = tc.get("arguments", "")
                                        try:
                                            args = json.loads(args_str) if args_str else {}
                                        except:
                                            args = {}
                                        parsed.append({
                                            "id": tc.get("id", ""),
                                            "name": tc.get("name", ""),
                                            "arguments": args,
                                        })
                                    yield {"type": "tool_call_end", "tool_calls": parsed}
                                
                                yield {"type": "done", "full_content": full_content, "reasoning_content": full_reasoning}
                                return
                            
                            try:
                                data = json.loads(data_str)
                                choices = data.get("choices", [])
                                if choices:
                                    choice = choices[0]
                                    delta = choice.get("delta", {})
                                    finish_reason = choice.get("finish_reason")
                                    
                                    # 内容
                                    content = delta.get("content")
                                    if content:
                                        full_content += content
                                        yield {"type": "token", "content": content}
                                    
                                    # 推理内容
                                    rc = delta.get("reasoning_content")
                                    if rc:
                                        full_reasoning += rc
                                        yield {"type": "thinking", "content": rc}
                                    
                                    # 工具调用（增量式，需要累积）
                                    tool_calls = delta.get("tool_calls")
                                    if tool_calls:
                                        for tc in tool_calls:
                                            idx = tc.get("index", 0)
                                            if idx not in pending_tool_calls:
                                                pending_tool_calls[idx] = {"id": "", "name": "", "arguments": ""}
                                            
                                            if tc.get("id"):
                                                pending_tool_calls[idx]["id"] = tc["id"]
                                            
                                            func = tc.get("function", {})
                                            if func.get("name"):
                                                pending_tool_calls[idx]["name"] = func["name"]
                                            if func.get("arguments"):
                                                pending_tool_calls[idx]["arguments"] += func["arguments"]
                                    
                                    # 工具调用完成
                                    if finish_reason == "tool_calls":
                                        if pending_tool_calls:
                                            parsed = []
                                            for idx in sorted(pending_tool_calls.keys()):
                                                tc = pending_tool_calls[idx]
                                                args_str = tc.get("arguments", "")
                                                try:
                                                    args = json.loads(args_str) if args_str else {}
                                                except:
                                                    args = {}
                                                parsed.append({
                                                    "id": tc.get("id", ""),
                                                    "name": tc.get("name", ""),
                                                    "arguments": args,
                                                })
                                            yield {"type": "tool_call_end", "tool_calls": parsed}
                                            pending_tool_calls = {}
                                    
                            except json.JSONDecodeError:
                                continue
                                
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.text
            except:
                error_detail = str(e)
            
            print(f"[LLMClient] Stream HTTP Error: {e.response.status_code} - {error_detail}")
            yield {"type": "error", "data": f"API 调用失败: {e.response.status_code}"}
        except Exception as e:
            print(f"[LLMClient] Stream Error: {e}")
            yield {"type": "error", "data": f"请求异常: {str(e)}"}
    
    def _process_stream_chunk(self, data: dict, provider: str):
        """已废弃：使用 stream_chat 内置处理"""
        return
# 全局单例
llm_client = LLMClient()
