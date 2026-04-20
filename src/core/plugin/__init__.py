"""Plugin System - Hooks and Extensions

Auto-import all hook modules to ensure hooks are registered.
"""

from .hooks import HookType, HookContext, HookRegistry, get_hook_registry, register_hook

# Auto-import hook modules to register them
try:
    from . import auto_memory_hook
except ImportError:
    pass

try:
    from . import tool_cleaner_hook
except ImportError:
    pass

__all__ = [
    "HookType",
    "HookContext", 
    "HookRegistry",
    "get_hook_registry",
    "register_hook",
]
