"""
Tool Call Protocol — 统一工具调用协议

本模块定义了 Omnia 的工具调用数据模型和解析器，用于：
- 统一不同 provider 的工具调用格式
- 从模型响应中提取工具调用意图
- 将工具结果格式化为可传回模型的消息
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from core.logging_config import get_logger

logger = get_logger(__name__)


# ════════════════════════════════════════════════════════════════
# 1. 统一数据模型
# ════════════════════════════════════════════════════════════════

class ToolCallFormat(Enum):
    """工具调用的来源格式"""
    OPENAI_TOOL_CALLS = "openai_tool_calls"    # OpenAI function-calling API
    ANTHROPIC_TOOL_USE = "anthropic_tool_use"  # Anthropic tool_use block
    TEXT_JSON_BLOCK = "text_json_block"         # 文本中的 ```json 代码块
    TEXT_FUNCTION_CALL = "text_function_call"  # 文本中的 read_file(...) 格式
    MCP_PROTOCOL = "mcp_protocol"             # MCP 协议返回


@dataclass
class ToolCall:
    """
    统一的工具调用表示

    与具体 provider/API 无关，所有 tool calling 都归一化为此结构。
    """
    id: str                          # 调用 ID（用于关联 tool_call_id）
    name: str                        # 工具名称 (e.g., "read_file")
    arguments: Dict[str, Any]        # 参数 (e.g., {"path": "/foo"})
    format: ToolCallFormat = ToolCallFormat.OPENAI_TOOL_CALLS
    raw_block: Any = None            # 原始数据块（调试用）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
            "format": self.format.value,
        }


@dataclass
class ToolResult:
    """
    工具执行结果

    与 ToolCall 对应，表示一次工具调用的结果。
    """
    tool_call_id: str                # 对应的 ToolCall.id
    name: str                        # 工具名称
    content: str                     # 结果文本（传回模型用）
    success: bool                    # 是否成功
    raw_result: Dict[str, Any] = field(default_factory=dict)  # 原始结果

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_call_id": self.tool_call_id,
            "name": self.name,
            "content": self.content,
            "success": self.success,
        }


# ════════════════════════════════════════════════════════════════
# 2. 工具调用解析器（从模型响应中提取 ToolCall）
# ════════════════════════════════════════════════════════════════

class ToolCallParser:
    """
    从模型响应中解析工具调用

    支持多种格式的自动识别：
    - OpenAI tool_calls 字段（GPT-4、Kimi、千帆等）
    - Anthropic tool_use content block
    - 文本中的 ```json 代码块
    - 文本中的 read_file("path") 格式
    """

    # 已知工具名称集合（用于文本解析时过滤）
    KNOWN_TOOLS = frozenset({
        "read_file", "write_file", "execute_shell",
        "list_directory", "web_search", "query_memory",
    })

    # 工具名称 → 单参数时的默认参数名
    _DEFAULT_ARG_NAME = {
        "read_file": "path",
        "list_directory": "path",
        "execute_shell": "command",
        "web_search": "query",
        "write_file": "path",   # write_file 需要两个参数，单参数时给 path
        "query_memory": "query",
    }

    # 文本函数调用正则：name("arg") 或 name({"key": "val"})
    _FUNC_CALL_RE = re.compile(
        r'(\w+)\(\s*(\{[^)]*\}|"[^"]*"|\'[^\']*\')\s*\)',
        re.DOTALL,
    )

    @classmethod
    def parse(cls, response: Dict[str, Any]) -> List[ToolCall]:
        """
        从模型响应中提取所有工具调用

        Args:
            response: 模型原始响应（包含 choices/message 或 content blocks）

        Returns:
            ToolCall 列表（可能为空）
        """
        calls: List[ToolCall] = []

        # ── 策略 1：OpenAI tool_calls 字段 ──
        message = cls._extract_message(response)
        if message:
            tool_calls_raw = message.get("tool_calls") or []
            for i, tc in enumerate(tool_calls_raw):
                fn = tc.get("function", {})
                name = fn.get("name", "")
                try:
                    args = json.loads(fn.get("arguments", "{}"))
                except (json.JSONDecodeError, TypeError):
                    args = {}
                if name:
                    calls.append(ToolCall(
                        id=tc.get("id", f"call_{i}"),
                        name=name,
                        arguments=args,
                        format=ToolCallFormat.OPENAI_TOOL_CALLS,
                        raw_block=tc,
                    ))

        if calls:
            return calls

        # ── 策略 2：Anthropic tool_use content blocks ──
        content = cls._extract_content(response)
        if isinstance(content, list):
            for i, block in enumerate(content):
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    calls.append(ToolCall(
                        id=block.get("id", f"tool_use_{i}"),
                        name=block.get("name", ""),
                        arguments=block.get("input", {}),
                        format=ToolCallFormat.ANTHROPIC_TOOL_USE,
                        raw_block=block,
                    ))

        if calls:
            return calls

        # ── 策略 3：文本解析（fallback） ──
        text = cls._extract_text(response)
        if text:
            calls = cls._parse_text(text)

        return calls

    @classmethod
    def _extract_message(cls, response: Dict[str, Any]) -> Optional[Dict]:
        """提取 OpenAI 格式的 message 对象"""
        choices = response.get("choices")
        if choices and isinstance(choices, list) and len(choices) > 0:
            return choices[0].get("message")
        return None

    @classmethod
    def _extract_content(cls, response: Dict[str, Any]) -> Any:
        """提取 Anthropic 格式的 content blocks"""
        content = response.get("content")
        if content:
            return content
        message = cls._extract_message(response)
        if message:
            return message.get("content")
        return None

    @classmethod
    def _extract_text(cls, response: Dict[str, Any]) -> Optional[str]:
        """提取纯文本内容"""
        message = cls._extract_message(response)
        if message:
            return message.get("content", "")
        content = cls._extract_content(response)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(block.get("text", ""))
            return "\n".join(texts) if texts else None
        return None

    @classmethod
    def _parse_text(cls, text: str) -> List[ToolCall]:
        """从文本中解析工具调用（fallback 策略）"""
        calls: List[ToolCall] = []

        # 策略 3a：JSON 代码块
        json_calls = cls._parse_json_blocks(text)
        if json_calls:
            return json_calls

        # 策略 3b：函数调用格式
        for match in cls._FUNC_CALL_RE.finditer(text):
            func_name = match.group(1)
            if func_name not in cls.KNOWN_TOOLS:
                continue

            args_str = match.group(2).strip()
            args = cls._parse_function_args(func_name, args_str)

            if args:
                calls.append(ToolCall(
                    id=f"text_{len(calls)}",
                    name=func_name,
                    arguments=args,
                    format=ToolCallFormat.TEXT_FUNCTION_CALL,
                    raw_block=match.group(0),
                ))

        return calls

    @classmethod
    def _parse_json_blocks(cls, text: str) -> List[ToolCall]:
        """从 JSON 代码块中解析工具调用"""
        calls: List[ToolCall] = []
        json_pattern = re.compile(r'```(?:json|tool_calls)?\s*([\s\S]*?)```', re.MULTILINE)

        for match in json_pattern.finditer(text):
            raw = match.group(1).strip()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if isinstance(data, list):
                for i, item in enumerate(data):
                    if not isinstance(item, dict):
                        continue
                    name = (
                        item.get("tool")
                        or item.get("action")
                        or item.get("name")
                        or item.get("function")
                        or ""
                    )
                    args = (
                        item.get("arguments")
                        or item.get("args")
                        or item.get("parameters")
                        or item.get("params")
                        or {}
                    )
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    if name:
                        calls.append(ToolCall(
                            id=f"json_{i}",
                            name=name,
                            arguments=args,
                            format=ToolCallFormat.TEXT_JSON_BLOCK,
                            raw_block=item,
                        ))

        return calls

    @classmethod
    def _parse_function_args(cls, func_name: str, args_str: str) -> Dict[str, Any]:
        """
        解析函数调用参数

        Args:
            func_name: 工具名称（用于推断单参数的参数名）
            args_str: 参数字符串
        """
        if not args_str:
            return {}

        # JSON 对象格式
        if args_str.startswith("{"):
            try:
                return json.loads(args_str)
            except json.JSONDecodeError:
                pass

        # 单字符串参数
        if (args_str.startswith('"') and args_str.endswith('"')) or \
           (args_str.startswith("'") and args_str.endswith("'")):
            value = args_str[1:-1]
            arg_name = cls._DEFAULT_ARG_NAME.get(func_name, "path")
            return {arg_name: value}

        # key=value 格式
        if "=" in args_str:
            args = {}
            for part in args_str.split(","):
                if "=" in part:
                    k, v = part.split("=", 1)
                    args[k.strip()] = v.strip().strip("\"'")
            return args

        # 原始字符串，根据工具名称推断参数名
        value = args_str.strip("\"'")
        arg_name = cls._DEFAULT_ARG_NAME.get(func_name, "path")
        return {arg_name: value}


# ════════════════════════════════════════════════════════════════
# 3. 工具结果格式化器
# ════════════════════════════════════════════════════════════════

class ToolResultFormatter:
    """将 ToolResult 转换为各 provider 需要的消息格式"""

    @staticmethod
    def to_openai_tool_message(result: ToolResult) -> Dict[str, Any]:
        """转换为 OpenAI 的 tool 消息"""
        return {
            "role": "tool",
            "tool_call_id": result.tool_call_id,
            "content": result.content,
        }

    @staticmethod
    def to_anthropic_tool_result(result: ToolResult) -> Dict[str, Any]:
        """转换为 Anthropic 的 tool_result content block"""
        return {
            "type": "tool_result",
            "tool_use_id": result.tool_call_id,
            "content": result.content,
        }

    @staticmethod
    def format_result_content(raw: Any, max_len: int = 4000) -> str:
        """将原始工具结果格式化为文本"""
        if isinstance(raw, str):
            text = raw
        elif isinstance(raw, dict):
            # 优先提取有意义的字段
            if "content" in raw:
                text = str(raw["content"])
            elif "stdout" in raw:
                text = str(raw["stdout"])
            elif "results" in raw:
                text = json.dumps(raw["results"], ensure_ascii=False, indent=2)
            elif "result" in raw:
                text = str(raw["result"])
            else:
                text = json.dumps(raw, ensure_ascii=False, indent=2)
        else:
            text = str(raw)

        # 截断
        if len(text) > max_len:
            text = text[:max_len] + "\n[...truncated...]"
        return text


# ════════════════════════════════════════════════════════════════
# 4. Provider Tool Call 接口（抽象协议）
# ════════════════════════════════════════════════════════════════

@runtime_checkable
class SupportsToolCalling(Protocol):
    """
    支持工具调用的 Provider 协议

    任何实现了此协议的 provider 都可以参与统一的工具调用流程。
    """

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """返回该 provider 支持的工具定义（OpenAI function 格式）"""
        ...

    async def call_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        发送带工具定义的对话请求

        Returns:
            模型原始响应（包含 tool_calls 或纯文本）
        """
        ...


# ════════════════════════════════════════════════════════════════
# 5. 便捷函数
# ════════════════════════════════════════════════════════════════

def parse_tool_calls(response: Dict[str, Any]) -> List[ToolCall]:
    """从模型响应中解析工具调用（便捷函数）"""
    return ToolCallParser.parse(response)


def make_tool_result(
    tool_call: ToolCall,
    raw_result: Any,
    success: bool = True,
) -> ToolResult:
    """创建工具结果（便捷函数）"""
    content = ToolResultFormatter.format_result_content(raw_result)
    return ToolResult(
        tool_call_id=tool_call.id,
        name=tool_call.name,
        content=content,
        success=success,
        raw_result=raw_result if isinstance(raw_result, dict) else {"raw": str(raw_result)},
    )
