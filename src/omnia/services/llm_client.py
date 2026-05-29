"""
LLM 客户端 - 异步版本
支持：多 Provider、流式输出、工具调用
"""
import asyncio
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
        "kimi": "https://api.kimi.com/coding/v1/chat/completions",
        "xiaomi": "https://token-plan-cn.xiaomimimo.com/v1/chat/completions",
        "openai": "https://api.openai.com/v1/chat/completions",
        "qianfan": "https://qianfan.baidubce.com/v2/coding/chat/completions",
    }
    
    PROVIDER_MODELS = {
        "deepseek": "deepseek-v4-pro",
        "kimi": "kimi-for-coding",
        "xiaomi": "mimo-v2.5-pro",
        "openai": "gpt-4o",
        "qianfan": "qianfan-code-latest",
    }
    
    # 支持工具调用的 Provider
    API_TOOL_PROVIDERS = {"deepseek", "openai", "xiaomi", "qianfan", "kimi"}
    
    def __init__(self):
        timeout = httpx.Timeout(connect=5.0, read=180.0, write=10.0, pool=5.0)
        self.client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(
                max_connections=50,
                max_keepalive_connections=10,
                keepalive_expiry=30.0,  # 30秒后关闭空闲连接
            ),
        )
    
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
        
        api_key = os.environ.get(env_key)
        if api_key:
            return api_key
        
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
        elif provider == "kimi":
            headers["Authorization"] = f"Bearer {api_key}"
            headers["User-Agent"] = "claude-code/0.1.0"
        else:
            headers["Authorization"] = f"Bearer {api_key}"
        
        return headers
    
    def _get_model(self, provider: str) -> str:
        """获取模型名称"""
        env_model = os.environ.get(f"{provider.upper()}_MODEL")
        if env_model:
            return env_model
        return self.PROVIDER_MODELS.get(provider, "unknown")
    
    async def chat(self, messages: List[dict], provider: str = "deepseek", 
                   tools: List[dict] = None, stream: bool = False, 
                   max_retries: int = 2) -> dict:
        """非流式聊天（带重试）"""
        api_key = self._load_api_key(provider)
        if not api_key:
            return {"content": f"未配置 {provider} API Key", "error": "missing_api_key"}
        
        url = self.PROVIDER_URLS.get(provider)
        model = self._get_model(provider)
        
        if not url:
            return {"content": f"不支持的 Provider: {provider}", "error": "unsupported_provider"}
        
        body = {"model": model, "messages": messages, "stream": False}
        
        if tools and provider in self.API_TOOL_PROVIDERS:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        
        headers = self._build_headers(api_key, provider)
        
        # Retry loop
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = await self.client.post(url, json=body, headers=headers)
                response.raise_for_status()
                data = response.json()
                return self._parse_openai_response(data)
                
            except httpx.HTTPStatusError as e:
                # API returned error status (4xx, 5xx)
                status_code = e.response.status_code
                try:
                    err_body = await e.response.aread()
                    err_text = err_body.decode('utf-8', errors='replace')[:500]
                except:
                    err_text = ""
                
                last_error = f"API 错误 ({status_code}): {err_text}"
                
                # Don't retry on 4xx errors (client errors)
                if 400 <= status_code < 500:
                    break
                    
            except httpx.TimeoutException as e:
                last_error = f"请求超时: {str(e)}"
                # Timeout is retryable
                
            except httpx.ConnectError as e:
                last_error = f"连接失败: {str(e)}"
                # Connection error is retryable
                
            except Exception as e:
                last_error = f"请求异常: {str(e)}"
                # Unknown errors: retry once
                
            if attempt < max_retries:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s
                print(f"[LLMClient] Retry {attempt + 1}/{max_retries} after {wait_time}s: {last_error}")
                await asyncio.sleep(wait_time)
        
        # All retries exhausted
        return {"content": f"请求失败: {last_error}", "error": last_error}
    
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
        
        parsed_tool_calls = []
        for tc in tool_calls:
            function = tc.get("function", {})
            arguments = function.get("arguments", "{}")
            try:
                parsed_args = json.loads(arguments) if isinstance(arguments, str) else arguments
            except:
                parsed_args = {}
            
            parsed_tool_calls.append({
                "id": tc.get("id", ""),
                "name": function.get("name", ""),
                "arguments": parsed_args,
            })
        
        return {
            "content": content,
            "tool_calls": parsed_tool_calls,
            "reasoning_content": reasoning_content,
            "usage": data.get("usage", {}),
        }
    
    def _parse_kimi_response(self, data: dict) -> dict:
        """解析 Kimi 响应"""
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
                    "arguments": block.get("input", {}),
                })
        
        return {
            "content": "\n".join(text_parts),
            "tool_calls": tool_calls,
            "reasoning_content": "",
            "usage": data.get("usage", {}),
        }
    
    async def stream_chat(
        self,
        messages: List[dict],
        provider: str = "deepseek",
        tools: Optional[List[dict]] = None,
        max_retries: int = 1,
    ) -> AsyncGenerator[dict, None]:
        """
        流式聊天
        
        Yields:
            {"type": "token|thinking|tool_call_end|error|done", ...}
        """
        api_key = self._load_api_key(provider)
        if not api_key:
            yield {"type": "error", "message": f"未配置 {provider} API Key"}
            return
        
        url = self.PROVIDER_URLS.get(provider)
        model = self._get_model(provider)
        
        if not url:
            yield {"type": "error", "message": f"不支持的 Provider: {provider}"}
            return
        
        body = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        
        # Kimi 需要 max_tokens 参数
        if provider == "kimi":
            body["max_tokens"] = 32768
        
        # 添加工具（如果支持）
        if tools and provider in self.API_TOOL_PROVIDERS:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        
        headers = self._build_headers(api_key, provider)
        
        try:
            print(f"[LLMClient] Starting stream request to {provider}, timeout: {self.client.timeout}")
            async with self.client.stream("POST", url, json=body, headers=headers) as response:
                response.raise_for_status()
                
                # Kimi/Anthropic 格式 SSE vs OpenAI 格式 SSE
                if provider == "kimi":
                    async for event in self._stream_openai(response):
                        yield event
                else:
                    async for event in self._stream_openai(response):
                        yield event
                    
        except httpx.HTTPStatusError as e:
            error_msg = f"API 调用失败: {e.response.status_code}"
            try:
                err_body = await e.response.aread()
                error_msg += f" - {err_body.decode('utf-8', errors='replace')[:500]}"
            except:
                pass
            yield {"type": "error", "message": error_msg}
        except Exception as e:
            error_msg = f"请求异常: {str(e)}"
            yield {"type": "error", "message": error_msg}
    
    async def _stream_openai(self, response) -> AsyncGenerator[dict, None]:
        """解析 OpenAI 格式 SSE（DeepSeek/Xiaomi/QianFan/OpenAI）"""
        full_content = ""
        full_reasoning = ""
        tool_calls = {}
        
        buffer = ""
        async for chunk in response.aiter_text():
            buffer += chunk
            
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                
                if not line or line.startswith(":"):
                    continue
                
                if not line.startswith("data:"):
                    continue
                
                data_str = line[5:].strip()
                
                if data_str == "[DONE]":
                    yield self._yield_done(tool_calls, full_content, full_reasoning)
                    return
                
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                
                choices = data.get("choices", [])
                if not choices:
                    continue
                
                choice = choices[0]
                delta = choice.get("delta", {})
                finish_reason = choice.get("finish_reason")
                
                # 文本内容
                content = delta.get("content")
                if content:
                    full_content += content
                    yield {"type": "token", "content": content}
                
                # 推理内容 (Kimi/DeepSeek/Xiaomi thinking mode)
                reasoning = delta.get("reasoning_content")
                if reasoning:
                    full_reasoning += reasoning
                    # full_content += reasoning  # 修复：避免污染最终输出
                    # 只作为 thinking 发送，不作为 token（避免重复）
                    yield {"type": "thinking", "content": reasoning}
                
                # 工具调用（增量累积）
                tool_calls_delta = delta.get("tool_calls") or []
                for tc_delta in tool_calls_delta:
                    idx = tc_delta.get("index", 0)
                    if idx not in tool_calls:
                        tool_calls[idx] = {"id": "", "name": "", "arguments": ""}
                    
                    if tc_delta.get("id"):
                        tool_calls[idx]["id"] = tc_delta["id"]
                    
                    func = tc_delta.get("function", {})
                    if func.get("name"):
                        tool_calls[idx]["name"] += func["name"]
                    if func.get("arguments"):
                        tool_calls[idx]["arguments"] += func["arguments"]
                
                # 结束原因处理
                if finish_reason in ("stop", "tool_calls"):
                    yield self._yield_done(tool_calls, full_content, full_reasoning)
                    return
        
        # 流正常结束但没有 [DONE] 或 finish_reason
        yield self._yield_done(tool_calls, full_content, full_reasoning)
        print(f"[LLMClient] OpenAI stream completed normally")
    
    async def _stream_anthropic(self, response) -> AsyncGenerator[dict, None]:
        """解析 Anthropic 格式 SSE（Kimi）"""
        full_content = ""
        full_reasoning = ""
        tool_calls = {}
        current_tool_index = 0
        
        buffer = ""
        async for chunk in response.aiter_text():
            buffer += chunk
            
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                
                if not line or line.startswith(":"):
                    continue
                
                # Anthropic 格式 SSE 有 event:xxx 和 data:xxx 两行 (注意没有空格)
                if line.startswith("event:"):
                    event_type = line[5:].strip()
                    # 下一行应该是 data:...
                    if "\n" not in buffer:
                        # 数据还没来，把 event 放回 buffer
                        buffer = line + "\n" + buffer
                        break
                    data_line, buffer = buffer.split("\n", 1)
                    data_line = data_line.strip()
                    
                    if not data_line.startswith("data:"):
                        continue
                    
                    data_str = data_line[5:]
                    
                    try:
                        data = json.loads(data_str) if data_str else {}
                    except json.JSONDecodeError:
                        continue
                    
                    # 处理不同类型的 event
                    if event_type == "message_start":
                        pass  # 初始化消息
                    
                    elif event_type == "content_block_start":
                        block = data.get("content_block", {})
                        block_type = block.get("type", "")
                        
                        if block_type == "tool_use":
                            idx = current_tool_index
                            tool_calls[idx] = {
                                "id": block.get("id", ""),
                                "name": block.get("name", ""),
                                "arguments": "",
                            }
                    
                    elif event_type == "content_block_delta":
                        delta = data.get("delta", {})
                        delta_type = delta.get("type", "")
                        
                        if delta_type == "text_delta":
                            text = delta.get("text", "")
                            if text:
                                full_content += text
                                yield {"type": "token", "content": text}
                        
                        elif delta_type == "thinking_delta":
                            thinking = delta.get("thinking", "")
                            if thinking:
                                full_reasoning += thinking
                                # 兼容旧客户端
                                yield {"type": "token", "content": "[思考] " + thinking}
                                yield {"type": "thinking", "content": thinking}
                        
                        elif delta_type == "input_json_delta":
                            partial_json = delta.get("partial_json", "")
                            if partial_json:
                                # 找到当前正在构建的工具调用
                                idx = current_tool_index
                                if idx in tool_calls:
                                    tool_calls[idx]["arguments"] += partial_json
                    
                    elif event_type == "content_block_stop":
                        block = data.get("content_block", {})
                        if block and block.get("type") == "tool_use":
                            current_tool_index += 1
                    
                    elif event_type == "message_delta":
                        delta = data.get("delta", {})
                        stop_reason = delta.get("stop_reason", "")
                        
                        if stop_reason in ("end_turn", "tool_use"):
                            yield self._yield_done(tool_calls, full_content, full_reasoning)
                            return
                    
                    elif event_type == "message_stop":
                        yield self._yield_done(tool_calls, full_content, full_reasoning)
                        return
        
        # 流结束
        yield self._yield_done(tool_calls, full_content, full_reasoning)
        print(f"[LLMClient] Anthropic stream completed normally")
    
    def _yield_done(self, tool_calls, full_content, full_reasoning):
        """生成 done 事件，包含工具调用结果"""
        if tool_calls:
            parsed = []
            for idx in sorted(tool_calls.keys()):
                tc = tool_calls[idx]
                args_str = tc.get("arguments", "")
                try:
                    args = json.loads(args_str) if args_str else {}
                except:
                    args = {"raw": args_str}
                tc_id = tc.get("id", "")
                if not tc_id:
                    tc_id = f"call_{idx}"
                parsed.append({
                    "id": tc_id,
                    "name": tc.get("name", ""),
                    "arguments": args,
                })
            return {"type": "tool_call_end", "tool_calls": parsed, 
                    "full_content": full_content, "reasoning_content": full_reasoning}
        
        return {"type": "done", "full_content": full_content, "reasoning_content": full_reasoning}
