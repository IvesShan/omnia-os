"""Omnia CLI entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.neuro_center import PersonaDaemon, DaemonConfig
from core.neuro_center.notification_queue import pop_notifications_for_session
from omnia.wake import assemble_wake_prompt
from omnia.chat import chat


def cmd_wake(args):
    message = " ".join(args.message) if args.message else None
    prompt = assemble_wake_prompt(message)
    print(prompt)


def cmd_chat(args):
    message = " ".join(args.message)
    if not message:
        print("Usage: omnia chat <message>")
        return
    chat(message)


def cmd_status(args):
    workspace_root = PROJECT_ROOT.parent
    pid_file = settings.omnia_home / "daemon.pid"
    log_file = settings.omnia_home / "daemon.log"
    db_file = settings.memory_palace_db
    queue_file = settings.omnia_home / "notifications.jsonl"

    print("=" * 60)
    print("Omnia Status")
    print("=" * 60)

    # Daemon
    if pid_file.exists():
        pid = pid_file.read_text().strip()
        try:
            import os
            os.kill(int(pid), 0)
            print(f"\nPersona Daemon: running (pid={pid})")
        except ProcessLookupError:
            print(f"\nPersona Daemon: stale pid file ({pid})")
    else:
        print("\nPersona Daemon: not running")

    # Recent log tail
    if log_file.exists():
        lines = log_file.read_text().splitlines()
        recent = lines[-5:]
        print(f"\nRecent daemon log ({len(recent)} line(s)):")
        for line in recent:
            print(f"  {line}")
    else:
        print("\nDaemon log: not found")

    # Memory palace
    if db_file.exists():
        import sqlite3
        with sqlite3.connect(str(db_file)) as conn:
            cursor = conn.cursor()
            counts = {}
            for table in ["facts", "relations", "habits", "timeline"]:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
        print("\nMemory Palace:")
        for k, v in counts.items():
            print(f"  {k}: {v}")
    else:
        print("\nMemory Palace: not initialized")

    # Pending notifications
    pulse = pop_notifications_for_session(queue_file)
    if pulse:
        print(f"\nPending notifications:{pulse}")
    else:
        print("\nPending notifications: none")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(prog="omnia", description="Omnia Agent OS")
    subparsers = parser.add_subparsers(dest="command", required=True)

    wake_parser = subparsers.add_parser("wake", help="Run the full wake cycle and print system prompt")
    wake_parser.add_argument("message", nargs="*", help="Optional user message to plan against")
    wake_parser.set_defaults(func=cmd_wake)

    chat_parser = subparsers.add_parser("chat", help="Chat with Omnia in the terminal")
    chat_parser.add_argument("message", nargs="+", help="Your message to Omnia")
    chat_parser.set_defaults(func=cmd_chat)

    status_parser = subparsers.add_parser("status", help="Show Omnia system status")
    status_parser.set_defaults(func=cmd_status)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
