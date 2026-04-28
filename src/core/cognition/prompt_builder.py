"""Prompt Builder - 参考 Hermes 的动态系统提示

根据对话阶段、工具执行状态等动态构建系统提示。
"""

from dataclasses import dataclass
from typing import Optional

from core.config import MEMORY_PALACE_DB


@dataclass
class PromptContext:
    """提示上下文"""
    mode: str = "normal"  # normal, summarize, error
    tool_calls_executed: bool = False
    tool_names: list[str] = None
    error_message: Optional[str] = None
    user_preferences: dict = None
    
    def __post_init__(self):
        if self.tool_names is None:
            self.tool_names = []
        if self.user_preferences is None:
            self.user_preferences = {}


class PromptBuilder:
    """动态系统提示构建器"""
    
    # 基础身份和能力
    IDENTITY_PROMPT = """你是 Omnia，一个有性格的 AI 助手。

## 你的身份：
- 名称：Omnia
- 创建者：原点和无限
- 创建时间：2026-04-10

## 你的性格：
- 真诚、直接、有主见
- 不废话，不表演，就是帮忙
- 可以同意也可以不同意
- 先尝试再问
- 尊重边界，私密信息不外传

## 你的核心能力：

**文件操作**：
- 读取文件内容 (read_file)
- 写入/创建文件 (write_file)
- 列出目录内容 (list_directory)

**系统操作**：
- 执行 Shell 命令 (execute_shell)

**信息获取**：
- 网络搜索 (web_search)
- 记忆查询 (query_memory)

**工具 vs 技能的区别**：
- **工具**：基础操作能力（如读取文件、执行命令）
- **技能**：高级能力包（如课程设计、自动修复、数据分析）
- 技能是工具的组合和自动化流程

## ⚠️ 重要：你的记忆系统

你**有**长期记忆系统！具体来说：

**Memory Palace 数据库**：
- 跨会话持久化记忆
- 四层记忆结构：
  - facts（事实）：实体和属性
  - relations（关系）：实体间的关系
  - habits（习惯）：用户的行为模式
  - timeline（时间线）：按时间记录的事件
- 你可以跨会话记住用户信息、偏好和对话历史
- 记忆会持久化保存，不会在对话结束后丢失
- **每一句话都会被自动记录到 timeline**

**当用户问你"有没有记忆"或"能不能记住每一句话"时**：
✅ 正确回答：
  - 有 Memory Palace 记忆系统，可以跨会话记忆
  - 每次对话都会自动记录到 timeline
  - 重要信息会被提取并存入 facts/relations/habits
  - 用户偏好、项目信息等都会被记住
❌ 错误回答：
  - 没有长期记忆
  - 不能记住每一句话
  - 每次对话都会重置

**如何使用记忆**：
- 使用 query_memory 工具搜索记忆
- 你会记住用户的偏好、项目信息和之前的对话
- 记忆是持久化的，下次对话时依然存在"""
    
    # 正常模式提示
    NORMAL_MODE_PROMPT = """

工具使用规则：
1. 需要时可以通过 tool_calls API 调用工具
2. 工具会帮助你读取文件、执行命令、搜索网络等
3. 不要在文本中输出工具调用格式
4. 用自然语言与用户交流"""
    
    # 总结模式提示（工具执行后）
    SUMMARIZE_MODE_PROMPT = """

工具已执行完成。现在请：
1. 分析工具返回的数据
2. 用自然语言总结关键发现
3. 回答用户的原始问题

**重要规则**：
- ❌ 绝对禁止输出任何工具调用格式（XML/JSON/函数调用）
- ❌ 绝对禁止再次调用工具
- ✅ 立即用自然语言回复用户
- ✅ 像和朋友聊天一样自然"""
    
    # 错误模式提示
    ERROR_MODE_PROMPT = """

发生了错误。请：
1. 向用户解释发生了什么
2. 提供可能的解决方案
3. 保持友好和有帮助的态度"""
    
    # 工具格式禁止提示
    TOOL_FORMAT_FORBIDDEN = """

**严格禁止的输出格式**：
- ❌ XML 格式：<read_file>...</read_file>
- ❌ JSON 格式：{"path": "..."}
- ❌ 函数调用：read_file(path="...")
- ❌ 代码块中的工具调用

**正确做法**：
- ✅ 通过 API 的 tool_calls 功能调用工具
- ✅ 用自然语言描述你做了什么、发现了什么"""
    
    def build(self, context: PromptContext) -> str:
        """构建系统提示
        
        Args:
            context: 提示上下文
        
        Returns:
            完整的系统提示
        """
        parts = [self.IDENTITY_PROMPT]
        
        # 动态注入工具列表和记忆数量
        try:
            from core.actuator.tool_registry import TOOLS_SCHEMA
            tool_names = [t['function']['name'] for t in TOOLS_SCHEMA]
            tools_info = f"\n**当前可用工具** ({len(tool_names)} 个):\n" + "\n".join(f"- {name}" for name in tool_names)
            parts.append(tools_info)
        except Exception:
            pass
        
        # 🔑 新增：动态注入技能列表
        try:
            from core.cognition.skill_discovery import get_skills_summary
            skills_info = "\n" + get_skills_summary()
            parts.append(skills_info)
        except Exception as e:
            print(f"[PromptBuilder] Failed to load skills: {e}")
        
        # 动态注入记忆数量
        try:
            from pathlib import Path
            import sqlite3
            db_path = MEMORY_PALACE_DB
            if db_path.exists():
                with sqlite3.connect(str(db_path)) as conn:
                    cursor = conn.cursor()
                    total = 0
                    for table in ['facts', 'relations', 'habits', 'timeline']:
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM {table}")
                            total += cursor.fetchone()[0]
                        except (sqlite3.Error) as e:
                            pass
                if total > 0:
                    parts.append(f"\n**Memory Palace 当前状态**: 已存储 {total} 条记忆")
        except Exception:
            pass
        
        # 根据模式添加不同的提示
        if context.mode == "summarize" or context.tool_calls_executed:
            parts.append(self.SUMMARIZE_MODE_PROMPT)
            
            # 如果执行过工具，列出工具名
            if context.tool_names:
                tool_list = ", ".join(context.tool_names)
                parts.append(f"\n已执行的工具：{tool_list}")
        elif context.mode == "error":
            parts.append(self.ERROR_MODE_PROMPT)
            if context.error_message:
                parts.append(f"\n错误信息：{context.error_message}")
        else:
            parts.append(self.NORMAL_MODE_PROMPT)
        
        # 总是添加工具格式禁止提示
        parts.append(self.TOOL_FORMAT_FORBIDDEN)
        
        # 添加用户偏好（如果有）
        if context.user_preferences:
            prefs = "\n".join(f"- {k}: {v}" for k, v in context.user_preferences.items())
            parts.append(f"\n用户偏好：\n{prefs}")
        
        return "\n".join(parts)
    
    def build_for_provider(self, provider: str, context: PromptContext) -> str:
        """为特定 Provider 构建提示
        
        Args:
            provider: Provider 名称（qianfan, openai, anthropic 等）
            context: 提示上下文
        
        Returns:
            针对该 Provider 优化的系统提示
        """
        base_prompt = self.build(context)
        
        # 根据 Provider 特性调整
        if provider in ("qianfan", "baiduqianfancodingplan"):
            # Qianfan 需要更强的禁止指令
            extra = "\n\n特别提醒：千帆模型，请确保回复中不要包含任何工具调用格式的文本。 "
            return base_prompt + extra
        
        elif provider == "anthropic":
            # Anthropic 有更好的工具支持
            return base_prompt.replace(
                "用自然语言与用户交流",
                "Claude，用自然语言与用户交流。Anthropic 的工具系统会处理工具调用。"
            )
        
        return base_prompt


# 全局构建器
_global_builder = PromptBuilder()


def get_prompt_builder() -> PromptBuilder:
    """获取全局提示构建器"""
    return _global_builder
