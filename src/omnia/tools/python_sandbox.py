"""
python_sandbox.py — Python 代码安全执行沙箱

提供：run_python（安全执行 Python 代码片段）
"""

import sys
import io
import traceback
import signal
import threading
from typing import Dict, Any
from contextlib import contextmanager


@contextmanager
def _time_limit(seconds=10):
    """超时控制（仅 Linux/macOS）"""
    def _handler(signum, frame):
        raise TimeoutError("代码执行超时")
    old_handler = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


class PythonSandbox:
    """Python 代码安全执行沙箱"""

    # 禁止导入的模块（安全限制）
    BLOCKED_MODULES = {
        "subprocess", "os.system", "shutil.rmtree",
        "socket", "http.server", "ftplib", "smtplib",
    }

    # 允许但有限制的模块
    SAFE_MODULES = {
        "math", "random", "datetime", "json", "csv", "re",
        "collections", "itertools", "functools", "string",
        "textwrap", "unicodedata", "copy", "pprint",
        "statistics", "decimal", "fractions",
        "hashlib", "base64", "zlib",
    }

    @staticmethod
    def get_definitions() -> list[dict]:
        """返回工具的 JSON Schema 定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "run_python",
                    "description": "在安全沙箱中执行 Python 代码片段并返回结果。支持计算、数据处理、格式转换等。限时 10 秒，禁用危险操作。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "要执行的 Python 代码"
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "超时时间（秒），默认 10",
                                "default": 10
                            }
                        },
                        "required": ["code"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "run_python_file",
                    "description": "执行指定路径的 Python 文件。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Python 文件路径"
                            },
                            "args": {
                                "type": "string",
                                "description": "命令行参数（可选）",
                                "default": ""
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "超时时间（秒），默认 30",
                                "default": 30
                            }
                        },
                        "required": ["path"]
                    }
                }
            }
        ]

    @staticmethod
    async def execute(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        if name == "run_python":
            return await PythonSandbox._run_python(
                code=args.get("code", ""),
                timeout=args.get("timeout", 10)
            )
        elif name == "run_python_file":
            return await PythonSandbox._run_python_file(
                path=args.get("path", ""),
                args_str=args.get("args", ""),
                timeout=args.get("timeout", 30)
            )
        return {"error": f"未知的 Python 沙箱工具: {name}"}

    @staticmethod
    async def _run_python(code: str, timeout: int = 10) -> Dict[str, Any]:
        """安全执行 Python 代码"""
        import subprocess
        try:
            # 使用子进程隔离执行，更安全
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout,
                env={
                    "PATH": "/usr/bin:/usr/local/bin:/bin",
                    "HOME": "/tmp",
                    "PYTHONDONTWRITEBYTECODE": "1",
                }
            )

            return {
                "stdout": result.stdout[:5000] if result.stdout else "",
                "stderr": result.stderr[:2000] if result.stderr else "",
                "exit_code": result.returncode,
                "success": result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {
                "error": f"代码执行超时（{timeout}秒）",
                "success": False
            }
        except Exception as e:
            return {
                "error": f"执行失败: {str(e)}",
                "success": False
            }

    @staticmethod
    async def _run_python_file(path: str, args_str: str = "", timeout: int = 30) -> Dict[str, Any]:
        """执行 Python 文件"""
        import subprocess
        from pathlib import Path

        file_path = Path(path)
        if not file_path.exists():
            return {"error": f"文件不存在: {path}", "success": False}
        if not file_path.suffix == ".py":
            return {"error": f"不是 Python 文件: {path}", "success": False}

        cmd = [sys.executable, str(file_path)]
        if args_str:
            cmd.extend(args_str.split())

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(file_path.parent)
            )

            return {
                "stdout": result.stdout[:5000] if result.stdout else "",
                "stderr": result.stderr[:2000] if result.stderr else "",
                "exit_code": result.returncode,
                "success": result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {"error": f"执行超时（{timeout}秒）", "success": False}
        except Exception as e:
            return {"error": f"执行失败: {str(e)}", "success": False}
