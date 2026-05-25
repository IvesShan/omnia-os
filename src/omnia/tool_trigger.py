"""
tool_trigger.py — 统一工具触发判断模块

整合了:
- chat_handler.py 的触发逻辑
- tool_preroll.py 的前置检查逻辑

设计原则：
1. 宁可多触发，不可漏触发
2. 支持正则表达式和模糊匹配
3. 上下文感知（考虑历史消息）
4. 前置检查（某些场景直接执行并注入结果）
"""

import re
import subprocess
from typing import List, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ToolTriggerResult:
    """工具触发判断结果"""
    should_trigger: bool
    trigger_type: str  # "keyword", "context", "explicit", "promise", "preroll"
    matched_keyword: Optional[str] = None
    confidence: float = 0.0
    suggested_tools: List[str] = None
    
    def __post_init__(self):
        if self.suggested_tools is None:
            self.suggested_tools = []


# ─── 核心关键词定义 ───
# 简化版：只保留最关键的关键词

KEYWORD_CATEGORIES = {
    # 文件操作类
    "file_ops": {
        "keywords": [
            "读文件", "读取", "read", "查看文件", "检查文件",
            "看看文件", "文件内容", "读一下", "打开文件",
            "write", "写文件", "保存文件", "修改文件",
            "list", "列出", "目录", "文件夹", "ls ", "dir ",
        ],
        "tools": ["read_file", "write_file", "list_directory"],
    },
    
    # 命令执行类
    "command_exec": {
        "keywords": [
            "执行", "运行", "跑一下", "跑个", "命令", "shell",
            "bash", "终端", "命令行", "execute",
        ],
        "tools": ["execute_shell"],
    },
    
    # 状态检查类（高频场景）
    "status_check": {
        "keywords": [
            "检查", "确认", "验证", "查一下", "看一下", "看看",
            "检测", "测试", "试一下", "改好了吗", "生效了吗",
            "状态", "怎么样了", "分析",
        ],
        "tools": ["execute_shell", "read_file", "list_directory"],
    },
    
    # Git 相关
    "git_ops": {
        "keywords": [
            "git", "提交", "commit", "push", "pull", "branch", "分支",
            "提交记录", "git log", "git status",
        ],
        "tools": ["execute_shell"],
    },
    
    # 服务/进程检查
    "service_check": {
        "keywords": [
            "服务", "运行", "启动", "端口", "进程", "daemon",
            "重启", "在线", "监听",
        ],
        "tools": ["execute_shell"],
    },
    
    # 网络搜索
    "web_search": {
        "keywords": ["搜索", "search", "google", "最新", "文档"],
        "tools": ["web_search"],
    },
    
    # 记忆查询
    "memory_query": {
        "keywords": ["记忆", "回忆", "之前", "上次", "历史"],
        "tools": ["query_memory"],
    },
}

# ─── 前置检查规则 ───
# 这些场景直接执行命令并注入结果，不需要模型决策

PROJECT_ROOT = Path(__file__).parent.parent.parent

PREROLL_RULES = [
    # Git 状态
    (r"(git|提交|commit|有没有提交|提交记录)",
     [
         ("Git状态", f"git -C {PROJECT_ROOT} status --short 2>/dev/null | head -20 || echo '不是git仓库'"),
         ("最近提交", f"git -C {PROJECT_ROOT} log --oneline -5 2>/dev/null || echo '不是git仓库'"),
     ]),
    
    # 服务/端口检查
    (r"(服务|运行|端口|5001|8765|进程|daemon|重启.*成功)",
     [
         ("端口监听", "ss -tlnp 2>/dev/null | grep -E '5001|8765' || echo '无相关端口'"),
     ]),
]

# ─── 排除规则 ───

EXCLUDE_PATTERNS = [
    r"写.*诗", r"作.*诗", r"写.*歌",
    r"^你好", r"^嗨", r"^hi", r"^hello",
    r"^再见", r"^bye",
]


def analyze_message(
    user_message: str,
    last_assistant_message: str = "",
    history: List[dict] = None,
) -> ToolTriggerResult:
    """
    综合分析是否需要触发工具调用。
    """
    # 处理 content 可能是列表的情况（vision 多模态格式）
    if isinstance(user_message, list):
        texts = [item.get("text", "") for item in user_message if isinstance(item, dict) and item.get("type") == "text"]
        user_message = "\n".join(texts)

    user_lower = user_message.lower()
    
    # 0. 排除检查
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, user_message, re.IGNORECASE):
            return ToolTriggerResult(
                should_trigger=False,
                trigger_type="excluded",
                confidence=0.0,
            )
    
    # 1. 显式工具请求
    if re.search(r"(调用|使用|执行)(工具|tool)", user_lower):
        return ToolTriggerResult(
            should_trigger=True,
            trigger_type="explicit",
            confidence=1.0,
            suggested_tools=["read_file", "execute_shell", "list_directory"],
        )
    
    # 2. 关键词匹配
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
    
    # 3. 上下文触发（助手承诺但未执行）
    if last_assistant_message:
        if re.search(r"让我(检查|看看|查一下)", last_assistant_message, re.IGNORECASE):
            return ToolTriggerResult(
                should_trigger=True,
                trigger_type="promise",
                confidence=0.8,
                suggested_tools=["read_file", "execute_shell"],
            )
    
    # 4. 短消息模糊匹配
    if len(user_message) < 20:
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
    """
    if not result.should_trigger:
        return None
    
    # 支持强制调用的 Provider
    providers_support_required = ["kimi", "openai", "anthropic"]
    
    if provider.lower() in providers_support_required:
        if result.confidence >= 0.8:
            return "required"
        else:
            return "auto"
    else:
        # DeepSeek 等不支持 required
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


# ─── 前置检查功能（从 tool_preroll.py 合并）───

def check_and_run(user_message: str) -> str:
    """
    前置工具检查：直接执行命令并返回结果。
    用于某些确定性的场景（如 git status）。
    """
    results = []
    
    for pattern, commands in PREROLL_RULES:
        if re.search(pattern, user_message, re.IGNORECASE):
            results.append(f"🔍 [前置检查] 命中: '{pattern}'")
            for desc, cmd in commands:
                try:
                    result = subprocess.run(
                        cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )
                    output = result.stdout.strip() or result.stderr.strip() or "(无输出)"
                    if len(output) > 300:
                        output = output[:300] + "..."
                    results.append(f"  📋 {desc}:")
                    results.append(f"    {output}")
                except subprocess.TimeoutExpired:
                    results.append(f"  ⏱️ {desc}: 超时")
                except Exception as e:
                    results.append(f"  ❌ {desc}: 错误 - {e}")
            break
    
    return "\n".join(results) if results else ""


def should_force_tool_check(user_message: str, last_assistant_message: str = "") -> bool:
    """
    判断是否应该强制执行工具检查。
    """
    result = analyze_message(user_message, last_assistant_message)
    return result.should_trigger


# ─── 兼容旧接口 ───

def should_require_tool(user_message: str, provider: str = "deepseek") -> Optional[str]:
    """兼容 chat_handler.py 的旧接口"""
    result = analyze_message(user_message)
    return get_tool_choice_for_provider(result, provider)
