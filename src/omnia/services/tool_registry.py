"""
tool_registry.py — 统一工具注册表

核心功能：
1. 管理所有工具的注册
2. 提供 JSON Schema 供 LLM 使用
3. 统一调度工具执行
"""

import json
from typing import Dict, Any, List, Optional, Callable, Awaitable
from pathlib import Path


class ToolRegistry:
    """工具注册表 — 单例模式"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # 工具存储
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._executors: Dict[str, Callable] = {}
        
        # 工作目录
        self.workspace: str = str(Path(__file__).parent.parent.parent.parent)
        
        # MCP 工具
        self.mcp_tools: List[dict] = []

    def register_tool(
        self,
        name: str,
        schema: dict,
        executor: Callable[..., Awaitable[Dict[str, Any]]]
    ):
        """注册一个工具"""
        self._tools[name] = schema
        self._executors[name] = executor

    def register_module(self, module_name: str, definitions: list[dict], executor_instance: Any):
        """注册一个模块的所有工具"""
        for tool_def in definitions:
            func_def = tool_def.get("function", {})
            name = func_def.get("name")
            if name:
                # 为每个工具创建绑定方法
                executor = getattr(executor_instance, f"execute", None)
                if executor:
                    # 创建包装器，绑定工具名称
                    async def make_wrapper(n, exec_instance):
                        async def wrapper(**kwargs):
                            return await exec_instance.execute(n, kwargs)
                        return wrapper
                    
                    import asyncio
                    try:
                        loop = asyncio.get_running_loop()
                        # 不能直接这么用，简化处理
                        pass
                    except RuntimeError:
                        pass
                    
                    self._tools[name] = tool_def
                    # 保存模块信息以便延迟执行
                    self._tools[name]["_module"] = module_name
                    self._tools[name]["_instance"] = str(id(executor_instance))

    def register_tool_direct(
        self,
        name: str,
        schema: dict,
        executor_fn: Callable[..., Awaitable[Dict[str, Any]]]
    ):
        """直接注册工具（保留函数引用）"""
        self._tools[name] = schema
        self._executors[name] = executor_fn

    def register_mcp_tools(self, tools: list[dict]):
        """注册 MCP 工具"""
        self.mcp_tools = tools

    def get_all_schemas(self) -> list[dict]:
        """获取所有工具 schema（不含内部字段）"""
        schemas = []
        for name, tool in self._tools.items():
            # 过滤掉内部字段
            clean = {k: v for k, v in tool.items() if not k.startswith("_")}
            schemas.append(clean)
        
        # 添加 MCP 工具
        schemas.extend(self.mcp_tools)
        
        return schemas

    def get_tool_names(self) -> list[str]:
        """获取所有已注册工具名称"""
        return list(self._tools.keys())

    def get_tool_count(self) -> int:
        """获取工具总数"""
        return len(self._tools) + len(self.mcp_tools)

    def has_tool(self, name: str) -> bool:
        """检查工具是否已注册"""
        return name in self._tools

    async def execute(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        # 1. 检查直接注册的执行器
        if name in self._executors:
            try:
                result = await self._executors[name](**args)
                return {"name": name, "result": result}
            except Exception as e:
                return {"name": name, "error": str(e)}
        
        # 2. 检查模块注册的工具（SystemTools/MemoryTools）
        if name in self._tools:
            module_name = self._tools[name].get("_module", "")
            if module_name == "system":
                from src.omnia.tools.system_tools import SystemTools
                result = await SystemTools.execute(name, args, self.workspace)
                return {"name": name, "result": result}
            elif module_name == "memory":
                from src.omnia.tools.memory_tools import MemoryTools
                mt = MemoryTools()
                result = await mt.execute(name, args)
                return {"name": name, "result": result}
        
        # 3. 尝试 MCP 工具
        # TODO: MCP 执行
        
        return {"name": name, "error": f"工具 '{name}' 未注册"}

    def get_system_prompt(self) -> str:
        """生成工具系统提示词"""
        tool_names = self.get_tool_names()
        if not tool_names:
            return ""
        
        tools_desc = "\n".join([f"- **{name}**: {self._tools[name].get('function', {}).get('description', '')}" for name in tool_names])
        
        return f"""## 可用工具

你可以使用以下工具来辅助回答，但**不是所有问题都需要工具**：

{tools_desc}

### 工具调用规则

1. **简单问答**（问候、闲聊、概念解释）：**直接回答，不调用工具**
2. **涉及文件、命令、搜索、记忆查询时**：使用 API 原生 tool_calls 字段调用工具
3. **禁止**在 content 中输出 JSON 格式的工具调用文本
4. 工具执行后，基于结果继续回答"""

    async def initialize_default_tools(self):
        """初始化默认工具集"""
        # 注册系统工具
        from src.omnia.tools.system_tools import SystemTools
        system_defs = SystemTools.get_definitions()
        for tool_def in system_defs:
            func_def = tool_def.get("function", {})
            name = func_def.get("name")
            if name:
                tool_def["_module"] = "system"
                self._tools[name] = tool_def

        # 注册记忆工具
        from src.omnia.tools.memory_tools import MemoryTools
        memory_defs = MemoryTools.get_definitions()
        for tool_def in memory_defs:
            func_def = tool_def.get("function", {})
            name = func_def.get("name")
            if name:
                tool_def["_module"] = "memory"
                self._tools[name] = tool_def

        return len(self._tools)


# 全局单例
tool_registry = ToolRegistry()
