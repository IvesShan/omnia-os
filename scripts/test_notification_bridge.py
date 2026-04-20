#!/usr/bin/env python3
"""Test script: Verify daemon-to-session notification bridge."""

import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.neuro_center import PersonaDaemon, DaemonConfig
from core.neuro_center.notification_queue import NotificationQueue, pop_notifications_for_session


def main():
    print("=" * 60)
    print("Notification Bridge Test")
    print("=" * 60)

    queue_path = PROJECT_ROOT / ".omnia_test_notifications.jsonl"
    queue_path.unlink(missing_ok=True)

    cfg = DaemonConfig(
        workspace_root=str(WORKSPACE_ROOT),
        poll_interval_seconds=2,
        heartbeat_interval_minutes=10,
    )
    daemon = PersonaDaemon(cfg)
    # Force our test queue into the daemon
    daemon._queue = NotificationQueue(queue_path)

    test_file = WORKSPACE_ROOT / "memory" / "daemon_test_bridge.md"

    def simulate():
        time.sleep(3)
        print("\n[TEST] Creating test memory file...")
        test_file.write_text("# Bridge test\n", encoding="utf-8")

        time.sleep(3)
        print("[TEST] Stopping daemon...")
        daemon.stop()

    threading.Thread(target=simulate, daemon=True).start()
    daemon.start()

    # Now simulate a "new session" reading the queue
    print("\n[TEST] Simulating new session startup...")
    pulse = pop_notifications_for_session(queue_path)
    if pulse:
        print(f"PULSE: {pulse}")
    else:
        print("PULSE: (empty)")

    # Cleanup
    test_file.unlink(missing_ok=True)
    queue_path.unlink(missing_ok=True)

    print("\n" + "=" * 60)
    print("Bridge test complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
