"""Hook System - 参考 FreeCode 的生命周期钩子

支持在工具执行前后、消息处理等关键节点触发自定义逻辑。
"""

from dataclasses import dataclass
from typing import Callable, Any, Optional
from enum import Enum


class HookType(Enum):
    """钩子类型"""
    PRE_TOOL_USE = "pre_tool_use"           # 工具执行前
    POST_TOOL_USE = "post_tool_use"         # 工具执行后
    ON_MESSAGE = "on_message"               # 消息处理
    ON_TOOL_PATTERN = "on_tool_pattern"     # 检测到工具格式
    ON_COMPACT = "on_compact"               # 压缩事件
    ON_ERROR = "on_error"                   # 错误处理
    POST_RESPONSE = "post_response"         # 响应后


@dataclass
class HookContext:
    """钩子上下文"""
    type: HookType
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None
    tool_result: Optional[Any] = None
    message: Optional[str] = None
    output: Optional[str] = None
    response: Optional[str] = None          # 最终响应文本（POST_RESPONSE 使用）
    error: Optional[Exception] = None
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


HookCallback = Callable[[HookContext], Any]


class HookRegistry:
    """钩子注册表"""
    
    _instance: 'HookRegistry' = None
    
    def __init__(self):
        self._hooks: dict[HookType, list[tuple[int, str, HookCallback]]] = {}
    
    @classmethod
    def get_instance(cls) -> 'HookRegistry':
        """获取全局单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register(
        self,
        hook_type: HookType,
        callback: HookCallback,
        priority: int = 0,
        name: str = None
    ) -> None:
        """注册钩子
        
        Args:
            hook_type: 钩子类型
            callback: 回调函数
            priority: 优先级（数字越小越先执行）
            name: 钩子名称
        """
        if hook_type not in self._hooks:
            self._hooks[hook_type] = []
        
        name = name or callback.__name__
        self._hooks[hook_type].append((priority, name, callback))
        
        # 按优先级排序
        self._hooks[hook_type].sort(key=lambda x: x[0])
    
    def trigger(self, hook_type: HookType, context: HookContext) -> Any:
        """触发钩子（支持同步和异步回调）
        
        Args:
            hook_type: 钩子类型
            context: 钩子上下文
        
        Returns:
            最后一个钩子的返回值（如果有）
        """
        hooks = self._hooks.get(hook_type, [])
        
        result = None
        for priority, name, callback in hooks:
            try:
                # 判断是同步还是异步
                import asyncio
                if asyncio.iscoroutinefunction(callback):
                    # 异步回调：检测是否在事件循环中
                    try:
                        loop = asyncio.get_running_loop()
                        # 已在事件循环中：后台调度，不阻塞
                        loop.create_task(callback(context))
                        result = None
                    except RuntimeError:
                        # 没有运行中的事件循环，直接运行
                        result = asyncio.run(callback(context))
                else:
                    # 同步回调：直接调用
                    result = callback(context)
            except Exception as e:
                # 错误不中断其他钩子
                print(f"[Hook] {name} failed: {e}")
        
        return result
    
    def list_hooks(self, hook_type: HookType = None) -> list[str]:
        """列出所有钩子"""
        if hook_type:
            return [name for _, name, _ in self._hooks.get(hook_type, [])]
        
        result = []
        for ht, hooks in self._hooks.items():
            for _, name, _ in hooks:
                result.append(f"{ht.value}:{name}")
        return result


# 全局注册表
def get_hook_registry() -> HookRegistry:
    """获取全局钩子注册表"""
    return HookRegistry.get_instance()


def register_hook(
    hook_type: HookType,
    callback: HookCallback = None,
    priority: int = 0,
    name: str = None
):
    """注册钩子（支持装饰器用法和直接调用）
    
    用法1 - 装饰器：
        @register_hook(HookType.POST_RESPONSE, priority=10, name="my_hook")
        def my_callback(context: HookContext):
            ...
    
    用法2 - 直接调用：
        register_hook(HookType.POST_RESPONSE, my_callback, priority=10)
    
    Args:
        hook_type: 钩子类型
        callback: 回调函数（装饰器用法时可省略）
        priority: 优先级（数字越小越先执行）
        name: 钩子名称
    
    Returns:
        装饰器函数（装饰器用法）或 None（直接调用）
    """
    registry = get_hook_registry()
    
    # 装饰器用法：callback 为 None，返回装饰器
    if callback is None:
        def decorator(func: HookCallback) -> HookCallback:
            registry.register(hook_type, func, priority, name)
            return func
        return decorator
    
    # 直接调用：callback 不为 None
    registry.register(hook_type, callback, priority, name)
    return None


# ========== 内置钩子 ==========

def log_tool_call(context: HookContext):
    """记录工具调用日志"""
    if context.type == HookType.PRE_TOOL_USE:
        print(f"[Hook] Tool call: {context.tool_name}({context.tool_args})")
    elif context.type == HookType.POST_TOOL_USE:
        result_summary = str(context.tool_result)[:100] if context.tool_result else "None"
        print(f"[Hook] Tool result: {context.tool_name} -> {result_summary}...")


def error_handler(context: HookContext):
    """错误处理钩子"""
    if context.error:
        print(f"[Hook] Error in {context.type.value}: {context.error}")
        # 可以在这里添加错误上报、重试等逻辑


# 注册内置钩子
def _register_builtin_hooks():
    """注册内置钩子"""
    register_hook(HookType.PRE_TOOL_USE, log_tool_call, priority=100)
    register_hook(HookType.POST_TOOL_USE, log_tool_call, priority=100)
    register_hook(HookType.ON_ERROR, error_handler, priority=0)


# 自动注册（延迟执行，避免循环导入）
_builtin_hooks_registered = False

def ensure_builtin_hooks():
    """确保内置钩子已注册"""
    global _builtin_hooks_registered
    if not _builtin_hooks_registered:
        _register_builtin_hooks()
        _builtin_hooks_registered = True
