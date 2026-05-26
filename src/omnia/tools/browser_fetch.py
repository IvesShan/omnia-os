"""
browser_fetch.py — 网页浏览/抓取工具

提供：fetch_page（网页抓取）、browser_screenshot（网页截图，可选）
"""

import httpx
from pathlib import Path
from typing import Dict, Any
from urllib.parse import urljoin, urlparse


class BrowserFetchTools:
    """网页浏览工具集"""

    @staticmethod
    def get_definitions() -> list[dict]:
        """返回工具的 JSON Schema 定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "fetch_page",
                    "description": "抓取网页内容并转换为可读文本/markdown。用于查看文档、检查部署效果、获取 API 文档、阅读博客等。支持处理重定向、超时和常见反爬措施。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "要抓取的网页 URL"
                            },
                            "max_chars": {
                                "type": "integer",
                                "description": "最大返回字符数，默认 10000",
                                "default": 10000
                            },
                            "extract_mode": {
                                "type": "string",
                                "enum": ["markdown", "text"],
                                "description": "提取模式：markdown 保留格式，text 纯文本",
                                "default": "markdown"
                            }
                        },
                        "required": ["url"]
                    }
                }
            }
        ]

    @staticmethod
    async def execute(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        if name == "fetch_page":
            return await BrowserFetchTools._fetch_page(
                url=args.get("url", ""),
                max_chars=args.get("max_chars", 10000),
                extract_mode=args.get("extract_mode", "markdown")
            )
        else:
            return {"error": f"Unknown browser tool: {name}"}

    @staticmethod
    async def _fetch_page(url: str, max_chars: int, extract_mode: str) -> Dict[str, Any]:
        """抓取网页内容"""
        try:
            # 验证 URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return {"error": f"无效 URL: {url}"}
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # 检测编码
                content_type = response.headers.get("content-type", "")
                if "charset=" in content_type:
                    charset = content_type.split("charset=")[-1].split(";")[0].strip()
                    try:
                        text = response.content.decode(charset, errors="replace")
                    except:
                        text = response.text
                else:
                    text = response.text
                
                # 提取内容
                if extract_mode == "markdown":
                    result = BrowserFetchTools._html_to_markdown(text, url)
                else:
                    result = BrowserFetchTools._html_to_text(text)
                
                # 截断
                truncated = len(result) > max_chars
                preview = result[:max_chars]
                if truncated:
                    preview += f"\n\n[内容已截断，共 {len(result)} 字符。如需查看更多内容，可减小 max_chars 或分段抓取]"
                
                return {
                    "url": str(response.url),
                    "title": BrowserFetchTools._extract_title(text),
                    "content": preview,
                    "total_length": len(result),
                    "truncated": truncated,
                    "status_code": response.status_code,
                    "content_type": content_type
                }
                
        except httpx.TimeoutException:
            return {"error": f"请求超时（30秒）: {url}"}
        except httpx.HTTPStatusError as e:
            return {
                "error": f"HTTP 错误 {e.response.status_code}: {url}",
                "status_code": e.response.status_code,
                "response_preview": e.response.text[:500] if hasattr(e.response, 'text') else ""
            }
        except Exception as e:
            return {"error": f"抓取失败: {str(e)}"}

    @staticmethod
    def _extract_title(html: str) -> str:
        """从 HTML 中提取 title"""
        import re
        m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if m:
            title = m.group(1).strip()
            # 移除 HTML 实体
            title = title.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
            title = title.replace('&amp;', '&').replace('&quot;', '"')
            return title
        return ""

    @staticmethod
    def _html_to_markdown(html: str, base_url: str) -> str:
        """将 HTML 转换为 Markdown"""
        import re
        
        text = html
        
        # 移除 script/style 标签
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<noscript[^>]*>.*?</noscript>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # 转换标题
        text = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n# \1\n', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<h4[^>]*>(.*?)</h4>', r'\n#### \1\n', text, flags=re.IGNORECASE | re.DOTALL)
        
        # 转换段落和换行
        text = re.sub(r'</p>\s*<p[^>]*>', '\n\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</div>\s*<div[^>]*>', '\n', text, flags=re.IGNORECASE)
        
        # 转换列表
        text = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<ul[^>]*>|</ul>|<ol[^>]*>|</ol>', '', text, flags=re.IGNORECASE)
        
        # 转换链接
        def link_repl(m):
            href = m.group(1)
            label = m.group(2)
            # 处理相对 URL
            if href.startswith('/'):
                parsed_base = urlparse(base_url)
                href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
            return f"[{label}]({href})"
        
        text = re.sub(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', link_repl, text, flags=re.IGNORECASE | re.DOTALL)
        
        # 转换代码块
        text = re.sub(r'<pre[^>]*>(.*?)</pre>', r'\n```\n\1\n```\n', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', text, flags=re.IGNORECASE | re.DOTALL)
        
        # 加粗和斜体
        text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', text, flags=re.IGNORECASE | re.DOTALL)
        
        # 移除剩余标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 处理 HTML 实体
        text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'")
        text = text.replace('&mdash;', '—').replace('&ndash;', '–').replace('&hellip;', '...')
        
        # 清理多余空白
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        return text.strip()

    @staticmethod
    def _html_to_text(html: str) -> str:
        """将 HTML 转换为纯文本"""
        import re
        
        text = html
        # 移除 script/style
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # 转换换行
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<li[^>]*>', '\n- ', text, flags=re.IGNORECASE)
        
        # 移除所有标签
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # 处理实体
        text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&amp;', '&').replace('&quot;', '"')
        
        # 清理空白
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        return text.strip()
