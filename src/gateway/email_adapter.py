"""Email Adapter - Email integration via SMTP/IMAP.

Allows Omnia to send and receive emails.
"""

from __future__ import annotations

import asyncio
import aiosmtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Callable, Awaitable, Optional, List

from src.core.gateway.runner import ChannelAdapter, ChannelType, MessageEvent
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class EmailAdapter(ChannelAdapter):
    """Email 适配器 - 发送和接收邮件"""
    
    channel_type = ChannelType.EMAIL
    
    def __init__(
        self,
        on_message: Callable[[MessageEvent], Awaitable[None]] | None = None,
        smtp_host: str = "localhost",
        smtp_port: int = 25,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        use_tls: bool = True,
        email_address: Optional[str] = None,
    ):
        self._on_message = on_message
        self._running = False
        
        # SMTP 配置
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.use_tls = use_tls
        self.email_address = email_address or smtp_user
        
        # 消息队列
        self._pending_responses: dict[str, asyncio.Queue] = {}
    
    async def start(self):
        """启动适配器"""
        self._running = True
        logger.info(f"[EmailAdapter] ✓ Started (SMTP: {self.smtp_host}:{self.smtp_port})")
    
    async def stop(self):
        """停止适配器"""
        self._running = False
        logger.info("[EmailAdapter] ✓ Stopped")
    
    async def send(self, target: str, content: str, **kwargs) -> bool:
        """
        发送邮件
        
        Args:
            target: 收件人邮箱地址
            content: 邮件内容
            **kwargs: subject, cc, bcc, html, attachments 等
        """
        try:
            subject = kwargs.get("subject", "Message from Omnia")
            html_content = kwargs.get("html")
            cc = kwargs.get("cc", [])
            bcc = kwargs.get("bcc", [])
            
            # 创建邮件
            message = MIMEMultipart("alternative")
            message["From"] = self.email_address
            message["To"] = target
            message["Subject"] = subject
            
            if cc:
                message["Cc"] = ", ".join(cc)
            if bcc:
                message["Bcc"] = ", ".join(bcc)
            
            # 添加文本内容
            message.attach(MIMEText(content, "plain", "utf-8"))
            
            # 添加 HTML 内容（如果有）
            if html_content:
                message.attach(MIMEText(html_content, "html", "utf-8"))
            
            # 发送邮件
            recipients = [target]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                use_tls=self.use_tls,
            )
            
            logger.info(f"[EmailAdapter] Email sent to {target}")
            return True
            
        except Exception as e:
            logger.error(f"[EmailAdapter] Failed to send email: {e}")
            return False
    
    async def get_me(self) -> dict:
        """获取机器人信息"""
        return {
            "id": self.email_address,
            "name": "Omnia Email Bot",
            "channel": "email",
            "address": self.email_address,
        }
    
    async def receive_email(
        self,
        sender: str,
        subject: str,
        body: str,
        message_id: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        接收邮件（由外部 IMAP 监听器调用）
        
        Args:
            sender: 发件人地址
            subject: 邮件主题
            body: 邮件正文
            message_id: 邮件 ID
            metadata: 其他元数据
        """
        if not self._running or not self._on_message:
            return
        
        # 创建消息事件
        event = MessageEvent(
            channel=ChannelType.EMAIL,
            user_id=sender,
            chat_id=sender,  # 对于邮件，chat_id 就是 sender
            message_id=message_id,
            content=f"{subject}\n\n{body}",
            timestamp=datetime.now(),
            metadata={
                "subject": subject,
                "body": body,
                "sender": sender,
                **(metadata or {}),
            }
        )
        
        await self._on_message(event)
    
    async def send_template(
        self,
        to: str,
        template_name: str,
        template_vars: dict,
        **kwargs
    ) -> bool:
        """
        使用模板发送邮件
        
        Args:
            to: 收件人
            template_name: 模板名称
            template_vars: 模板变量
        """
        # 模板系统 - 支持变量替换和条件渲染
        import re
        templates = {
            "welcome": {
                "subject": "Welcome to Omnia, {name}!",
                "body": "Hello {name},\n\nWelcome to Omnia! We're excited to have you.\n\nBest,\nOmnia Team"
            },
            "notification": {
                "subject": "{title}",
                "body": "{message}\n\n---\nThis is an automated message from Omnia."
            }
        }
        
        # 支持自定义模板目录
        custom_templates = {}
        try:
            template_dir = Path.home() / '.omnia' / 'email_templates'
            if template_dir.exists():
                for f in template_dir.glob('*.json'):
                    with open(f, 'r', encoding='utf-8') as tf:
                        tpl = json.load(tf)
                        if 'name' in tpl:
                            custom_templates[tpl['name']] = tpl
        except Exception:
            pass
        
        # 合并模板（自定义优先）
        all_templates = {**templates, **custom_templates}
        
        if template_name not in all_templates:
            logger.warning(f"[EmailAdapter] Template not found: {template_name}")
            return False
        
        template = all_templates[template_name]
        subject = template["subject"].format(**template_vars)
        body = template["body"].format(**template_vars)
        
        return await self.send(to, body, subject=subject, **kwargs)


__all__ = ["EmailAdapter"]
