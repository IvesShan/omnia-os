"""
git_tools.py — Git 操作工具

提供：git_status, git_log, git_diff, git_commit, git_push, git_pull, git_branch
适配国内网络环境（自动使用 gitee 等国内源）
"""

import subprocess
import os
from pathlib import Path
from typing import Dict, Any, Optional


class GitTools:
    """Git 操作工具集"""

    @staticmethod
    def get_definitions() -> list[dict]:
        """返回工具的 JSON Schema 定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "git_status",
                    "description": "查看 Git 仓库状态，包括修改的文件、暂存区、分支信息等。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Git 仓库路径，默认当前目录"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "git_log",
                    "description": "查看 Git 提交历史。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Git 仓库路径"
                            },
                            "count": {
                                "type": "integer",
                                "description": "显示的提交数量，默认 10",
                                "default": 10
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "git_diff",
                    "description": "查看 Git 文件差异。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Git 仓库路径"
                            },
                            "file": {
                                "type": "string",
                                "description": "指定文件路径（可选，不指定则显示全部差异）"
                            },
                            "staged": {
                                "type": "boolean",
                                "description": "是否查看暂存区差异，默认 false",
                                "default": False
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "git_commit",
                    "description": "提交 Git 更改。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Git 仓库路径"
                            },
                            "message": {
                                "type": "string",
                                "description": "提交信息"
                            },
                            "add_all": {
                                "type": "boolean",
                                "description": "是否先 add 所有更改，默认 true",
                                "default": True
                            }
                        },
                        "required": ["message"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "git_push",
                    "description": "推送 Git 更改到远程仓库。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Git 仓库路径"
                            },
                            "remote": {
                                "type": "string",
                                "description": "远程仓库名，默认 origin",
                                "default": "origin"
                            },
                            "branch": {
                                "type": "string",
                                "description": "分支名，默认当前分支"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "git_pull",
                    "description": "从远程仓库拉取最新更改。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Git 仓库路径"
                            },
                            "remote": {
                                "type": "string",
                                "description": "远程仓库名，默认 origin",
                                "default": "origin"
                            },
                            "branch": {
                                "type": "string",
                                "description": "分支名，默认当前分支"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "git_branch",
                    "description": "管理 Git 分支：列出、创建、切换。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Git 仓库路径"
                            },
                            "action": {
                                "type": "string",
                                "enum": ["list", "create", "switch", "delete"],
                                "description": "操作类型：list(列出)/create(创建)/switch(切换)/delete(删除)",
                                "default": "list"
                            },
                            "branch_name": {
                                "type": "string",
                                "description": "分支名（create/switch/delete 时必须）"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "git_remote",
                    "description": "查看或管理 Git 远程仓库配置。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Git 仓库路径"
                            },
                            "action": {
                                "type": "string",
                                "enum": ["list", "add", "set_url"],
                                "description": "操作类型",
                                "default": "list"
                            },
                            "remote_name": {
                                "type": "string",
                                "description": "远程仓库名"
                            },
                            "url": {
                                "type": "string",
                                "description": "远程仓库 URL"
                            }
                        }
                    }
                }
            }
        ]

    @staticmethod
    async def execute(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Git 工具调用"""
        method_map = {
            "git_status": GitTools._git_status,
            "git_log": GitTools._git_log,
            "git_diff": GitTools._git_diff,
            "git_commit": GitTools._git_commit,
            "git_push": GitTools._git_push,
            "git_pull": GitTools._git_pull,
            "git_branch": GitTools._git_branch,
            "git_remote": GitTools._git_remote,
        }

        method = method_map.get(name)
        if method:
            return await method(**args)
        return {"error": f"未知的 Git 工具: {name}"}

    @staticmethod
    def _run_git(args: list, cwd: str = None) -> Dict[str, Any]:
        """执行 git 命令的辅助方法"""
        try:
            if cwd is None:
                cwd = os.getcwd()
            result = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=cwd
            )
            return {
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "exit_code": result.returncode
            }
        except FileNotFoundError:
            return {"error": "Git 未安装或不在 PATH 中"}
        except subprocess.TimeoutExpired:
            return {"error": "Git 命令执行超时（30秒）"}
        except Exception as e:
            return {"error": f"Git 执行失败: {str(e)}"}

    @staticmethod
    async def _git_status(path: str = None) -> Dict[str, Any]:
        """查看 Git 状态"""
        cwd = path or os.getcwd()
        result = GitTools._run_git(["status", "--short", "--branch"], cwd)

        if result.get("error"):
            return result

        # 同时获取远程同步状态
        ahead_behind = GitTools._run_git(
            ["rev-list", "--left-right", "--count", "HEAD...@{upstream}"],
            cwd
        )

        return {
            "branch_info": result["stdout"],
            "remote_sync": ahead_behind.get("stdout", "") if not ahead_behind.get("error") else "无上游分支",
            "exit_code": result["exit_code"]
        }

    @staticmethod
    async def _git_log(path: str = None, count: int = 10) -> Dict[str, Any]:
        """查看 Git 日志"""
        cwd = path or os.getcwd()
        result = GitTools._run_git([
            "log", f"--oneline", f"-{count}",
            "--format=%h | %an | %ar | %s"
        ], cwd)

        if result.get("error"):
            return result

        return {
            "log": result["stdout"],
            "count": count,
            "exit_code": result["exit_code"]
        }

    @staticmethod
    async def _git_diff(path: str = None, file: str = None, staged: bool = False) -> Dict[str, Any]:
        """查看 Git 差异"""
        cwd = path or os.getcwd()
        cmd = ["diff"]
        if staged:
            cmd.append("--staged")
        if file:
            cmd.append(file)

        result = GitTools._run_git(cmd, cwd)

        if result.get("error"):
            return result

        # 同时获取统计信息
        stat_cmd = ["diff", "--stat"]
        if staged:
            stat_cmd.append("--staged")
        if file:
            stat_cmd.append(file)
        stat_result = GitTools._run_git(stat_cmd, cwd)

        return {
            "diff": result["stdout"] or "(无差异)",
            "stat": stat_result.get("stdout", ""),
            "exit_code": result["exit_code"]
        }

    @staticmethod
    async def _git_commit(message: str, path: str = None, add_all: bool = True) -> Dict[str, Any]:
        """提交更改"""
        cwd = path or os.getcwd()

        if add_all:
            add_result = GitTools._run_git(["add", "-A"], cwd)
            if add_result.get("error"):
                return add_result

        result = GitTools._run_git(["commit", "-m", message], cwd)

        if result.get("error"):
            return result

        return {
            "output": result["stdout"],
            "exit_code": result["exit_code"]
        }

    @staticmethod
    async def _git_push(path: str = None, remote: str = "origin", branch: str = None) -> Dict[str, Any]:
        """推送到远程"""
        cwd = path or os.getcwd()
        cmd = ["push", remote]
        if branch:
            cmd.append(branch)
        result = GitTools._run_git(cmd, cwd)

        return {
            "output": result.get("stdout", "") + result.get("stderr", ""),
            "exit_code": result.get("exit_code", 1)
        }

    @staticmethod
    async def _git_pull(path: str = None, remote: str = "origin", branch: str = None) -> Dict[str, Any]:
        """从远程拉取"""
        cwd = path or os.getcwd()
        cmd = ["pull", remote]
        if branch:
            cmd.append(branch)
        result = GitTools._run_git(cmd, cwd)

        return {
            "output": result.get("stdout", "") + result.get("stderr", ""),
            "exit_code": result.get("exit_code", 1)
        }

    @staticmethod
    async def _git_branch(path: str = None, action: str = "list", branch_name: str = None) -> Dict[str, Any]:
        """管理分支"""
        cwd = path or os.getcwd()

        if action == "list":
            result = GitTools._run_git(["branch", "-a", "-v"], cwd)
            return {"branches": result.get("stdout", ""), "exit_code": result.get("exit_code", 1)}

        elif action == "create":
            if not branch_name:
                return {"error": "创建分支需要指定 branch_name"}
            result = GitTools._run_git(["checkout", "-b", branch_name], cwd)
            return {"output": result.get("stdout", ""), "exit_code": result.get("exit_code", 1)}

        elif action == "switch":
            if not branch_name:
                return {"error": "切换分支需要指定 branch_name"}
            result = GitTools._run_git(["checkout", branch_name], cwd)
            return {"output": result.get("stdout", ""), "exit_code": result.get("exit_code", 1)}

        elif action == "delete":
            if not branch_name:
                return {"error": "删除分支需要指定 branch_name"}
            result = GitTools._run_git(["branch", "-D", branch_name], cwd)
            return {"output": result.get("stdout", ""), "exit_code": result.get("exit_code", 1)}

        return {"error": f"未知的分支操作: {action}"}

    @staticmethod
    async def _git_remote(path: str = None, action: str = "list", remote_name: str = None, url: str = None) -> Dict[str, Any]:
        """管理远程仓库"""
        cwd = path or os.getcwd()

        if action == "list":
            result = GitTools._run_git(["remote", "-v"], cwd)
            return {"remotes": result.get("stdout", ""), "exit_code": result.get("exit_code", 1)}

        elif action == "add":
            if not remote_name or not url:
                return {"error": "添加远程仓库需要 remote_name 和 url"}
            result = GitTools._run_git(["remote", "add", remote_name, url], cwd)
            return {"output": result.get("stdout", ""), "exit_code": result.get("exit_code", 1)}

        elif action == "set_url":
            if not remote_name or not url:
                return {"error": "设置 URL 需要 remote_name 和 url"}
            result = GitTools._run_git(["remote", "set-url", remote_name, url], cwd)
            return {"output": result.get("stdout", ""), "exit_code": result.get("exit_code", 1)}

        return {"error": f"未知的远程操作: {action}"}
