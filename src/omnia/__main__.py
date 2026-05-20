"""Omnia CLI entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.core.neuro_center import PersonaDaemon, DaemonConfig
from src.core.neuro_center.notification_queue import pop_notifications_for_session
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
    db_file = settings.memory_palace_db
    queue_file = settings.omnia_home / "notifications.jsonl"

    print("=" * 60)
    print("Omnia Status (FastAPI)")
    print("=" * 60)

    # FastAPI Server
    import urllib.request
    try:
        req = urllib.request.Request("http://localhost:8765/api/status", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                print("\nFastAPI Server: running (http://localhost:8765)")
            else:
                print(f"\nFastAPI Server: returned status {resp.status}")
    except Exception as e:
        print(f"\nFastAPI Server: not reachable ({e})")

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
