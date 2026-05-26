"""
tool_call_validator.py — 工具调用验证器（v2.0 修复版）

修复内容：
1. 区分"虚假声称已完成"和"表达意图但未调用"——后者是 API 兼容性问题，不应 retry
2. 添加 text-based fallback：当 native tool_calls 失败时，尝试从文本解析工具调用
3. 添加最大 retry 次数限制（2次），防止无限循环
4. 清理过度激进的检测模式
"""

import re
from typing import List, Dict, Tuple


# ====== 虚假声称检测：只检测"声称已完成"，不检测"表达意图" ======
# 
# 根本区别：
# - "已修复"/"已完成" → 模型声称已经做了某事但没工具调用 → 这是幻觉，需要 retry
# - "我需要调用"/"让我来查看" → 模型表达要做某事但 API 没返回 tool_calls → 
#   这是 API/模型兼容性问题，retry 没用，应该用 text fallback
#
FALSE_CLAIM_PATTERNS = [
    # 已完成类（这些才是虚假声称）
    r"已(经)?修复",
    r"已(经)?完成",
    r"已(经)?修改",
    r"已(经)?创建",
    r"已(经)?删除",
    r"已(经)?提交",
    r"已(经)?执行",
    r"已(经)?上传",
    r"已(经)?部署",
    r"成功(修复|修改|创建|删除|提交|执行|上传|部署)",
    r"修复完成",
    r"修改完成",
    r"创建完成",
    r"删除完成",
    r"执行完成",
    r"✅\s*(完成|修复|修改|创建|删除|提交|执行|成功)",
]

# 意图表达类——这些不应该触发 retry
# 它们只是模型在解释自己要做什么，不是虚假声称
INTENT_PATTERNS = [
    r"让我来(查看|检查|读取|分析|诊断|搜索)",
    r"我(来|先)(查看|检查|读取|分析|诊断|搜索)",
    r"我需要?(先)?(查看|检查|读取|分析|诊断|搜索)",
    r"我(将|会|要)(尝试|查看|检查|读取|分析|诊断|搜索)",
]

# 需要工具操作的关键词（用于判断用户请求是否需要工具）
TOOL_REQUIRED_KEYWORDS = [
    "修复", "修改", "创建", "删除", "提交", "执行", "检查", "查看",
    "读取", "写入", "运行", "测试", "分析", "诊断", "安装", "部署",
    "搜索", "查找", "更新", "添加",
]

# 工具名提取模式（用于 text-based fallback）
TOOL_NAME_MAP = {
    "read_file": ["read_file", "读取文件", "读取", "查看文件", "查看"],
    "write_file": ["write_file", "写入文件", "保存文件", "写文件"],
    "execute_shell": ["execute_shell", "执行命令", "运行命令", "shell", "命令行", "终端"],
    "list_directory": ["list_directory", "列出目录", "查看目录", "目录", "ls"],
    "web_search": ["web_search", "搜索网络", "网络搜索", "搜索", "google"],
    "search_files": ["search_files", "搜索文件", "grep", "查找文件"],
    "edit_file": ["edit_file", "精确编辑", "替换文本"],
    "apply_diff": ["apply_diff", "应用diff", "diff补丁"],
    "fetch_page": ["fetch_page", "抓取网页", "网页抓取", "浏览网页", "访问网页"],
    "query_memory": ["query_memory", "查询记忆", "搜索记忆"],
    "save_memory": ["save_memory", "保存记忆", "记录记忆"],
}


def detect_false_claim(
    response: str,
    tool_calls: List[Dict],
    user_message: str,
) -> Tuple[bool, str, str]:
    """
    检测模型是否虚假声称已完成了操作
    
    Returns:
        (is_false_claim, reason, suggestion)
        is_false_claim=True: 模型声称已完成，但实际没调用工具 → 需要 retry
        is_false_claim=False: 没有虚假声称
    """
    # 如果有工具调用，不是虚假声称
    if tool_calls:
        return False, "", ""

    # 检查用户消息是否需要工具操作
    needs_tool = any(kw in user_message for kw in TOOL_REQUIRED_KEYWORDS)
    if not needs_tool:
        return False, "", ""

    # 只检查"已完成"类声称
    for pattern in FALSE_CLAIM_PATTERNS:
        if re.search(pattern, response):
            return True, f"检测到虚假声称：'{pattern}'，但没有实际工具调用", "强制重试"

    return False, "", ""


def detect_expressed_intent(response: str) -> Tuple[bool, List[str]]:
    """
    检测模型是否在文本中表达了工具调用意图（但不是虚假声称）
    
    Returns:
        (has_intent, mentioned_tools)
        has_intent=True: 模型表达了要做某事的意图，但没有 tool_calls
        这通常意味着 API 兼容性 issues，不应 retry，而应尝试 text fallback
    """
    mentioned_tools = []
    
    # 检查是否提到了工具名
    for tool_name, keywords in TOOL_NAME_MAP.items():
        for kw in keywords:
            if kw in response:
                # 排除明显不是工具调用的上下文
                # 例如："你可以使用 read_file" 是建议，不是意图
                if re.search(rf"(?:我要|我来|让我|我需要|我将|我会|使用|调用|执行)\s+.*{re.escape(kw)}", response):
                    mentioned_tools.append(tool_name)
                    break
    
    # 检查意图表达
    has_intent = any(re.search(p, response) for p in INTENT_PATTERNS)
    
    return has_intent, list(set(mentioned_tools))


def extract_tool_call_from_text(response: str) -> Dict:
    """
    从模型文本回复中提取工具调用（text-based fallback）
    
    支持的格式：
    1. JSON: {"name": "read_file", "arguments": {"path": "/tmp/test.txt"}}
    2. 简写: read_file(path="/tmp/test.txt")
    3. Markdown: ```json\n{"tool": "read_file", "args": {"path": "/tmp/test.txt"}}\n```
    """
    # 尝试提取 JSON 代码块
    json_blocks = re.findall(r'```(?:json)?\s*\n?(.*?)\n?```', response, re.DOTALL)
    for block in json_blocks:
        block = block.strip()
        try:
            import json
            data = json.loads(block)
            if isinstance(data, dict):
                # 检查是否是工具调用格式
                name = data.get("name") or data.get("tool") or data.get("function")
                args = data.get("arguments") or data.get("args") or data.get("input") or data.get("parameters", {})
                if name and name in TOOL_NAME_MAP:
                    return {"name": name, "arguments": args}
        except:
            pass
    
    # 尝试内联 JSON
    inline_json = re.findall(r'\{\s*"(?:name|tool|function)"\s*:\s*"(\w+)"\s*,\s*"(?:arguments|args|input|parameters)"\s*:\s*(\{[^}]*\})\s*\}', response)
    for name, args_str in inline_json:
        if name in TOOL_NAME_MAP:
            try:
                import json
                args = json.loads(args_str)
                return {"name": name, "arguments": args}
            except:
                pass
    
    return {}


def validate_tool_execution(
    response: str,
    tool_calls: List[Dict],
    tool_results: List[Dict],
    user_message: str,
    retry_count: int = 0,
) -> Dict:
    """
    验证工具执行是否有效（v2.0）
    
    修复：
    1. 区分虚假声称和意图表达
    2. 添加 text fallback
    3. 限制 retry 次数
    
    Returns:
        {
            "valid": bool,
            "false_claim": bool,
            "text_fallback": dict or None,  # 从文本提取的工具调用
            "reason": str,
            "retry_hint": str,
            "should_retry": bool,
        }
    """
    # 1. 检测虚假声称（已完成但没调用）
    is_false, reason, suggestion = detect_false_claim(response, tool_calls, user_message)

    if is_false:
        # 超过最大 retry 次数，不再 retry
        if retry_count >= 2:
            return {
                "valid": False,
                "false_claim": True,
                "text_fallback": None,
                "reason": reason,
                "retry_hint": f"⚠️ 已重试 {retry_count} 次，模型仍声称已完成操作但未调用工具。接受模型当前回答。",
                "should_retry": False,
            }
        
        return {
            "valid": False,
            "false_claim": True,
            "text_fallback": None,
            "reason": reason,
            "retry_hint": f"""⚠️ 检测到问题：{reason}

你声称已经执行操作，但没有实际调用任何工具。

**必须**：使用 tool_calls API 调用工具来执行操作。
- read_file: 读取文件
- write_file: 写入文件  
- execute_shell: 执行命令
- list_directory: 查看目录

请重新响应，这次必须调用工具。""",
            "should_retry": True,
        }

    # 2. 检测意图表达（不是虚假声称，但 API 没返回 tool_calls）
    has_intent, mentioned_tools = detect_expressed_intent(response)
    
    if has_intent and not tool_calls and mentioned_tools:
        # 尝试从文本提取工具调用
        text_fallback = extract_tool_call_from_text(response)
        
        if text_fallback:
            return {
                "valid": True,  # text fallback 算作有效
                "false_claim": False,
                "text_fallback": text_fallback,
                "reason": f"模型表达了工具调用意图（{mentioned_tools}），使用 text fallback 提取",
                "retry_hint": "",
                "should_retry": False,
            }
        
        # 无法提取，但也不是虚假声称——这是 API 兼容性问题
        # 接受模型回答，不强求 retry
        return {
            "valid": True,
            "false_claim": False,
            "text_fallback": None,
            "reason": "",
            "retry_hint": "",
            "should_retry": False,
        }

    # 3. 检查工具执行结果
    if tool_calls:
        for result in tool_results:
            if isinstance(result, dict) and "error" in result:
                return {
                    "valid": False,
                    "false_claim": False,
                    "text_fallback": None,
                    "reason": f"工具执行失败：{result.get('error')}",
                    "retry_hint": "工具执行失败，请尝试其他方法。",
                    "should_retry": False,
                }

    return {
        "valid": True,
        "false_claim": False,
        "text_fallback": None,
        "reason": "",
        "retry_hint": "",
        "should_retry": False,
    }


def build_retry_prompt(user_message: str, failed_response: str, reason: str) -> str:
    """构建重试提示"""
    return f"""## ⚠️ 工具调用验证失败

**原因**: {reason}

**用户原始请求**: {user_message}

**你的错误响应**:
{failed_response[:500]}

---

**你必须**：
1. 使用 tool_calls API 调用工具
2. 等待工具返回结果
3. 基于结果回答

**不要**：
- 声称"已修复"但没有工具调用
- 编造结果
- 跳过工具调用

请重新处理用户的请求。"""


def analyze_tool_results(steps: list) -> dict:
    """
    分析工具执行结果，判断是否已获得足够信息

    Returns:
        {
            "sufficient": bool,
            "has_error": bool,
            "summary": str,
            "result_types": list,
        }
    """
    if not steps:
        return {"sufficient": False, "has_error": False, "summary": "无工具执行", "result_types": []}

    has_error = False
    successful_count = 0
    result_types = set()

    for step in steps:
        result = step.get("result_summary", "")

        if "error" in result.lower() or "失败" in result or "exception" in result.lower():
            has_error = True
        else:
            successful_count += 1

        tool_name = step.get("tool", "")
        if "read_file" in tool_name:
            result_types.add("file_content")
        elif "execute_shell" in tool_name:
            result_types.add("command_output")
        elif "list_directory" in tool_name:
            result_types.add("directory_listing")

    sufficient = successful_count > 0 and not has_error

    summary = f"执行了 {len(steps)} 个工具，成功 {successful_count} 个"
    if has_error:
        summary += "，有错误"

    return {
        "sufficient": sufficient,
        "has_error": has_error,
        "summary": summary,
        "result_types": list(result_types),
    }
