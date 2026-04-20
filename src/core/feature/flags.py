"""
Feature Flags System - Omnia 2.0

参考：FreeCode 的 88+ Feature Flags
目的：隔离实验性功能，允许运行时开关

Usage:
    from core.feature.flags import FeatureFlags as FF
    
    if FF.is_enabled("EXECUTION_PARALLEL_TOOLS"):
        # 并行执行工具
        ...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
import json
from pathlib import Path


class FeatureCategory(Enum):
    """功能分类"""
    CORE = "core"                      # 核心功能（默认启用）
    EXPERIMENTAL = "experimental"      # 实验性功能
    UI = "ui"                          # 用户界面
    COGNITION = "cognition"            # 认知功能
    MEMORY = "memory"                  # 记忆功能
    EXECUTION = "execution"            # 执行功能
    PROVIDER = "provider"              # 模型提供商
    CHANNEL = "channel"                # 通道功能
    SECURITY = "security"              # 安全功能
    DEBUG = "debug"                    # 调试功能


@dataclass
class FeatureFlag:
    """特性开关定义"""
    name: str
    description: str
    default: bool
    category: FeatureCategory
    requires_restart: bool = False     # 是否需要重启
    dependencies: list[str] = field(default_factory=list)  # 依赖的其他 flag
    conflicts: list[str] = field(default_factory=list)     # 冲突的 flag


# ============================================================================
# Feature Flags Definition
# ============================================================================

FLAGS: dict[str, FeatureFlag] = {
    # === 核心功能（默认启用）===
    "CORE_SELF_EVOLUTION": FeatureFlag(
        name="CORE_SELF_EVOLUTION",
        description="自进化引擎 - 自动学习新技能、优化现有能力",
        default=True,
        category=FeatureCategory.CORE,
    ),
    "CORE_INTENT_ENGINE": FeatureFlag(
        name="CORE_INTENT_ENGINE",
        description="意图识别引擎 - 理解用户意图并路由到正确的技能",
        default=True,
        category=FeatureCategory.CORE,
    ),
    "CORE_MEMORY_VECTOR_STORE": FeatureFlag(
        name="CORE_MEMORY_VECTOR_STORE",
        description="向量记忆系统 - 语义搜索和相似度匹配",
        default=True,
        category=FeatureCategory.CORE,
    ),
    "CORE_WORKFLOW_ENGINE": FeatureFlag(
        name="CORE_WORKFLOW_ENGINE",
        description="工作流引擎 - DAG 多步骤任务编排",
        default=True,
        category=FeatureCategory.CORE,
    ),
    "CORE_NEURAL_GRAPH": FeatureFlag(
        name="CORE_NEURAL_GRAPH",
        description="神经图谱 - 实体关系图谱和上下文增强",
        default=True,
        category=FeatureCategory.CORE,
    ),
    "CORE_AGENT_SWARM": FeatureFlag(
        name="CORE_AGENT_SWARM",
        description="代理集群 - 并行子代理执行",
        default=True,
        category=FeatureCategory.CORE,
    ),
    
    # === 实验性功能（默认关闭，需要手动启用）===
    "EXPERIMENTAL_VERIFIED_EXECUTION": FeatureFlag(
        name="EXPERIMENTAL_VERIFIED_EXECUTION",
        description="可验证执行 - 执行证明和回滚机制",
        default=False,
        category=FeatureCategory.EXPERIMENTAL,
    ),
    "EXPERIMENTAL_PROGRESSIVE_CAPABILITY": FeatureFlag(
        name="EXPERIMENTAL_PROGRESSIVE_CAPABILITY",
        description="渐进式能力解锁 - 根据用户熟练度逐步开放功能",
        default=False,
        category=FeatureCategory.EXPERIMENTAL,
    ),
    "EXPERIMENTAL_PERSONA_CONTINUITY": FeatureFlag(
        name="EXPERIMENTAL_PERSONA_CONTINUITY",
        description="跨会话人格连续性 - 情感状态追踪和记忆注入",
        default=False,
        category=FeatureCategory.EXPERIMENTAL,
    ),
    "EXPERIMENTAL_REFLECTION": FeatureFlag(
        name="EXPERIMENTAL_REFLECTION",
        description="反思模块 - 自动总结和改进建议",
        default=False,
        category=FeatureCategory.EXPERIMENTAL,
    ),
    
    # === 用户界面 ===
    "UI_TYPING_EFFECT": FeatureFlag(
        name="UI_TYPING_EFFECT",
        description="Show typing effect for responses",
        default=True,
        category=FeatureCategory.UI,
    ),
    "UI_VOICE_MODE": FeatureFlag(
        name="UI_VOICE_MODE",
        description="Enable voice input/output mode",
        default=False,
        category=FeatureCategory.UI,
    ),
    "UI_DESKTOP_NOTIFICATION": FeatureFlag(
        name="UI_DESKTOP_NOTIFICATION",
        description="Show desktop notifications",
        default=True,
        category=FeatureCategory.UI,
    ),
    "UI_MARKDOWN_RENDER": FeatureFlag(
        name="UI_MARKDOWN_RENDER",
        description="Render markdown in responses",
        default=True,
        category=FeatureCategory.UI,
    ),
    "UI_CODE_HIGHLIGHT": FeatureFlag(
        name="UI_CODE_HIGHLIGHT",
        description="Syntax highlighting for code blocks",
        default=True,
        category=FeatureCategory.UI,
    ),
    "UI_SUGGESTIONS": FeatureFlag(
        name="UI_SUGGESTIONS",
        description="Show action suggestions",
        default=True,
        category=FeatureCategory.UI,
    ),
    "UI_DARK_MODE": FeatureFlag(
        name="UI_DARK_MODE",
        description="Use dark theme",
        default=True,
        category=FeatureCategory.UI,
    ),
    
    # === 认知功能 ===
    "COGNITION_CONTEXT_COMPRESSION": FeatureFlag(
        name="COGNITION_CONTEXT_COMPRESSION",
        description="Enable context compression for long conversations",
        default=True,
        category=FeatureCategory.COGNITION,
    ),
    "COGNITION_PLAN_CACHING": FeatureFlag(
        name="COGNITION_PLAN_CACHING",
        description="Cache generated plans for similar intents",
        default=True,
        category=FeatureCategory.COGNITION,
    ),
    "COGNITION_REASONING_CHAIN": FeatureFlag(
        name="COGNITION_REASONING_CHAIN",
        description="Show reasoning steps in responses",
        default=False,
        category=FeatureCategory.COGNITION,
    ),
    
    # === 记忆功能 ===
    "MEMORY_AUTO_PERSIST": FeatureFlag(
        name="MEMORY_AUTO_PERSIST",
        description="Automatically persist important facts to Memory Palace",
        default=True,
        category=FeatureCategory.MEMORY,
    ),
    "MEMORY_FTS_SEARCH": FeatureFlag(
        name="MEMORY_FTS_SEARCH",
        description="Enable full-text search in Memory Palace",
        default=True,
        category=FeatureCategory.MEMORY,
    ),
    "MEMORY_GRAPH_SYNC": FeatureFlag(
        name="MEMORY_GRAPH_SYNC",
        description="Sync Memory Palace changes to Neural Graph",
        default=True,
        category=FeatureCategory.MEMORY,
    ),
    "MEMORY_IDLE_INDEXING": FeatureFlag(
        name="MEMORY_IDLE_INDEXING",
        description="Index memories during idle time",
        default=True,
        category=FeatureCategory.MEMORY,
    ),
    
    # === 执行功能 ===
    "EXECUTION_PARALLEL_TOOLS": FeatureFlag(
        name="EXECUTION_PARALLEL_TOOLS",
        description="Execute independent tools in parallel",
        default=True,
        category=FeatureCategory.EXECUTION,
    ),
    "EXECUTION_AUTO_RETRY": FeatureFlag(
        name="EXECUTION_AUTO_RETRY",
        description="Automatically retry failed tool calls",
        default=True,
        category=FeatureCategory.EXECUTION,
    ),
    "EXECUTION_TIMEOUT_GUARD": FeatureFlag(
        name="EXECUTION_TIMEOUT_GUARD",
        description="Enforce timeouts on tool execution",
        default=True,
        category=FeatureCategory.EXECUTION,
    ),
    "EXECUTION_SANDBOX": FeatureFlag(
        name="EXECUTION_SANDBOX",
        description="Run shell commands in sandboxed environment",
        default=False,
        category=FeatureCategory.EXECUTION,
    ),
    
    # === 安全功能 ===
    "SECURITY_SAFETY_GATE": FeatureFlag(
        name="SECURITY_SAFETY_GATE",
        description="Require confirmation for dangerous operations",
        default=True,
        category=FeatureCategory.SECURITY,
    ),
    "SECURITY_AUDIT_LOG": FeatureFlag(
        name="SECURITY_AUDIT_LOG",
        description="Log all tool executions for audit",
        default=True,
        category=FeatureCategory.SECURITY,
    ),
    "SECURITY_RATE_LIMIT": FeatureFlag(
        name="SECURITY_RATE_LIMIT",
        description="Rate limit tool calls to prevent abuse",
        default=False,
        category=FeatureCategory.SECURITY,
    ),
    
    # === Provider 功能 ===
    "PROVIDER_KIMI": FeatureFlag(
        name="PROVIDER_KIMI",
        description="Enable Kimi (Moonshot) provider",
        default=True,
        category=FeatureCategory.PROVIDER,
    ),
    "PROVIDER_QIANFAN": FeatureFlag(
        name="PROVIDER_QIANFAN",
        description="Enable Baidu Qianfan provider",
        default=True,
        category=FeatureCategory.PROVIDER,
    ),
    "PROVIDER_OPENAI": FeatureFlag(
        name="PROVIDER_OPENAI",
        description="Enable OpenAI provider",
        default=False,
        category=FeatureCategory.PROVIDER,
    ),
    "PROVIDER_ANTHROPIC": FeatureFlag(
        name="PROVIDER_ANTHROPIC",
        description="Enable Anthropic Claude provider",
        default=False,
        category=FeatureCategory.PROVIDER,
    ),
    "PROVIDER_FALLBACK": FeatureFlag(
        name="PROVIDER_FALLBACK",
        description="Fallback to alternative provider on failure",
        default=True,
        category=FeatureCategory.PROVIDER,
    ),
    
    # === Channel 功能 ===
    "CHANNEL_FEISHU": FeatureFlag(
        name="CHANNEL_FEISHU",
        description="Enable Feishu bot adapter",
        default=True,
        category=FeatureCategory.CHANNEL,
    ),
    "CHANNEL_IDE_BRIDGE": FeatureFlag(
        name="CHANNEL_IDE_BRIDGE",
        description="Enable IDE bridge for VSCode integration",
        default=True,
        category=FeatureCategory.CHANNEL,
    ),
    "CHANNEL_WEB_UI": FeatureFlag(
        name="CHANNEL_WEB_UI",
        description="Enable web dashboard",
        default=True,
        category=FeatureCategory.CHANNEL,
    ),
    "CHANNEL_CLI": FeatureFlag(
        name="CHANNEL_CLI",
        description="Enable CLI interface",
        default=True,
        category=FeatureCategory.CHANNEL,
    ),
    
    # === 调试功能 ===
    "DEBUG_VERBOSE_LOGGING": FeatureFlag(
        name="DEBUG_VERBOSE_LOGGING",
        description="Enable verbose logging for debugging",
        default=False,
        category=FeatureCategory.DEBUG,
    ),
    "DEBUG_TRACE_TOOLS": FeatureFlag(
        name="DEBUG_TRACE_TOOLS",
        description="Trace all tool calls with timing",
        default=False,
        category=FeatureCategory.DEBUG,
    ),
    "DEBUG_PROFILE_MEMORY": FeatureFlag(
        name="DEBUG_PROFILE_MEMORY",
        description="Profile memory usage during execution",
        default=False,
        category=FeatureCategory.DEBUG,
    ),
}


class FeatureFlags:
    """Feature Flags Manager"""
    
    _overrides: dict[str, bool] = {}
    _config_file: Path | None = None
    
    @classmethod
    def set_config_file(cls, path: Path) -> None:
        """Set config file path for persistence"""
        cls._config_file = path
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                cls._overrides = data.get("overrides", {})
            except Exception:
                cls._overrides = {}
    
    @classmethod
    def save_config(cls) -> None:
        """Save current overrides to config file"""
        if cls._config_file:
            cls._config_file.parent.mkdir(parents=True, exist_ok=True)
            data = {"overrides": cls._overrides}
            cls._config_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    
    @classmethod
    def is_enabled(cls, name: str) -> bool:
        """Check if a feature flag is enabled"""
        if name not in FLAGS:
            raise ValueError(f"Unknown feature flag: {name}")
        
        # Check override first
        if name in cls._overrides:
            return cls._overrides[name]
        
        # Fall back to default
        return FLAGS[name].default
    
    @classmethod
    def is_defined(cls, name: str) -> bool:
        """Check if a feature flag exists"""
        return name in FLAGS
    
    @classmethod
    def enable(cls, name: str) -> None:
        """Enable a feature flag"""
        if name not in FLAGS:
            raise ValueError(f"Unknown feature flag: {name}")
        cls._overrides[name] = True
        cls.save_config()
    
    @classmethod
    def disable(cls, name: str) -> None:
        """Disable a feature flag"""
        if name not in FLAGS:
            raise ValueError(f"Unknown feature flag: {name}")
        cls._overrides[name] = False
        cls.save_config()
    
    @classmethod
    def reset(cls, name: str) -> None:
        """Reset a feature flag to default"""
        if name not in FLAGS:
            raise ValueError(f"Unknown feature flag: {name}")
        cls._overrides.pop(name, None)
        cls.save_config()
    
    @classmethod
    def get_all(cls) -> dict[str, bool]:
        """Get all feature flags and their current values"""
        return {name: cls.is_enabled(name) for name in FLAGS}
    
    @classmethod
    def get_by_category(cls, category: FeatureCategory) -> dict[str, bool]:
        """Get feature flags by category"""
        return {
            name: cls.is_enabled(name)
            for name, flag in FLAGS.items()
            if flag.category == category
        }
    
    @classmethod
    def list_all(cls) -> list[dict]:
        """List all feature flags with details"""
        result = []
        for name, flag in FLAGS.items():
            result.append({
                "name": name,
                "description": flag.description,
                "default": flag.default,
                "current": cls.is_enabled(name),
                "category": flag.category.value,
                "requires_restart": flag.requires_restart,
            })
        return result


# Convenience alias
FF = FeatureFlags
