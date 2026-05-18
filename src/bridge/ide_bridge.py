#!/usr/bin/env python3
"""
IDE Bridge Service - 桥接IDE/编辑器与Omnia

支持：
1. VSCode扩展推送上下文
2. 终端工作目录检测
3. Git仓库状态

使用方式：
- 作为独立服务运行：python ide_bridge.py
- 或通过API调用：POST /api/ide/context
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.core.config import OMNIA_HOME

IDE_CONTEXT_FILE = OMNIA_HOME / "ide_context.json"
WORKSPACE_ROOT = PROJECT_ROOT.parent


def detect_git_context(workspace: Path) -> dict:
    """检测Git仓库状态"""
    result = {
        "branch": None,
        "uncommitted": 0,
        "recent_commits": [],
    }
    
    try:
        # 获取当前分支
        branch_res = subprocess.run(
            ["git", "-C", str(workspace), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        if branch_res.returncode == 0:
            result["branch"] = branch_res.stdout.strip()
        
        # 获取未提交文件数
        status_res = subprocess.run(
            ["git", "-C", str(workspace), "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        )
        if status_res.returncode == 0:
            result["uncommitted"] = len([l for l in status_res.stdout.strip().split('\n') if l])
        
        # 获取最近提交
        log_res = subprocess.run(
            ["git", "-C", str(workspace), "log", "-3", "--oneline"],
            capture_output=True, text=True, timeout=5
        )
        if log_res.returncode == 0:
            result["recent_commits"] = log_res.stdout.strip().split('\n')[:3]
            
    except Exception as e:
        print(f"[IDE Bridge] Git detection failed: {e}")
    
    return result


def detect_terminal_context() -> dict:
    """检测终端工作目录"""
    result = {
        "cwd": None,
        "shell": None,
    }
    
    try:
        result["cwd"] = os.getcwd()
        result["shell"] = os.environ.get("SHELL", "unknown")
    except Exception:
        pass
    
    return result


def update_ide_context(
    file: Optional[str] = None,
    line: Optional[int] = None,
    column: Optional[int] = None,
    language: Optional[str] = None,
    workspace: Optional[str] = None,
    source: str = "terminal"
) -> dict:
    """更新IDE上下文"""
    
    ws_path = Path(workspace) if workspace else WORKSPACE_ROOT
    
    context = {
        "file": file,
        "line": line,
        "column": column,
        "language": language,
        "workspace": str(ws_path),
        "source": source,  # terminal, vscode, vim, etc.
        "timestamp": datetime.now().isoformat(),
    }
    
    # 添加Git信息
    git_ctx = detect_git_context(ws_path)
    context["git"] = git_ctx
    
    # 添加终端信息
    term_ctx = detect_terminal_context()
    context["terminal"] = term_ctx
    
    # 保存到文件
    IDE_CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
    IDE_CONTEXT_FILE.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"[IDE Bridge] Updated context: {file or 'no file'} @ {source}")
    return context


def clear_ide_context():
    """清除IDE上下文"""
    if IDE_CONTEXT_FILE.exists():
        IDE_CONTEXT_FILE.unlink()
        print("[IDE Bridge] Context cleared")


def get_ide_context() -> Optional[dict]:
    """获取当前IDE上下文"""
    if IDE_CONTEXT_FILE.exists():
        try:
            return json.loads(IDE_CONTEXT_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return None


def watch_mode(interval: int = 5):
    """监控模式 - 定期更新终端上下文"""
    print(f"[IDE Bridge] Watch mode started (interval={interval}s)")
    print(f"[IDE Bridge] Workspace: {WORKSPACE_ROOT}")
    print("[IDE Bridge] Press Ctrl+C to stop")
    
    try:
        while True:
            # 定期更新Git和终端信息
            git_ctx = detect_git_context(WORKSPACE_ROOT)
            term_ctx = detect_terminal_context()
            
            # 读取现有上下文（如果有）
            existing = get_ide_context() or {}
            
            # 更新非IDE字段
            existing.update({
                "git": git_ctx,
                "terminal": term_ctx,
                "timestamp": datetime.now().isoformat(),
                "source": existing.get("source", "terminal"),
                "workspace": str(WORKSPACE_ROOT),
            })
            
            # 如果没有文件信息，显示工作目录
            if not existing.get("file"):
                existing["file"] = None
                existing["status"] = "terminal_mode"
            
            IDE_CONTEXT_FILE.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
            
            # 打印状态
            branch = git_ctx.get("branch", "?")
            uncommitted = git_ctx.get("uncommitted", 0)
            print(f"\r[IDE Bridge] {branch} | {uncommitted} changes | {term_ctx.get('cwd', '?')[-30:]}", end="", flush=True)
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n[IDE Bridge] Watch mode stopped")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Omnia IDE Bridge")
    parser.add_argument("--watch", "-w", action="store_true", help="启动监控模式")
    parser.add_argument("--interval", "-i", type=int, default=5, help="监控间隔（秒）")
    parser.add_argument("--file", "-f", type=str, help="当前文件")
    parser.add_argument("--line", "-l", type=int, help="当前行号")
    parser.add_argument("--clear", "-c", action="store_true", help="清除上下文")
    parser.add_argument("--show", "-s", action="store_true", help="显示当前上下文")
    
    args = parser.parse_args()
    
    if args.clear:
        clear_ide_context()
        return
    
    if args.show:
        ctx = get_ide_context()
        if ctx:
            print(json.dumps(ctx, ensure_ascii=False, indent=2))
        else:
            print("No IDE context")
        return
    
    if args.watch:
        watch_mode(args.interval)
        return
    
    if args.file:
        update_ide_context(file=args.file, line=args.line)
        print(f"Updated: {args.file}")
        return
    
    # 默认：显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()
