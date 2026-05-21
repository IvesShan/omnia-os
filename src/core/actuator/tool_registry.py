"""Tool Registry — Define and dispatch Omnia's hands and feet.

All tools are JSON-schema compatible for OpenAI function-calling.
Supports both native tools and external MCP servers.
"""

from __future__ import annotations

from core.logging_config import get_logger

logger = get_logger(__name__)

from core.config import MEMORY_PALACE_DB
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .safety_gate import (
    SafetyResult,
    classify_file_read,
    classify_file_write,
    classify_shell_command,
)

# MCP integration (optional)
_mcp_registry = None
_mcp_available = False

try:
    from .mcp_client import get_mcp_registry, MCP_AVAILABLE as _MCP_AVAILABLE
    _mcp_available = _MCP_AVAILABLE
except ImportError:
    pass

ToolFunction = Callable[..., Dict[str, Any]]

_WORKSPACE = Path.home() / ".openclaw" / "workspace"

TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a text file. Returns the full text or an error message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative path to the file.",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Creates directories if needed. Use for creating or overwriting files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative path to the file.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full text content to write.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_shell",
            "description": "Execute a shell command in the workspace directory. Returns stdout/stderr/exit_code. Use for searches, git, builds, installations, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and directories inside a given path. Returns a markdown list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list.",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web using Kimi. Returns AI-synthesized answer with citations. Use for up-to-date facts, documentation, troubleshooting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_memory",
            "description": "Query Omnia's Memory Palace for stored facts, relations, habits, or timeline entries. Use to recall previous conversations, decisions, user preferences, or project history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant memories.",
                    },
                    "layer": {
                        "type": "string",
                        "description": "Memory layer to search: facts, relations, habits, timeline. Default: all layers.",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


def _resolve_path(path: str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = _WORKSPACE / p
    return p.resolve()


def tool_read_file(path: str) -> Dict[str, Any]:
    safety = classify_file_read(path)
    if not safety.allowed:
        return {"error": f"[BLOCKED] {safety.reason}"}

    try:
        p = _resolve_path(path)
        if not p.exists():
            return {"error": f"File not found: {p}"}
        text = p.read_text(encoding="utf-8", errors="replace")
        # Truncate very large files
        if len(text) > 50_000:
            text = text[:50_000] + "\n\n[...truncated at 50KB...]"
        return {"path": str(p), "content": text}
    except (FileNotFoundError, IOError, PermissionError) as e:
        return {"error": str(e)}


def tool_write_file(path: str, content: str) -> Dict[str, Any]:
    safety = classify_file_write(path, content)
    if not safety.allowed:
        return {"error": f"[BLOCKED] {safety.reason}"}

    try:
        p = _resolve_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        # Create backup if overwriting existing file > 0 bytes
        if p.exists() and p.stat().st_size > 0:
            backup = p.with_suffix(p.suffix + ".omnia.bak")
            backup.write_bytes(p.read_bytes())
        p.write_text(content, encoding="utf-8")
        return {"path": str(p), "bytes_written": len(content.encode("utf-8"))}
    except (FileNotFoundError, IOError, PermissionError) as e:
        return {"error": str(e)}


def tool_execute_shell(command: str) -> Dict[str, Any]:
    safety = classify_shell_command(command)
    if not safety.allowed:
        return {"error": f"[BLOCKED] {safety.reason}"}

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(_WORKSPACE),
            timeout=60,
        )
        stdout = result.stdout
        stderr = result.stderr
        # Truncate very large outputs
        if len(stdout) > 30_000:
            stdout = stdout[:30_000] + "\n\n[...truncated...]"
        if len(stderr) > 10_000:
            stderr = stderr[:10_000] + "\n\n[...truncated...]"
        return {
            "command": command,
            "exit_code": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out after 60 seconds"}
    except Exception as e:
        return {"error": str(e)}


def tool_list_directory(path: str) -> Dict[str, Any]:
    try:
        p = _resolve_path(path)
        if not p.exists():
            return {"error": f"Path not found: {p}"}
        if not p.is_dir():
            return {"error": f"Not a directory: {p}"}
        items = []
        for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            marker = "[D]" if child.is_dir() else "[F]"
            items.append(f"{marker} {child.name}")
        return {"path": str(p), "items": items}
    except (FileNotFoundError, IOError, PermissionError) as e:
        return {"error": str(e)}



def tool_web_search(query: str) -> Dict[str, Any]:
    """Search the web using Bing HTML scraping.
    
    NOTE: ddgs library causes DEADLOCK when called from ThreadPoolExecutor.
    We use direct HTTP requests to Bing instead.
    """
    import re
    import requests
    from urllib.parse import quote_plus
    
    try:
        url = "https://www.bing.com/search?q=" + quote_plus(query)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code != 200:
            return {"query": query, "error": f"Bing returned status {resp.status_code}"}
        
        html = resp.text
        
        # Extract search results
        all_links = re.findall(r'href="(https?://([^"]+))"[^>]*>([^<]+)</a>', html)
        seen_urls = set()
        results = []
        
        for full_url, domain, link_text in all_links:
            # Skip bing's own links and short links
            if 'bing.com' in domain or 'microsoft.com' in domain:
                continue
            if len(link_text.strip()) < 5:
                continue
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            
            title = re.sub(r'<[^>]+>', '', link_text).strip()
            if title and len(results) < 5:
                results.append({"title": title, "href": full_url})
        
        if results:
            lines = ["**" + r['title'] + "**\n<" + r['href'] + ">" for r in results]
            return {"query": query, "engine": "bing", "result": "\n\n".join(lines)}
        
        return {"query": query, "error": "No results found"}
        
    except requests.Timeout:
        return {"query": query, "error": "Search timeout after 10s"}
    except Exception as e:
        return {"query": query, "error": str(e)}



def tool_query_memory(query: str, layer: str = "all") -> Dict[str, Any]:
    """Query Omnia's Memory Palace for stored information."""
    try:
        import sqlite3
        
        db_path = MEMORY_PALACE_DB
        if not db_path.exists():
            return {"error": "Memory Palace database not found", "db_path": str(db_path)}
        
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
        
            results = []
            search_pattern = f"%{query}%"
        
        # Search in facts table
            if layer in ("all", "facts"):
                cursor.execute(
                    "SELECT id, category, key, value, created_at FROM facts WHERE (value LIKE ? OR key LIKE ?) AND status = 'active' ORDER BY id DESC LIMIT 10",
                    (search_pattern, search_pattern)
                )
                for row in cursor.fetchall():
                    results.append({
                        "layer": "facts",
                        "id": row["id"],
                        "category": row["category"],
                        "key": row["key"],
                        "value": row["value"][:500],
                        "created_at": row["created_at"]
                    })
        
        # Search in timeline table
            if layer in ("all", "timeline"):
                cursor.execute(
                    "SELECT id, event_date, event_type, title, description FROM timeline WHERE (title LIKE ? OR description LIKE ?) AND status = 'active' ORDER BY id DESC LIMIT 10",
                    (search_pattern, search_pattern)
                )
                for row in cursor.fetchall():
                    results.append({
                        "layer": "timeline",
                        "id": row["id"],
                        "event_date": row["event_date"],
                        "event_type": row["event_type"],
                        "title": row["title"][:200],
                        "description": row["description"][:500] if row["description"] else None,
                    })
        
        # Search in relations table
            if layer in ("all", "relations"):
                cursor.execute(
                    "SELECT id, subject, predicate, object, context FROM relations WHERE (subject LIKE ? OR object LIKE ? OR context LIKE ?) AND status = 'active' ORDER BY id DESC LIMIT 10",
                    (search_pattern, search_pattern, search_pattern)
                )
                for row in cursor.fetchall():
                    results.append({
                        "layer": "relations",
                        "id": row["id"],
                        "subject": row["subject"],
                        "predicate": row["predicate"],
                        "object": row["object"],
                        "context": row["context"][:200] if row["context"] else None,
                    })
        
        
        if not results:
            return {"query": query, "result": "No matching memories found"}
        
        return {"query": query, "layer": layer, "results": results, "count": len(results)}
    
    except Exception as e:
        return {"error": str(e)}


TOOL_MAP: Dict[str, ToolFunction] = {
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "execute_shell": tool_execute_shell,
    "list_directory": tool_list_directory,
    "web_search": tool_web_search,
    "query_memory": tool_query_memory,
}


def check_tool_safety(name: str, arguments: Dict[str, Any]) -> SafetyResult:
    """Preview safety classification without executing."""
    # Check if it's an MCP tool (prefixed with server name)
    if _mcp_available and _mcp_registry and name not in TOOL_MAP:
        # MCP tools 安全分类
        # 根据工具名称和参数进行风险评估
        danger_keywords = ['delete', 'remove', 'exec', 'eval', 'system', 'shell', 'command', 'sudo', 'rm ', 'drop']
        safe_keywords = ['get', 'list', 'search', 'query', 'read', 'find', 'status', 'info']
        
        tool_name_lower = name.lower()
        args_str = str(arguments).lower()
        
        # 检查是否包含危险操作
        if any(kw in tool_name_lower or kw in args_str for kw in danger_keywords):
            return SafetyResult(allowed=True, level="high", reason=f"MCP工具 {name} 包含敏感操作")
        
        # 检查是否是安全操作
        if any(kw in tool_name_lower for kw in safe_keywords):
            return SafetyResult(allowed=True, level="low", reason=f"MCP工具 {name} 为只读操作")
        
        # 默认中等风险
        return SafetyResult(allowed=True, level="medium", reason=f"MCP外部工具 {name}")
    
    if name == "execute_shell":
        return classify_shell_command(arguments.get("command", ""))
    if name == "write_file":
        return classify_file_write(arguments.get("path", ""), arguments.get("content", ""))
    if name == "read_file":
        return classify_file_read(arguments.get("path", ""))
    # list_directory and web_search are generally safe
    return SafetyResult(allowed=True, level="low", reason="低风险工具")


# =============================================================================
# MCP Integration
# =============================================================================

def init_mcp_tools() -> bool:
    """
    Initialize MCP tools. Call this at system startup.
    Returns True if MCP is available and initialized.
    """
    global _mcp_registry, _mcp_available
    
    if not _mcp_available:
        return False
    
    try:
        _mcp_registry = get_mcp_registry()
        _mcp_registry.initialize()
        return True
    except Exception as e:
        print(f"[MCP] Initialization failed: {e}")
        _mcp_available = False
        return False


def get_all_tools_schema() -> List[Dict[str, Any]]:
    """
    Get all tools (native + MCP) in OpenAI function format.
    This is the main entry point for tool discovery.
    """
    schemas = list(TOOLS_SCHEMA)  # Start with native tools
    
    # Add MCP tools if available
    if _mcp_available and _mcp_registry:
        try:
            mcp_tools = _mcp_registry.get_tools()
            schemas.extend(mcp_tools)
        except Exception as e:
            print(f"[MCP] Failed to get tools: {e}")
    
    return schemas


async def dispatch_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch a tool call to either native implementation or MCP server.
    """
    print(f"[dispatch_tool] Called with name='{name}', arguments={arguments}")
    
    # Try native tool first
    fn = TOOL_MAP.get(name)
    if fn:
        print(f"[dispatch_tool] Found native tool: {name}")
        try:
            result = fn(**arguments)
            logger.info(f"[dispatch_tool] Tool executed successfully")
            return result
        except (TypeError, ValueError) as e:
            print(f"[dispatch_tool] Error: {e}")
            return {"error": f"Tool call failed: {e}. Arguments received: {arguments}"}
    
    # Try MCP tool
    if _mcp_available and _mcp_registry:
        print(f"[dispatch_tool] Trying MCP tool: {name}")
        try:
            return _mcp_registry.call(name, **arguments)
        except (ValueError) as e:
            print(f"[dispatch_tool] MCP error: {e}")
            return {"error": f"MCP tool error: {e}"}
    
    print(f"[dispatch_tool] Unknown tool: '{name}'")
    return {"error": f"Unknown tool: {name}"}


def shutdown_mcp() -> None:
    """Cleanup MCP connections. Call this at system shutdown."""
    global _mcp_registry
    
    if _mcp_registry:
        try:
            _mcp_registry.shutdown()
        except Exception as e:
            print(f"[MCP] Shutdown error: {e}")
        finally:
            _mcp_registry = None
