#!/usr/bin/env python3
"""
OpenMythos 快速启动脚本

一键启动所有服务
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def main():
    print("=" * 60)
    print("OpenMythos 快速启动")
    print("=" * 60)
    
    print("\n1️⃣  运行集成测试...")
    import subprocess
    result = subprocess.run(
        ["python3", "tests/test_openmythos_integration.py"],
        cwd=PROJECT_ROOT
    )
    
    if result.returncode != 0:
        print("❌ 集成测试失败")
        return
    
    print("\n2️⃣  运行性能测试...")
    result = subprocess.run(
        ["python3", "tests/test_openmythos_performance.py"],
        cwd=PROJECT_ROOT
    )
    
    print("\n3️⃣  运行记忆压缩...")
    result = subprocess.run(
        ["python3", "scripts/memory_auto_compression.py"],
        cwd=PROJECT_ROOT
    )
    
    print("\n" + "=" * 60)
    print("✅ 所有任务完成！")
    print("=" * 60)
    
    print("\n下一步:")
    print("  启动 Web Server: python3 src/omnia/web_server.py")
    print("  测试 Web API: python3 test_openmythos_web.py")


if __name__ == "__main__":
    main()
