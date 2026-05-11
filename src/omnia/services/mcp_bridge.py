"""
mcp_bridge.py — MCP 桥接

负责：
1. 连接 MCP 服务
2. 注册 MCP 工具到工具注册表
3. 通过 MCP 协议执行工具
"""

import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.omnia.services.tool_registry import tool_registry


class MCPBridge:
    """MCP 桥接 — 连接外部 MCP 服务"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.connected = False
        self.tools_count = 0
        self.error = None

    async def initialize(self):
        """
        初始化 MCP 桥接
        尝试从环境变量或配置文件读取 MCP 服务地址并连接
        """
        # 检查 MCP 配置
        mcp_url = os.environ.get("OMNIA_MCP_URL")
        if not mcp_url:
            # 检查配置文件
            config_file = Path(__file__).parent.parent.parent.parent / "config" / "mcp.json"
            if config_file.exists():
                try:
                    config = json.loads(config_file.read_text())
                    mcp_url = config.get("url")
                except (json.JSONDecodeError, OSError):
                    pass
        
        if not mcp_url:
            self.connected = False
            self.tools_count = 0
            return
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{mcp_url}/tools")
                
                if response.status_code == 200:
                    tools = response.json()
                    tool_registry.register_mcp_tools(tools)
                    self.connected = True
                    self.tools_count = len(tools)
                else:
                    self.error = f"MCP 服务返回 {response.status_code}"
                    self.connected = False
        except ImportError:
            self.error = "缺少 httpx 库"
            self.connected = False
        except Exception as e:
            self.error = str(e)
            self.connected = False

    async def execute_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """通过 MCP 执行工具"""
        if not self.connected:
            return {"error": "MCP 未连接"}
        
        mcp_url = os.environ.get("OMNIA_MCP_URL")
        if not mcp_url:
            return {"error": "MCP URL 未配置"}
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{mcp_url}/execute",
                    json={"name": name, "args": args}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"MCP 执行失败: {response.status_code}"}
        except Exception as e:
            return {"error": f"MCP 执行异常: {str(e)}"}


# 全局单例
mcp_bridge = MCPBridge()
