"""
system_tools.py — 系统工具实现

提供：read_file, write_file, execute_shell, list_directory, web_search
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any


class SystemTools:
    """系统级工具集"""

    @staticmethod
    def get_definitions() -> list[dict]:
        """返回工具的 JSON Schema 定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "读取文件内容。返回完整文本或错误信息。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "文件的绝对或相对路径"
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "写入内容到文件。如果目录不存在会自动创建。用于创建或覆盖文件。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "文件的绝对或相对路径"
                            },
                            "content": {
                                "type": "string",
                                "description": "要写入的完整文本内容"
                            }
                        },
                        "required": ["path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_shell",
                    "description": "执行 Shell 命令。返回 stdout/stderr/exit_code。用于搜索、git、构建、安装等操作。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "要执行的 Shell 命令"
                            }
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_directory",
                    "description": "列出目录内的文件和子目录。返回 markdown 格式列表。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "要列出的目录路径"
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "使用搜索引擎搜索网络。返回 AI 综合答案和引用。用于获取最新资讯、文档、排查问题。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索关键词"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
        ]

    @staticmethod
    async def execute(name: str, args: Dict[str, Any], workspace: str = None) -> Dict[str, Any]:
        """执行工具调用"""
        
        if name == "read_file":
            return await SystemTools._read_file(args.get("path", ""))
        elif name == "write_file":
            return await SystemTools._write_file(args.get("path", ""), args.get("content", ""))
        elif name == "execute_shell":
            return await SystemTools._execute_shell(args.get("command", ""), workspace)
        elif name == "list_directory":
            return await SystemTools._list_directory(args.get("path", ""))
        elif name == "web_search":
            return await SystemTools._web_search(args.get("query", ""))
        else:
            return {"error": f"Unknown system tool: {name}"}

    @staticmethod
    async def _read_file(path: str) -> Dict[str, Any]:
        """读取文件"""
        try:
            p = Path(path)
            if not p.exists():
                return {"error": f"文件不存在: {path}"}
            if not p.is_file():
                return {"error": f"不是文件: {path}"}
            
            content = p.read_text(encoding="utf-8", errors="replace")
            return {"content": content}
        except Exception as e:
            return {"error": f"读取失败: {str(e)}"}

    @staticmethod
    async def _write_file(path: str, content: str) -> Dict[str, Any]:
        """写入文件"""
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return {"ok": True, "path": str(p), "bytes_written": len(content)}
        except Exception as e:
            return {"error": f"写入失败: {str(e)}"}

    @staticmethod
    async def _execute_shell(command: str, workspace: str = None) -> Dict[str, Any]:
        """执行 Shell 命令"""
        try:
            cwd = workspace or os.getcwd()
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=cwd
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"error": "命令执行超时（30秒）"}
        except Exception as e:
            return {"error": f"执行失败: {str(e)}"}

    @staticmethod
    async def _list_directory(path: str) -> Dict[str, Any]:
        """列出目录"""
        try:
            p = Path(path)
            if not p.exists():
                return {"error": f"路径不存在: {path}"}
            if not p.is_dir():
                return {"error": f"不是目录: {path}"}
            
            items = []
            for item in sorted(p.iterdir()):
                prefix = "[D]" if item.is_dir() else "[F]"
                items.append(f"{prefix} {item.name}")
            
            return {
                "path": str(p),
                "items": items,
                "count": len(items)
            }
        except Exception as e:
            return {"error": f"列出失败: {str(e)}"}

    @staticmethod
    async def _web_search(query: str) -> Dict[str, Any]:
        """网络搜索 — 使用 httpx 调用外部搜索 API"""
        try:
            import httpx
            
            # 尝试使用外部搜索服务
            search_url = f"https://api.duckduckgo.com/?q={query}&format=json"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_html": "1"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {"result": data.get("AbstractText", "未找到结果")}
                else:
                    return {"result": f"搜索请求失败: HTTP {response.status_code}"}
        except ImportError:
            return {"result": "搜索服务不可用（缺少 httpx）"}
        except Exception as e:
            return {"result": f"搜索出错: {str(e)}"}
