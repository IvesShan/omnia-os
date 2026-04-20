"""Safety Gate — Risk classification and confirmation layer for Omnia tools.

Every external action (file write, shell execution) must pass through here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class SafetyResult:
    allowed: bool
    level: str  # low | medium | high | critical
    reason: str
    requires_confirm: bool = False


# Shell command risk classification
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
    cmd = command.strip()
    lower = cmd.lower()

    # Critical patterns
    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in lower:
            return SafetyResult(
                allowed=False,
                level="critical",
                reason=f"检测到高危模式: {pattern}",
            )

    # Parse the base command
    tokens = cmd.split()
    if not tokens:
        return SafetyResult(allowed=False, level="high", reason="空命令")

    base = tokens[0].lower()

    # Destructive commands always require confirmation
    if base in {"rm", "rmdir", "mv", "cp", "chmod", "chown", "kill", "pkill", "sudo", "su"}:
        return SafetyResult(
            allowed=True,
            level="high",
            reason=f"命令 {base} 属于破坏性/特权操作",
            requires_confirm=True,
        )

    if base in {"dd", "fdisk", "parted", "mkfs", "iptables"}:
        return SafetyResult(
            allowed=True,
            level="high",
            reason=f"系统级命令 {base} 需要确认",
            requires_confirm=True,
        )

    # systemctl --user is safe (user session only); systemctl without --user needs confirm
    if base == "systemctl":
        if "--user" in lower:
            return SafetyResult(
                allowed=True,
                level="low",
                reason="systemctl --user 仅影响当前用户会话",
                requires_confirm=False,
            )
        return SafetyResult(
            allowed=True,
            level="high",
            reason="systemctl 系统级服务操作需要确认",
            requires_confirm=True,
        )

    # Generally safe commands
    if base in READONLY_COMMANDS:
        return SafetyResult(
            allowed=True,
            level="low",
            reason="只读/低风险命令",
            requires_confirm=False,
        )

    # Medium-risk: installation, build, deployment
    if base in {"pip", "pip3", "apt", "apt-get", "npm", "yarn", "pnpm", "docker", "make"}:
        return SafetyResult(
            allowed=True,
            level="medium",
            reason=f"环境变更命令 {base} 需要确认",
            requires_confirm=True,
        )

    # Unknown commands default to medium
    return SafetyResult(
        allowed=True,
        level="medium",
        reason=f"未知命令 {base}，建议确认",
        requires_confirm=True,
    )


def classify_file_write(path: str, content: str = "") -> SafetyResult:
    p = Path(path).resolve()
    home = Path.home().resolve()
    workspace = (home / ".openclaw" / "workspace").resolve()
    omnia_root = (home / ".openclaw" / "workspace" / "omnia-os").resolve()

    # Block system paths
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

    # Safe zone: workspace or omnia-os
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
            requires_confirm=False,
        )
    except ValueError:
        pass

    # Home directory but outside workspace
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

    # Anything else
    return SafetyResult(
        allowed=True,
        level="high",
        reason="写入未知外部路径",
        requires_confirm=True,
    )


def classify_file_read(path: str) -> SafetyResult:
    p = Path(path).resolve()
    home = Path.home().resolve()
    workspace = (home / ".openclaw" / "workspace").resolve()

    # Block sensitive system paths
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

    try:
        p.relative_to(workspace)
        return SafetyResult(allowed=True, level="low", reason="读取工作区文件")
    except ValueError:
        pass

    return SafetyResult(allowed=True, level="low", reason="读取外部文件")
