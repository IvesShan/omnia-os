import asyncio
"""
package_manager.py — 包管理工具

提供：pip_install, pip_uninstall, pip_list, npm_install, npm_uninstall, npm_list
适配国内网络环境（自动使用阿里云/清华/腾讯镜像源）
"""

import subprocess
import sys
import shutil
from typing import Dict, Any, List, Optional


class PackageManagerTools:
    """包管理工具集（适配国内网络环境）"""

    # 国内 pip 镜像源
    PIP_MIRRORS = {
        "aliyun": "https://mirrors.aliyun.com/pypi/simple/",
        "tsinghua": "https://pypi.tuna.tsinghua.edu.cn/simple/",
        "tencent": "https://mirrors.cloud.tencent.com/pypi/simple/",
        "douban": "https://pypi.douban.com/simple/",
        "huawei": "https://repo.huaweicloud.com/repository/pypi/simple/",
    }

    # 国内 npm 镜像源
    NPM_MIRRORS = {
        "taobao": "https://registry.npmmirror.com",
        "tencent": "https://mirrors.cloud.tencent.com/npm/",
        "huawei": "https://repo.huaweicloud.com/repository/npm/",
    }

    DEFAULT_PIP_MIRROR = "aliyun"
    DEFAULT_NPM_MIRROR = "taobao"

    @staticmethod
    def get_definitions() -> list[dict]:
        """返回工具的 JSON Schema 定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "pip_install",
                    "description": "使用 pip 安装 Python 包。自动使用国内镜像源加速（阿里云/清华/腾讯等）。支持安装单个或多个包，支持指定版本。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "packages": {
                                "type": "string",
                                "description": "要安装的包名，多个用空格分隔。支持版本约束，如 'requests>=2.28 flask==3.0'"
                            },
                            "mirror": {
                                "type": "string",
                                "description": "镜像源: aliyun(默认), tsinghua, tencent, douban, huawei",
                                "default": "aliyun"
                            },
                            "upgrade": {
                                "type": "boolean",
                                "description": "是否升级到最新版本，默认 false",
                                "default": False
                            },
                            "requirements_file": {
                                "type": "string",
                                "description": "从 requirements.txt 文件安装（可选）"
                            },
                            "extra_args": {
                                "type": "string",
                                "description": "额外的 pip 参数，如 '--no-deps'（可选）"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "pip_uninstall",
                    "description": "使用 pip 卸载 Python 包。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "packages": {
                                "type": "string",
                                "description": "要卸载的包名，多个用空格分隔"
                            }
                        },
                        "required": ["packages"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "pip_list",
                    "description": "列出已安装的 Python 包。可按关键词过滤。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filter": {
                                "type": "string",
                                "description": "过滤关键词（可选）"
                            },
                            "outdated": {
                                "type": "boolean",
                                "description": "是否只显示可更新的包，默认 false",
                                "default": False
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "npm_install",
                    "description": "使用 npm 安装 Node.js 包。自动使用国内镜像源加速（淘宝等）。支持全局安装和开发依赖。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "packages": {
                                "type": "string",
                                "description": "要安装的包名，多个用空格分隔"
                            },
                            "global": {
                                "type": "boolean",
                                "description": "是否全局安装，默认 false",
                                "default": False
                            },
                            "save_dev": {
                                "type": "boolean",
                                "description": "是否保存为开发依赖，默认 false",
                                "default": False
                            },
                            "mirror": {
                                "type": "string",
                                "description": "镜像源: taobao(默认), tencent, huawei",
                                "default": "taobao"
                            },
                            "workdir": {
                                "type": "string",
                                "description": "工作目录（可选）"
                            }
                        },
                        "required": ["packages"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "npm_uninstall",
                    "description": "使用 npm 卸载 Node.js 包。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "packages": {
                                "type": "string",
                                "description": "要卸载的包名，多个用空格分隔"
                            },
                            "global": {
                                "type": "boolean",
                                "description": "是否全局卸载，默认 false",
                                "default": False
                            },
                            "workdir": {
                                "type": "string",
                                "description": "工作目录（可选）"
                            }
                        },
                        "required": ["packages"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "npm_list",
                    "description": "列出已安装的 Node.js 包。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "global": {
                                "type": "boolean",
                                "description": "是否列出全局包，默认 false",
                                "default": False
                            },
                            "depth": {
                                "type": "integer",
                                "description": "依赖深度，默认 0（只显示顶层）",
                                "default": 0
                            },
                            "workdir": {
                                "type": "string",
                                "description": "工作目录（可选）"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "poetry_install",
                    "description": "使用 Poetry 安装 Python 依赖。自动配置国内镜像源。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "packages": {
                                "type": "string",
                                "description": "要安装的包名（可选，不填则安装 pyproject.toml 中的所有依赖）"
                            },
                            "dev": {
                                "type": "boolean",
                                "description": "是否安装开发依赖，默认 true",
                                "default": True
                            },
                            "workdir": {
                                "type": "string",
                                "description": "项目目录（可选）"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "pip_freeze",
                    "description": "导出当前环境的 Python 依赖列表（pip freeze 格式）。可用于生成 requirements.txt。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "output_file": {
                                "type": "string",
                                "description": "输出文件路径（可选，不填则直接返回内容）"
                            }
                        }
                    }
                }
            },
        ]

    @staticmethod
    async def execute(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        method_map = {
            "pip_install": PackageManagerTools._pip_install,
            "pip_uninstall": PackageManagerTools._pip_uninstall,
            "pip_list": PackageManagerTools._pip_list,
            "npm_install": PackageManagerTools._npm_install,
            "npm_uninstall": PackageManagerTools._npm_uninstall,
            "npm_list": PackageManagerTools._npm_list,
            "poetry_install": PackageManagerTools._poetry_install,
            "pip_freeze": PackageManagerTools._pip_freeze,
        }
        method = method_map.get(name)
        if method:
            return await method(**args)
        return {"error": f"未知的包管理工具: {name}"}

    @staticmethod
    def _run_cmd(cmd: list, timeout: int = 120, cwd: str = None) -> Dict[str, Any]:
        """执行命令的辅助方法"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            stdout = result.stdout
            stderr = result.stderr
            # 截断过长输出
            if len(stdout) > 20_000:
                stdout = stdout[:20_000] + "\n\n[...输出已截断...]"
            if len(stderr) > 5_000:
                stderr = stderr[:5_000] + "\n\n[...stderr已截断...]"
            return {
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": result.returncode,
            }
        except FileNotFoundError:
            return {"error": f"命令未找到: {cmd[0]}。请确认已安装该工具。"}
        except subprocess.TimeoutExpired:
            return {"error": f"命令执行超时（{timeout}秒）"}
        except Exception as e:
            return {"error": f"命令执行失败: {str(e)}"}

    @staticmethod
    async def _pip_install(
        packages: str = "",
        mirror: str = "aliyun",
        upgrade: bool = False,
        requirements_file: str = "",
        extra_args: str = "",
    ) -> Dict[str, Any]:
        """pip 安装"""
        cmd = [sys.executable, "-m", "pip", "install"]

        if upgrade:
            cmd.append("--upgrade")

        mirror_url = PackageManagerTools.PIP_MIRRORS.get(
            mirror, PackageManagerTools.PIP_MIRRORS[PackageManagerTools.DEFAULT_PIP_MIRROR]
        )
        cmd.extend(["-i", mirror_url, "--trusted-host", mirror_url.split("//")[1].split("/")[0]])

        if requirements_file:
            cmd.extend(["-r", requirements_file])
        elif packages:
            cmd.extend(packages.split())
        else:
            return {"error": "请指定要安装的包名或 requirements.txt 文件"}

        if extra_args:
            cmd.extend(extra_args.split())

        result = await asyncio.to_thread(PackageManagerTools._run_cmd, cmd, timeout=180)
        result["mirror"] = mirror
        result["mirror_url"] = mirror_url
        return result

    @staticmethod
    async def _pip_uninstall(packages: str) -> Dict[str, Any]:
        """pip 卸载"""
        cmd = [sys.executable, "-m", "pip", "uninstall", "-y"]
        cmd.extend(packages.split())
        return await asyncio.to_thread(PackageManagerTools._run_cmd, cmd)

    @staticmethod
    async def _pip_list(filter: str = "", outdated: bool = False) -> Dict[str, Any]:
        """pip 列表"""
        cmd = [sys.executable, "-m", "pip", "list"]
        if outdated:
            cmd.append("--outdated")
        if filter:
            cmd.extend(["--format", "columns", "--filter", filter])
        return await asyncio.to_thread(PackageManagerTools._run_cmd, cmd)

    @staticmethod
    async def _npm_install(
        packages: str,
        global_: bool = False,
        save_dev: bool = False,
        mirror: str = "taobao",
        workdir: str = "",
    ) -> Dict[str, Any]:
        """npm 安装"""
        npm_cmd = shutil.which("npm") or "npm"
        cmd = [npm_cmd, "install"]

        if global_:
            cmd.append("-g")
        if save_dev:
            cmd.append("--save-dev")

        mirror_url = PackageManagerTools.NPM_MIRRORS.get(
            mirror, PackageManagerTools.NPM_MIRRORS[PackageManagerTools.DEFAULT_NPM_MIRROR]
        )
        cmd.extend(["--registry", mirror_url])

        cmd.extend(packages.split())

        result = await asyncio.to_thread(PackageManagerTools._run_cmd, cmd, timeout=180, cwd=workdir or None)
        result["mirror"] = mirror
        result["mirror_url"] = mirror_url
        return result

    @staticmethod
    async def _npm_uninstall(
        packages: str,
        global_: bool = False,
        workdir: str = "",
    ) -> Dict[str, Any]:
        """npm 卸载"""
        npm_cmd = shutil.which("npm") or "npm"
        cmd = [npm_cmd, "uninstall"]
        if global_:
            cmd.append("-g")
        cmd.extend(packages.split())
        return await asyncio.to_thread(PackageManagerTools._run_cmd, cmd, cwd=workdir or None)

    @staticmethod
    async def _npm_list(
        global_: bool = False,
        depth: int = 0,
        workdir: str = "",
    ) -> Dict[str, Any]:
        """npm 列表"""
        npm_cmd = shutil.which("npm") or "npm"
        cmd = [npm_cmd, "list"]
        if global_:
            cmd.append("-g")
        cmd.extend(["--depth", str(depth)])
        return await asyncio.to_thread(PackageManagerTools._run_cmd, cmd, cwd=workdir or None)

    @staticmethod
    async def _poetry_install(
        packages: str = "",
        dev: bool = True,
        workdir: str = "",
    ) -> Dict[str, Any]:
        """poetry 安装"""
        poetry_cmd = shutil.which("poetry") or "poetry"
        if not packages:
            # 安装所有依赖
            cmd = [poetry_cmd, "install"]
            if not dev:
                cmd.append("--without dev")
        else:
            cmd = [poetry_cmd, "add"]
            if dev:
                cmd.append("--group dev")
            cmd.extend(packages.split())

        result = await asyncio.to_thread(PackageManagerTools._run_cmd, cmd, timeout=180, cwd=workdir or None)

        # 如果 poetry 不可用，提示安装
        if result.get("error") and "未找到" in result.get("error", ""):
            result["suggestion"] = "Poetry 未安装。可通过 pip install poetry 安装，或使用 pip_install 代替。"

        return result

    @staticmethod
    async def _pip_freeze(output_file: str = "") -> Dict[str, Any]:
        """pip freeze"""
        cmd = [sys.executable, "-m", "pip", "freeze"]
        result = await asyncio.to_thread(PackageManagerTools._run_cmd, cmd)

        if output_file and result.get("stdout"):
            try:
                from pathlib import Path
                p = Path(output_file)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(result["stdout"], encoding="utf-8")
                result["saved_to"] = str(p.resolve())
            except Exception as e:
                result["save_error"] = str(e)

        return result