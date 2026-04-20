#!/usr/bin/env python3
import sys
from pathlib import Path
import os

# Add uv to PATH
os.environ['PATH'] = os.path.expanduser('~/.local/bin') + ':' + os.environ.get('PATH', '')

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Direct test
print("Testing mcp_client directly...")
from core.actuator.mcp_client import MCP_SDK_AVAILABLE, MCPClientManager

print(f"MCP_SDK_AVAILABLE: {MCP_SDK_AVAILABLE}")

if MCP_SDK_AVAILABLE:
    print("\nTesting MCP connection...")
    import asyncio
    
    async def test():
        manager = MCPClientManager()
        await manager.connect_all()
        
        tools = manager.get_all_tools_schema()
        print(f"\nTotal tools: {len(tools)}")
        
        for tool in tools[:5]:
            name = tool["function"]["name"]
            print(f"  • {name}")
        
        await manager.close()
    
    asyncio.run(test())
else:
    print("MCP SDK not available")
