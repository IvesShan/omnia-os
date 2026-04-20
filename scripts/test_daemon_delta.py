#!/usr/bin/env python3
"""Test script: Verify PersonaDaemon detects memory file changes in real time."""

import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.neuro_center import PersonaDaemon, DaemonConfig


def main():
    print("=" * 60)
    print("Persona Daemon — Delta Detection Test")
    print("=" * 60)

    cfg = DaemonConfig(
        workspace_root=str(WORKSPACE_ROOT),
        poll_interval_seconds=2,
        heartbeat_interval_minutes=10,  # disable heartbeat for this test
    )
    daemon = PersonaDaemon(cfg)

    test_file = WORKSPACE_ROOT / "memory" / "_daemon_test_delta.md"

    def simulate_changes():
        time.sleep(3)
        print("\n[TEST] Creating test memory file...")
        test_file.write_text("# Delta test\nCreated by daemon test.\n", encoding="utf-8")

        time.sleep(3)
        print("[TEST] Modifying test memory file...")
        test_file.write_text("# Delta test\nModified by daemon test.\n", encoding="utf-8")

        time.sleep(3)
        print("[TEST] Cleaning up test file...")
        test_file.unlink(missing_ok=True)

        time.sleep(3)
        print("[TEST] Stopping daemon...\n")
        daemon.stop()

    threading.Thread(target=simulate_changes, daemon=True).start()

    daemon.start()

    # Inspect log
    print("[TEST] Checking log for delta events...")
    if daemon.log_path.exists():
        lines = daemon.log_path.read_text().splitlines()
        events = [l for l in lines if "[EVENT]" in l or "[START]" in l or "[STOP]" in l]
        for line in events[-10:]:
            print(f"  {line}")
    else:
        print("  No log file found.")

    print("\n" + "=" * 60)
    print("Delta detection test complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
