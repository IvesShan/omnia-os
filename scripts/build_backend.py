#!/usr/bin/env python3
"""
PyInstaller 打包脚本 - 将 Python 后端打包成独立可执行文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
DIST_DIR = PROJECT_ROOT / "dist"
TAURI_BINARIES = PROJECT_ROOT / "src-tauri" / "binaries"

def check_pyinstaller():
    """检查 PyInstaller 是否安装"""
    try:
        import PyInstaller
        print("✓ PyInstaller 已安装")
    except ImportError:
        print("PyInstaller 未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("✓ PyInstaller 安装完成")

def build_backend():
    """打包后端"""
    print("\n" + "="*50)
    print("开始打包 Python 后端...")
    print("="*50 + "\n")
    
    # 创建输出目录
    TAURI_BINARIES.mkdir(parents=True, exist_ok=True)
    
    # PyInstaller 命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                    # 单文件模式
        "--name", "omnia-backend",      # 输出文件名
        "--distpath", str(TAURI_BINARIES),
        "--workpath", str(DIST_DIR / "build"),
        "--specpath", str(DIST_DIR),
        "--clean",
        str(BACKEND_DIR / "standalone_main.py")
    ]
    
    # 添加隐式导入
    hidden_imports = [
        "flask", "flask_cors", "requests", 
        "threading", "json", "os", "sys",
        "datetime", "pathlib", "typing"
    ]
    
    for module in hidden_imports:
        cmd.extend(["--hidden-import", module])
    
    # 添加数据文件
    config_dir = PROJECT_ROOT / "config"
    if config_dir.exists():
        cmd.extend(["--add-data", f"{config_dir}:config"])
    
    print(f"执行命令: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    
    if result.returncode == 0:
        print("\n✓ 后端打包成功！")
        print(f"  输出位置: {TAURI_BINARIES / 'omnia-backend'}")
        return True
    else:
        print("\n✗ 后端打包失败！")
        return False

def main():
    print("="*50)
    print("Omnia 后端打包工具")
    print("="*50)
    
    # 检查 PyInstaller
    check_pyinstaller()
    
    # 打包后端
    if build_backend():
        print("\n" + "="*50)
        print("打包完成！")
        print("="*50)
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
