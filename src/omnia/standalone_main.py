"""
Omnia Standalone Entry Point (FastAPI Version)
用于 Nuitka 打包后的独立启动
"""
import os
import sys
import socket
import time
import webbrowser
import threading
from pathlib import Path


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except OSError:
            return True


def setup_paths():
    """
    设置路径和环境变量，确保打包后能正确导入模块。
    
    Nuitka --onefile 模式下：
    - sys.executable 指向 exe 文件
    - __file__ 指向临时解压目录中的文件
    - 需要将 src 目录加入 sys.path
    """
    if getattr(sys, 'frozen', False):
        # 打包模式：base_path 是 exe 所在目录
        base_path = Path(sys.executable).parent
        # Nuitka --standalone --onefile 会解压到临时目录
        # __file__ 的父目录就是 src/omnia/，再往上两级是项目根
        temp_root = Path(__file__).parent.parent.parent
        
        # 将两个路径都加入 sys.path
        for p in [str(base_path), str(temp_root), str(temp_root / "src")]:
            if p not in sys.path:
                sys.path.insert(0, p)
        
        # 设置环境变量供 config.py 使用
        os.environ["OMNIA_ROOT"] = str(base_path)
        
        print(f"[Omnia] 打包模式 - 可执行文件目录: {base_path}")
        print(f"[Omnia] 临时解压目录: {temp_root}")
    else:
        # 开发模式：项目根目录是 src/omnia 的父级
        project_root = Path(__file__).parent.parent.parent
        src_path = str(project_root / "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        os.environ["OMNIA_ROOT"] = str(project_root)
        
        print(f"[Omnia] 开发模式 - 项目根目录: {project_root}")


def main():
    # 1. 设置路径
    setup_paths()
    
    # 2. 延迟导入 FastAPI app（路径设置后才能导入）
    try:
        from src.omnia.main import app
        print("[Omnia] FastAPI app 加载成功！")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")
        return

    # 3. 启动配置
    port = 8765
    host = "0.0.0.0"

    print(f"\n🚀 Omnia Personal OS is running!")
    print(f"👉 Open in browser: http://127.0.0.1:{port}")
    print(f"👉 License page: http://127.0.0.1:{port}/license")
    print("   Press Ctrl+C to stop the server.\n")

    # 4. 自动打开浏览器
    def open_browser():
        time.sleep(3)
        if not is_port_in_use(port):
            webbrowser.open(f"http://127.0.0.1:{port}/license")

    try:
        if os.environ.get("DISPLAY") or sys.platform in ("win32", "darwin"):
            threading.Thread(target=open_browser, daemon=True).start()
    except:
        pass

    # 5. 启动 uvicorn
    import uvicorn
    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")


if __name__ == "__main__":
    main()
