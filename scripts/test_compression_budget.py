#!/usr/bin/env python3
"""Test script: Context Compressor + Token Budget Accountant."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.cognition.context_compressor import ContextCompressor, extract_key_lines
from core.cognition.token_budget import TokenBudget, PromptComponent


def main():
    print("=" * 60)
    print("Context Compressor + Token Budget Test")
    print("=" * 60)

    cc = ContextCompressor()

    # 1. Small output (keep full)
    small = "Error: cannot find module 'requests'."
    r1 = cc.compress(small)
    print(f"\n[SMALL] method={r1.method}, tokens={r1.original_tokens}->{r1.compressed_tokens}")

    # 2. Medium output (extract key lines)
    medium = "\n".join([f"Line {i}: processing item {i}" for i in range(50)])
    medium += "\nSuccess: 50 items processed."
    medium += "\nWarning: 3 items failed validation."
    r2 = cc.compress(medium, label="batch_result")
    print(f"\n[MEDIUM] method={r2.method}, tokens={r2.original_tokens}->{r2.compressed_tokens}")
    print("Summary preview:", r2.summary[:120], "...")

    # 3. Large output (aggressive)
    large = "\n".join([f"Log entry {i}: some verbose debug text here" for i in range(500)])
    large += "\nException: Connection timeout at line 499."
    r3 = cc.compress(large, label="deploy_log")
    print(f"\n[LARGE] method={r3.method}, tokens={r3.original_tokens}->{r3.compressed_tokens}")
    print("Evidence lines:", len(r3.preserved_evidence))

    # 4. Token Budget enforcement
    print("\n" + "=" * 60)
    print("Token Budget Enforcement")
    print("=" * 60)

    tb = TokenBudget(system_limit=200, session_limit=1000)

    components = [
        PromptComponent("persona", "You are Infinite. Be helpful.", priority=100),
        PromptComponent("facts", "Fact A: project X is active.\nFact B: user likes dark mode.", priority=80),
        PromptComponent("habits", "Habit 1: late night worker.\nHabit 2: prefers concise.", priority=60),
        PromptComponent("timeline", "2026-04-10: Omnia born.\n2026-04-11: chat works.", priority=40),
        PromptComponent("skills", "Skill A: content gen.\nSkill B: deployment.", priority=20),
    ]

    system_text, evicted, system_tokens = tb.enforce_system_prompt(components)
    print(f"\nKept components: {[c.name for c in components if c.name not in evicted]}")
    print(f"Evicted: {evicted}")
    print(f"System tokens: {system_tokens} / {tb.system_limit}")

    report = tb.check_session(system_text, history_text="User: hello\nAssistant: hi")
    print(f"Session status: {report.status} ({report.session_tokens} / {report.limit_session})")

    print("\n" + "=" * 60)
    print("Compression + Budget test complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
