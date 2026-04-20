"""
Tool System - Omnia 2.0

参考：FreeCode Tool 抽象 + Hermes Registry
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar, Callable, Awaitable
from pydantic import BaseModel

# ============================================================================
# Types
# ============================================================================

InputT = TypeVar('InputT', bound=BaseModel)
OutputT = TypeVar('OutputT')


class PermissionBehavior(Enum):
    """权限行为"""
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"  # 需要用户确认


@dataclass
class PermissionResult:
    """权限检查结果"""
    behavior: PermissionBehavior
    reason: str | None = None
    updated_input: dict | None = None  # 允许修改输入


@dataclass
class ToolResult(Generic[OutputT]):
    """工具执行结果"""
    data: OutputT
    error: str | None = None
    new_messages: list[dict] | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ToolContext:
    """工具执行上下文"""
    session_id: str
    user_id: str
    working_directory: str
    abort_controller: Any = None  # AbortController
    messages: list[dict] = field(default_factory=list)
    feature_flags: dict[str, bool] = field(default_factory=dict)
    
    # 回调
    on_progress: Callable[[str, dict], None] | None = None
    on_notification: Callable[[str, str], None] | None = None


# ============================================================================
# Tool Base Class
# ============================================================================

class Tool(ABC, Generic[InputT, OutputT]):
    """
    工具基类 - 参考 FreeCode 的 Tool 抽象
    
    每个工具需要定义：
    - name: 工具名称
    - description: 工具描述
    - input_schema: 输入参数 Schema (Pydantic Model)
    - call(): 执行逻辑
    - check_permissions(): 权限检查（可选）
    - is_concurrency_safe(): 是否并发安全
    - is_read_only(): 是否只读
    - is_destructive(): 是否破坏性操作
    """
    
    # 基本信息
    name: str = ""
    description: str = ""
    aliases: list[str] = []
    
    # Schema
    input_schema: type[InputT] | None = None
    
    # 配置
    max_result_size_chars: int = 100_000  # 最大结果字符数
    timeout_seconds: int = 300  # 默认超时
    
    @abstractmethod
    async def call(
        self, 
        args: InputT, 
        context: ToolContext
    ) -> ToolResult[OutputT]:
        """执行工具"""
        pass
    
    def check_permissions(
        self, 
        args: InputT, 
        context: ToolContext
    ) -> PermissionResult:
        """
        检查权限 - 默认允许
        子类可以覆盖实现更严格的权限控制
        """
        return PermissionResult(behavior=PermissionBehavior.ALLOW)
    
    def is_concurrency_safe(self, args: InputT) -> bool:
        """
        是否并发安全 - 默认 False
        并发安全的工具可以并行执行
        """
        return False
    
    def is_read_only(self, args: InputT) -> bool:
        """
        是否只读 - 默认 False
        只读工具不会修改文件系统
        """
        return False
    
    def is_destructive(self, args: InputT) -> bool:
        """
        是否破坏性操作 - 默认 False
        破坏性操作会删除/覆盖数据，需要额外确认
        """
        return False
    
    def requires_user_interaction(self) -> bool:
        """是否需要用户交互"""
        return False
    
    def get_tool_use_summary(self, args: dict) -> str | None:
        """获取工具使用摘要（用于 UI 显示）"""
        return None
    
    def get_activity_description(self, args: dict) -> str | None:
        """获取活动描述（用于 spinner 显示）"""
        return f"Running {self.name}"
    
    def to_openai_schema(self) -> dict:
        """转换为 OpenAI function calling schema"""
        if self.input_schema is None:
            return {
                "type": "function",
                "function": {
                    "name": self.name,
                    "description": self.description,
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema.model_json_schema()
            }
        }


# ============================================================================
# Tool Registry
# ============================================================================

class ToolRegistry:
    """
    工具注册表 - 参考 Hermes Registry
    
    支持：
    - 工具注册/注销
    - 按名称查找
    - 按 tag 筛选
    - 导出 OpenAI schema
    """
    
    _instance: ToolRegistry | None = None
    
    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._tags: dict[str, set[str]] = {}  # tag -> tool names
    
    @classmethod
    def get_instance(cls) -> ToolRegistry:
        """获取单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register(self, tool: Tool, tags: list[str] | None = None):
        """注册工具"""
        self._tools[tool.name] = tool
        
        # 注册别名
        for alias in tool.aliases:
            self._tools[alias] = tool
        
        # 注册 tags
        if tags:
            for tag in tags:
                if tag not in self._tags:
                    self._tags[tag] = set()
                self._tags[tag].add(tool.name)
    
    def unregister(self, name: str):
        """注销工具"""
        if name in self._tools:
            tool = self._tools[name]
            del self._tools[name]
            
            # 删除别名
            for alias in tool.aliases:
                self._tools.pop(alias, None)
            
            # 删除 tags
            for tag_tools in self._tags.values():
                tag_tools.discard(tool.name)
    
    def get(self, name: str) -> Tool | None:
        """获取工具"""
        return self._tools.get(name)
    
    def has(self, name: str) -> bool:
        """检查工具是否存在"""
        return name in self._tools
    
    def list_all(self) -> list[Tool]:
        """列出所有工具（去重）"""
        seen = set()
        tools = []
        for tool in self._tools.values():
            if tool.name not in seen:
                seen.add(tool.name)
                tools.append(tool)
        return tools
    
    def list_by_tag(self, tag: str) -> list[Tool]:
        """按 tag 列出工具"""
        names = self._tags.get(tag, set())
        return [self._tools[name] for name in names if name in self._tools]
    
    def get_tags(self) -> list[str]:
        """获取所有 tags"""
        return list(self._tags.keys())
    
    def to_openai_schemas(self) -> list[dict]:
        """导出所有工具的 OpenAI schema"""
        return [tool.to_openai_schema() for tool in self.list_all()]


# ============================================================================
# Decorator for easy tool registration
# ============================================================================

def tool(
    name: str,
    description: str,
    aliases: list[str] | None = None,
    tags: list[str] | None = None,
    input_schema: type[BaseModel] | None = None,
):
    """
    工具注册装饰器
    
    Usage:
        @tool(
            name="read_file",
            description="Read file contents",
            tags=["file", "read"],
            input_schema=ReadFileInput
        )
        async def read_file(args: ReadFileInput, context: ToolContext):
            ...
    """
    def decorator(func: Callable[[InputT, ToolContext], Awaitable[ToolResult[OutputT]]]):
        # 创建工具类
        class FunctionTool(Tool):
            pass
        
        # 设置属性
        FunctionTool.name = name
        FunctionTool.description = description
        FunctionTool.aliases = aliases or []
        FunctionTool.input_schema = input_schema
        FunctionTool.call = func
        
        # 创建实例
        tool_instance = FunctionTool()
        
        # 注册到全局 registry
        registry = ToolRegistry.get_instance()
        registry.register(tool_instance, tags)
        
        return func
    
    return decorator


# ============================================================================
# Built-in Tool Examples
# ============================================================================

class ReadFileInput(BaseModel):
    """读取文件输入"""
    path: str
    offset: int | None = None
    limit: int | None = None


class ReadFileTool(Tool[ReadFileInput, str]):
    """读取文件工具"""
    
    name = "read_file"
    description = "Read file contents from the filesystem"
    input_schema = ReadFileInput
    aliases = ["cat", "read"]
    
    def is_read_only(self, args: ReadFileInput) -> bool:
        return True
    
    async def call(self, args: ReadFileInput, context: ToolContext) -> ToolResult[str]:
        try:
            with open(args.path, 'r', encoding='utf-8') as f:
                if args.offset:
                    f.seek(args.offset)
                content = f.read(args.limit) if args.limit else f.read()
            return ToolResult(data=content)
        except Exception as e:
            return ToolResult(data="", error=str(e))


class ExecuteShellInput(BaseModel):
    """执行 Shell 输入"""
    command: str
    timeout: int = 60


class ExecuteShellTool(Tool[ExecuteShellInput, dict]):
    """执行 Shell 命令工具"""
    
    name = "execute_shell"
    description = "Execute a shell command"
    input_schema = ExecuteShellInput
    aliases = ["sh", "bash", "run"]
    
    def is_destructive(self, args: ExecuteShellInput) -> bool:
        """检查是否破坏性命令"""
        destructive_patterns = ["rm -rf", "rm -r", "dd", "mkfs", "format"]
        # 支持 dict 或 Pydantic model
        if isinstance(args, dict):
            cmd = args.get("command", "").lower()
        else:
            cmd = args.command.lower()
        return any(p in cmd for p in destructive_patterns)
    
    def check_permissions(self, args: ExecuteShellInput, context: ToolContext) -> PermissionResult:
        """检查权限"""
        # 支持 dict 或 Pydantic model
        if isinstance(args, dict):
            cmd = args.get("command", "")
        else:
            cmd = args.command
        
        if self.is_destructive(args):
            return PermissionResult(
                behavior=PermissionBehavior.ASK,
                reason=f"命令 '{cmd}' 可能是破坏性操作，需要确认"
            )
        return PermissionResult(behavior=PermissionBehavior.ALLOW)
    
    async def call(self, args: ExecuteShellInput, context: ToolContext) -> ToolResult[dict]:
        import asyncio
        
        try:
            proc = await asyncio.create_subprocess_shell(
                args.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=context.working_directory
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=args.timeout
            )
            
            return ToolResult(
                data={
                    "exit_code": proc.returncode,
                    "stdout": stdout.decode('utf-8', errors='replace'),
                    "stderr": stderr.decode('utf-8', errors='replace')
                }
            )
        except asyncio.TimeoutError:
            return ToolResult(data={}, error=f"Command timed out after {args.timeout}s")
        except Exception as e:
            return ToolResult(data={}, error=str(e))


# ============================================================================
# Initialize Registry with built-in tools
# ============================================================================

def init_builtin_tools():
    """初始化内置工具"""
    registry = ToolRegistry.get_instance()
    
    # 注册内置工具
    registry.register(ReadFileTool(), tags=["file", "read", "basic"])
    registry.register(ExecuteShellTool(), tags=["shell", "execute", "basic"])


# 自动初始化
init_builtin_tools()
