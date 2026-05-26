"""
grep_search.py — 代码/文本搜索工具

提供：search_files, grep_code, find_symbol
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, List


class GrepSearchTools:
    """搜索工具集"""

    @staticmethod
    def get_definitions() -> list[dict]:
        """返回工具的 JSON Schema 定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_files",
                    "description": "在目录中搜索包含指定文本或正则的文件。返回匹配文件列表及上下文片段。支持通配符过滤文件类型。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索关键词或正则表达式"
                            },
                            "path": {
                                "type": "string",
                                "description": "搜索起始目录（绝对或相对路径）"
                            },
                            "glob": {
                                "type": "string",
                                "description": "文件通配符过滤，如 '*.py', '*.js', '*.{ts,tsx}'。默认 '*.*'",
                                "default": "*"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "最大返回结果数，默认 20",
                                "default": 20
                            },
                            "context_lines": {
                                "type": "integer",
                                "description": "匹配行前后显示的上下文行数，默认 2",
                                "default": 2
                            }
                        },
                        "required": ["query", "path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_symbol",
                    "description": "在代码库中查找函数/类/变量定义。支持 Python、JavaScript/TypeScript、Go 等语言。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "要查找的符号名称（函数名、类名、变量名）"
                            },
                            "path": {
                                "type": "string",
                                "description": "搜索起始目录"
                            },
                            "language": {
                                "type": "string",
                                "description": "语言过滤，如 'python', 'javascript', 'typescript', 'go'。可选。",
                                "default": ""
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "最大返回结果数，默认 10",
                                "default": 10
                            }
                        },
                        "required": ["symbol", "path"]
                    }
                }
            }
        ]

    @staticmethod
    async def execute(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        if name == "search_files":
            return await GrepSearchTools._search_files(
                query=args.get("query", ""),
                path=args.get("path", "."),
                glob=args.get("glob", "*"),
                max_results=args.get("max_results", 20),
                context_lines=args.get("context_lines", 2)
            )
        elif name == "find_symbol":
            return await GrepSearchTools._find_symbol(
                symbol=args.get("symbol", ""),
                path=args.get("path", "."),
                language=args.get("language", ""),
                max_results=args.get("max_results", 10)
            )
        else:
            return {"error": f"Unknown search tool: {name}"}

    @staticmethod
    async def _search_files(query: str, path: str, glob: str, max_results: int, context_lines: int) -> Dict[str, Any]:
        """在目录中搜索文件内容"""
        try:
            base = Path(path)
            if not base.exists():
                return {"error": f"路径不存在: {path}"}
            
            # 使用 ripgrep 或 grep
            cmd = ["grep", "-r", "-n", "-I", "--include", glob]
            
            # 检查是否是正则表达式（包含特殊字符）
            regex_chars = set(".*+?[]{}()^$\\|")
            if any(c in query for c in regex_chars):
                cmd.append("-E")  # 扩展正则
            
            cmd.extend(["-C", str(context_lines), query, str(base)])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # 解析结果
            matches = []
            current_file = None
            current_lines = []
            
            for line in result.stdout.split("\n")[:max_results * (context_lines * 2 + 3)]:
                if not line.strip():
                    continue
                    
                # 匹配行格式: path:line:content 或 path-line-content（grep -C 输出）
                import re as re_module
                m = re_module.match(r'^(.+):(\d+)[\-:](.*)$', line)
                if m:
                    file_path, line_no, content = m.groups()
                    matches.append({
                        "file": file_path,
                        "line": int(line_no),
                        "content": content
                    })
            
            # 去重并聚合
            file_matches = {}
            for m in matches:
                fp = m["file"]
                if fp not in file_matches:
                    file_matches[fp] = []
                file_matches[fp].append(m)
            
            # 格式化输出
            results = []
            for fp, lines in list(file_matches.items())[:max_results]:
                results.append({
                    "file": fp,
                    "matches": lines[:5]  # 每文件最多 5 行
                })
            
            return {
                "query": query,
                "path": str(base),
                "total_files": len(file_matches),
                "total_matches": len(matches),
                "results": results
            }
            
        except subprocess.TimeoutExpired:
            return {"error": "搜索超时（30秒）"}
        except FileNotFoundError:
            # fallback: 使用 Python 实现
            return await GrepSearchTools._search_files_python(query, path, glob, max_results, context_lines)
        except Exception as e:
            return {"error": f"搜索失败: {str(e)}"}

    @staticmethod
    async def _search_files_python(query: str, path: str, glob: str, max_results: int, context_lines: int) -> Dict[str, Any]:
        """纯 Python 实现的搜索（fallback）"""
        try:
            base = Path(path)
            if not base.exists():
                return {"error": f"路径不存在: {path}"}
            
            # 解析 glob
            import fnmatch
            patterns = glob.replace(" ", "").split(",") if "," in glob else [glob]
            
            results = []
            total_matches = 0
            
            for root, dirs, files in os.walk(base):
                # 跳过隐藏目录和常见排除目录
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', 'venv', '__pycache__', 'dist', 'build')]
                
                for file in files:
                    # 检查 glob 匹配
                    matched = any(fnmatch.fnmatch(file, p) for p in patterns)
                    if not matched and glob != "*":
                        continue
                    
                    file_path = Path(root) / file
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                    except Exception:
                        continue
                    
                    file_matches = []
                    for i, line in enumerate(lines):
                        if query in line:
                            # 收集上下文
                            start = max(0, i - context_lines)
                            end = min(len(lines), i + context_lines + 1)
                            context = []
                            for j in range(start, end):
                                prefix = ">>> " if j == i else "    "
                                context.append(f"{prefix}{j+1}: {lines[j].rstrip()}")
                            
                            file_matches.append({
                                "line": i + 1,
                                "content": line.rstrip(),
                                "context": "\n".join(context)
                            })
                            total_matches += 1
                    
                    if file_matches:
                        results.append({
                            "file": str(file_path),
                            "matches": file_matches[:5]
                        })
                        
                        if len(results) >= max_results:
                            break
                
                if len(results) >= max_results:
                    break
            
            return {
                "query": query,
                "path": str(base),
                "total_files": len(results),
                "total_matches": total_matches,
                "results": results,
                "note": "使用纯 Python 搜索（grep 不可用）"
            }
            
        except Exception as e:
            return {"error": f"搜索失败: {str(e)}"}

    @staticmethod
    async def _find_symbol(symbol: str, path: str, language: str, max_results: int) -> Dict[str, Any]:
        """查找符号定义"""
        try:
            base = Path(path)
            if not base.exists():
                return {"error": f"路径不存在: {path}"}
            
            # 语言特定模式
            patterns = {
                "python": [
                    rf"^\s*(async\s+)?def\s+{re.escape(symbol)}\s*\(",
                    rf"^\s*class\s+{re.escape(symbol)}\b",
                    rf"\b{re.escape(symbol)}\s*="
                ],
                "javascript": [
                    rf"\b(function|const|let|var)\s+{re.escape(symbol)}\b",
                    rf"\b{re.escape(symbol)}\s*[:=]\s*(function|async\s*function|\()",
                    rf"class\s+{re.escape(symbol)}\b"
                ],
                "typescript": [
                    rf"\b(function|const|let|var|interface|type)\s+{re.escape(symbol)}\b",
                    rf"\b{re.escape(symbol)}\s*[:=]\s*",
                    rf"class\s+{re.escape(symbol)}\b"
                ],
                "go": [
                    rf"^\s*func\s+\([^)]*\)\s*{re.escape(symbol)}\s*\(",
                    rf"^\s*func\s+{re.escape(symbol)}\s*\(",
                    rf"\btype\s+{re.escape(symbol)}\b"
                ]
            }
            
            # 如果没有指定语言，尝试所有 Python/JS 模式
            if language and language.lower() in patterns:
                regex_patterns = patterns[language.lower()]
            else:
                regex_patterns = (
                    patterns.get("python", []) + 
                    patterns.get("javascript", []) + 
                    patterns.get("typescript", [])
                )
            
            results = []
            
            for root, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', 'venv', '__pycache__', 'dist', 'build')]
                
                for file in files:
                    if not any(file.endswith(ext) for ext in ('.py', '.js', '.ts', '.tsx', '.go')):
                        continue
                    
                    file_path = Path(root) / file
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                    except Exception:
                        continue
                    
                    file_matches = []
                    for i, line in enumerate(lines):
                        for pattern in regex_patterns:
                            if re.search(pattern, line):
                                file_matches.append({
                                    "line": i + 1,
                                    "content": line.rstrip(),
                                    "type": "definition"
                                })
                                break
                    
                    if file_matches:
                        results.append({
                            "file": str(file_path),
                            "matches": file_matches[:3]
                        })
                        
                        if len(results) >= max_results:
                            break
                
                if len(results) >= max_results:
                    break
            
            return {
                "symbol": symbol,
                "path": str(base),
                "language": language or "auto",
                "total_files": len(results),
                "results": results
            }
            
        except Exception as e:
            return {"error": f"查找失败: {str(e)}"}
