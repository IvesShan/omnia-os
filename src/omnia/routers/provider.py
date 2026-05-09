"""
Provider 管理路由
负责：Provider 列表、切换、状态检测
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from pathlib import Path

from src.omnia.config import settings

router = APIRouter()

# Provider 配置映射
PROVIDER_CONFIG = {
    "xiaomi": ("MIMO_API_KEY", "小米 MiMo", "mimo-v2.5-pro"),
    "deepseek": ("DEEPSEEK_API_KEY", "DeepSeek", "deepseek-v4-flash"),
    "qianfan": ("QIANFAN_API_KEY", "百度千帆", "baiduqianfancodingplan/qianfan-code-latest"),
    "kimi": ("MOONSHOT_API_KEY", "Moonshot", "K2.6-code-preview"),
    "openai": ("OPENAI_API_KEY", "OpenAI", "gpt-4o"),
    "anthropic": ("ANTHROPIC_API_KEY", "Anthropic", "claude-3-5-sonnet-20241022"),
}


class SetProviderRequest(BaseModel):
    provider: str


class ProviderInfo(BaseModel):
    id: str
    name: str
    configured: bool
    model: str
    type: Optional[str] = None
    supports_tools: Optional[bool] = None
    supports_thinking: Optional[bool] = None


class SetProviderResponse(BaseModel):
    ok: bool
    provider: str


def _check_provider_configured(env_key: str) -> bool:
    """检查 Provider 是否已配置"""
    # 检查环境变量
    if os.environ.get(env_key):
        return True
    
    # 检查 .env 文件
    env_file = settings.project_root / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(f"{env_key}="):
                return True
    
    return False


def _load_local_models() -> list[ProviderInfo]:
    """加载本地模型配置"""
    local_models = []
    local_llm_config = settings.project_root / "config" / "local_llm.yaml"
    
    if not local_llm_config.exists():
        return local_models
    
    try:
        import yaml
        with open(local_llm_config, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        for model_id, model_info in config.get('models', {}).items():
            local_models.append(ProviderInfo(
                id=f"local-{model_id}",
                name=model_info.get('display_name', model_id),
                configured=True,
                model=model_id,
                type="local",
                supports_tools=model_info.get('supports_tools', False),
                supports_thinking=model_info.get('supports_thinking', False),
            ))
    except Exception as e:
        print(f"[providers] Failed to load local_llm.yaml: {e}")
    
    return local_models


def _detect_active_provider() -> str | None:
    """检测当前活跃的 Provider"""
    if settings.current_provider:
        return settings.current_provider
    
    # 从 .env 文件检测
    env_file = settings.project_root / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("OMNIA_PROVIDER="):
                provider = line.split("=", 1)[1].strip()
                if provider:
                    return provider
    
    # 自动检测：找到第一个配置好的 Provider
    for pid, (env_key, _, _) in PROVIDER_CONFIG.items():
        if _check_provider_configured(env_key):
            return pid
    
    return None


@router.get("/providers", response_model=list[ProviderInfo])
async def get_providers():
    """获取可用的 Provider 列表"""
    providers = []
    
    # 云端 Provider
    for pid, (env_key, name, default_model) in PROVIDER_CONFIG.items():
        configured = _check_provider_configured(env_key)
        model = os.environ.get(f"{pid.upper()}_MODEL", default_model)
        
        providers.append(ProviderInfo(
            id=pid,
            name=name,
            configured=configured,
            model=model,
        ))
    
    # 本地模型
    providers.extend(_load_local_models())
    
    return providers


@router.post("/provider", response_model=SetProviderResponse)
async def set_provider(req: SetProviderRequest):
    """设置当前活跃的 Provider"""
    provider = req.provider
    
    # 允许 local-* 格式
    valid_providers = {"deepseek", "qianfan", "kimi", "openai", "anthropic", "xiaomi", "local"}
    if not provider.startswith("local-") and provider not in valid_providers:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")
    
    # 本地模型：直接设置
    if provider == "local" or provider.startswith("local-"):
        settings.current_provider = provider
        return SetProviderResponse(ok=True, provider=provider)
    
    # 云端模型：检查是否已配置
    env_key = {
        "deepseek": "DEEPSEEK_API_KEY",
        "qianfan": "QIANFAN_API_KEY",
        "kimi": "MOONSHOT_API_KEY",
        "openai": "OPENAI_API_KEY",
        "xiaomi": "MIMO_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }[provider]
    
    if not _check_provider_configured(env_key):
        raise HTTPException(status_code=400, detail=f"Provider {provider} is not configured")
    
    settings.current_provider = provider
    return SetProviderResponse(ok=True, provider=provider)


@router.get("/provider/current")
async def get_current_provider():
    """获取当前活跃的 Provider"""
    provider = _detect_active_provider()
    return {"provider": provider}
