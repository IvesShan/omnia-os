#!/usr/bin/env python3
"""Stop the Omnia Persona Daemon."""

import os
import signal
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent
PID_FILE = WORKSPACE_ROOT / ".omnia" / "daemon.pid"


def main():
    if not PID_FILE.exists():
        print("Daemon is not running (no pid file found).")
        return

    pid = int(PID_FILE.read_text().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Sent SIGTERM to daemon (pid={pid}).")
    except ProcessLookupError:
        print(f"Process {pid} not found. Cleaning up stale pid file.")
    finally:
        PID_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
