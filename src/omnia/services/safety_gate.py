"""
Safety Gate — 工具执行风险分级和安全检查

移植自 Flask 版 core/actuator/safety_gate.py
适配 FastAPI 异步架构

核心功能：
1. Shell 命令风险分类（只读/中等/高危/致命）
2. 文件写入路径安全检查
3. 文件读取敏感路径拦截
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class SafetyResult:
    allowed: bool
    level: str  # low | medium | high | critical
    reason: str
    requires_confirm: bool = False


# ─── Shell 命令分类 ───

READONLY_COMMANDS = {
    "ls", "pwd", "cat", "head", "tail", "less", "more",
    "grep", "find", "ps", "top", "htop", "df", "du", "free",
    "whoami", "uname", "date", "echo", "which", "whereis",
    "git", "curl", "wget", "ping", "netstat", "ss",
    "code", "npm", "npx", "node", "python3", "python",
    "mkdir", "touch", "cd",
}

DANGEROUS_PATTERNS = [
    "rm -rf /", "rm -rf /*", "dd if=", "> /dev/sd", "mkfs",
    "iptables -F", "shutdown", "reboot", "halt",
    ":(){ :|:& };:", "curl .* | sh", "curl .* | bash",
    "wget .* -O- | sh", "wget .* -O- | bash",
    "eval $(", "eval `",
]


def classify_shell_command(command: str) -> SafetyResult:
    """对 Shell 命令进行风险分类"""
    cmd = command.strip()
    lower = cmd.lower()

    # 致命模式检测
    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in lower:
            return SafetyResult(
                allowed=False,
                level="critical",
                reason=f"检测到高危模式: {pattern}",
            )

    # 解析基础命令
    tokens = cmd.split()
    if not tokens:
        return SafetyResult(allowed=False, level="high", reason="空命令")

    base = tokens[0].lower()

    # 破坏性/特权命令
    if base in {"rm", "rmdir", "mv", "cp", "chmod", "chown", "kill", "pkill", "sudo", "su"}:
        return SafetyResult(
            allowed=True,
            level="high",
            reason=f"命令 {base} 属于破坏性/特权操作",
            requires_confirm=True,
        )

    # 系统级命令
    if base in {"dd", "fdisk", "parted", "mkfs", "iptables"}:
        return SafetyResult(
            allowed=True,
            level="high",
            reason=f"系统级命令 {base} 需要确认",
            requires_confirm=True,
        )

    # systemctl 分级
    if base == "systemctl":
        if "--user" in lower:
            return SafetyResult(
                allowed=True,
                level="low",
                reason="systemctl --user 仅影响当前用户会话",
            )
        return SafetyResult(
            allowed=True,
            level="high",
            reason="systemctl 系统级服务操作需要确认",
            requires_confirm=True,
        )

    # 只读/安全命令
    if base in READONLY_COMMANDS:
        return SafetyResult(
            allowed=True,
            level="low",
            reason="只读/低风险命令",
        )

    # 环境变更命令
    if base in {"pip", "pip3", "apt", "apt-get", "npm", "yarn", "pnpm", "docker", "make"}:
        return SafetyResult(
            allowed=True,
            level="medium",
            reason=f"环境变更命令 {base} 需要确认",
            requires_confirm=True,
        )

    # 未知命令
    return SafetyResult(
        allowed=True,
        level="medium",
        reason=f"未知命令 {base}，建议确认",
        requires_confirm=True,
    )


def classify_file_write(path: str, content: str = "") -> SafetyResult:
    """对文件写入进行安全分类"""
    p = Path(path).resolve()
    home = Path.home().resolve()
    workspace = (home / "omnia-os").resolve()

    # 禁止写入系统路径
    system_paths = ["/etc", "/usr", "/bin", "/lib", "/sys", "/proc", "/dev", "/boot"]
    for sp in system_paths:
        try:
            p.relative_to(Path(sp))
            return SafetyResult(
                allowed=False,
                level="critical",
                reason=f"禁止写入系统路径: {sp}",
            )
        except ValueError:
            pass

    size = len(content.encode("utf-8"))

    # 安全区：工作区
    try:
        p.relative_to(workspace)
        if size > 500_000:
            return SafetyResult(
                allowed=True,
                level="medium",
                reason="写入工作区超大文件",
                requires_confirm=True,
            )
        return SafetyResult(
            allowed=True,
            level="low",
            reason="写入工作区安全",
        )
    except ValueError:
        pass

    # 用户目录
    try:
        p.relative_to(home)
        return SafetyResult(
            allowed=True,
            level="medium",
            reason="写入用户目录非工作区",
            requires_confirm=True,
        )
    except ValueError:
        pass

    # 外部路径
    return SafetyResult(
        allowed=True,
        level="high",
        reason="写入未知外部路径",
        requires_confirm=True,
    )


def classify_file_read(path: str) -> SafetyResult:
    """对文件读取进行安全分类"""
    p = Path(path).resolve()

    # 敏感路径拦截
    blocked = ["/etc/shadow", "/etc/passwd", "/etc/hosts", "/proc", "/sys", "/dev/mem"]
    for bp in blocked:
        try:
            p.relative_to(Path(bp))
            return SafetyResult(
                allowed=False,
                level="critical",
                reason=f"禁止读取敏感路径: {bp}",
            )
        except ValueError:
            pass

    return SafetyResult(allowed=True, level="low", reason="读取文件")


def check_tool_safety(tool_name: str, arguments: dict) -> SafetyResult:
    """
    统一工具安全检查入口

    根据工具名称自动选择对应的安全检查策略。
    """
    if tool_name == "execute_shell":
        command = arguments.get("command", "")
        return classify_shell_command(command)

    elif tool_name == "write_file":
        path = arguments.get("path", "")
        content = arguments.get("content", "")
        return classify_file_write(path, content)

    elif tool_name == "read_file":
        path = arguments.get("path", "")
        return classify_file_read(path)

    elif tool_name == "list_directory":
        return SafetyResult(allowed=True, level="low", reason="列出目录")

    elif tool_name == "web_search":
        return SafetyResult(allowed=True, level="low", reason="网络搜索")

    elif tool_name in ("query_memory", "save_memory", "memory_stats"):
        return SafetyResult(allowed=True, level="low", reason="记忆操作")

    # 未知工具默认中等风险
    return SafetyResult(
        allowed=True,
        level="medium",
        reason=f"未知工具 {tool_name}",
        requires_confirm=True,
    )
