"""
MCP Client — Connect Omnia to the MCP ecosystem.

Omnia can now call external MCP servers (filesystem, git, playwright, etc.)
as if they were native tools.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

# MCP SDK
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import (
        CallToolResult,
        ListToolsResult,
        Tool as MCPTool,
        TextContent,
        ImageContent,
    )
    MCP_SDK_AVAILABLE = True
    MCP_AVAILABLE = True  # Alias for tool_registry.py
    print("[MCP] SDK imported successfully")
except ImportError as e:
    print(f"[MCP] SDK import failed: {e}")
    MCP_SDK_AVAILABLE = False
    MCP_AVAILABLE = False  # Alias for tool_registry.py
    # Define dummy classes for type hints
    class ClientSession:
        pass
    class StdioServerParameters:
        pass
    class MCPTool:
        pass
    class TextContent:
        pass
    class ImageContent:
        pass

_WORKSPACE = Path.home() / ".openclaw" / "workspace"
_MCP_CONFIG_PATH = _WORKSPACE / "omnia-os" / "config" / "mcp_servers.json"


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection."""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class ConnectedServer:
    """A connected MCP server with its session."""
    name: str
    session: ClientSession
    tools: List[MCPTool] = field(default_factory=list)
    _stdio_context: Any = None
    _write_stream: Any = None


class MCPClientManager:
    """
    Manages connections to multiple MCP servers.
    
    Usage:
        manager = MCPClientManager()
        await manager.connect_all()
        
        # All tools are now available
        tools = manager.get_all_tools_schema()
        
        # Call a tool
        result = await manager.call_tool("filesystem_read_file", {"path": "/tmp/test.txt"})
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or _MCP_CONFIG_PATH
        self.servers: Dict[str, ConnectedServer] = {}
        self._tool_to_server: Dict[str, str] = {}  # tool_name -> server_name
        self._exit_stack = AsyncExitStack()
        
    def _load_config(self) -> List[MCPServerConfig]:
        """Load MCP server configurations from JSON."""
        configs = []
        
        # Default config if file doesn't exist
        default_servers = [
            {
                "name": "filesystem",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", str(_WORKSPACE)],
                "enabled": True
            },
            {
                "name": "git",
                "command": "uvx",
                "args": ["mcp-server-git"],
                "enabled": True
            },
        ]
        
        if not self.config_path.exists():
            # Create default config
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(json.dumps(default_servers, indent=2))
            
        try:
            data = json.loads(self.config_path.read_text())
            for item in data:
                if item.get("enabled", True):
                    configs.append(MCPServerConfig(
                        name=item["name"],
                        command=item["command"],
                        args=item.get("args", []),
                        env=item.get("env", {}),
                        enabled=True
                    ))
        except Exception as e:
            print(f"[MCP] Warning: Failed to load config: {e}")
            
        return configs
    
    async def connect_server(self, config: MCPServerConfig) -> Optional[ConnectedServer]:
        """Connect to a single MCP server."""
        try:
            # Merge system env with config env (config env takes precedence)
            env = os.environ.copy()
            if config.env:
                env.update(config.env)
            
            server_params = StdioServerParameters(
                command=config.command,
                args=config.args,
                env=env
            )
            
            # Connect via stdio
            stdio_transport = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            stdio, write_stream = stdio_transport
            
            session = await self._exit_stack.enter_async_context(
                ClientSession(stdio, write_stream)
            )
            
            # Initialize
            await session.initialize()
            
            # List available tools
            tools_result = await session.list_tools()
            
            server = ConnectedServer(
                name=config.name,
                session=session,
                tools=tools_result.tools,
                _stdio_context=stdio,
                _write_stream=write_stream
            )
            
            # Register tool mappings
            for tool in tools_result.tools:
                full_name = f"{config.name}_{tool.name}"
                self._tool_to_server[full_name] = config.name
                self._tool_to_server[tool.name] = config.name  # Also register short name
            
            print(f"[MCP] ✓ Connected to '{config.name}' with {len(tools_result.tools)} tools")
            return server
            
        except Exception as e:
            print(f"[MCP] ✗ Failed to connect '{config.name}': {e}")
            return None
    
    async def connect_all(self) -> None:
        """Connect to all configured MCP servers."""
        configs = self._load_config()
        
        print(f"[MCP] Connecting to {len(configs)} servers...")
        
        for config in configs:
            server = await self.connect_server(config)
            if server:
                self.servers[config.name] = server
        
        total_tools = sum(len(s.tools) for s in self.servers.values())
        print(f"[MCP] Connected: {len(self.servers)}/{len(configs)} servers, {total_tools} tools available")
    
    def get_all_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Get all tools from all connected servers in OpenAI function format.
        This can be injected into the LLM's tools parameter.
        """
        schemas = []
        
        for server in self.servers.values():
            for tool in server.tools:
                # Use fully qualified name to avoid collisions
                full_name = f"{server.name}_{tool.name}"
                
                schema = {
                    "type": "function",
                    "function": {
                        "name": full_name,
                        "description": tool.description or f"Tool from {server.name}",
                        "parameters": tool.inputSchema or {"type": "object", "properties": {}}
                    }
                }
                schemas.append(schema)
        
        return schemas
    
    def get_tool_mapping(self) -> Dict[str, str]:
        """
        Get a mapping of tool names to server names.
        Useful for routing tool calls.
        """
        return self._tool_to_server.copy()
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool by name.
        
        Args:
            tool_name: The tool name (can be 'server_tool' or just 'tool')
            arguments: The tool arguments
            
        Returns:
            Dict with 'content', 'is_error', and 'tool_name'
        """
        # Find which server owns this tool
        server_name = self._tool_to_server.get(tool_name)
        
        if not server_name:
            return {
                "error": f"Unknown tool: {tool_name}",
                "is_error": True
            }
        
        server = self.servers.get(server_name)
        if not server:
            return {
                "error": f"Server '{server_name}' not connected",
                "is_error": True
            }
        
        # Strip server prefix if present
        actual_tool_name = tool_name
        if tool_name.startswith(f"{server_name}_"):
            actual_tool_name = tool_name[len(server_name) + 1:]
        
        try:
            result = await server.session.call_tool(actual_tool_name, arguments)
            
            # Convert MCP result to our format
            content = []
            for item in result.content:
                if isinstance(item, TextContent):
                    content.append({"type": "text", "text": item.text})
                elif isinstance(item, ImageContent):
                    content.append({
                        "type": "image",
                        "data": item.data,
                        "mime_type": item.mimeType
                    })
            
            return {
                "content": content,
                "is_error": result.isError if hasattr(result, 'isError') else False,
                "tool_name": tool_name
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "is_error": True,
                "tool_name": tool_name
            }
    
    async def close(self) -> None:
        """Close all MCP connections."""
        await self._exit_stack.aclose()
        self.servers.clear()
        self._tool_to_server.clear()


# Synchronous wrapper for easier integration with existing code
class MCPToolRegistry:
    """
    Synchronous wrapper for MCPClientManager.
    Drop-in replacement/extension for tool_registry.TOOL_MAP.
    """
    
    def __init__(self):
        self._manager: Optional[MCPClientManager] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
    def initialize(self) -> None:
        """Initialize MCP connections. Call this at startup."""
        self._manager = MCPClientManager()
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._manager.connect_all())
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get all MCP tools in OpenAI format."""
        if not self._manager:
            return []
        return self._manager.get_all_tools_schema()
    
    def call(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Call an MCP tool synchronously."""
        if not self._manager or not self._loop:
            return {"error": "MCP not initialized"}
        
        # Run async call in the event loop
        future = asyncio.run_coroutine_threadsafe(
            self._manager.call_tool(tool_name, kwargs),
            self._loop
        )
        return future.result(timeout=30)  # 30 second timeout
    
    def shutdown(self) -> None:
        """Cleanup MCP connections."""
        if self._manager and self._loop:
            self._loop.run_until_complete(self._manager.close())


# Global instance
_mcp_registry: Optional[MCPToolRegistry] = None


def get_mcp_registry() -> MCPToolRegistry:
    """Get the global MCP registry instance."""
    global _mcp_registry
    if _mcp_registry is None:
        _mcp_registry = MCPToolRegistry()
    return _mcp_registry


# For testing
if __name__ == "__main__":
    async def test():
        manager = MCPClientManager()
        await manager.connect_all()
        
        # Show available tools
        tools = manager.get_all_tools_schema()
        print(f"\n{'='*50}")
        print(f"Available MCP Tools: {len(tools)}")
        print(f"{'='*50}")
        for tool in tools[:10]:  # Show first 10
            name = tool["function"]["name"]
            desc = tool["function"]["description"][:60]
            print(f"  • {name}")
            print(f"    {desc}...")
        
        if len(tools) > 10:
            print(f"    ... and {len(tools) - 10} more")
        
        await manager.close()
    
    asyncio.run(test())
