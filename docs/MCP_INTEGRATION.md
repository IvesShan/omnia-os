# MCP Integration for Omnia OS

Omnia now supports the **Model Context Protocol (MCP)**, allowing her to:
1. **Call external MCP servers** (filesystem, git, browser, etc.)
2. **Expose her own capabilities** as an MCP server (coming soon)

## Quick Start

### 1. Install MCP SDK

```bash
pip install mcp
```

### 2. Configure MCP Servers

Edit `config/mcp_servers.json`:

```json
[
  {
    "name": "filesystem",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/shan/omnia-os"],
    "enabled": true
  },
  {
    "name": "git",
    "command": "uvx",
    "args": ["mcp-server-git"],
    "enabled": true
  }
]
```

### 3. Initialize in Code

```python
from src.core.actuator.tool_registry import init_mcp_tools, get_all_tools_schema, dispatch_tool

# Start MCP connections
init_mcp_tools()

# Get all tools (native + MCP)
tools = get_all_tools_schema()
print(f"Total tools available: {len(tools)}")

# Call a tool (works for both native and MCP)
result = dispatch_tool("filesystem_read_file", {"path": "README.md"})
```

### 4. Shutdown

```python
from src.core.actuator.tool_registry import shutdown_mcp

# Cleanup connections
shutdown_mcp()
```

## Available MCP Servers

| Server | Description | Install |
|--------|-------------|---------|
| `filesystem` | File read/write/traverse | `npx @modelcontextprotocol/server-filesystem` |
| `git` | Git operations | `uvx mcp-server-git` |
| `fetch` | HTTP requests | `uvx mcp-server-fetch` |
| `playwright` | Browser automation | `npx @executeautomation/playwright-mcp-server` |
| `sqlite` | Database queries | `uvx mcp-server-sqlite` |

## Tool Naming

MCP tools are prefixed with server name to avoid collisions:

- `filesystem_read_file` — Read file via MCP filesystem server
- `git_status` — Check git status via MCP git server
- `read_file` — Omnia's native file reader

## Architecture

```
┌─────────────────────────────────────────┐
│           Omnia Agent OS                │
│  ┌─────────────────────────────────┐    │
│  │   Tool Registry                 │    │
│  │   ├─ Native Tools (5)           │    │
│  │   └─ MCP Tools (dynamic)        │    │
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │   MCP Client Manager            │    │
│  │   ├─ Connect to MCP servers     │    │
│  │   ├─ Aggregate tool schemas     │    │
│  │   └─ Route tool calls           │    │
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │   MCP Servers (external)        │    │
│  │   ├─ filesystem                 │    │
│  │   ├─ git                        │    │
│  │   └─ ...                        │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

## Benefits

1. **Instant capability expansion** — Add 20+ tools without writing code
2. **Community ecosystem** — Use official MCP servers from Anthropic
3. **Isolation** — MCP servers run in separate processes
4. **Standardization** — Same protocol as Claude Desktop, Cursor, etc.

## Roadmap

- [x] MCP Client (call external servers)
- [ ] MCP Server (expose Omnia to other AI)
- [ ] Auto-discovery of MCP servers
- [ ] MCP tool safety classification

---

Built for 原点 by Infinite. ♾️
