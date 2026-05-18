"""
Omnia 配置管理
使用 pydantic-settings 统一管理配置
"""

from pathlib import Path
from typing import Optional, Dict, Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Omnia 配置"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # 项目路径
    project_root: Path = Path(__file__).parent.parent.parent
    
    # Omnia 主目录（保持与旧版本一致）
    omnia_home: Path = Path.home() / ".omnia"
    
    # 数据库路径（使用旧的数据库位置）
    memory_palace_db: Path = omnia_home / "memory_palace.db"
    neural_graph_db: Path = omnia_home / "neural_graph.db"
    
    # 文件路径
    pending_conf_path: Path = omnia_home / "pending_confirmations.json"
    local_llm_config: Path = project_root / "config" / "local_llm.yaml"
    model_mode_config: Path = project_root / "config" / "model_mode.yaml"
    env_file: Path = project_root / ".env"
    
    # Provider 配置
    current_provider: Optional[str] = None
    
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8765
    debug: bool = True
    
    # 飞书配置
    feishu_app_id: Optional[str] = None
    feishu_app_secret: Optional[str] = None
    feishu_verify_token: Optional[str] = None
    
    # LLM 配置
    openai_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    moonshot_api_key: Optional[str] = None
    zhipu_api_key: Optional[str] = None
    
    # 本地模型配置
    local_llm_base_url: str = "http://localhost:11434"
    local_llm_model: str = "qwen2.5:7b"
    
    # 性能配置
    max_concurrent_requests: int = 100
    request_timeout: int = 60
    
    # YAML 配置缓存
    _model_mode_config: Optional[Dict[str, Any]] = None
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保目录存在
        self.omnia_home.mkdir(parents=True, exist_ok=True)
        # 加载 YAML 配置
        self._load_yaml_configs()
    
    def _load_yaml_configs(self):
        """加载 YAML 配置文件"""
        # 加载 model_mode.yaml
        if self.model_mode_config.exists():
            try:
                with open(self.model_mode_config, "r", encoding="utf-8") as f:
                    self._model_mode_config = yaml.safe_load(f)
            except Exception as e:
                print(f"[Config] 加载 model_mode.yaml 失败: {e}")
                self._model_mode_config = {}
    
    def get_model_mode_config(self) -> Dict[str, Any]:
        """获取模型模式配置"""
        if self._model_mode_config is None:
            self._load_yaml_configs()
        return self._model_mode_config or {}
    
    def get_current_mode(self) -> str:
        """获取当前模型模式"""
        config = self.get_model_mode_config()
        return config.get("current_mode", "cloud")
    
    def get_current_provider(self) -> str:
        """获取当前 Provider"""
        # 优先从环境变量获取
        if self.current_provider:
            return self.current_provider
        
        # 从 YAML 配置获取
        config = self.get_model_mode_config()
        mode = self.get_current_mode()
        mode_config = config.get(mode, {})
        
        return mode_config.get("provider", "deepseek")
    
    def get_current_model(self) -> str:
        """获取当前模型名称"""
        config = self.get_model_mode_config()
        mode = self.get_current_mode()
        mode_config = config.get(mode, {})
        
        return mode_config.get("model", "default")
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """获取指定 Provider 的配置"""
        config = self.get_model_mode_config()
        return config.get(provider, {})
    
    # 兼容旧代码的属性别名
    @property
    def MEMORY_PALACE_DB(self) -> Path:
        """兼容旧代码的别名"""
        return self.memory_palace_db
    
    @property
    def NEURAL_GRAPH_DB(self) -> Path:
        """兼容旧代码的别名"""
        return self.neural_graph_db


# 全局单例
settings = Settings()
