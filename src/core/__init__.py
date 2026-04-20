"""
Omnia 2.0 Core Package

Phase 1 核心组件：
- Tool System (tool_base.py)
- Feature Flags (feature/flags.py)
- FTS5 Search (memory/fts_search.py)
- Hook System (plugin/hooks.py)

Phase 2 认知组件：
- Intent Engine (cognition/intent_engine.py)
- Provider Abstraction (providers/)
- Context Compressor (cognition/compressor.py)

Phase 3 核心功能：
- Bootstrap (bootstrap.py) - 自动初始化核心功能
"""

from .execution.tool_base import (
    Tool,
    ToolRegistry,
    ToolContext,
    ToolResult,
    PermissionBehavior,
    PermissionResult,
    tool,
)
from .feature.flags import (
    FeatureFlags,
    FeatureCategory,
    FeatureFlag,
    FF,  # Convenience alias
)
from .memory.fts_search import (
    FTSClient,
    AsyncFTSClient,
    SearchResult,
    MessageRecord,
)
from .plugin.hooks import (
    HookRegistry,
    HookType,
    HookContext,
)
from .cognition.intent_engine import (
    IntentEngine,
    IntentType,
    Intent,
    IntentContext,
)
from .providers import (
    ProviderResolver,
    ProviderType,
    ModelConfig,
    ModelClient,
    get_client,
    list_available_models,
)
from .cognition.compressor import (
    ContextCompressor,
    CompressionResult,
)
from .bootstrap import (
    bootstrap_omnia,
    get_feature_status,
    print_status,
)


# Convenience functions for FeatureFlags (wrappers around class methods)
def is_enabled(name: str) -> bool:
    """Check if a feature flag is enabled"""
    return FeatureFlags.is_enabled(name)


def enable_feature(name: str) -> None:
    """Enable a feature flag"""
    FeatureFlags.enable(name)


def disable_feature(name: str) -> None:
    """Disable a feature flag"""
    FeatureFlags.disable(name)


__all__ = [
    # Tool System
    "Tool",
    "ToolRegistry",
    "ToolContext",
    "ToolResult",
    "PermissionBehavior",
    "PermissionResult",
    "tool",
    
    # Feature Flags
    "FeatureFlags",
    "FeatureCategory",
    "FeatureFlag",
    "FF",
    "is_enabled",
    "enable_feature",
    "disable_feature",
    
    # FTS5 Search
    "FTSClient",
    "AsyncFTSClient",
    "SearchResult",
    "MessageRecord",
    
    # Hook System
    "HookRegistry",
    "HookType",
    "HookContext",
    
    # Intent Engine
    "IntentEngine",
    "IntentType",
    "Intent",
    "IntentContext",
    
    # Provider Abstraction
    "ProviderResolver",
    "ProviderType",
    "ModelConfig",
    "ModelClient",
    "get_client",
    "list_available_models",
    
    # Context Compressor
    "ContextCompressor",
    "CompressionResult",
    
    # Bootstrap
    "bootstrap_omnia",
    "get_feature_status",
    "print_status",
]
