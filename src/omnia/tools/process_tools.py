import asyncio
"""
process_tools.py — 进程管理工具

提供：process_list, process_kill, process_info, port_check
适配跨平台（Linux/macOS/Windows）
"""

import subprocess
import platform
import shutil
from typing import Dict, Any


class ProcessTools:
    """进程管理工具集"""

    @staticmethod
    def get_definitions() -> list[dict]:
        """返回工具的 JSON Schema 定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "process_list",
                    "description": "列出运行中的进程。可按名称/关键词过滤。返回 PID、名称、CPU/内存占用等信息。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filter": {
                                "type": "string",
                                "description": "过滤关键词（进程名或命令行包含的字符串）"
                            },
                            "sort_by": {
                                "type": "string",
                                "enum": ["cpu", "memory", "pid", "name"],
                                "description": "排序方式，默认 cpu",
                                "default": "cpu"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "最多返回的进程数，默认 20",
                                "default": 20
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "process_info",
                    "description": "获取指定进程的详细信息（PID、启动时间、命令行、内存占用等）。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pid": {
                                "type": "integer",
                                "description": "进程 ID"
                            },
                            "name": {
                                "type": "string",
                                "description": "进程名（会查找第一个匹配的进程）"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "process_kill",
                    "description": "终止指定进程。支持按 PID 或进程名终止。默认发送 SIGTERM，force=true 使用 SIGKILL。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pid": {
                                "type": "integer",
                                "description": "进程 ID"
                            },
                            "name": {
                                "type": "string",
                                "description": "进程名（终止所有匹配的进程）"
                            },
                            "force": {
                                "type": "boolean",
                                "description": "是否强制终止（SIGKILL），默认 false",
                                "default": False
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "port_check",
                    "description": "检查端口占用情况，显示占用指定端口的进程信息。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "port": {
                                "type": "integer",
                                "description": "要检查的端口号"
                            }
                        },
                        "required": ["port"]
                    }
                }
            },
        ]

    @staticmethod
    async def execute(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        method_map = {
            "process_list": ProcessTools._process_list,
            "process_info": ProcessTools._process_info,
            "process_kill": ProcessTools._process_kill,
            "port_check": ProcessTools._port_check,
        }
        method = method_map.get(name)
        if method:
            return await method(**args)
        return {"error": f"未知的进程管理工具: {name}"}

    @staticmethod
    def _run_cmd(cmd: list, timeout: int = 15) -> Dict[str, Any]:
        """执行命令"""
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            stdout = result.stdout
            if len(stdout) > 10000:
                stdout = stdout[:10000] + "\n[...输出已截断...]"
            return {
                "stdout": stdout,
                "stderr": result.stderr[:2000] if result.stderr else "",
                "exit_code": result.returncode,
            }
        except FileNotFoundError:
            return {"error": f"命令未找到: {cmd[0]}"}
        except subprocess.TimeoutExpired:
            return {"error": f"命令执行超时（{timeout}秒）"}
        except Exception as e:
            return {"error": f"命令执行失败: {str(e)}"}

    @staticmethod
    async def _process_list(filter: str = "", sort_by: str = "cpu", limit: int = 20) -> Dict[str, Any]:
        """列出进程"""
        system = platform.system()

        if system in ("Linux", "Darwin"):
            # 使用 ps 命令
            cmd = ["ps", "aux", "--sort=-%cpu"] if system == "Linux" else ["ps", "aux"]
            result = await asyncio.to_thread(ProcessTools._run_cmd, cmd)

            if result.get("error"):
                return result

            lines = result["stdout"].strip().split("\n")
            header = lines[0] if lines else ""
            procs = lines[1:]

            # 过滤
            if filter:
                filter_lower = filter.lower()
                procs = [l for l in procs if filter_lower in l.lower()]

            # macOS 不支持 --sort，手动排序
            if system == "Darwin":
                try:
                    cpu_idx = 2  # ps aux 的 CPU 列
                    mem_idx = 3  # ps aux 的 MEM 列
                    sort_idx = {"cpu": cpu_idx, "memory": mem_idx}.get(sort_by, cpu_idx)
                    procs.sort(key=lambda l: float(l.split()[sort_idx]) if len(l.split()) > sort_idx else 0, reverse=True)
                except (ValueError, IndexError):
                    pass

            procs = procs[:limit]

            return {
                "success": True,
                "header": header,
                "processes": procs,
                "total": len(procs),
                "platform": system,
            }

        elif system == "Windows":
            cmd = ["tasklist", "/FO", "CSV", "/NH"]
            result = await asyncio.to_thread(ProcessTools._run_cmd, cmd)

            if result.get("error"):
                return result

            lines = result["stdout"].strip().split("\n")
            if filter:
                filter_lower = filter.lower()
                lines = [l for l in lines if filter_lower in l.lower()]

            lines = lines[:limit]

            return {
                "success": True,
                "processes": lines,
                "total": len(lines),
                "platform": system,
            }

        return {"error": f"不支持的操作系统: {system}"}

    @staticmethod
    async def _process_info(pid: int = None, name: str = None) -> Dict[str, Any]:
        """获取进程详情"""
        if not pid and not name:
            return {"error": "需要提供 pid 或 name"}

        system = platform.system()

        if not pid and name:
            # 先查找 PID
            if system in ("Linux", "Darwin"):
                cmd = ["pgrep", "-f", name]
                result = await asyncio.to_thread(ProcessTools._run_cmd, cmd)
                if result.get("stdout", "").strip():
                    pid = int(result["stdout"].strip().split("\n")[0])
                else:
                    return {"error": f"未找到进程: {name}", "success": False}
            elif system == "Windows":
                cmd = ["tasklist", "/FI", f"IMAGENAME eq {name}", "/FO", "CSV", "/NH"]
                result = await asyncio.to_thread(ProcessTools._run_cmd, cmd)
                if result.get("stdout", "").strip():
                    first_line = result["stdout"].strip().split("\n")[0]
                    pid = int(first_line.split(",")[1].strip('"'))
                else:
                    return {"error": f"未找到进程: {name}", "success": False}

        if not pid:
            return {"error": "未指定 PID", "success": False}

        if system in ("Linux", "Darwin"):
            cmd = ["ps", "-p", str(pid), "-o", "pid,ppid,user,%cpu,%mem,vsz,rss,stat,start,etime,command"]
            result = await asyncio.to_thread(ProcessTools._run_cmd, cmd)

            if result.get("error"):
                return result

            # 在 Linux 上额外获取详细信息
            extra_info = {}
            if system == "Linux":
                try:
                    with open(f"/proc/{pid}/cmdline", "r") as f:
                        extra_info["cmdline"] = f.read().replace("\0", " ").strip()
                    with open(f"/proc/{pid}/status", "r") as f:
                        extra_info["status"] = f.read()[:500]
                except (FileNotFoundError, PermissionError):
                    pass

            return {
                "success": True,
                "pid": pid,
                "info": result["stdout"],
                "extra": extra_info,
            }

        elif system == "Windows":
            cmd = ["tasklist", "/FI", f"PID eq {pid}", "/FO", "LIST", "/V"]
            result = await asyncio.to_thread(ProcessTools._run_cmd, cmd)
            return {
                "success": True,
                "pid": pid,
                "info": result.get("stdout", ""),
            }

        return {"error": f"不支持的操作系统: {system}"}

    @staticmethod
    async def _process_kill(pid: int = None, name: str = None, force: bool = False) -> Dict[str, Any]:
        """终止进程"""
        if not pid and not name:
            return {"error": "需要提供 pid 或 name"}

        system = platform.system()

        try:
            if pid:
                if system in ("Linux", "Darwin"):
                    import os, signal
                    sig = signal.SIGKILL if force else signal.SIGTERM
                    os.kill(pid, sig)
                elif system == "Windows":
                    cmd = ["taskkill", "/PID", str(pid)]
                    if force:
                        cmd.append("/F")
                    result = await asyncio.to_thread(ProcessTools._run_cmd, cmd)
                    if result.get("exit_code", 1) != 0:
                        return {"error": result.get("stderr", "终止失败"), "success": False}
            elif name:
                if system in ("Linux", "Darwin"):
                    cmd = ["pkill", "-f", name] if not force else ["pkill", "-9", "-f", name]
                    result = await asyncio.to_thread(ProcessTools._run_cmd, cmd)
                    if result.get("exit_code", 1) != 0:
                        return {"error": f"终止 '{name}' 失败: {result.get('stderr', '')}", "success": False}
                elif system == "Windows":
                    cmd = ["taskkill", "/IM", name]
                    if force:
                        cmd.append("/F")
                    result = await asyncio.to_thread(ProcessTools._run_cmd, cmd)
                    if result.get("exit_code", 1) != 0:
                        return {"error": result.get("stderr", "终止失败"), "success": False}

            return {
                "success": True,
                "action": "killed",
                "pid": pid,
                "name": name,
                "force": force,
            }
        except ProcessLookupError:
            return {"error": f"进程不存在: PID={pid}", "success": False}
        except PermissionError:
            return {"error": f"权限不足，无法终止进程 PID={pid}。可能需要 sudo/管理员权限。", "success": False}
        except Exception as e:
            return {"error": f"终止进程失败: {str(e)}", "success": False}

    @staticmethod
    async def _port_check(port: int) -> Dict[str, Any]:
        """检查端口占用"""
        system = platform.system()

        if system == "Linux":
            cmd = ["ss", "-tlnp", f"sport = :{port}"]
            result = await asyncio.to_thread(ProcessTools._run_cmd, cmd)
            if not result.get("stdout", "").strip():
                # fallback 到 lsof
                cmd = ["lsof", "-i", f":{port}", "-P", "-n"]
                result = await asyncio.to_thread(ProcessTools._run_cmd, cmd)

        elif system == "Darwin":
            cmd = ["lsof", "-i", f":{port}", "-P", "-n"]
            result = await asyncio.to_thread(ProcessTools._run_cmd, cmd)

        elif system == "Windows":
            cmd = ["netstat", "-ano", "-p", "tcp"]
            result = await asyncio.to_thread(ProcessTools._run_cmd, cmd)
            if result.get("stdout"):
                lines = result["stdout"].strip().split("\n")
                filtered = [l for l in lines if f":{port}" in l]
                result["stdout"] = "\n".join(filtered)

        else:
            return {"error": f"不支持的操作系统: {system}"}

        if result.get("error"):
            return result

        is_in_use = bool(result.get("stdout", "").strip())

        return {
            "success": True,
            "port": port,
            "in_use": is_in_use,
            "details": result.get("stdout", "").strip() or f"端口 {port} 未被占用",
            "platform": system,
        }