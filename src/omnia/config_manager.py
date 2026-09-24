"""
Omnia 统一配置管理器
支持 YAML 配置 + 环境变量插值 + 配置校验 + 迁移
"""

import os
import re
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field


class ConfigValidationError(Exception):
    """配置校验错误"""
    pass


class ConfigMigrationError(Exception):
    """配置迁移错误"""
    pass


@dataclass
class ValidationResult:
    """校验结果"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class OmniaConfig:
    """Omnia 统一配置管理器"""

    # 配置版本，用于迁移
    CONFIG_VERSION = "1.0"

    # 必需的顶级字段
    REQUIRED_SECTIONS = ["version", "paths", "server", "llm"]

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self._find_config()
        self._config: Dict[str, Any] = {}
        self._env_cache: Dict[str, str] = {}
        self._load()

    def _find_config(self) -> Path:
        """查找配置文件"""
        candidates = [
            Path("./omnia.yaml"),
            Path("./omnia.yml"),
            Path.home() / ".omnia" / "omnia.yaml",
            Path.home() / ".config" / "omnia" / "config.yaml",
        ]
        for path in candidates:
            if path.exists():
                return path
        # 默认返回项目根目录的 omnia.yaml
        return Path("./omnia.yaml")

    def _load(self):
        """加载并解析配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            raw = f.read()

        # 环境变量插值
        interpolated = self._interpolate_env(raw)

        try:
            self._config = yaml.safe_load(interpolated)
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"YAML 解析失败: {e}")

        # 展开路径中的 ~
        self._expand_paths()

    def _interpolate_env(self, text: str) -> str:
        """环境变量插值，支持 ${env.VAR} 和 ${env.VAR:default} 语法"""
        pattern = r'\$\{env\.([A-Z_][A-Z0-9_]*)(?::([^}]*))?\}'

        def replace(match):
            var_name = match.group(1)
            default = match.group(2) or ""
            value = os.environ.get(var_name, default)
            if not value and not default:
                # 记录警告但不中断
                pass
            return value

        return re.sub(pattern, replace, text)

    def _expand_paths(self):
        """展开所有路径中的 ~ 和环境变量"""
        def expand_value(value):
            if isinstance(value, str):
                # 展开 ~
                if value.startswith("~"):
                    return str(Path(value).expanduser())
                # 展开 ${paths.xxx} 引用
                if "${paths." in value:
                    return self._resolve_path_reference(value)
            elif isinstance(value, dict):
                return {k: expand_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [expand_value(item) for item in value]
            return value

        self._config = expand_value(self._config)

    def _resolve_path_reference(self, value: str) -> str:
        """解析 ${paths.xxx} 引用"""
        pattern = r'\$\{paths\.([a-z_][a-z0-9_]*)\}'

        def replace(match):
            path_key = match.group(1)
            paths = self._config.get("paths", {})
            ref_value = paths.get(path_key, "")
            if isinstance(ref_value, str):
                return str(Path(ref_value).expanduser())
            return str(ref_value)

        return re.sub(pattern, replace, value)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的嵌套键"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value if value is not None else default

    def set(self, key: str, value: Any):
        """设置配置值"""
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    def save(self, path: Optional[Path] = None):
        """保存配置到文件"""
        save_path = path or self.config_path
        with open(save_path, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def validate(self) -> ValidationResult:
        """校验配置"""
        result = ValidationResult(valid=True)

        # 检查必需字段
        for section in self.REQUIRED_SECTIONS:
            if section not in self._config:
                result.errors.append(f"缺少必需配置段: {section}")
                result.valid = False

        # 检查版本
        version = self.get("version")
        if version != self.CONFIG_VERSION:
            result.warnings.append(f"配置版本 {version} 与当前版本 {self.CONFIG_VERSION} 不匹配")

        # 检查端口
        port = self.get("server.port")
        if port and (port < 1 or port > 65535):
            result.errors.append(f"端口 {port} 超出有效范围 (1-65535)")
            result.valid = False

        # 检查 LLM 配置
        llm_mode = self.get("llm.mode")
        if llm_mode not in ["cloud", "local"]:
            result.errors.append(f"llm.mode 必须是 'cloud' 或 'local'，当前: {llm_mode}")
            result.valid = False

        current_provider = self.get("llm.current")
        providers = self.get("llm.providers", {})
        if current_provider and current_provider not in providers:
            result.errors.append(f"当前 LLM provider '{current_provider}' 未在 providers 中定义")
            result.valid = False

        # 检查 API key 是否配置（仅警告）
        if llm_mode == "cloud" and current_provider:
            provider_config = providers.get(current_provider, {})
            api_key = provider_config.get("api_key", "")
            if not api_key or api_key.startswith("${env."):
                result.warnings.append(f"Provider '{current_provider}' 的 API key 可能未配置")

        return result

    def doctor(self) -> Dict[str, Any]:
        """诊断配置问题"""
        validation = self.validate()
        issues = {
            "valid": validation.valid,
            "errors": validation.errors,
            "warnings": validation.warnings,
            "checks": {}
        }

        # 检查路径可写性
        omnia_home = Path(self.get("paths.omnia_home", "~/.omnia")).expanduser()
        issues["checks"]["omnia_home_writable"] = os.access(omnia_home.parent, os.W_OK) if omnia_home.parent.exists() else False

        # 检查端口占用
        import socket
        port = self.get("server.port", 8765)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("127.0.0.1", port))
        issues["checks"]["port_available"] = result != 0
        sock.close()

        # 检查环境变量
        required_env_vars = []
        llm_mode = self.get("llm.mode")
        if llm_mode == "cloud":
            provider = self.get("llm.current")
            if provider:
                # 从配置中提取环境变量名
                provider_config = self.get(f"llm.providers.{provider}", {})
                api_key = provider_config.get("api_key", "")
                if isinstance(api_key, str) and api_key.startswith("${env."):
                    env_var = api_key.replace("${env.", "").replace("}", "").split(":")[0]
                    required_env_vars.append(env_var)

        missing_env = [v for v in required_env_vars if not os.environ.get(v)]
        issues["checks"]["missing_env_vars"] = missing_env

        return issues


# ============ 迁移工具 ============

class ConfigMigrator:
    """从旧配置格式迁移到 omnia.yaml"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.new_config = OmniaConfig.CONFIG_VERSION

    def migrate(self, output_path: Optional[Path] = None) -> Path:
        """执行迁移"""
        config = {
            "version": self.new_config,
            "paths": self._migrate_paths(),
            "server": self._migrate_server(),
            "llm": self._migrate_llm(),
            "integrations": self._migrate_integrations(),
            "memory": self._migrate_memory(),
            "personas": self._migrate_personas(),
            "skills": self._migrate_skills(),
            "logging": self._migrate_logging(),
            "advanced": self._migrate_advanced(),
        }

        output = output_path or self.project_root / "omnia.yaml"
        with open(output, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        return output

    def _migrate_paths(self) -> Dict[str, Any]:
        """迁移路径配置"""
        home = Path.home() / ".omnia"
        return {
            "omnia_home": str(home),
            "project_root": str(self.project_root),
            "memory_palace_db": str(home / "memory_palace.db"),
            "neural_graph_db": str(home / "neural_graph.db"),
            "pending_conf_path": str(home / "pending_confirmations.json"),
        }

    def _migrate_server(self) -> Dict[str, Any]:
        """迁移服务器配置"""
        # 从 .env 或旧 config 读取
        return {
            "host": os.environ.get("OMNIA_HOST", "0.0.0.0"),
            "port": int(os.environ.get("OMNIA_PORT", "8765")),
            "debug": os.environ.get("OMNIA_DEBUG", "true").lower() == "true",
            "max_concurrent_requests": int(os.environ.get("MAX_CONCURRENT_REQUESTS", "100")),
            "request_timeout": int(os.environ.get("REQUEST_TIMEOUT", "120")),
        }

    def _migrate_llm(self) -> Dict[str, Any]:
        """迁移 LLM 配置"""
        # 读取旧的 model_mode.yaml
        model_mode_path = self.project_root / "config" / "model_mode.yaml"
        current_mode = "cloud"
        current_provider = "kimi"
        providers = {}

        if model_mode_path.exists():
            with open(model_mode_path, "r", encoding="utf-8") as f:
                old_config = yaml.safe_load(f) or {}

            current_mode = old_config.get("current_mode", "cloud")

            # 迁移 kimi 配置
            kimi_config = old_config.get("kimi", {})
            if kimi_config.get("enabled"):
                providers["kimi"] = {
                    "enabled": True,
                    "api_key": "${env.MOONSHOT_API_KEY}",
                    "model": kimi_config.get("model", "k3"),
                    "api_url": kimi_config.get("api_url", "https://api.kimi.com/coding/v1/messages"),
                }
                current_provider = "kimi"

            # 迁移本地模型
            local_config = old_config.get("local", {})
            if local_config.get("enabled"):
                providers["local"] = {
                    "enabled": True,
                    "backend": local_config.get("backend", "transformers"),
                    "model": local_config.get("model", "qwen3-8b"),
                    "model_path": local_config.get("model_path", "~/models/Qwen3-8B"),
                }

        # 从 .env 检测其他 provider
        env_path = self.project_root / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DEEPSEEK_API_KEY="):
                        providers["deepseek"] = {
                            "enabled": False,
                            "api_key": "${env.DEEPSEEK_API_KEY}",
                            "model": "deepseek-chat",
                            "api_url": "https://api.deepseek.com/v1",
                        }
                    elif line.startswith("OPENAI_API_KEY="):
                        providers["openai"] = {
                            "enabled": False,
                            "api_key": "${env.OPENAI_API_KEY}",
                            "model": "gpt-4o",
                            "api_url": "https://api.openai.com/v1",
                        }

        return {
            "current": current_provider,
            "mode": current_mode,
            "providers": providers,
            "local": {
                "enabled": current_mode == "local",
                "backend": "transformers",
                "model": "qwen3-8b",
                "model_path": "~/models/Qwen3-8B",
                "base_url": "http://localhost:11434",
            }
        }

    def _migrate_integrations(self) -> Dict[str, Any]:
        """迁移集成配置"""
        return {
            "feishu": {
                "enabled": False,
                "app_id": "${env.FEISHU_APP_ID}",
                "app_secret": "${env.FEISHU_APP_SECRET}",
                "verify_token": "${env.FEISHU_VERIFY_TOKEN}",
            },
            "notifications": {
                "enabled": False,
                "system": True,
                "dingtalk_webhook": "${env.DINGTALK_WEBHOOK}",
                "wecom_webhook": "${env.WECOM_WEBHOOK}",
                "feishu_webhook": "${env.FEISHU_WEBHOOK}",
            }
        }

    def _migrate_memory(self) -> Dict[str, Any]:
        """迁移记忆配置"""
        return {
            "palace": {
                "enabled": True,
                "auto_save": True,
                "retention_days": 365,
            },
            "neural_graph": {
                "enabled": True,
                "auto_enhance": True,
                "visualization": True,
            }
        }

    def _migrate_personas(self) -> Dict[str, Any]:
        """迁移 Persona 配置"""
        return {
            "default": "无限",
            "available": ["无限", "Omnia"],
            "custom_dir": "~/.omnia/personas",
        }

    def _migrate_skills(self) -> Dict[str, Any]:
        """迁移 Skill 配置"""
        return {
            "directories": [
                str(self.project_root / "skills"),
                "~/.openclaw/workspace/skills",
            ],
            "enabled": [],
            "disabled": [],
        }

    def _migrate_logging(self) -> Dict[str, Any]:
        """迁移日志配置"""
        home = Path.home() / ".omnia"
        return {
            "level": "INFO",
            "file": str(home / "omnia.log"),
            "max_size_mb": 100,
            "backup_count": 5,
            "console": True,
        }

    def _migrate_advanced(self) -> Dict[str, Any]:
        """迁移高级配置"""
        return {
            "daemon": {
                "enabled": True,
                "auto_restart": True,
                "max_restarts": 3,
                "restart_interval": 5,
            },
            "health_check": {
                "enabled": True,
                "interval": 30,
                "endpoint": "/health",
            },
            "metrics": {
                "enabled": False,
                "endpoint": "/metrics",
            }
        }


# ============ CLI 入口 ============

def main():
    """CLI 入口"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Omnia 配置管理工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # validate 命令
    validate_parser = subparsers.add_parser("validate", help="校验配置文件")
    validate_parser.add_argument("--config", "-c", type=Path, help="配置文件路径")

    # doctor 命令
    doctor_parser = subparsers.add_parser("doctor", help="诊断配置问题")
    doctor_parser.add_argument("--config", "-c", type=Path, help="配置文件路径")

    # migrate 命令
    migrate_parser = subparsers.add_parser("migrate", help="从旧配置迁移")
    migrate_parser.add_argument("--output", "-o", type=Path, help="输出文件路径")
    migrate_parser.add_argument("--project-root", type=Path, default=Path("."), help="项目根目录")

    # show 命令
    show_parser = subparsers.add_parser("show", help="显示当前配置")
    show_parser.add_argument("--config", "-c", type=Path, help="配置文件路径")
    show_parser.add_argument("--key", "-k", help="显示特定键")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "validate":
            config = OmniaConfig(args.config)
            result = config.validate()
            if result.valid:
                print("✅ 配置校验通过")
                if result.warnings:
                    print("\n⚠️  警告:")
                    for w in result.warnings:
                        print(f"  - {w}")
            else:
                print("❌ 配置校验失败")
                for e in result.errors:
                    print(f"  - {e}")
                sys.exit(1)

        elif args.command == "doctor":
            config = OmniaConfig(args.config)
            issues = config.doctor()
            print("🔍 Omnia 配置诊断")
            print(f"  配置有效: {'✅' if issues['valid'] else '❌'}")
            if issues["errors"]:
                print("\n❌ 错误:")
                for e in issues["errors"]:
                    print(f"  - {e}")
            if issues["warnings"]:
                print("\n⚠️  警告:")
                for w in issues["warnings"]:
                    print(f"  - {w}")
            print("\n📋 环境检查:")
            for check, value in issues["checks"].items():
                if isinstance(value, bool):
                    status = "✅" if value else "❌"
                    print(f"  {status} {check}")
                elif isinstance(value, list) and value:
                    print(f"  ❌ {check}: {', '.join(value)}")
                else:
                    print(f"  ✅ {check}")

        elif args.command == "migrate":
            migrator = ConfigMigrator(args.project_root)
            output = migrator.migrate(args.output)
            print(f"✅ 配置迁移完成: {output}")

        elif args.command == "show":
            config = OmniaConfig(args.config)
            if args.key:
                value = config.get(args.key)
                print(f"{args.key}: {value}")
            else:
                print(yaml.dump(config._config, default_flow_style=False, allow_unicode=True))

    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
