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


def is_packed():
    """
    检测是否在打包模式下运行。
    Nuitka: __compiled__ 属性存在
    PyInstaller: sys.frozen 属性存在
    """
    return hasattr(sys, 'frozen') or hasattr(sys, '__compiled__')


def setup_module_aliases():
    """
    Nuitka 打包后模块路径是 src.core.*，但代码里用 core.* 导入。
    创建导入钩子，让 core.xxx 自动映射到 src.core.xxx。
    """
    import importlib

    original_import = __builtins__['__import__']

    def aliased_import(name, globals=None, locals=None, fromlist=(), level=0):
        # 拦截 core.xxx 的导入，重定向到 src.core.xxx
        if name == 'core' or name.startswith('core.'):
            src_name = 'src.' + name
            try:
                # 如果 src.core.xxx 还没加载，先加载它
                if src_name not in sys.modules:
                    original_import(src_name, globals, locals, fromlist, level)
                # 创建 core.xxx 的别名指向 src.core.xxx
                if src_name in sys.modules:
                    sys.modules[name] = sys.modules[src_name]
                    return sys.modules[src_name]
            except ImportError:
                pass  # src.core.xxx 也不存在，回退到原始导入
        return original_import(name, globals, locals, fromlist, level)

    __builtins__['__import__'] = aliased_import

    # 预加载 src.core 并创建 core 别名
    try:
        src_core = importlib.import_module('src.core')
        sys.modules['core'] = src_core
    except ImportError:
        pass


def setup_paths():
    """
    设置路径和环境变量，确保打包后能正确导入模块。

    Nuitka --onefile 模式下：
    - sys.executable 指向 exe 文件
    - __file__ 指向临时解压目录中的 .py 文件
    - 数据文件 (--include-data-dir) 解压到 sys.executable 同级目录
    """
    if is_packed():
        # 打包模式：base_path 是 exe 所在目录
        base_path = Path(sys.executable).parent

        # Nuitka --onefile 会把模块解压到临时目录
        # __file__ 的父目录就是 src/omnia/，再往上两级是临时根目录
        temp_root = Path(__file__).parent.parent.parent

        # 把临时目录和 src 子目录加入 sys.path（这样 import src.xxx 能找到）
        paths_to_add = [
            str(base_path),           # exe 所在目录
            str(temp_root),           # 临时解压根目录
            str(temp_root / "src"),   # 临时解压的 src 目录
            str(Path(__file__).parent.parent),  # src/ 目录
        ]
        for p in paths_to_add:
            if p not in sys.path:
                sys.path.insert(0, p)

        # 创建 core -> src.core 的模块别名
        setup_module_aliases()

        # 设置环境变量供 config.py 使用
        # OMNIA_ROOT 必须指向 exe 所在目录（数据文件在这里）
        os.environ["OMNIA_ROOT"] = str(base_path)

        print(f"[Omnia] 打包模式")
        print(f"  ├─ 可执行文件: {sys.executable}")
        print(f"  ├─ 工作目录 (exe 所在): {base_path}")
        print(f"  └─ 临时解压目录: {temp_root}")
    else:
        # 开发模式：项目根目录是 src/omnia 的父级
        project_root = Path(__file__).parent.parent.parent
        src_path = str(project_root / "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        os.environ["OMNIA_ROOT"] = str(project_root)

        print(f"[Omnia] 开发模式 - 项目根目录: {project_root}")


def main():
    # 1. 设置路径和模块别名
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
