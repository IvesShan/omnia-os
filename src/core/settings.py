"""Omnia 统一配置加载器

读取优先级（高 → 低）：
  1. omnia.yaml（由 --config 或 OMNIA_CONFIG 指定，默认查找 ~/.omnia/omnia.yaml 与项目根 omnia.yaml）
  2. .env 环境变量
  3. 内置默认值

支持模板变量插值：
  ${env.VAR}        -> 读取环境变量 VAR
  ${paths.omnia_home} -> 引用配置内 paths.omnia_home 的值
  ~                 -> 展开为用户主目录

设计原则：不破坏现有代码。本模块只提供读取入口，不改变任何现有常量。
现有 src/core/config.py 的路径常量保持不变；本模块是其超集，新增密钥/端口/模型等配置。
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Optional

import yaml

# 默认配置文件名
DEFAULT_CONFIG_NAME = "omnia.yaml"

# 插值语法
_ENV_PATTERN = re.compile(r"\$\{env\.([A-Za-z_][A-Za-z0-9_]*)\}")
_PATH_PATTERN = re.compile(r"\$\{paths\.([A-Za-z_][A-Za-z0-9_.]*)\}")


class ConfigError(Exception):
    """配置错误（缺失、格式非法、校验失败）"""


def _deep_get(data: dict, dotted: str) -> Any:
    """按 a.b.c 路径取嵌套字典值，不存在返回 None"""
    cur: Any = data
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _expand(value: Any, raw_config: dict) -> Any:
    """递归展开字符串中的插值变量与 ~ 路径"""
    if isinstance(value, dict):
        return {k: _expand(v, raw_config) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v, raw_config) for v in value]
    if not isinstance(value, str):
        return value

    # ${env.X}：环境变量，缺省为空字符串
    def _env_sub(m: re.Match) -> str:
        return os.environ.get(m.group(1), "")

    out = _ENV_PATTERN.sub(_env_sub, value)

    # ${paths.x}：引用配置内 paths 段的值（已部分展开）
    def _path_sub(m: re.Match) -> str:
        ref = _deep_get(raw_config, f"paths.{m.group(1)}")
        if ref is None:
            return ""
        return str(_expand(ref, raw_config))

    out = _PATH_PATTERN.sub(_path_sub, out)

    # ~ 展开
    if out.startswith("~"):
        out = str(Path(out).expanduser())
    return out


def find_config_file(explicit: Optional[str] = None) -> Optional[Path]:
    """按优先级定位 omnia.yaml"""
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    env_cfg = os.environ.get("OMNIA_CONFIG")
    if env_cfg:
        candidates.append(Path(env_cfg))
    candidates.append(Path.home() / ".omnia" / DEFAULT_CONFIG_NAME)
    candidates.append(Path.cwd() / DEFAULT_CONFIG_NAME)

    for c in candidates:
        c = c.expanduser()
        if c.is_file():
            return c
    return None


class Settings:
    """Omnia 运行时配置（只读，懒加载）"""

    def __init__(self, config_path: Optional[str] = None):
        self._config_path = find_config_file(config_path)
        self._raw: dict = {}
        self._expanded: Optional[dict] = None
        if self._config_path:
            try:
                self._raw = yaml.safe_load(self._config_path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as e:
                raise ConfigError(f"配置文件 {self._config_path} YAML 格式错误: {e}") from e
            except OSError as e:
                raise ConfigError(f"无法读取配置文件 {self._config_path}: {e}") from e

    # ---- 基础信息 ----
    @property
    def config_path(self) -> Optional[Path]:
        return self._config_path

    @property
    def loaded(self) -> bool:
        return self._config_path is not None

    def _cfg(self) -> dict:
        if self._expanded is None:
            self._expanded = _expand(self._raw, self._raw)
        return self._expanded

    def get(self, dotted: str, default: Any = None) -> Any:
        """通用读取：settings.get('server.port', 8765)"""
        v = _deep_get(self._cfg(), dotted)
        return default if v is None else v

    # ---- 常用快捷属性 ----
    @property
    def omnia_home(self) -> Path:
        return Path(self.get("paths.omnia_home", str(Path.home() / ".omnia")))

    @property
    def memory_palace_db(self) -> Path:
        return Path(self.get("paths.memory_palace_db", str(self.omnia_home / "memory_palace.db")))

    @property
    def server_host(self) -> str:
        return self.get("server.host", "0.0.0.0")

    @property
    def server_port(self) -> int:
        try:
            return int(self.get("server.port", 8765))
        except (TypeError, ValueError):
            return 8765

    @property
    def current_llm(self) -> str:
        return self.get("llm.current", "kimi")

    def llm_provider(self, name: Optional[str] = None) -> dict:
        name = name or self.current_llm
        return self.get(f"llm.providers.{name}", {}) or {}

    def api_key(self, provider: Optional[str] = None) -> str:
        return str(self.llm_provider(provider).get("api_key", ""))

    # ---- 校验 ----
    def validate(self) -> list[str]:
        """返回问题列表（空列表 = 通过）。不抛异常，便于 doctor 汇总。"""
        issues: list[str] = []
        if not self.loaded:
            issues.append("未找到 omnia.yaml（查找了 --config / OMNIA_CONFIG / ~/.omnia / 当前目录）")
            return issues

        port = self.get("server.port")
        if not isinstance(port, int) or not (1 <= port <= 65535):
            issues.append(f"server.port 非法: {port!r}（应为 1-65535 的整数）")

        cur = self.get("llm.current")
        if cur and not _deep_get(self._cfg(), f"llm.providers.{cur}"):
            issues.append(f"llm.current 指向的提供商 '{cur}' 未在 llm.providers 中定义")

        prov = self.llm_provider()
        if prov.get("enabled") and not prov.get("api_key"):
            issues.append(f"当前提供商 '{self.current_llm}' 已启用但 api_key 为空（检查对应环境变量）")

        for key in ("paths.omnia_home",):
            if not self.get(key):
                issues.append(f"{key} 为空")
        return issues


# 全局单例（与现有代码兼容：允许 from core.settings import settings）
_default: Optional[Settings] = None


def get_settings(config_path: Optional[str] = None) -> Settings:
    global _default
    if _default is None or config_path is not None:
        _default = Settings(config_path)
    return _default
