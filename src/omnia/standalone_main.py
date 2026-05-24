import os
import sys
import uvicorn
import threading
import webbrowser
import time
import socket
from pathlib import Path

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except OSError:
            return True

def main():
    # Determine the base path (next to the executable)
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_path = Path(sys.executable).parent
    else:
        # Running in a normal Python environment
        base_path = Path(__file__).parent

    # --- 关键修复：设置环境变量，供子模块(config.py)使用 ---
    os.environ["OMNIA_ROOT"] = str(base_path)
    
    # --- 关键修复：设置 sys.path，确保 import 语句能工作 ---
    current_path_str = str(base_path)
    if current_path_str not in sys.path:
        sys.path.insert(0, current_path_str)

    # Now it is safe to import the FastAPI app
    try:
        # This 'import app' will trigger the loading of config.py and routers
        from src.omnia.main import app 
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("按回车键退出...")
        return

    port = 8765
    host = "0.0.0.0"

    print(f"\n🚀 Omnia Personal OS is running!")
    print(f"👉 Open in browser: http://127.0.0.1:{port}")
    print("   Press Ctrl+C to stop the server.\n")

    def open_browser():
        time.sleep(2)
        if not is_port_in_use(port):
             webbrowser.open(f"http://127.0.0.1:{port}/license")

    # Open browser automatically
    try:
        if os.environ.get("DISPLAY") or sys.platform == "win32" or sys.platform == "darwin":
            threading.Thread(target=open_browser, daemon=True).start()
    except:
        pass

    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")

if __name__ == "__main__":
    main()
