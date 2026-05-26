"""
download_tools.py — 文件下载工具

提供：download_file（下载文件到本地）
适配国内网络环境（支持代理、国内镜像源）
"""

import httpx
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse, unquote


class DownloadTools:
    """文件下载工具集"""

    # 国内镜像源映射
    MIRROR_MAP = {
        "github.com": "https://ghproxy.com",
        "raw.githubusercontent.com": "https://ghproxy.com",
        "pypi.org": "https://mirrors.aliyun.com/pypi",
        "npmjs.org": "https://registry.npmmirror.com",
    }

    @staticmethod
    def get_definitions() -> list[dict]:
        """返回工具的 JSON Schema 定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "download_file",
                    "description": "下载文件到本地。支持代理和国内镜像源加速。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "文件下载地址"
                            },
                            "save_path": {
                                "type": "string",
                                "description": "保存路径（默认自动从 URL 推断文件名）"
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "超时时间（秒），默认 60",
                                "default": 60
                            },
                            "use_mirror": {
                                "type": "boolean",
                                "description": "是否使用国内镜像加速（GitHub 等国外源），默认 true",
                                "default": True
                            }
                        },
                        "required": ["url"]
                    }
                }
            }
        ]

    @staticmethod
    async def execute(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        if name == "download_file":
            return await DownloadTools._download_file(
                url=args.get("url", ""),
                save_path=args.get("save_path"),
                timeout=args.get("timeout", 60),
                use_mirror=args.get("use_mirror", True)
            )
        return {"error": f"未知的下载工具: {name}"}

    @staticmethod
    def _get_mirror_url(url: str, use_mirror: bool) -> str:
        """获取镜像 URL"""
        if not use_mirror:
            return url
        
        parsed = urlparse(url)
        for domain, mirror in DownloadTools.MIRROR_MAP.items():
            if domain in parsed.netloc:
                # 构造镜像 URL
                if mirror.startswith("https://ghproxy.com"):
                    return f"{mirror}/{url}"
                else:
                    return url.replace(f"https://{domain}", mirror)
        return url

    @staticmethod
    async def _download_file(
        url: str,
        save_path: Optional[str] = None,
        timeout: int = 60,
        use_mirror: bool = True
    ) -> Dict[str, Any]:
        """下载文件"""
        try:
            # 使用镜像
            actual_url = DownloadTools._get_mirror_url(url, use_mirror)
            
            # 确定保存路径
            if save_path:
                file_path = Path(save_path)
            else:
                # 从 URL 提取文件名
                parsed = urlparse(actual_url)
                filename = unquote(parsed.path.split("/")[-1])
                if not filename:
                    filename = "downloaded_file"
                file_path = Path(filename)
            
            # 创建目录
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 流式下载
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                limits=httpx.Limits(max_connections=10)
            ) as client:
                async with client.stream("GET", actual_url) as response:
                    response.raise_for_status()
                    
                    # 获取文件大小
                    total_size = int(response.headers.get("content-length", 0))
                    
                    # 写入文件
                    downloaded = 0
                    with open(file_path, "wb") as f:
                        async for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)
            
            return {
                "success": True,
                "path": str(file_path),
                "size": downloaded,
                "total_size": total_size,
                "url": actual_url
            }
            
        except httpx.TimeoutException:
            return {"error": f"下载超时（{timeout}秒）: {url}", "success": False}
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP 错误 {e.response.status_code}: {url}", "success": False}
        except Exception as e:
            return {"error": f"下载失败: {str(e)}", "success": False}
