"""工具调用验证器 - 检测模型是否虚假声称调用了工具"""

import re
from typing import List, Dict, Tuple


# 声称已执行但没有工具调用的关键词模式
FALSE_CLAIM_PATTERNS = [
    r"已(经)?修复",
    r"已(经)?完成",
    r"已(经)?修改",
    r"已(经)?创建",
    r"已(经)?删除",
    r"已(经)?提交",
    r"已(经)?执行",
    r"成功(修复|修改|创建|删除|提交|执行)",
    r"修复完成",
    r"修改完成",
    r"创建完成",
    r"✅",
]

# 需要工具操作的关键词
TOOL_REQUIRED_KEYWORDS = [
    "修复", "修改", "创建", "删除", "提交", "执行", "检查", "查看",
    "读取", "写入", "运行", "测试", "分析", "诊断", "安装", "部署"
]


def detect_false_claim(
    response: str,
    tool_calls: List[Dict],
    user_message: str
) -> Tuple[bool, str, str]:
    """
    检测模型是否虚假声称调用了工具。
    
    Args:
        response: 模型的文本响应
        tool_calls: 实际的工具调用列表
        user_message: 用户消息
    
    Returns:
        (is_false_claim, reason, suggestion)
        - is_false_claim: 是否检测到虚假声称
        - reason: 检测原因
        - suggestion: 建议的行动
    """
    # 如果有工具调用，不是虚假声称
    if tool_calls:
        return False, "", ""
    
    # 检查用户消息是否需要工具操作
    needs_tool = any(kw in user_message for kw in TOOL_REQUIRED_KEYWORDS)
    if not needs_tool:
        return False, "", ""
    
    # 检查响应中是否有虚假声称
    for pattern in FALSE_CLAIM_PATTERNS:
        if re.search(pattern, response):
            return True, f"检测到虚假声称：'{pattern}'，但没有实际工具调用", "强制重试"
    
    return False, "", ""


def validate_tool_execution(
    response: str,
    tool_calls: List[Dict],
    tool_results: List[Dict],
    user_message: str
) -> Dict:
    """
    验证工具执行是否有效。
    
    Args:
        response: 模型的文本响应
        tool_calls: 工具调用列表
        tool_results: 工具执行结果
        user_message: 用户消息
    
    Returns:
        {
            "valid": bool,
            "false_claim": bool,
            "reason": str,
            "retry_hint": str,
        }
    """
    # 检测虚假声称
    is_false, reason, suggestion = detect_false_claim(response, tool_calls, user_message)
    
    if is_false:
        return {
            "valid": False,
            "false_claim": True,
            "reason": reason,
            "retry_hint": f"""⚠️ 检测到问题：{reason}

你声称已经执行操作，但没有实际调用任何工具。

**必须**：使用 tool_calls API 调用工具来执行操作。
- read_file: 读取文件
- write_file: 写入文件
- execute_shell: 执行命令
- list_directory: 查看目录

请重新响应，这次必须调用工具。"""
        }
    
    # 检查工具执行结果
    if tool_calls:
        for result in tool_results:
            if "error" in result:
                return {
                    "valid": False,
                    "false_claim": False,
                    "reason": f"工具执行失败：{result.get('error')}",
                    "retry_hint": "工具执行失败，请尝试其他方法。"
                }
    
    return {
        "valid": True,
        "false_claim": False,
        "reason": "",
        "retry_hint": ""
    }


def build_retry_prompt(user_message: str, failed_response: str, reason: str) -> str:
    """
    构建重试提示。
    """
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
