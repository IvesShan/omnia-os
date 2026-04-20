"""
URL 检测和处理模块
自动检测聊天中的 URL 并提供打开/查看功能
"""

import re
from typing import List, Optional
import urllib.parse


def extract_urls(text: str) -> List[str]:
    """
    从文本中提取所有 URL
    
    Args:
        text: 输入文本
        
    Returns:
        URL 列表
    """
    # URL 正则表达式
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, text)
    return urls


def is_url_message(message: str) -> bool:
    """
    判断消息是否主要是 URL（用户想打开网页）
    
    Args:
        message: 用户消息
        
    Returns:
        是否是 URL 消息
    """
    message = message.strip()
    urls = extract_urls(message)
    
    # 如果消息只包含 URL（或 URL + 少量文字）
    if urls:
        # 移除 URL 后剩余的文字
        remaining = message
        for url in urls:
            remaining = remaining.replace(url, '')
        remaining = remaining.strip()
        
        # 如果剩余文字少于 10 个字符，认为是 URL 消息
        if len(remaining) < 10:
            return True
    
    return False


def get_primary_url(message: str) -> Optional[str]:
    """
    获取消息中的主要 URL
    
    Args:
        message: 用户消息
        
    Returns:
        主要 URL 或 None
    """
    urls = extract_urls(message)
    return urls[0] if urls else None


def format_url_for_display(url: str, max_length: int = 50) -> str:
    """
    格式化 URL 用于显示
    
    Args:
        url: URL 字符串
        max_length: 最大显示长度
        
    Returns:
        格式化后的 URL
    """
    if len(url) <= max_length:
        return url
    
    # 截断并添加省略号
    return url[:max_length-3] + '...'


def get_url_domain(url: str) -> str:
    """
    获取 URL 的域名
    
    Args:
        url: URL 字符串
        
    Returns:
        域名
    """
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc
    except:
        return url


# 支持的特殊 URL 处理
SPECIAL_URL_HANDLERS = {
    'github.com': 'GitHub 仓库',
    'stackoverflow.com': 'Stack Overflow 问题',
    'docs.python.org': 'Python 文档',
    'open.feishu.cn': '飞书开放平台文档',
    'developer.mozilla.org': 'MDN 文档',
}


def get_url_type(url: str) -> str:
    """
    获取 URL 的类型描述
    
    Args:
        url: URL 字符串
        
    Returns:
        URL 类型描述
    """
    domain = get_url_domain(url)
    
    for special_domain, type_name in SPECIAL_URL_HANDLERS.items():
        if special_domain in domain:
            return type_name
    
    return '网页'


if __name__ == '__main__':
    # 测试
    test_messages = [
        "https://open.feishu.cn/document/server-docs/server-side-sdk",
        "看看这个 https://github.com/example/repo",
        "帮我打开 https://docs.python.org/3/library/os.html",
        "这是一个普通消息",
        "https://example.com 和 https://another.com",
    ]
    
    for msg in test_messages:
        print(f"\n消息: {msg}")
        print(f"  是 URL 消息: {is_url_message(msg)}")
        urls = extract_urls(msg)
        print(f"  URL 列表: {urls}")
        if urls:
            print(f"  主要 URL: {get_primary_url(msg)}")
            print(f"  URL 类型: {get_url_type(urls[0])}")
