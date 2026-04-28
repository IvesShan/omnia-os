"""Tool Pattern Cleaner Hook - 专门处理工具格式清理

from core.logging_config import get_logger

logger = get_logger(__name__)

这是 FreeCode 风格的 Hook 实现，用于在检测到工具格式时自动清理。
"""

import re
from core.plugin.hooks import register_hook, HookType, HookContext


@register_hook(HookType.ON_TOOL_PATTERN, priority=5, name="clean_tool_pattern")
def clean_tool_pattern(context: HookContext) -> str:
    """清理工具调用格式（同步版本）
    
    Args:
        context: Hook 上下文，包含检测到工具格式的输出
    
    Returns:
        清理后的内容
    """
    output = context.output
    if not output:
        return output
    
    print(f"[Hook:clean_tool_pattern] Processing output of {len(output)} chars")
    
    # 所有工具名
    all_tools = ['read_file', 'write_file', 'execute_shell', 'list_directory', 'web_search', 'query_memory']
    
    # 策略1: 提取工具调用之前的内容
    lines = output.split('\n')
    clean_lines = []
    
    for line in lines:
        # 检查是否包含工具格式
        if any(f'<{tool}' in line for tool in all_tools):
            logger.info(f"[Hook:clean_tool_pattern] Stopping at tool XML tag")
            break
        if re.match(r'^\s*(read_file|write_file|execute_shell|list_directory|web_search|query_memory)\s*[\(\{]', line):
            logger.info(f"[Hook:clean_tool_pattern] Stopping at function call")
            break
        if re.match(r'^\s*\{\s*["\']?(path|command|query|content)["\']?\s*:', line):
            logger.info(f"[Hook:clean_tool_pattern] Stopping at JSON argument")
            break
        clean_lines.append(line)
    
    extracted = '\n'.join(clean_lines).strip()
    
    if extracted and len(extracted) > 20:
        print(f"[Hook:clean_tool_pattern] Extracted {len(extracted)} chars")
        return extracted
    
    # 策略2: 如果没有有效内容，返回 None 让主流程处理
    logger.info(f"[Hook:clean_tool_pattern] No valid content extracted, returning None")
    return None


@register_hook(HookType.POST_TOOL_USE, priority=20, name="compress_large_output")
def compress_large_output(context: HookContext):
    """压缩大输出（同步版本）
    
    如果工具输出太大，进行压缩
    """
    result = context.tool_result
    if not result:
        return
    
    # 检查输出大小
    result_str = str(result)
    if len(result_str) > 5000:
        print(f"[Hook:compress_large_output] Large output detected: {len(result_str)} chars")
        # 这里可以调用压缩器，但为了简化，我们只是记录
        # 实际压缩在 chat_handler 中已经处理


@register_hook(HookType.ON_ERROR, priority=0, name="log_error")
def log_error(context: HookContext):
    """记录错误（同步版本）"""
    if context.error:
        print(f"[Hook:log_error] Error: {context.error}")
        if context.tool_name:
            print(f"[Hook:log_error] Tool: {context.tool_name}")
