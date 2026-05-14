"""
Provider 管理路由
负责：Provider 列表、切换、状态检测、持久化
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
    "deepseek": ("DEEPSEEK_API_KEY", "DeepSeek", "deepseek-v4-pro"),
    "qianfan": ("QIANFAN_API_KEY", "百度千帆", "qianfan-code-latest"),
    "kimi": ("MOONSHOT_API_KEY", "Moonshot", "kimi-code"),
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


class ProviderListResponse(BaseModel):
    """兼容 Flask 前端的 Provider 列表响应"""
    providers: list[ProviderInfo]
    active: Optional[str] = None


def _check_provider_configured(env_key: str) -> bool:
    """检查 Provider 是否已配置"""
    if os.environ.get(env_key):
        return True
    env_file = settings.project_root / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(f"{env_key}="):
                return True
    return False


def _persist_provider_to_env(provider: str):
    """将 Provider 持久化到 .env 文件"""
    env_file = settings.project_root / ".env"
    lines = []
    found = False

    # 读取现有内容
    if env_file.exists():
        lines = env_file.read_text(encoding="utf-8").splitlines()

    # 查找并替换 OMNIA_PROVIDER 行
    new_lines = []
    for line in lines:
        if line.strip().startswith("OMNIA_PROVIDER="):
            new_lines.append(f"OMNIA_PROVIDER={provider}")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"\n# Active provider (auto-set)\nOMNIA_PROVIDER={provider}")

    # 写回 .env 文件
    env_file.write_text("\n".join(new_lines), encoding="utf-8")
    print(f"[Provider] Persisted provider '{provider}' to .env")


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
        print(f"[provider] Failed to load local_llm.yaml: {e}")

    return local_models


def _get_active_provider() -> Optional[str]:
    """获取当前活跃的 Provider"""
    # 优先检查 .env 文件中的 OMNIA_PROVIDER
    env_file = settings.project_root / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("OMNIA_PROVIDER="):
                provider = line.split("=", 1)[1].strip()
                if provider:
                    return provider

    # 检查环境变量
    env_provider = os.environ.get("OMNIA_PROVIDER")
    if env_provider:
        return env_provider

    # 检查哪个 provider 已配置
    for pid, (env_key, _, _) in PROVIDER_CONFIG.items():
        if _check_provider_configured(env_key):
            return pid

    return None


@router.get("/providers", response_model=ProviderListResponse)
async def get_providers():
    """获取可用的 Provider 列表"""
    providers = []

    # 添加云端 Provider
    for pid, (env_key, name, default_model) in PROVIDER_CONFIG.items():
        configured = _check_provider_configured(env_key)
        model = os.environ.get(f"{pid.upper()}_MODEL", default_model)
        providers.append(ProviderInfo(
            id=pid,
            name=name,
            configured=configured,
            model=model,
        ))

    # 添加本地模型
    providers.extend(_load_local_models())

    # 获取当前活跃的 Provider
    active = _get_active_provider()

    return ProviderListResponse(providers=providers, active=active)


@router.post("/providers", response_model=SetProviderResponse)
async def set_provider(request: SetProviderRequest):
    """设置活跃的 Provider"""
    provider = request.provider

    # 验证 Provider 是否有效
    valid_providers = set(PROVIDER_CONFIG.keys()) | {"local"}
    if not provider.startswith("local-") and provider not in valid_providers:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

    # 检查 Provider 是否已配置
    if provider in PROVIDER_CONFIG:
        env_key = PROVIDER_CONFIG[provider][0]
        if not _check_provider_configured(env_key):
            raise HTTPException(
                status_code=400,
                detail=f"Provider {provider} is not configured. Please add {env_key} to .env file."
            )

    # 持久化到 .env 文件
    _persist_provider_to_env(provider)

    # 更新环境变量
    os.environ["OMNIA_PROVIDER"] = provider

    return SetProviderResponse(ok=True, provider=provider)


@router.get("/providers/{provider}/status")
async def get_provider_status(provider: str):
    """获取 Provider 状态"""
    if provider not in PROVIDER_CONFIG and not provider.startswith("local-"):
        raise HTTPException(status_code=404, detail=f"Provider {provider} not found")

    if provider.startswith("local-"):
        return {"id": provider, "configured": True, "status": "available"}

    env_key, name, default_model = PROVIDER_CONFIG[provider]
    configured = _check_provider_configured(env_key)
    model = os.environ.get(f"{provider.upper()}_MODEL", default_model)

    return {
        "id": provider,
        "name": name,
        "configured": configured,
        "model": model,
        "status": "configured" if configured else "not_configured",
    }
