"""
Omnia FastAPI 独立打包入口
用于 Nuitka 打包的 FastAPI 版本
"""
import sys
import os
import argparse
from pathlib import Path

# 打包后路径处理
if getattr(sys, 'frozen', False):
    # Nuitka 打包后的路径
    PROJECT_ROOT = Path(sys.executable).parent
else:
    # 开发环境路径
    PROJECT_ROOT = Path(__file__).parent.parent.parent

# 确保 src 目录在 Python 路径中
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# 设置环境变量
os.environ["OMNIA_PROJECT_ROOT"] = str(PROJECT_ROOT)
os.environ["OMNIA_PORTABLE_MODE"] = "1"


def main():
    """FastAPI 启动入口"""
    import uvicorn
    
    parser = argparse.ArgumentParser(description="Omnia AIOS - FastAPI Version")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    parser.add_argument("--port", type=int, default=8765, help="Port number")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    print("=" * 60)
    print("  Omnia AIOS v2.0.0 (FastAPI)")
    print("=" * 60)
    print(f"  Starting server on {args.host}:{args.port}")
    print(f"  Project root: {PROJECT_ROOT}")
    print(f"  Debug mode: {args.debug}")
    print("=" * 60)
    print()
    
    # 导入 FastAPI 应用
    from src.omnia.main import app
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="debug" if args.debug else "info"
    )


if __name__ == "__main__":
    main()
