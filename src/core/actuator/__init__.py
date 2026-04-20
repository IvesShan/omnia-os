"""
Actuator — Omnia's hands and feet.

Tools for interacting with the world.
"""

from .tool_registry import (
    TOOLS_SCHEMA,
    TOOL_MAP,
    dispatch_tool,
    check_tool_safety,
)

# MCP integration (optional)
try:
    from .mcp_client import MCPToolRegistry, get_mcp_registry, MCP_SDK_AVAILABLE
    MCP_AVAILABLE = MCP_SDK_AVAILABLE
except ImportError as e:
    print(f"[MCP] Failed to import from mcp_client: {e}")
    MCP_AVAILABLE = False

__all__ = [
    "TOOLS_SCHEMA",
    "TOOL_MAP",
    "dispatch_tool",
    "check_tool_safety",
]

if MCP_AVAILABLE:
    __all__.extend(["MCPToolRegistry", "get_mcp_registry"])
