#!/usr/bin/env python3
"""Test script: Run Persona Daemon in foreground for a short time."""

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
    print("Persona Daemon — Foreground Smoke Test")
    print("=" * 60)

    cfg = DaemonConfig(
        workspace_root=str(WORKSPACE_ROOT),
        poll_interval_seconds=3,
        heartbeat_interval_minutes=1,
    )
    daemon = PersonaDaemon(cfg)

    # Auto-stop after 12 seconds
    def auto_stop():
        time.sleep(12)
        print("\n[TEST] Auto-stopping daemon...")
        daemon.stop()

    threading.Thread(target=auto_stop, daemon=True).start()

    print("\nDaemon will run for ~12 seconds.")
    print(f"Monitoring memory dir: {daemon.memory_path}")
    print("Try editing any file in that directory to see a detection event.\n")
    daemon.start()

    print("\n[TEST] Checking log output...")
    if daemon.log_path.exists():
        lines = daemon.log_path.read_text().splitlines()
        recent = lines[-12:]
        for line in recent:
            print(f"  LOG: {line}")
    else:
        print("  No log file found.")

    print("\n" + "=" * 60)
    print("Daemon smoke test complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
