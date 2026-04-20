"""Auto Memory Hook - 自动记忆存储

在每次对话结束后，自动提取、归纳、存储重要信息到 Memory Palace。

核心策略：
1. 智能提取：从对话中提取事实、关系、习惯
2. 去重：避免重复存储相同信息
3. 归纳：合并相似信息，更新强度
4. 持久化：存储到 Memory Palace

参考：
- OpenClaw 的 verbatim-memory 系统
- Hermes 的记忆管理器
- FreeCode 的上下文引擎
"""

import json
import re
from datetime import datetime, date
from typing import Optional, List, Tuple, Dict, Any

from core.plugin.hooks import register_hook, HookType, HookContext
from core.memory_palace import MemoryPalace


# 全局 Memory Palace 实例
_memory_palace = None


def get_memory_palace() -> MemoryPalace:
    """获取 Memory Palace 单例"""
    global _memory_palace
    if _memory_palace is None:
        from core.config import MEMORY_PALACE_DB
        _memory_palace = MemoryPalace(str(MEMORY_PALACE_DB))
        _memory_palace.initialize()
    return _memory_palace


def extract_important_info(user_msg: str, assistant_msg: str) -> dict:
    """提取对话中的重要信息
    
    Returns:
        {
            "facts": [(category, key, value), ...],
            "relations": [(subject, predicate, object, context), ...],
            "habits": [(domain, pattern, certainty), ...],
            "timeline_summary": str or None
        }
    """
    result = {
        "facts": [],
        "relations": [],
        "habits": [],
        "timeline_summary": None
    }
    
    # 模式1: 用户偏好
    preference_patterns = [
        (r"我喜欢(.+)", "preference", "喜欢"),
        (r"我偏好(.+)", "preference", "偏好"),
        (r"我想要(.+)", "goal", "想要"),
        (r"我不喜欢(.+)", "preference", "不喜欢"),
        (r"我希望(.+)", "goal", "希望"),
        (r"我的(.+)是(.+)", "profile", None),
    ]
    
    for pattern, category, label in preference_patterns:
        matches = re.findall(pattern, user_msg)
        for match in matches:
            if isinstance(match, tuple) and len(match) >= 2:
                result["facts"].append((category, match[0], match[1]))
            elif isinstance(match, tuple) and len(match) == 1:
                result["facts"].append((category, label or "用户偏好", match[0]))
            else:
                result["facts"].append((category, label or "用户偏好", str(match)))
    
    # 模式2: 项目信息
    project_patterns = [
        r"项目[名称]?[是为]?(.+)",
        r"正在做(.+)",
        r"开发(.+)",
        r"在(.+)工作",
    ]
    
    for pattern in project_patterns:
        matches = re.findall(pattern, user_msg)
        for match in matches:
            result["facts"].append(("project", "当前项目", str(match)))
    
    # 模式3: 决策记录
    decision_keywords = ["决定", "选择", "采用", "确定", "同意", "确认"]
    if any(kw in assistant_msg for kw in decision_keywords):
        # 提取决策内容
        result["timeline_summary"] = f"用户决策: {user_msg[:100]}"
    
    # 模式4: 关系提取
    relation_patterns = [
        (r"(.+)是(.+)的(.+)", lambda m: (m[0], m[2], m[1])),
        (r"(.+)属于(.+)", lambda m: (m[0], "属于", m[1])),
        (r"(.+)包含(.+)", lambda m: (m[0], "包含", m[1])),
    ]
    
    for pattern, extractor in relation_patterns:
        matches = re.findall(pattern, user_msg)
        for match in matches:
            try:
                subject, predicate, obj = extractor(match)
                result["relations"].append((subject, predicate, obj, user_msg[:50]))
            except:
                pass
    
    # 模式5: 习惯提取
    habit_keywords = ["总是", "经常", "习惯", "每次", "通常"]
    for kw in habit_keywords:
        if kw in user_msg:
            result["habits"].append(("general", user_msg[:100], 0.7))
            break
    
    return result


def should_store_memory(user_msg: str, assistant_msg: str) -> bool:
    """判断是否需要存储这次对话"""
    
    # 跳过太短的用户消息
    if len(user_msg) < 5:
        return False
    
    # 跳过纯问候
    simple_patterns = [
        r"^(你好|hi|hello|谢谢|thank|ok|好的|嗯)$",
    ]
    
    for pattern in simple_patterns:
        if re.match(pattern, user_msg.lower().strip()):
            return False
    
    # 包含重要关键词
    important_keywords = [
        "项目", "偏好", "喜欢", "决定", "计划", "目标",
        "记住", "记得", "保存", "存储", "创建", "配置",
        "重要", "关键", "核心", "必须", "需要", "开发",
        "正在", "我的", "我们", "我正在", "我决定"
    ]
    
    if any(kw in user_msg for kw in important_keywords):
        return True
    
    # 工具执行（表示有实际行动）
    if "execute_shell" in assistant_msg or "read_file" in assistant_msg or "write_file" in assistant_msg:
        return True
    
    # 默认：存储所有有意义的对话
    return len(user_msg) >= 10


@register_hook(HookType.ON_MESSAGE, priority=100, name="auto_memory_storage")
def auto_store_memory(context: HookContext):
    """自动存储对话到 Memory Palace
    
    触发时机：每次消息处理时
    策略：智能提取 + 去重 + 归纳
    """
    
    # 获取消息
    message = context.message
    if not message:
        return
    
    print(f"[Hook:auto_memory] Processing message: {message[:50]}...")
    
    # 从 metadata 获取完整对话
    if context.metadata:
        conversation = context.metadata.get("conversation", {})
        user_msg = conversation.get("user", message)
        assistant_msg = conversation.get("assistant", "")
        
        if should_store_memory(user_msg, assistant_msg):
            # 提取重要信息
            info = extract_important_info(user_msg, assistant_msg)
            
            # 存储到 Memory Palace
            palace = get_memory_palace()
            
            # 存储事实
            for category, key, value in info["facts"]:
                palace.remember_fact(category, key, value, source="conversation")
                print(f"[Hook:auto_memory] Stored fact: {category}.{key} = {value[:30]}...")
            
            # 存储关系
            for subject, predicate, obj, ctx in info["relations"]:
                palace.remember_relation(subject, predicate, obj, context=ctx)
                print(f"[Hook:auto_memory] Stored relation: {subject} -> {predicate} -> {obj}")
            
            # 存储习惯
            for domain, pattern, certainty in info["habits"]:
                palace.remember_habit(domain, pattern, certainty=certainty)
                print(f"[Hook:auto_memory] Stored habit: {domain}")
            
            # 存储时间线
            if info["timeline_summary"]:
                palace.remember_timeline(
                    event_type="decision",
                    content=info["timeline_summary"],
                    metadata={"user_message": user_msg[:200]}
                )
                print(f"[Hook:auto_memory] Stored timeline: {info['timeline_summary'][:50]}...")
    
    return None


@register_hook(HookType.POST_RESPONSE, priority=100, name="auto_memory_after_response")
def auto_store_after_response(context: HookContext):
    """在响应完成后自动存储对话
    
    这是主要的自动记忆入口点。
    """
    
    response = context.response
    if not response:
        return
    
    # 从 metadata 获取完整对话
    if not context.metadata:
        return
    
    user_msg = context.metadata.get("user_message", "")
    assistant_msg = response
    
    if not user_msg:
        return
    
    print(f"[Hook:auto_memory] Storing conversation after response...")
    
    # 判断是否需要存储
    if not should_store_memory(user_msg, assistant_msg):
        return
    
    # 提取重要信息
    info = extract_important_info(user_msg, assistant_msg)
    
    # 存储到 Memory Palace
    palace = get_memory_palace()
    
    # 存储事实
    for category, key, value in info["facts"]:
        palace.remember_fact(category, key, value, source="conversation")
        print(f"[Hook:auto_memory] ✓ Fact: {category}.{key}")
    
    # 存储关系
    for subject, predicate, obj, ctx in info["relations"]:
        palace.remember_relation(subject, predicate, obj, context=ctx)
        print(f"[Hook:auto_memory] ✓ Relation: {subject} -> {predicate} -> {obj}")
    
    # 存储习惯
    for domain, pattern, certainty in info["habits"]:
        palace.remember_habit(domain, pattern, certainty=certainty)
        print(f"[Hook:auto_memory] ✓ Habit: {domain}")
    
    # 存储时间线
    if info["timeline_summary"]:
        palace.remember_timeline(
            event_type="decision",
            content=info["timeline_summary"],
            metadata={"user_message": user_msg[:200], "assistant_message": assistant_msg[:200]}
        )
        print(f"[Hook:auto_memory] ✓ Timeline: {info['timeline_summary'][:50]}...")
    
    # 总是存储对话到时间线
    palace.remember_timeline(
        event_type="conversation",
        content=f"用户: {user_msg[:100]}",
        metadata={"full_user": user_msg, "full_assistant": assistant_msg[:500]}
    )
    
    return None


@register_hook(HookType.POST_TOOL_USE, priority=50, name="extract_tool_knowledge")
def extract_knowledge_from_tool_use(context: HookContext):
    """从工具使用中提取知识
    
    当工具执行成功后，提取有价值的信息存储到 Memory Palace。
    """
    
    tool_name = context.tool_name
    tool_args = context.tool_args or {}
    tool_result = context.tool_result
    
    if not tool_name or not tool_result:
        return
    
    print(f"[Hook:auto_memory] Extracting knowledge from tool: {tool_name}")
    
    palace = get_memory_palace()
    
    # 根据工具类型提取不同的知识
    if tool_name == "read_file":
        # 记录文件访问
        file_path = tool_args.get("path", "unknown")
        palace.remember_timeline(
            event_type="file_access",
            content=f"读取文件: {file_path}",
            metadata={"tool": tool_name, "path": file_path}
        )
    
    elif tool_name == "write_file":
        # 记录文件修改
        file_path = tool_args.get("path", "unknown")
        palace.remember_timeline(
            event_type="file_modification",
            content=f"写入文件: {file_path}",
            metadata={"tool": tool_name, "path": file_path}
        )
    
    elif tool_name == "execute_shell":
        # 记录命令执行
        command = tool_args.get("command", "unknown")
        palace.remember_timeline(
            event_type="command",
            content=f"执行命令: {command[:50]}",
            metadata={"tool": tool_name, "command": command}
        )
    
    elif tool_name == "web_search":
        # 记录搜索历史
        query = tool_args.get("query", "unknown")
        palace.remember_fact(
            category="search_history",
            key=query[:50],
            value=str(tool_result)[:200] if tool_result else "",
            source="web_search"
        )
    
    return None


# 初始化时打印日志
print("[AutoMemory] Hook registered: ON_MESSAGE -> auto_store_memory")
print("[AutoMemory] Hook registered: POST_RESPONSE -> auto_store_after_response")
print("[AutoMemory] Hook registered: POST_TOOL_USE -> extract_tool_knowledge")
