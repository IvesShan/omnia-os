"""Omnia CLI entry point（pip 安装与开发模式双兼容）.

设计原则：
- 开发模式（git clone）：检测到 src/ 在仓库内 → 加入 sys.path，行为和原 __main__.py 一致
- pip 安装模式：包已通过 setuptools 安装到 site-packages，无需修改 sys.path
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _bootstrap_project_root() -> Path:
    """定位项目根目录并准备 sys.path。

    返回项目根（开发模式下是仓库根目录；pip 安装后是包的上一级）。
    """
    this_file = Path(__file__).resolve()
    # 开发模式：__file__ = <repo>/src/omnia/cli.py → 根是 <repo>
    candidate = this_file.parent.parent.parent
    if (candidate / "src" / "omnia").is_dir() and (candidate / "src" / "core").is_dir():
        # 开发模式：把 src 加进 sys.path，让 `from core.xxx` / `from src.core.xxx` 都能工作
        src_path = candidate / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        if str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
        return candidate
    # pip 安装模式：site-packages 已经在 sys.path，不需要调整
    return this_file.parent.parent.parent


PROJECT_ROOT = _bootstrap_project_root()


def _load_dotenv():
    """轻量加载 .env 到环境变量（不覆盖已存在的变量）。

    优先从 ~/.omnia/.env 加载（pip 安装场景），其次从项目根 .env 加载（开发场景）。
    """
    candidates = [
        Path.home() / ".omnia" / ".env",
        PROJECT_ROOT / ".env",
    ]
    for env_file in candidates:
        if not env_file.is_file():
            continue
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
        except OSError:
            pass


_load_dotenv()


def main():
    """延迟导入主逻辑，确保 sys.path 已经准备好。"""
    # 复用 __main__.py 的 main 实现，避免逻辑分裂
    from omnia import __main__ as _impl
    _impl.main()


if __name__ == "__main__":
    main()
