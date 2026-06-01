#!/usr/bin/env python3
"""
Omnia 代码保护脚本
==================
使用 PyArmor 对 Python 源码进行字节码加密保护
使用 javascript-obfuscator 对前端 JS 进行混淆

用法:
    python protect_code.py [--pyarmor] [--js-obfuscate] [--all]
"""

import os
import sys
import json
import shutil
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
SRC_DIR = ROOT / "src" / "omnia"
WEB_DIR = ROOT / "web"
BUILD_DIR = ROOT / "build" / "protected"

# 需要保护的 Python 模块
PY_MODULES = [
    "src/omnia/license.py",
    "src/omnia/main.py",
    "src/omnia/config.py",
    "src/omnia/auth_middleware.py",
    "src/omnia/routers/license.py",
    "src/omnia/routers/chat.py",
    "src/omnia/routers/brain.py",
    "src/omnia/routers/memory.py",
    "src/omnia/routers/neural_graph.py",
    "src/omnia/routers/auto_evolution.py",
    "src/omnia/routers/backup.py",
    "src/omnia/routers/health.py",
    "src/omnia/services/llm_client.py",
    "src/omnia/services/memory_service.py",
    "src/omnia/services/neural_graph_service.py",
    "src/omnia/services/auto_evolution_service.py",
    "src/omnia/services/recall_service.py",
    "backend/standalone_main.py",
]

# 需要混淆的前端 JS
JS_FILES = [
    "web/app.js",
]


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def pyarmor_obfuscate():
    """使用 PyArmor 混淆 Python 源码"""
    print("\n" + "=" * 60)
    print("🛡️  PyArmor 代码保护")
    print("=" * 60)

    # 检查 PyArmor 是否安装
    try:
        result = subprocess.run(
            ["pyarmor", "--version"],
            capture_output=True, text=True, timeout=10
        )
        print(f"  PyArmor 版本: {result.stdout.strip()}")
    except FileNotFoundError:
        print("  ❌ PyArmor 未安装，尝试安装...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyarmor"],
            capture_output=True
        )
        print("  ✅ PyArmor 安装完成")

    output_dir = BUILD_DIR / "pyarmor"
    ensure_dir(output_dir)

    # 逐个混淆关键模块
    protected_files = []
    for mod in PY_MODULES:
        mod_path = ROOT / mod
        if not mod_path.exists():
            print(f"  ⏭️  跳过（不存在）: {mod}")
            continue

        # 创建目标目录
        rel_dir = Path(mod).parent
        target_dir = output_dir / rel_dir
        ensure_dir(target_dir)

        try:
            # 使用 PyArmor 混淆单个文件
            # pyarmor gen -O output_dir -i src_file
            result = subprocess.run(
                [
                    "pyarmor", "gen",
                    "-O", str(target_dir),
                    "--exact",
                    "--no-runtime",
                    "--enable-suffix",
                    str(mod_path),
                ],
                capture_output=True, text=True, timeout=60,
                cwd=str(ROOT)
            )

            if result.returncode == 0:
                protected_files.append(mod)
                print(f"  ✅ {mod}")
            else:
                print(f"  ⚠️  {mod} - {result.stderr[:100]}")

        except subprocess.TimeoutExpired:
            print(f"  ⏰ {mod} - 超时")
        except Exception as e:
            print(f"  ❌ {mod} - {e}")

    # 生成保护清单
    manifest = {
        "version": "1.0",
        "protected_at": datetime.now().isoformat(),
        "files": protected_files,
        "count": len(protected_files),
    }

    manifest_path = BUILD_DIR / "protection_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    print(f"\n  📦 保护了 {len(protected_files)}/{len(PY_MODULES)} 个文件")
    print(f"  📋 清单: {manifest_path}")

    return protected_files


def js_obfuscate():
    """混淆前端 JavaScript"""
    print("\n" + "=" * 60)
    print("🛡️  JavaScript 代码混淆")
    print("=" * 60)

    # 检查 javascript-obfuscator 是否安装
    try:
        result = subprocess.run(
            ["javascript-obfuscator", "--version"],
            capture_output=True, text=True, timeout=10
        )
        print(f"  javascript-obfuscator 版本: {result.stdout.strip()}")
    except FileNotFoundError:
        print("  ❌ javascript-obfuscator 未安装，尝试全局安装...")
        subprocess.run(
            ["npm", "install", "-g", "javascript-obfuscator"],
            capture_output=True
        )
        print("  ✅ 安装完成")

    output_dir = BUILD_DIR / "web"
    ensure_dir(output_dir)

    for js_file in JS_FILES:
        js_path = ROOT / js_file
        if not js_path.exists():
            print(f"  ⏭️  跳过（不存在）: {js_file}")
            continue

        output_path = output_dir / Path(js_file).name

        try:
            result = subprocess.run(
                [
                    "javascript-obfuscator",
                    str(js_path),
                    "--output", str(output_path),
                    "--compact", "true",
                    "--control-flow-flattening", "true",
                    "--control-flow-flattening-threshold", "0.5",
                    "--dead-code-injection", "true",
                    "--dead-code-injection-threshold", "0.2",
                    "--string-array", "true",
                    "--string-array-encoding", "base64",
                    "--string-array-threshold", "0.75",
                    "--rename-globals", "false",
                    "--self-defending", "false",
                    "--target", "browser",
                ],
                capture_output=True, text=True, timeout=120
            )

            if result.returncode == 0:
                orig_size = js_path.stat().st_size
                new_size = output_path.stat().st_size
                print(f"  ✅ {js_file} ({orig_size//1024}KB → {new_size//1024}KB)")
            else:
                print(f"  ⚠️  {js_file} - {result.stderr[:100]}")

        except subprocess.TimeoutExpired:
            print(f"  ⏰ {js_file} - 超时")
        except Exception as e:
            print(f"  ❌ {js_file} - {e}")


def generate_integrity_signatures():
    """生成完整性校验签名"""
    print("\n" + "=" * 60)
    print("🔐 生成完整性校验签名")
    print("=" * 60)

    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "src" / "omnia" / "integrity.py"), "sign"],
            capture_output=True, text=True, timeout=10,
            cwd=str(ROOT)
        )
        if result.returncode == 0:
            print(f"  ✅ {result.stdout.strip()}")
        else:
            print(f"  ⚠️  {result.stderr.strip()}")
    except Exception as e:
        print(f"  ❌ {e}")


def create_build_info():
    """创建构建信息"""
    build_info = {
        "build_time": datetime.now().isoformat(),
        "git_hash": "",
        "version": "",
    }

    # 获取 Git 信息
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=str(ROOT)
        )
        if result.returncode == 0:
            build_info["git_hash"] = result.stdout.strip()
    except Exception:
        pass

    # 获取版本号
    version_file = ROOT / "VERSION"
    if version_file.exists():
        build_info["version"] = version_file.read_text().strip()

    # 写入构建信息
    build_info_path = BUILD_DIR / "build_info.json"
    ensure_dir(BUILD_DIR)
    build_info_path.write_text(json.dumps(build_info, indent=2, ensure_ascii=False))

    print(f"\n📋 构建信息:")
    print(f"  版本: {build_info['version']}")
    print(f"  Git:  {build_info['git_hash']}")
    print(f"  时间: {build_info['build_time']}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Omnia 代码保护工具")
    parser.add_argument("--pyarmor", action="store_true", help="混淆 Python 代码")
    parser.add_argument("--js-obfuscate", action="store_true", help="混淆 JavaScript")
    parser.add_argument("--sign", action="store_true", help="生成完整性签名")
    parser.add_argument("--all", action="store_true", help="全部执行")
    args = parser.parse_args()

    if not any([args.pyarmor, args.js_obfuscate, args.sign, args.all]):
        # 默认全部执行
        args.all = True

    print("\n🛡️  Omnia 代码保护")
    print("=" * 60)
    print(f"  项目根目录: {ROOT}")
    print(f"  输出目录:   {BUILD_DIR}")
    print("=" * 60)

    if args.pyarmor or args.all:
        pyarmor_obfuscate()

    if args.js_obfuscate or args.all:
        js_obfuscate()

    if args.sign or args.all:
        generate_integrity_signatures()

    create_build_info()

    print("\n" + "=" * 60)
    print("✅ 代码保护完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
