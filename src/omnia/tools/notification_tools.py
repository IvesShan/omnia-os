"""
notification_tools.py — 通知工具

提供：send_notification（系统通知）、send_email（邮件通知）
适配国内环境（微信/钉钉/企业微信 webhook）
"""

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    import urllib.request
    import urllib.error


class NotificationTools:
    """通知工具集（适配国内环境）"""

    @staticmethod
    def get_definitions() -> list[dict]:
        """返回工具的 JSON Schema 定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "send_notification",
                    "description": "发送通知消息。支持系统通知、钉钉/企业微信/飞书 Webhook。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "通知标题"
                            },
                            "message": {
                                "type": "string",
                                "description": "通知内容"
                            },
                            "channel": {
                                "type": "string",
                                "description": "通知渠道: system(系统通知), dingtalk(钉钉), wecom(企业微信), feishu(飞书)",
                                "default": "system"
                            },
                            "webhook_url": {
                                "type": "string",
                                "description": "Webhook URL（dingtalk/wecom/feishu 时必填）"
                            },
                            "level": {
                                "type": "string",
                                "description": "通知级别: info, warning, error",
                                "default": "info"
                            }
                        },
                        "required": ["title", "message"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "send_email",
                    "description": "发送邮件通知。支持 HTML 格式。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to": {
                                "type": "string",
                                "description": "收件人邮箱，多个用逗号分隔"
                            },
                            "subject": {
                                "type": "string",
                                "description": "邮件主题"
                            },
                            "body": {
                                "type": "string",
                                "description": "邮件正文"
                            },
                            "smtp_host": {
                                "type": "string",
                                "description": "SMTP 服务器地址"
                            },
                            "smtp_port": {
                                "type": "integer",
                                "description": "SMTP 端口，默认 465",
                                "default": 465
                            },
                            "smtp_user": {
                                "type": "string",
                                "description": "SMTP 用户名（邮箱地址）"
                            },
                            "smtp_password": {
                                "type": "string",
                                "description": "SMTP 密码/授权码"
                            },
                            "html": {
                                "type": "boolean",
                                "description": "是否使用 HTML 格式，默认 false",
                                "default": False
                            }
                        },
                        "required": ["to", "subject", "body"]
                    }
                }
            },
        ]

    @staticmethod
    async def execute(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        if name == "send_notification":
            return await NotificationTools._send_notification(**args)
        elif name == "send_email":
            return await NotificationTools._send_email(**args)
        return {"error": f"未知的通知工具: {name}"}

    @staticmethod
    async def _send_notification(
        title: str,
        message: str,
        channel: str = "system",
        webhook_url: str = "",
        level: str = "info",
    ) -> Dict[str, Any]:
        """发送通知"""
        if channel == "system":
            return NotificationTools._system_notify(title, message, level)
        elif channel == "dingtalk":
            return await NotificationTools._dingtalk_notify(title, message, webhook_url, level)
        elif channel == "wecom":
            return await NotificationTools._wecom_notify(title, message, webhook_url, level)
        elif channel == "feishu":
            return await NotificationTools._feishu_notify(title, message, webhook_url, level)
        else:
            return {"error": f"不支持的通知渠道: {channel}"}

    @staticmethod
    def _system_notify(title: str, message: str, level: str) -> Dict[str, Any]:
        """系统通知"""
        import subprocess
        import platform
        import shutil

        system = platform.system()

        try:
            if system == "Darwin":
                # macOS
                script = f'display notification "{message}" with title "{title}"'
                subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10)
            elif system == "Linux":
                notify_send = shutil.which("notify-send")
                if notify_send:
                    subprocess.run(
                        ["notify-send", f"--urgency={'critical' if level == 'error' else 'normal'}", title, message],
                        capture_output=True, timeout=10
                    )
                else:
                    # Fallback: 打印到终端
                    print(f"\n{'='*50}")
                    print(f"📢 [{level.upper()}] {title}")
                    print(f"   {message}")
                    print(f"{'='*50}\n")
            elif system == "Windows":
                # PowerShell toast notification
                ps_script = f'''
                [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
                $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
                $template.GetElementsByTagName("text")[0].AppendChild($template.CreateTextNode("{title}"))
                $template.GetElementsByTagName("text")[1].AppendChild($template.CreateTextNode("{message}"))
                $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
                [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Omnia").Show($toast)
                '''
                subprocess.run(["powershell", "-Command", ps_script], capture_output=True, timeout=10)
            else:
                # 未知系统，打印到终端
                print(f"\n{'='*50}")
                print(f"📢 [{level.upper()}] {title}")
                print(f"   {message}")
                print(f"{'='*50}\n")

            return {
                "success": True,
                "channel": "system",
                "platform": system,
                "title": title,
                "message": message,
            }
        except Exception as e:
            return {"error": f"系统通知发送失败: {str(e)}", "success": False}

    @staticmethod
    async def _dingtalk_notify(title: str, message: str, webhook_url: str, level: str) -> Dict[str, Any]:
        """钉钉 Webhook 通知"""
        if not webhook_url:
            return {"error": "钉钉通知需要提供 webhook_url"}
        if not HAS_HTTPX:
            return {"error": "需要安装 httpx: pip install httpx"}

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"### {title}\n\n{message}\n\n> 级别: {level}"
            }
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(webhook_url, json=payload)
                data = resp.json()
                return {
                    "success": data.get("errcode", -1) == 0,
                    "channel": "dingtalk",
                    "response": data,
                }
        except Exception as e:
            return {"error": f"钉钉通知发送失败: {str(e)}", "success": False}

    @staticmethod
    async def _wecom_notify(title: str, message: str, webhook_url: str, level: str) -> Dict[str, Any]:
        """企业微信 Webhook 通知"""
        if not webhook_url:
            return {"error": "企业微信通知需要提供 webhook_url"}
        if not HAS_HTTPX:
            return {"error": "需要安装 httpx: pip install httpx"}

        level_emoji = {"info": "ℹ️", "warning": "⚠️", "error": "🔴"}.get(level, "📢")

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"## {level_emoji} {title}\n\n{message}\n\n> 级别: {level}"
            }
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(webhook_url, json=payload)
                data = resp.json()
                return {
                    "success": data.get("errcode", -1) == 0,
                    "channel": "wecom",
                    "response": data,
                }
        except Exception as e:
            return {"error": f"企业微信通知发送失败: {str(e)}", "success": False}

    @staticmethod
    async def _feishu_notify(title: str, message: str, webhook_url: str, level: str) -> Dict[str, Any]:
        """飞书 Webhook 通知"""
        if not webhook_url:
            return {"error": "飞书通知需要提供 webhook_url"}
        if not HAS_HTTPX:
            return {"error": "需要安装 httpx: pip install httpx"}

        level_emoji = {"info": "ℹ️", "warning": "⚠️", "error": "🔴"}.get(level, "📢")

        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": f"{level_emoji} {title}"},
                    "template": {"info": "blue", "warning": "orange", "error": "red"}.get(level, "blue"),
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "plain_text", "content": message}},
                    {"tag": "hr"},
                    {"tag": "note", "elements": [{"tag": "plain_text", "content": f"Omnia AI · 级别: {level}"}]},
                ],
            },
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(webhook_url, json=payload)
                data = resp.json()
                return {
                    "success": data.get("code", -1) == 0,
                    "channel": "feishu",
                    "response": data,
                }
        except Exception as e:
            return {"error": f"飞书通知发送失败: {str(e)}", "success": False}

    @staticmethod
    async def _send_email(
        to: str,
        subject: str,
        body: str,
        smtp_host: str = "",
        smtp_port: int = 465,
        smtp_user: str = "",
        smtp_password: str = "",
        html: bool = False,
    ) -> Dict[str, Any]:
        """发送邮件"""
        if not smtp_host:
            return {"error": "需要提供 SMTP 服务器地址 (smtp_host)"}
        if not smtp_user or not smtp_password:
            return {"error": "需要提供 SMTP 用户名和密码 (smtp_user, smtp_password)"}

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = smtp_user
            msg["To"] = to

            if html:
                msg.attach(MIMEText(body, "html", "utf-8"))
            else:
                msg.attach(MIMEText(body, "plain", "utf-8"))

            recipients = [addr.strip() for addr in to.split(",")]

            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
                server.starttls()

            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipients, msg.as_string())
            server.quit()

            return {
                "success": True,
                "to": to,
                "subject": subject,
                "smtp_host": smtp_host,
            }
        except smtplib.SMTPAuthenticationError:
            return {"error": "SMTP 认证失败，请检查用户名和密码/授权码", "success": False}
        except Exception as e:
            return {"error": f"邮件发送失败: {str(e)}", "success": False}
