"""Organic Heartbeat — Rich health checks for the Persona Daemon."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class HeartbeatEvent:
    level: str      # info | warning | alert
    source: str     # git | cron | filesystem
    title: str
    body: str = ""


class OrganicHeartbeat:
    """Generates contextual health events for the daemon to evaluate."""

    def __init__(
        self,
        workspace_root: str | Path = ".",
        cron_log_paths: List[str] = None,
    ):
        self.workspace = Path(workspace_root).resolve()
        self.cron_log_paths = cron_log_paths or [
            "/tmp/seo_pipeline.log",
            "/tmp/auto_forge.log",
        ]

    # ------------------------------------------------------------------
    # Cron checks
    # ------------------------------------------------------------------
    def check_cron(self) -> List[HeartbeatEvent]:
        events: List[HeartbeatEvent] = []
        for log_path_str in self.cron_log_paths:
            log_path = Path(log_path_str)
            if not log_path.exists():
                continue
            try:
                text = log_path.read_text(encoding="utf-8", errors="ignore")
                recent = "\n".join(text.splitlines()[-10:])
                lower = recent.lower()
                if any(k in lower for k in ["error", "fail", "traceback", "exception"]):
                    events.append(
                        HeartbeatEvent(
                            level="alert",
                            source="cron",
                            title=f"Cron log anomaly: {log_path.name}",
                            body="Check recent lines for errors.",
                        )
                    )
                elif "success" in lower or "complete" in lower:
                    # Healthy recent run — info level only
                    pass
            except OSError:
                continue
        return events

    # ------------------------------------------------------------------
    # Git checks
    # ------------------------------------------------------------------
    def check_git(self, repo_path: str | Path = None) -> List[HeartbeatEvent]:
        target = Path(repo_path) if repo_path else self.workspace
        events: List[HeartbeatEvent] = []

        # 1. Uncommitted changes
        try:
            result = subprocess.run(
                ["git", "-C", str(target), "status", "--short"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().splitlines()
                events.append(
                    HeartbeatEvent(
                        level="warning",
                        source="git",
                        title=f"{len(lines)} uncommitted change(s) in Omnia repo",
                        body="\n".join(lines[:5]),
                    )
                )
        except Exception:
            pass

        # 2. Recent commits (last 24h)
        try:
            result = subprocess.run(
                [
                    "git", "-C", str(target), "log",
                    "--since=24 hours ago", "--oneline", "--no-decorate"
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                commits = result.stdout.strip().splitlines()
                events.append(
                    HeartbeatEvent(
                        level="info",
                        source="git",
                        title=f"{len(commits)} commit(s) in the last 24 hours",
                        body="\n".join(commits[:3]),
                    )
                )
        except Exception:
            pass

        return events

    # ------------------------------------------------------------------
    # File-system checks
    # ------------------------------------------------------------------
    def check_filesystem(self) -> List[HeartbeatEvent]:
        events: List[HeartbeatEvent] = []

        # Check if daemon log is growing (basic self-health)
        log_path = self.workspace / ".omnia" / "daemon.log"
        if log_path.exists():
            size_kb = log_path.stat().st_size / 1024
            if size_kb > 1024:
                events.append(
                    HeartbeatEvent(
                        level="warning",
                        source="filesystem",
                        title=f"Daemon log is large ({size_kb:.0f} KB)",
                        body="Consider rotating or truncating the log.",
                    )
                )

        return events

    # ------------------------------------------------------------------
    # Full heartbeat scan
    # ------------------------------------------------------------------
    def scan(self) -> List[HeartbeatEvent]:
        return self.check_cron() + self.check_git() + self.check_filesystem()
