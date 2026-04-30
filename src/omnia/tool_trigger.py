"""
tool_trigger.py — 统一工具触发判断模块

整合 chat_handler.py 和 tool_preroll.py 的触发逻辑，
提供统一的工具调用判断接口。

设计原则：
1. 宁可多触发，不可漏触发
2. 支持正则表达式和模糊匹配
3. 上下文感知（考虑历史消息）
"""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ToolTriggerResult:
    """工具触发判断结果"""
    should_trigger: bool
    trigger_type: str  # "keyword", "context", "explicit", "promise"
    matched_keyword: Optional[str] = None
    confidence: float = 0.0
    suggested_tools: List[str] = None
    
    def __post_init__(self):
        if self.suggested_tools is None:
            self.suggested_tools = []


# ─── 核心关键词定义 ───
# 分类整理，便于维护和扩展

KEYWORD_CATEGORIES = {
    # 文件操作类
    "file_ops": {
        "keywords": [
            "读文件", "读取", "read", "cat ", "查看文件", "检查文件",
            "看看文件", "文件内容", "读一下", "打开文件",
            "write", "写文件", "保存文件", "修改文件",
            "list", "列出", "目录", "文件夹", "ls ", "dir ",
        ],
        "tools": ["read_file", "write_file", "list_directory"],
    },
    
    # 命令执行类
    "command_exec": {
        "keywords": [
            "执行", "运行", "跑一下", "跑个", "命令", "cmd", "shell",
            "bash", "终端", "命令行", "execute", "run ",
        ],
        "tools": ["execute_shell"],
    },
    
    # 状态检查类（高频场景）
    "status_check": {
        "keywords": [
            # 中文
            "检查", "确认", "验证", "核实", "查一下", "看一下", "看看",
            "检查一下", "看一下", "检测", "测试", "试一下",
            "改好了吗", "生效了吗", "有没有生效", "完成了吗", "成功了吗",
            "好了没", "有没有问题", "状态", "怎么样了", "效果",
            "分析", "重新分析", "完整分析", "全面分析", "深入分析",
            "查看", "查看一下", "确认一下", "验证一下",
            # 英文
            "check", "verify", "confirm", "test", "analyze",
            "status", "state",
        ],
        "tools": ["execute_shell", "read_file", "list_directory"],
    },
    
    # Git 相关
    "git_ops": {
        "keywords": [
            "git", "提交", "commit", "push", "pull", "branch", "分支",
            "有没有提交", "生效了没", "提交记录", "git log", "git status",
            "改了什么", "最近提交", "代码提交",
        ],
        "tools": ["execute_shell"],
    },
    
    # 服务/进程检查
    "service_check": {
        "keywords": [
            "服务", "运行", "启动", "端口", "进程", "daemon", "守护",
            "重启", "在线", "离线", "监听", "5001", "8765",
        ],
        "tools": ["execute_shell"],
    },
    
    # 网络搜索
    "web_search": {
        "keywords": [
            "搜索", "查找", "search", "google", "百度", "bing",
            "网上", "网络", "最新", "新闻", "文档",
        ],
        "tools": ["web_search"],
    },
    
    # 记忆查询
    "memory_query": {
        "keywords": [
            "记忆", "回忆", "remember", "之前", "上次", "历史",
            "记住", "忘记", "recall", "memory",
        ],
        "tools": ["query_memory"],
    },
    
    # 代码分析
    "code_analysis": {
        "keywords": [
            "代码", "函数", "方法", "类", "class ", "def ", "function",
            "实现", "逻辑", "算法", "源码", "源代码",
            "分析代码", "理解代码", "解释代码",
        ],
        "tools": ["read_file", "execute_shell"],
    },
}


# ─── 上下文触发规则 ───
# 基于历史消息判断是否需要工具

CONTEXT_TRIGGER_PATTERNS = [
    # 助手承诺检查但未执行
    (r"让我(检查|看看|查一下|读一下|验证)", "promise"),
    (r"我(来|会|将)(检查|看看|读取|验证)", "promise"),
    (r"(需要|应该)(调用|使用)工具", "promise"),
    
    # 用户追问（暗示上次回答不完整）
    (r"然后呢", "follow_up"),
    (r"继续", "follow_up"),
    (r"还有呢", "follow_up"),
    (r"具体(是|有)什么", "follow_up"),
]



# ─── 排除规则 ───
# 这些场景不应该触发工具调用

EXCLUDE_PATTERNS = [
    # 创意生成
    r"写.*诗", r"作.*诗", r"写.*歌", r"作.*歌",
    r"写.*故事", r"讲.*故事",
    # 纯闲聊
    r"^你好", r"^嗨", r"^hi", r"^hello",
    r"^再见", r"^bye",
    # 纯知识问答
    r"^什么是", r"^为什么是", r"^如何.*吗$",
]


def analyze_message(
    user_message: str,
    last_assistant_message: str = "",
    history: List[dict] = None,
) -> ToolTriggerResult:
    """
    综合分析是否需要触发工具调用。
    
    Args:
        user_message: 当前用户消息
        last_assistant_message: 上一条助手消息
        history: 历史消息列表
    
    Returns:
        ToolTriggerResult: 触发判断结果
    """
    user_lower = user_message.lower()
    
    # 0. 排除检查（优先级最高）
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, user_message, re.IGNORECASE):
            return ToolTriggerResult(
                should_trigger=False,
                trigger_type="excluded",
                confidence=0.0,
                suggested_tools=[],
            )
    
    # 1. 显式工具请求（最高优先级）
    explicit_patterns = [
        r"(调用|使用|执行)(工具|tool)",
        r"用工具(查|看|检查|分析)",
        r"tool_call",
    ]
    for pattern in explicit_patterns:
        if re.search(pattern, user_lower):
            return ToolTriggerResult(
                should_trigger=True,
                trigger_type="explicit",
                matched_keyword=pattern,
                confidence=1.0,
                suggested_tools=["read_file", "execute_shell", "list_directory"],
            )
    
    # 2. 关键词匹配
    all_keywords = []
    for category, data in KEYWORD_CATEGORIES.items():
        for kw in data["keywords"]:
            if kw.lower() in user_lower:
                return ToolTriggerResult(
                    should_trigger=True,
                    trigger_type="keyword",
                    matched_keyword=kw,
                    confidence=0.9,
                    suggested_tools=data["tools"],
                )
            all_keywords.append((kw, data["tools"]))
    
    # 3. 上下文触发（基于历史消息）
    if last_assistant_message:
        for pattern, trigger_type in CONTEXT_TRIGGER_PATTERNS:
            if re.search(pattern, last_assistant_message, re.IGNORECASE):
                return ToolTriggerResult(
                    should_trigger=True,
                    trigger_type=trigger_type,
                    matched_keyword=pattern,
                    confidence=0.8,
                    suggested_tools=["read_file", "execute_shell", "list_directory"],
                )
    
    # 4. 模糊匹配（编辑距离）
    # 对于短消息（< 20 字），更积极地触发
    if len(user_message) < 20:
        # 检查是否包含动词
        verbs = ["看", "查", "检", "测", "试", "读", "写", "跑", "执"]
        for v in verbs:
            if v in user_message:
                return ToolTriggerResult(
                    should_trigger=True,
                    trigger_type="keyword",
                    matched_keyword=v,
                    confidence=0.7,
                    suggested_tools=["read_file", "execute_shell"],
                )
    
    # 5. 历史消息分析（如果提供了）
    if history and len(history) > 0:
        # 检查最近 3 轮是否有未完成的工具请求
        recent = history[-6:] if len(history) >= 6 else history
        for msg in recent:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                # 助手提到需要工具但未调用
                if re.search(r"需要(检查|查看|读取|验证)", content):
                    return ToolTriggerResult(
                        should_trigger=True,
                        trigger_type="context",
                        matched_keyword="历史未完成",
                        confidence=0.6,
                        suggested_tools=["read_file", "execute_shell"],
                    )
    
    return ToolTriggerResult(
        should_trigger=False,
        trigger_type="none",
        confidence=0.0,
    )


def get_tool_choice_for_provider(
    result: ToolTriggerResult,
    provider: str,
) -> Optional[str]:
    """
    根据 Provider 和触发结果决定 tool_choice 参数。
    
    Args:
        result: 触发判断结果
        provider: Provider 名称
    
    Returns:
        "required" - 强制调用
        "auto" - 建议调用
        None - API 默认行为
    """
    if not result.should_trigger:
        return None
    
    # 支持强制调用的 Provider
    providers_support_required = ["kimi", "openai", "anthropic"]
    
    if provider.lower() in providers_support_required:
        # 高置信度时强制调用
        if result.confidence >= 0.8:
            return "required"
        else:
            return "auto"
    else:
        # DeepSeek 等不支持 required，返回 auto 或 None
        if result.confidence >= 0.7:
            return "auto"
        return None


def get_suggested_tool_prompt(result: ToolTriggerResult) -> str:
    """
    生成建议工具使用的提示文本。
    用于不支持 tool_choice: required 的 Provider。
    """
    if not result.should_trigger:
        return ""
    
    tools = result.suggested_tools or []
    if not tools:
        return ""
    
    tool_hints = {
        "read_file": "read_file(path='...') 读取文件内容",
        "write_file": "write_file(path='...', content='...') 写入文件",
        "execute_shell": "execute_shell(command='...') 执行 shell 命令",
        "list_directory": "list_directory(path='...') 列出目录内容",
        "web_search": "web_search(query='...') 搜索网络",
        "query_memory": "query_memory(query='...') 查询记忆",
    }
    
    suggestions = [tool_hints.get(t, t) for t in tools[:3]]
    
    return f"""
⚠️ 检测到可能需要使用工具。建议的工具：
{chr(10).join('- ' + s for s in suggestions)}

请先调用工具获取信息，再回答用户问题。
"""


# ─── 兼容旧接口 ───

def should_require_tool(user_message: str, provider: str = "deepseek") -> Optional[str]:
    """
    兼容 chat_handler.py 的旧接口。
    """
    result = analyze_message(user_message)
    return get_tool_choice_for_provider(result, provider)


def should_force_tool_check(user_message: str, last_assistant_message: str = "") -> bool:
    """
    兼容 tool_preroll.py 的旧接口。
    """
    result = analyze_message(user_message, last_assistant_message)
    return result.should_trigger
