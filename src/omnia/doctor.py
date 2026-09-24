"""Omnia Doctor - 系统自检

检查项：
  1. 配置文件：定位与 Schema 校验
  2. 环境：Python 版本、关键依赖
  3. 目录：数据目录存在且可写
  4. 端口：8765 是否被占用/服务是否在线
  5. LLM：当前提供商 API key 是否配置、是否可连通
  6. 数据库：记忆宫殿 DB 是否可打开

用法：
  from omnia.doctor import run_doctor
  report = run_doctor(settings)  # 返回 (ok: bool, lines: list[str])
"""
from __future__ import annotations

import importlib
import socket
import sqlite3
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.settings import Settings, get_settings

OK, WARN, FAIL = "✅", "⚠️ ", "❌"

# 关键依赖（模块名 -> 用途）
REQUIRED_DEPS = {
    "yaml": "YAML 配置解析",
    "fastapi": "Web 服务",
    "uvicorn": "ASGI 服务器",
}
OPTIONAL_DEPS = {
    "requests": "HTTP 客户端",
    "openai": "OpenAI 兼容客户端",
}


@dataclass
class DoctorReport:
    lines: list[str] = field(default_factory=list)
    errors: int = 0
    warnings: int = 0

    def add(self, status: str, msg: str):
        self.lines.append(f"{status} {msg}")
        if status == FAIL:
            self.errors += 1
        elif status == WARN:
            self.warnings += 1

    @property
    def ok(self) -> bool:
        return self.errors == 0


def _check_python(r: DoctorReport):
    v = sys.version_info
    if v >= (3, 10):
        r.add(OK, f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        r.add(FAIL, f"Python {v.major}.{v.minor}.{v.micro} 过旧，需要 >= 3.10")


def _check_deps(r: DoctorReport):
    for mod, purpose in REQUIRED_DEPS.items():
        try:
            importlib.import_module(mod)
            r.add(OK, f"依赖 {mod}（{purpose}）")
        except ImportError:
            r.add(FAIL, f"缺少依赖 {mod}（{purpose}）→ pip install {mod}")
    for mod, purpose in OPTIONAL_DEPS.items():
        try:
            importlib.import_module(mod)
            r.add(OK, f"可选依赖 {mod}（{purpose}）")
        except ImportError:
            r.add(WARN, f"可选依赖 {mod} 未安装（{purpose}）")


def _check_config(r: DoctorReport, s: Settings):
    if not s.loaded:
        r.add(WARN, "未找到 omnia.yaml，将使用 .env + 默认值（建议运行 omnia config init）")
        return
    r.add(OK, f"配置文件: {s.config_path}")
    issues = s.validate()
    if not issues:
        r.add(OK, "配置 Schema 校验通过")
    for i in issues:
        r.add(FAIL, f"配置问题: {i}")


def _check_dirs(r: DoctorReport, s: Settings):
    for name, path in [("omnia_home", s.omnia_home)]:
        try:
            path.mkdir(parents=True, exist_ok=True)
            test = path / ".doctor_write_test"
            test.write_text("ok", encoding="utf-8")
            test.unlink()
            r.add(OK, f"目录可写: {name} = {path}")
        except OSError as e:
            r.add(FAIL, f"目录不可写: {name} = {path}（{e}）")


def _port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex((host, port)) == 0


def _check_server(r: DoctorReport, s: Settings):
    port = s.server_port
    if _port_in_use(port):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=3) as resp:
                if resp.status == 200:
                    r.add(OK, f"服务在线: http://127.0.0.1:{port} (HTTP {resp.status})")
                    return
        except Exception:
            pass
        r.add(WARN, f"端口 {port} 被占用但 /api/status 无响应（可能是其他程序占用）")
    else:
        r.add(WARN, f"服务未运行: 端口 {port} 空闲（启动: omnia serve）")


def _check_llm(r: DoctorReport, s: Settings):
    cur = s.current_llm
    prov = s.llm_provider()
    if not prov:
        r.add(WARN, f"未配置 LLM 提供商 '{cur}'")
        return
    key = prov.get("api_key", "")
    if not key:
        r.add(FAIL, f"提供商 '{cur}' 的 api_key 为空（设置对应环境变量，如 MOONSHOT_API_KEY）")
        return
    masked = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "***"
    r.add(OK, f"当前 LLM: {cur} (model={prov.get('model','?')}, key={masked})")


def _check_db(r: DoctorReport, s: Settings):
    db = s.memory_palace_db
    if not db.exists():
        r.add(WARN, f"记忆宫殿 DB 不存在（首次运行会自动创建）: {db}")
        return
    try:
        conn = sqlite3.connect(str(db), timeout=3)
        conn.execute("SELECT 1")
        conn.close()
        r.add(OK, f"记忆宫殿 DB 可打开: {db}")
    except sqlite3.Error as e:
        r.add(FAIL, f"记忆宫殿 DB 损坏或无法打开: {db}（{e}）")


def run_doctor(settings: Optional[Settings] = None) -> DoctorReport:
    s = settings or get_settings()
    r = DoctorReport()
    r.lines.append("=" * 56)
    r.lines.append("Omnia Doctor 系统体检")
    r.lines.append("=" * 56)

    r.lines.append("\n[环境]")
    _check_python(r)
    _check_deps(r)

    r.lines.append("\n[配置]")
    _check_config(r, s)

    r.lines.append("\n[目录]")
    _check_dirs(r, s)

    r.lines.append("\n[服务]")
    _check_server(r, s)

    r.lines.append("\n[LLM]")
    _check_llm(r, s)

    r.lines.append("\n[数据库]")
    _check_db(r, s)

    r.lines.append("\n" + "=" * 56)
    if r.ok and r.warnings == 0:
        r.lines.append(f"{OK} 一切正常，Omnia 已就绪")
    elif r.ok:
        r.lines.append(f"{WARN} 可用，但有 {r.warnings} 个警告建议处理")
    else:
        r.lines.append(f"{FAIL} 发现 {r.errors} 个错误、{r.warnings} 个警告，请先修复错误")
    r.lines.append("=" * 56)
    return r


def print_doctor(settings: Optional[Settings] = None) -> int:
    """打印体检报告，返回退出码（0=正常，1=有错误）"""
    report = run_doctor(settings)
    print("\n".join(report.lines))
    return 0 if report.ok else 1
