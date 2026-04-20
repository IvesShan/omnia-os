#!/usr/bin/env python3
"""
Test MCP integration for Omnia.

This script tests if MCP servers can be connected and tools are available.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Test MCP SDK first
print("Checking MCP SDK...")
try:
    import mcp
    print(f"  ✓ MCP SDK imported")
except Exception as e:
    print(f"  ✗ MCP import failed: {e}")
    sys.exit(1)

from core.actuator.tool_registry import init_mcp_tools, get_all_tools_schema, shutdown_mcp

def test_mcp():
    print("=" * 50)
    print("MCP Integration Test")
    print("=" * 50)
    
    # Initialize MCP
    print("\n1. Initializing MCP...")
    initialized = init_mcp_tools()
    
    if not initialized:
        print("   ⚠ MCP not available (SDK not installed)")
        print("   Install with: pip install mcp")
        return False
    
    print("   ✓ MCP initialized")
    
    # Get all tools
    print("\n2. Getting tool schemas...")
    tools = get_all_tools_schema()
    
    native_tools = [t for t in tools if not t["function"]["name"].startswith(("filesystem_", "git_", "fetch_"))]
    mcp_tools = [t for t in tools if t["function"]["name"].startswith(("filesystem_", "git_", "fetch_"))]
    
    print(f"   Native tools: {len(native_tools)}")
    print(f"   MCP tools: {len(mcp_tools)}")
    print(f"   Total: {len(tools)}")
    
    # Show some MCP tools
    if mcp_tools:
        print("\n3. Sample MCP tools:")
        for tool in mcp_tools[:5]:
            name = tool["function"]["name"]
            desc = tool["function"]["description"][:60]
            print(f"   • {name}")
            print(f"     {desc}...")
    
    # Test a tool call (if available)
    print("\n4. Testing tool call...")
    from core.actuator.tool_registry import dispatch_tool
    
    # Try to read this file
    result = dispatch_tool("read_file", {"path": "README.md"})
    if "error" not in result:
        print("   ✓ Native tool works")
    else:
        print(f"   ⚠ Native tool error: {result['error']}")
    
    # Cleanup
    print("\n5. Cleaning up...")
    shutdown_mcp()
    print("   ✓ MCP shut down")
    
    print("\n" + "=" * 50)
    print("Test completed successfully!")
    print("=" * 50)
    return True

if __name__ == "__main__":
    success = test_mcp()
    sys.exit(0 if success else 1)
