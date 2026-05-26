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
        
        # MCP 管理器引用（由 main.py lifespan 设置）
        self.mcp_manager = None

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

    def set_mcp_manager(self, manager):
        """设置 MCP 管理器引用，用于执行 MCP 工具"""
        self.mcp_manager = manager

    def get_all_schemas(self) -> list[dict]:
        """获取所有工具 schema（不含内部字段）"""
        schemas = []
        for name, tool in self._tools.items():
            # 过滤掉内部字段
            clean = {k: v for k, v in tool.items() if not k.startswith("_")}
            schemas.append(clean)
        
        # 添加 MCP 工具，排除已经在 _tools 中的（避免重复）
        existing_names = {tool.get("function", {}).get("name") for tool in schemas}
        for tool_def in self.mcp_tools:
            func_def = tool_def.get("function", {})
            name = func_def.get("name")
            if name and name not in existing_names:
                clean = {k: v for k, v in tool_def.items() if not k.startswith("_")}
                schemas.append(clean)
        
        return schemas

    def get_tool_names(self) -> list[str]:
        """获取所有已注册工具名称"""
        return list(self._tools.keys())

    def get_tool_count(self) -> int:
        """获取工具总数"""
        # 添加 MCP 工具到 _tools（如果已注册）
        if self.mcp_tools:
            for tool_def in self.mcp_tools:
                func_def = tool_def.get("function", {})
                name = func_def.get("name")
                if name and name not in self._tools:
                    tool_def_copy = dict(tool_def)
                    tool_def_copy["_module"] = "mcp"
                    self._tools[name] = tool_def_copy
            print(f"[ToolRegistry] MCP tools: {len(self.mcp_tools)} registered")

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
            elif module_name == "grep_search":
                from src.omnia.tools.grep_search import GrepSearchTools
                result = await GrepSearchTools.execute(name, args)
                return {"name": name, "result": result}
            elif module_name == "edit_diff":
                from src.omnia.tools.edit_diff import EditDiffTools
                result = await EditDiffTools.execute(name, args)
                return {"name": name, "result": result}
            elif module_name == "browser_fetch":
                from src.omnia.tools.browser_fetch import BrowserFetchTools
                result = await BrowserFetchTools.execute(name, args)
                return {"name": name, "result": result}
            elif module_name == "git_tools":
                from src.omnia.tools.git_tools import GitTools
                result = await GitTools.execute(name, args)
                return {"name": name, "result": result}
            elif module_name == "python_sandbox":
                from src.omnia.tools.python_sandbox import PythonSandbox
                result = await PythonSandbox.execute(name, args)
                return {"name": name, "result": result}
            elif module_name == "download_tools":
                from src.omnia.tools.download_tools import DownloadTools
                result = await DownloadTools.execute(name, args)
                return {"name": name, "result": result}
            elif module_name == "database_tools":
                from src.omnia.tools.database_tools import DatabaseTools
                result = await DatabaseTools.execute(name, args)
                return {"name": name, "result": result}
            elif module_name == "notification_tools":
                from src.omnia.tools.notification_tools import NotificationTools
                result = await NotificationTools.execute(name, args)
                return {"name": name, "result": result}
            elif module_name == "package_manager":
                from src.omnia.tools.package_manager import PackageManagerTools
                result = await PackageManagerTools.execute(name, args)
                return {"name": name, "result": result}
            elif module_name == "diff_tools":
                from src.omnia.tools.diff_tools import DiffTools
                result = await DiffTools.execute(name, args)
                return {"name": name, "result": result}
            elif module_name == "process_tools":
                from src.omnia.tools.process_tools import ProcessTools
                result = await ProcessTools.execute(name, args)
                return {"name": name, "result": result}
            elif module_name == "screenshot_tools":
                from src.omnia.tools.screenshot_tools import ScreenshotTools
                result = await ScreenshotTools.execute(name, args)
                return {"name": name, "result": result}
            elif module_name == "mcp":
                # 使用 MCP 管理器执行
                if self.mcp_manager:
                    try:
                        result = await self.mcp_manager.call_tool(name, args)
                        return {"name": name, "result": result}
                    except Exception as e:
                        return {"name": name, "error": f"MCP执行失败: {e}"}
                else:
                    return {"name": name, "error": "MCP管理器未初始化"}
        
        # 3. 尝试 MCP 工具执行
        if self.mcp_tools:
            try:
                from src.core.actuator.mcp_client import MCPClient
                client = MCPClient()
                result = await client.call_tool(name, args)
                return {"name": name, "result": result}
            except ImportError:
                pass
            except Exception as e:
                return {"name": name, "error": f"MCP执行失败: {e}"}
        
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

        # 注册搜索工具
        from src.omnia.tools.grep_search import GrepSearchTools
        grep_defs = GrepSearchTools.get_definitions()
        for tool_def in grep_defs:
            func_def = tool_def.get("function", {})
            name = func_def.get("name")
            if name:
                tool_def["_module"] = "grep_search"
                self._tools[name] = tool_def

        # 注册编辑工具
        from src.omnia.tools.edit_diff import EditDiffTools
        edit_defs = EditDiffTools.get_definitions()
        for tool_def in edit_defs:
            func_def = tool_def.get("function", {})
            name = func_def.get("name")
            if name:
                tool_def["_module"] = "edit_diff"
                self._tools[name] = tool_def

        # 注册网页工具
        from src.omnia.tools.browser_fetch import BrowserFetchTools
        browser_defs = BrowserFetchTools.get_definitions()
        for tool_def in browser_defs:
            func_def = tool_def.get("function", {})
            name = func_def.get("name")
            if name:
                tool_def["_module"] = "browser_fetch"
                self._tools[name] = tool_def

        # 注册 Git 工具
        from src.omnia.tools.git_tools import GitTools
        git_defs = GitTools.get_definitions()
        for tool_def in git_defs:
            func_def = tool_def.get("function", {})
            name = func_def.get("name")
            if name:
                tool_def["_module"] = "git_tools"
                self._tools[name] = tool_def

        # 注册 Python 沙箱工具
        from src.omnia.tools.python_sandbox import PythonSandbox
        sandbox_defs = PythonSandbox.get_definitions()
        for tool_def in sandbox_defs:
            func_def = tool_def.get("function", {})
            name = func_def.get("name")
            if name:
                tool_def["_module"] = "python_sandbox"
                self._tools[name] = tool_def

        # 注册下载工具
        from src.omnia.tools.download_tools import DownloadTools
        download_defs = DownloadTools.get_definitions()
        for tool_def in download_defs:
            func_def = tool_def.get("function", {})
            name = func_def.get("name")
            if name:
                tool_def["_module"] = "download_tools"
                self._tools[name] = tool_def

        # 注册数据库工具
        from src.omnia.tools.database_tools import DatabaseTools
        db_defs = DatabaseTools.get_definitions()
        for tool_def in db_defs:
            func_def = tool_def.get("function", {})
            name = func_def.get("name")
            if name:
                tool_def["_module"] = "database_tools"
                self._tools[name] = tool_def

        # 注册通知工具
        from src.omnia.tools.notification_tools import NotificationTools
        notify_defs = NotificationTools.get_definitions()
        for tool_def in notify_defs:
            func_def = tool_def.get("function", {})
            name = func_def.get("name")
            if name:
                tool_def["_module"] = "notification_tools"
                self._tools[name] = tool_def

        # 注册包管理工具
        from src.omnia.tools.package_manager import PackageManagerTools
        pkg_defs = PackageManagerTools.get_definitions()
        for tool_def in pkg_defs:
            func_def = tool_def.get("function", {})
            name = func_def.get("name")
            if name:
                tool_def["_module"] = "package_manager"
                self._tools[name] = tool_def

        # 注册文件对比工具
        from src.omnia.tools.diff_tools import DiffTools
        diff_defs = DiffTools.get_definitions()
        for tool_def in diff_defs:
            func_def = tool_def.get("function", {})
            name = func_def.get("name")
            if name:
                tool_def["_module"] = "diff_tools"
                self._tools[name] = tool_def

        # 注册进程管理工具（可选，可能有平台限制）
        try:
            from src.omnia.tools.process_tools import ProcessTools
            process_defs = ProcessTools.get_definitions()
            for tool_def in process_defs:
                func_def = tool_def.get("function", {})
                name = func_def.get("name")
                if name:
                    tool_def["_module"] = "process_tools"
                    self._tools[name] = tool_def
        except ImportError:
            pass

        # 注册截屏工具（可选，可能有平台限制）
        try:
            from src.omnia.tools.screenshot_tools import ScreenshotTools
            screen_defs = ScreenshotTools.get_definitions()
            for tool_def in screen_defs:
                func_def = tool_def.get("function", {})
                name = func_def.get("name")
                if name:
                    tool_def["_module"] = "screenshot_tools"
                    self._tools[name] = tool_def
        except ImportError:
            pass

        # 添加 MCP 工具到 _tools（如果已注册）
        if self.mcp_tools:
            for tool_def in self.mcp_tools:
                func_def = tool_def.get("function", {})
                name = func_def.get("name")
                if name and name not in self._tools:
                    tool_def_copy = dict(tool_def)
                    tool_def_copy["_module"] = "mcp"
                    self._tools[name] = tool_def_copy
            print(f"[ToolRegistry] MCP tools: {len(self.mcp_tools)} registered")

        return len(self._tools)


# 全局单例
tool_registry = ToolRegistry()
