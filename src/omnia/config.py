"""
Omnia 配置管理
使用 pydantic-settings 统一管理配置
"""

from pathlib import Path
from typing import Optional

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
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保目录存在
        self.omnia_home.mkdir(parents=True, exist_ok=True)
        
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
