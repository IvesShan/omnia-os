"""
Actuator — Omnia's hands and feet.

Tools for interacting with the world.

Architecture:
- tool_registry.py: 原生工具定义、安全检查、dispatch
- tool_call_protocol.py: 统一工具调用协议（ToolCall/ToolResult/Parser/Formatter）
- mcp_client.py: MCP 协议集成（可选）
- plan_executor.py: 多步骤任务编排
- agent_swarm.py: 并行子代理编排
"""

from .tool_registry import (
    TOOLS_SCHEMA,
    TOOL_MAP,
    dispatch_tool,
    check_tool_safety,
)

from .tool_call_protocol import (
    ToolCall,
    ToolCallFormat,
    ToolCallParser,
    ToolResult,
    ToolResultFormatter,
    SupportsToolCalling,
    parse_tool_calls,
    make_tool_result,
)

# MCP integration (optional)
try:
    from .mcp_client import MCPToolRegistry, get_mcp_registry, MCP_SDK_AVAILABLE
    MCP_AVAILABLE = MCP_SDK_AVAILABLE
except ImportError:
    MCP_AVAILABLE = False

__all__ = [
    # Tool Registry
    "TOOLS_SCHEMA",
    "TOOL_MAP",
    "dispatch_tool",
    "check_tool_safety",
    # Tool Call Protocol
    "ToolCall",
    "ToolCallFormat",
    "ToolCallParser",
    "ToolResult",
    "ToolResultFormatter",
    "SupportsToolCalling",
    "parse_tool_calls",
    "make_tool_result",
]

if MCP_AVAILABLE:
    __all__.extend(["MCPToolRegistry", "get_mcp_registry"])
