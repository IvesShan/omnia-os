"""
screenshot_tools.py — 截屏工具

提供：take_screenshot（截取屏幕截图）
适配跨平台（Linux/macOS/Windows）
"""

import subprocess
import platform
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


class ScreenshotTools:
    """截屏工具集"""

    @staticmethod
    def get_definitions() -> list[dict]:
        """返回工具的 JSON Schema 定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "take_screenshot",
                    "description": "截取屏幕截图并保存到指定路径。支持全屏截图和区域截图。适配 Linux/macOS/Windows。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "save_path": {
                                "type": "string",
                                "description": "截图保存路径（默认自动生成在临时目录）"
                            },
                            "region": {
                                "type": "string",
                                "description": "截取区域，格式为 'x,y,width,height'（可选，默认全屏）"
                            },
                            "display": {
                                "type": "string",
                                "description": "显示器编号（Linux/macOS 多显示器时使用，默认为当前显示器）"
                            }
                        }
                    }
                }
            },
        ]

    @staticmethod
    async def execute(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        if name == "take_screenshot":
            return await ScreenshotTools._take_screenshot(
                save_path=args.get("save_path"),
                region=args.get("region"),
                display=args.get("display"),
            )
        return {"error": f"未知的截屏工具: {name}"}

    @staticmethod
    async def _take_screenshot(
        save_path: str = None,
        region: str = None,
        display: str = None,
    ) -> Dict[str, Any]:
        """截取屏幕"""
        system = platform.system()

        # 确定保存路径
        if save_path:
            file_path = Path(save_path)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = Path(tempfile.gettempdir()) / f"screenshot_{timestamp}.png"

        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if system == "Darwin":
                return await ScreenshotTools._screenshot_macos(str(file_path), region)
            elif system == "Linux":
                return await ScreenshotTools._screenshot_linux(str(file_path), region, display)
            elif system == "Windows":
                return await ScreenshotTools._screenshot_windows(str(file_path), region)
            else:
                return {"error": f"不支持的操作系统: {system}"}
        except Exception as e:
            return {"error": f"截屏失败: {str(e)}", "success": False}

    @staticmethod
    async def _screenshot_macos(save_path: str, region: str = None) -> Dict[str, Any]:
        """macOS 截屏"""
        cmd = ["screencapture"]
        if not region:
            cmd.append("-x")  # 不播放声音
        else:
            # 区域截屏: screencapture -R x,y,w,h file
            cmd.extend(["-x", "-R", region])
        cmd.append(save_path)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

        if result.returncode != 0:
            return {"error": f"macOS 截屏失败: {result.stderr}", "success": False}

        return {
            "success": True,
            "path": save_path,
            "platform": "macOS",
        }

    @staticmethod
    async def _screenshot_linux(save_path: str, region: str = None, display: str = None) -> Dict[str, Any]:
        """Linux 截屏"""
        # 尝试 scrot
        scrot = shutil.which("scrot")
        if scrot:
            cmd = [scrot]
            if region:
                cmd.extend(["--select", "--line", "style=dash"])
            cmd.append(save_path)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                return {"success": True, "path": save_path, "platform": "Linux", "tool": "scrot"}

        # 尝试 gnome-screenshot
        gnome_screenshot = shutil.which("gnome-screenshot")
        if gnome_screenshot:
            cmd = [gnome_screenshot, "-f", save_path]
            if region:
                cmd.append("-a")  # 区域选择
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                return {"success": True, "path": save_path, "platform": "Linux", "tool": "gnome-screenshot"}

        # 尝试 import (ImageMagick)
        import_cmd = shutil.which("import")
        if import_cmd:
            cmd = [import_cmd]
            if not region:
                cmd.extend(["-window", "root"])
            cmd.append(save_path)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                return {"success": True, "path": save_path, "platform": "Linux", "tool": "import"}

        # 尝试 xdg-screencapture / grim (Wayland)
        grim = shutil.which("grim")
        if grim:
            cmd = [grim]
            if region:
                cmd.extend(["-g", region])
            cmd.append(save_path)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                return {"success": True, "path": save_path, "platform": "Linux/Wayland", "tool": "grim"}

        return {
            "error": "Linux 截屏需要安装以下任一工具: scrot, gnome-screenshot, imagemagick, grim",
            "install_hint": "sudo apt install scrot  # 或 sudo apt install gnome-screenshot",
            "success": False,
        }

    @staticmethod
    async def _screenshot_windows(save_path: str, region: str = None) -> Dict[str, Any]:
        """Windows 截屏（使用 PowerShell）"""
        # 使用 .NET 的 System.Windows.Forms 截屏
        ps_script = f'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$screen = [System.Windows.Forms.Screen]::PrimaryScreen
$bounds = $screen.Bounds
$bitmap = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$bitmap.Save("{save_path.replace(chr(92), chr(92)+chr(92))}")
$graphics.Dispose()
$bitmap.Dispose()
Write-Output "OK"
'''
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True, text=True, timeout=15
        )

        if result.returncode != 0 or "OK" not in result.stdout:
            return {"error": f"Windows 截屏失败: {result.stderr}", "success": False}

        return {
            "success": True,
            "path": save_path,
            "platform": "Windows",
        }
