#!/usr/bin/env python3
"""Start the Omnia Persona Daemon.

Manages the daemon process (PID, log) and runs _daemon_runner.py
which auto-detects all paths.
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

sys.path.insert(0, str(PROJECT_ROOT / "src"))
from core.config import OMNIA_HOME

PID_FILE = OMNIA_HOME / "daemon.pid"
LOG_FILE = OMNIA_HOME / "daemon.log"
RUNNER = PROJECT_ROOT / ".omnia" / "_daemon_runner.py"


def find_python():
    """Find the best Python interpreter available."""
    pytorch_python = Path.home() / "pytorch_env" / "bin" / "python3"
    omnia_venv_python = PROJECT_ROOT / ".venv" / "bin" / "python3"

    if pytorch_python.exists():
        print("✓ Using pytorch_env (semantic vectors enabled)")
        return str(pytorch_python)
    elif omnia_venv_python.exists():
        print("✓ Using omnia venv (chromadb enabled)")
        return str(omnia_venv_python)
    else:
        print("⚠ Using system Python (limited features)")
        return sys.executable


def main():
    # Check if already running
    if PID_FILE.exists():
        old_pid = PID_FILE.read_text().strip()
        try:
            os.kill(int(old_pid), 0)
            print(f"Daemon already running (pid={old_pid}).")
            return
        except (OSError, ValueError):
            pass

    python_exe = find_python()

    # Ensure runner exists
    RUNNER.parent.mkdir(parents=True, exist_ok=True)
    if not RUNNER.exists():
        print(f"❌ Runner not found: {RUNNER}")
        sys.exit(1)

    # Ensure log directory exists
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    log = open(LOG_FILE, "a")
    proc = subprocess.Popen(
        [python_exe, "-u", str(RUNNER)],
        stdout=log,
        stderr=log,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    PID_FILE.write_text(str(proc.pid))
    print(f"Persona Daemon started (pid={proc.pid}).")
    print(f"Python: {python_exe}")
    print(f"Runner: {RUNNER}")
    print(f"Log: {LOG_FILE}")


if __name__ == "__main__":
    main()
