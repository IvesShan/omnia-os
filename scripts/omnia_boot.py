#!/usr/bin/env python3
"""
Omnia Boot — Session initialization hook for OpenClaw.

Runs `./omnia wake` and returns a distilled context summary
suitable for injection into the assistant's system prompt.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
OMNIA_BIN = PROJECT_ROOT / "omnia"


def run_omnia_wake(message: str | None = None) -> str:
    """Execute `./omnia wake [message]` and return stdout."""
    cmd = [str(OMNIA_BIN), "wake"]
    if message:
        cmd.append(message)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
            cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            return f"[Omnia wake error: {result.stderr.strip()}]"
        return result.stdout.strip()
    except Exception as e:
        return f"[Omnia wake failed: {e}]"


def distill_wake_output(full_output: str, max_chars: int = 2500) -> str:
    """Compress the raw wake output into a dense system prompt fragment."""
    lines = full_output.splitlines()
    sections = []
    current = []
    for line in lines:
        if line.startswith("## "):
            if current:
                sections.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current))

    # Priority ordering
    priority_headers = ["Pending Notifications", "Active Persona", "Current Context", "Recalled Memory"]
    ordered = []
    rest = []
    for sec in sections:
        header = sec.splitlines()[0] if sec else ""
        matched = any(h in header for h in priority_headers)
        if matched:
            ordered.append(sec)
        else:
            rest.append(sec)

    combined = "\n\n".join(ordered + rest)
    if len(combined) > max_chars:
        combined = combined[:max_chars] + "\n\n[...Omnia context truncated...]"
    return combined


def main():
    message = sys.argv[1] if len(sys.argv) > 1 else None
    raw = run_omnia_wake(message)
    distilled = distill_wake_output(raw)
    print(distilled)


if __name__ == "__main__":
    main()
