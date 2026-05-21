"""
Tool Call Executor — 统一工具调用执行器

串联整个工具调用流程：
  模型响应 → 解析工具调用 → 安全检查 → 执行 → 格式化结果 → 返回给模型

支持：
- OpenAI / Anthropic / 文本格式的工具调用解析
- 原生工具 + MCP 工具的统一执行
- 安全门控（Safety Gate）
- 结果格式化（OpenAI / Anthropic）
"""

from __future__ import annotations

from core.logging_config import get_logger

logger = get_logger(__name__)

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .tool_call_protocol import (
    ToolCall,
    ToolCallFormat,
    ToolCallParser,
    ToolResult,
    ToolResultFormatter,
)
from .tool_registry import (
    check_tool_safety,
    dispatch_tool,
    get_all_tools_schema,
)


@dataclass
class ExecutionResult:
    """一次工具调用执行的结果"""
    tool_call: ToolCall
    tool_result: ToolResult
    safety_level: str = "low"
    blocked: bool = False
    block_reason: str = ""

    def to_openai_message(self) -> Dict[str, Any]:
        """转换为 OpenAI tool 消息"""
        return ToolResultFormatter.to_openai_tool_message(self.tool_result)

    def to_anthropic_message(self) -> Dict[str, Any]:
        """转换为 Anthropic tool_result 消息"""
        return ToolResultFormatter.to_anthropic_tool_result(self.tool_result)


@dataclass
class BatchExecutionResult:
    """批量工具调用执行的结果"""
    results: List[ExecutionResult] = field(default_factory=list)
    all_success: bool = True
    blocked_count: int = 0
    error_count: int = 0

    @property
    def has_results(self) -> bool:
        return len(self.results) > 0

    def to_openai_messages(self) -> List[Dict[str, Any]]:
        """转换为 OpenAI tool 消息列表"""
        return [r.to_openai_message() for r in self.results]

    def to_anthropic_messages(self) -> List[Dict[str, Any]]:
        """转换为 Anthropic tool_result 消息列表"""
        return [r.to_anthropic_message() for r in self.results]


class ToolCallExecutor:
    """
    统一工具调用执行器

    使用方式：
        executor = ToolCallExecutor()

        # 从模型响应中解析并执行工具调用
        result = await executor.execute_from_response(model_response)

        # 或者直接执行单个工具
        result = await executor.execute_single("read_file", {"path": "/tmp/test.txt"})

        # 获取所有工具定义（传给模型）
        tools_schema = executor.get_tools_schema()
    """

    def __init__(
        self,
        enable_safety_check: bool = True,
        max_content_length: int = 4000,
    ):
        self.enable_safety_check = enable_safety_check
        self.max_content_length = max_content_length

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """获取所有工具定义（OpenAI function-calling 格式）"""
        return get_all_tools_schema()

    async def execute_from_response(
        self,
        response: Dict[str, Any],
        target_format: str = "openai",
    ) -> BatchExecutionResult:
        """
        从模型响应中解析并执行所有工具调用

        Args:
            response: 模型原始响应
            target_format: 目标格式 ("openai" | "anthropic")

        Returns:
            BatchExecutionResult
        """
        batch = BatchExecutionResult()

        # 1. 解析工具调用
        tool_calls = ToolCallParser.parse(response)

        if not tool_calls:
            logger.debug("[ToolExecutor] No tool calls found in response")
            return batch

        logger.info(f"[ToolExecutor] Found {len(tool_calls)} tool calls")

        # 2. 逐个执行
        for tc in tool_calls:
            result = await self.execute_single(tc.name, tc.arguments, tool_call=tc)
            batch.results.append(result)

            if result.blocked:
                batch.blocked_count += 1
                batch.all_success = False
            elif not result.tool_result.success:
                batch.error_count += 1
                batch.all_success = False

        logger.info(
            f"[ToolExecutor] Batch complete: {len(batch.results)} total, "
            f"{batch.blocked_count} blocked, {batch.error_count} errors"
        )

        return batch

    async def execute_single(
        self,
        name: str,
        arguments: Dict[str, Any],
        tool_call: Optional[ToolCall] = None,
    ) -> ExecutionResult:
        """
        执行单个工具调用

        Args:
            name: 工具名称
            arguments: 工具参数
            tool_call: 原始 ToolCall（可选，用于关联 ID）

        Returns:
            ExecutionResult
        """
        if tool_call is None:
            tool_call = ToolCall(
                id=f"exec_{name}",
                name=name,
                arguments=arguments,
                format=ToolCallFormat.OPENAI_TOOL_CALLS,
            )

        # 1. 安全检查
        if self.enable_safety_check:
            safety = check_tool_safety(name, arguments)
            if not safety.allowed:
                logger.warning(f"[ToolExecutor] BLOCKED: {name} - {safety.reason}")
                return ExecutionResult(
                    tool_call=tool_call,
                    tool_result=ToolResult(
                        tool_call_id=tool_call.id,
                        name=name,
                        content=f"[BLOCKED] {safety.reason}",
                        success=False,
                    ),
                    safety_level=safety.level,
                    blocked=True,
                    block_reason=safety.reason,
                )
            safety_level = safety.level
        else:
            safety_level = "unchecked"

        # 2. 执行工具
        try:
            raw_result = await dispatch_tool(name, arguments)
            success = "error" not in raw_result

            # 3. 格式化结果
            content = ToolResultFormatter.format_result_content(
                raw_result, max_len=self.max_content_length
            )

            tool_result = ToolResult(
                tool_call_id=tool_call.id,
                name=name,
                content=content,
                success=success,
                raw_result=raw_result if isinstance(raw_result, dict) else {"raw": str(raw_result)},
            )

            if not success:
                logger.warning(f"[ToolExecutor] Tool error: {name} -> {content[:200]}")

            return ExecutionResult(
                tool_call=tool_call,
                tool_result=tool_result,
                safety_level=safety_level,
            )

        except Exception as e:
            logger.error(f"[ToolExecutor] Exception executing {name}: {e}")
            return ExecutionResult(
                tool_call=tool_call,
                tool_result=ToolResult(
                    tool_call_id=tool_call.id,
                    name=name,
                    content=f"[ERROR] {str(e)}",
                    success=False,
                ),
                safety_level=safety_level,
            )

    def format_for_model(
        self,
        batch_result: BatchExecutionResult,
        target_format: str = "openai",
    ) -> List[Dict[str, Any]]:
        """
        将执行结果格式化为可传回模型的消息

        Args:
            batch_result: 批量执行结果
            target_format: 目标格式 ("openai" | "anthropic")

        Returns:
            消息列表
        """
        if target_format == "anthropic":
            return batch_result.to_anthropic_messages()
        return batch_result.to_openai_messages()


# ─────────────────────────────────────────────
# 全局单例
# ─────────────────────────────────────────────

_executor: Optional[ToolCallExecutor] = None


def get_tool_executor() -> ToolCallExecutor:
    """获取全局工具执行器"""
    global _executor
    if _executor is None:
        _executor = ToolCallExecutor()
    return _executor


def reset_tool_executor():
    """重置全局工具执行器（用于测试）"""
    global _executor
    _executor = None
