"""Persona Daemon — Omnia's ambient presence layer.

A lightweight, always-on process that:
  1. Watches the filesystem for changes relevant to the user
  2. Polls Memory Palace for deltas
  3. Evaluates low-cost escalation rules
  4. Runs periodic self-evolution cycles
  5. Logs activity; only surfaces to the user when threshold is crossed
"""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .notification_queue import NotificationQueue
from ..bootstrap import bootstrap_omnia
from core.config import OMNIA_HOME


@dataclass
class DaemonConfig:
    """Configuration for the Persona Daemon."""

    workspace_root: str = "."
    memory_dir: str = "memory"
    poll_interval_seconds: int = 30
    heartbeat_interval_minutes: int = 5
    log_file: str = ".omnia/daemon.log"
    state_file: str = str(OMNIA_HOME / "daemon_state.json")
    pid_file: str = str(OMNIA_HOME / "daemon.pid")
    # Rules
    watch_memory_changes: bool = True
    watch_project_git_changes: bool = False
    watch_cron_failures: bool = True
    cron_log_paths: List[str] = field(default_factory=lambda: [
        "/tmp/seo_pipeline.log",
        "/tmp/auto_forge.log",
    ])
    ide_bridge_port: int = 6789
    ide_bridge_enabled: bool = True
    # Self-evolution
    evolution_enabled: bool = True
    evolution_interval_hours: float = 24.0


class PersonaDaemon:
    """Lightweight ambient daemon for Omnia."""

    def __init__(self, config: Optional[DaemonConfig] = None):
        self.config = config or DaemonConfig()
        self.running = False
        self._shutdown_hooks: List[Callable[[], None]] = []
        self._last_memory_mtimes: Dict[str, float] = {}
        self._last_heartbeat_at: float = 0.0

        # Resolve paths relative to workspace
        self.workspace = Path(self.config.workspace_root).resolve()
        self.memory_path = self.workspace / self.config.memory_dir
        self.log_path = self.workspace / self.config.log_file
        self.state_path = self.workspace / self.config.state_file

        # Ensure log directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        # Notification queue bridge
        self._queue = NotificationQueue(self.workspace / ".omnia" / "notifications.jsonl")

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        # HTTP server for IDE bridge
        self._http_server: Optional[HTTPServer] = None
        self._http_thread: Optional[threading.Thread] = None

        # Self-evolution scheduler
        self._evolution_scheduler = None

    # ------------------------------------------------------------------
    # PID File Management
    # ------------------------------------------------------------------
    def _write_pid(self) -> None:
        """Write current PID to file for external monitoring."""
        pid_path = OMNIA_HOME / "daemon.pid"
        try:
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            pid_path.write_text(str(os.getpid()))
            self._log("PID", f"Wrote PID {os.getpid()} to {pid_path}")
        except Exception as e:
            self._log("ERROR", f"Failed to write PID file: {e}")

    def _cleanup_pid(self) -> None:
        """Remove PID file on shutdown."""
        pid_path = OMNIA_HOME / "daemon.pid"
        try:
            if pid_path.exists():
                pid_path.unlink()
                self._log("PID", f"Removed PID file {pid_path}")
        except Exception as e:
            self._log("ERROR", f"Failed to cleanup PID file: {e}")

    # ------------------------------------------------------------------
    # IDE Bridge
    # ------------------------------------------------------------------
    def _start_ide_bridge(self) -> None:
        if not self.config.ide_bridge_enabled:
            return

        ide_context_path = OMNIA_HOME / "ide_context.json"

        class IdeHandler(BaseHTTPRequestHandler):
            daemon_queue = self._queue
            daemon_log = self._log
            ctx_path = ide_context_path

            def do_POST(self):
                if self.path != "/ide-context":
                    self.send_response(404)
                    self.end_headers()
                    return
                try:
                    content_length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(content_length).decode("utf-8")
                    data = json.loads(body)
                    self.ctx_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                    self.send_response(204)
                    self.end_headers()
                except Exception as e:
                    self.daemon_log("ERROR", f"IDE bridge error: {e}")
                    self.send_response(500)
                    self.end_headers()

            def log_message(self, format, *args):
                pass  # Suppress default logging

            def do_GET(self):
                """Handle GET requests for health checks."""
                if self.path in ["/api/status", "/health", "/"]:
                    try:
                        # Return daemon status
                        status = {
                            "status": "running",
                            "daemon": "omnia",
                            "pid": os.getpid(),
                            "timestamp": datetime.now().isoformat(),
                        }
                        response = json.dumps(status, ensure_ascii=False)
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(response.encode("utf-8"))
                    except Exception as e:
                        self.daemon_log("ERROR", f"Health check error: {e}")
                        self.send_response(500)
                        self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()

                pass  # Suppress default HTTP logging

        # Allow socket reuse to avoid "Address already in use" errors
        import socket
        self._http_server = HTTPServer(("127.0.0.1", self.config.ide_bridge_port), IdeHandler)
        self._http_server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._http_thread = threading.Thread(target=self._http_server.serve_forever, daemon=True)
        self._http_thread.start()
        self._log("INFO", f"IDE bridge listening on port {self.config.ide_bridge_port}")

    def _stop_ide_bridge(self) -> None:
        if self._http_server:
            self._http_server.shutdown()
            self._log("INFO", "IDE bridge stopped.")

    # ------------------------------------------------------------------
    # Self-Evolution
    # ------------------------------------------------------------------
    def _start_evolution(self) -> None:
        """Start the self-evolution scheduler."""
        if not self.config.evolution_enabled:
            return

        try:
            from .evolution_scheduler import EvolutionScheduler

            def on_evolution_complete(result):
                self._log("EVOLUTION", f"Cycle complete: {result.patterns_found} patterns, {result.skills_generated} skills")

            self._evolution_scheduler = EvolutionScheduler(
                workspace_root=self.workspace,
                interval_hours=self.config.evolution_interval_hours,
                on_evolution_complete=on_evolution_complete,
            )
            self._evolution_scheduler.start()
            self._log("EVOLUTION", f"Scheduler started (interval: {self.config.evolution_interval_hours}h)")

        except Exception as e:
            self._log("ERROR", f"Failed to start evolution scheduler: {e}")

    def _stop_evolution(self) -> None:
        """Stop the self-evolution scheduler."""
        if self._evolution_scheduler:
            self._evolution_scheduler.stop()
            self._log("EVOLUTION", "Scheduler stopped.")

    def run_evolution_now(self) -> dict:
        """Manually trigger an evolution cycle."""
        if not self._evolution_scheduler:
            return {"error": "Evolution scheduler not initialized"}
        
        try:
            result = self._evolution_scheduler.run_now()
            return {
                "patterns_found": len(result.patterns_found),
                "skills_generated": result.skills_generated,
                "skills_approved": result.skills_approved,
                "skills_rejected": result.skills_rejected,
                "error": result.error,
            }
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Memory Watcher
    # ------------------------------------------------------------------
    def _scan_memory_changes(self) -> List[str]:
        """Scan memory directory for changes since last check."""
        changes = []
        if not self.memory_path.exists():
            return changes

        for md in self.memory_path.glob("*.md"):
            current_mtime = md.stat().st_mtime
            last_mtime = self._last_memory_mtimes.get(str(md))

            if last_mtime is None:
                changes.append(f"New memory file: {md.name}")
            elif current_mtime > last_mtime:
                changes.append(f"Modified: {md.name}")

            self._last_memory_mtimes[str(md)] = current_mtime

        return changes

    def _check_cron_failures(self) -> List[str]:
        """Check configured cron logs for failure patterns."""
        alerts = []
        for log_path in self.config.cron_log_paths:
            p = Path(log_path)
            if not p.exists():
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                if "error" in text.lower() or "fail" in text.lower():
                    alerts.append(f"Potential failure in {p.name}")
            except Exception:
                pass
        return alerts

    def _evaluate(self, memory_changes: List[str], cron_alerts: List[str]) -> List[str]:
        """Evaluate whether to surface changes to the user."""
        events = []

        if len(memory_changes) >= 3:
            events.append(f"Multiple memory changes: {', '.join(memory_changes[:3])}")

        return events

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------
    def _run_heartbeat(self) -> None:
        """Periodic deeper checks."""
        self._log("HEARTBEAT", "Daemon is alive and watching.")

        from .heartbeat import OrganicHeartbeat

        hb = OrganicHeartbeat(
            workspace_root=self.workspace,
            cron_log_paths=self.config.cron_log_paths,
        )
        events = hb.scan()
        for ev in events:
            self._log(ev.level.upper(), f"{ev.title}")
            if ev.level in ("warning", "alert"):
                self._queue.push(ev.level, ev.source, ev.title, ev.body)

        # Legacy fallback if nothing specific fired
        if not events:
            cron_alerts = self._check_cron_failures()
            for alert in cron_alerts:
                self._log("ALERT", alert)
                self._queue.push("alert", "daemon", alert, "Check cron logs for details.")

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    def _log(self, level: str, message: str) -> None:
        timestamp = datetime.now().isoformat(timespec="seconds")
        line = f"[{timestamp}] [{level}] {message}\n"
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass  # Avoid crashing on log failures

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def _handle_signal(self, signum, frame) -> None:
        self._log("INFO", f"Received signal {signum}, initiating graceful shutdown...")
        self.stop()

    def start(self) -> None:
        self._log("START", "Persona Daemon is waking up.")
        self.running = True
        self._write_pid()

        # Bootstrap core features
        bootstrap_result = bootstrap_omnia(self.workspace)
        self._log("BOOTSTRAP", f"Core features initialized: {bootstrap_result['status']}")
        for module in bootstrap_result.get('initialized_modules', []):
            self._log("BOOTSTRAP", f"  ✓ {module}")

        self._start_ide_bridge()
        self.on_shutdown(self._stop_ide_bridge)

        # Start self-evolution
        self._start_evolution()
        self.on_shutdown(self._stop_evolution)

        # Prime memory mtimes so we don't report pre-existing files as changes
        if self.memory_path.exists():
            for md in self.memory_path.glob("*.md"):
                self._last_memory_mtimes[str(md)] = md.stat().st_mtime

        while self.running:
            loop_start = time.time()

            # 1. Memory watch
            memory_changes = []
            if self.config.watch_memory_changes:
                memory_changes = self._scan_memory_changes()

            # 2. Heartbeat
            cron_alerts = []
            if self.config.watch_cron_failures:
                # Failures are checked both continuously and on heartbeat
                pass  # actual check happens inside heartbeat to avoid noise

            # 3. Escalation
            events = self._evaluate(memory_changes, cron_alerts)
            for ev in events:
                self._log("EVENT", ev)

            # 4. Periodic heartbeat
            now = time.time()
            if now - self._last_heartbeat_at >= self.config.heartbeat_interval_minutes * 60:
                self._run_heartbeat()
                self._last_heartbeat_at = now

            # Sleep until next poll
            elapsed = time.time() - loop_start
            sleep_for = max(0.1, self.config.poll_interval_seconds - elapsed)
            time.sleep(sleep_for)

        self._log("STOP", "Persona Daemon has gone to sleep.")
        for hook in self._shutdown_hooks:
            try:
                hook()
            except Exception as e:
                self._log("ERROR", f"Shutdown hook failed: {e}")

    def stop(self) -> None:
        self._cleanup_pid()
        self.running = False

    def on_shutdown(self, hook: Callable[[], None]) -> Callable[[], None]:
        self._shutdown_hooks.append(hook)
        return hook


if __name__ == "__main__":
    # Standalone smoke test
    config = DaemonConfig(
        workspace_root=str(Path(__file__).parent.parent.parent.parent),
        poll_interval_seconds=5,
        heartbeat_interval_minutes=1,
    )
    daemon = PersonaDaemon(config)
    daemon.start()
