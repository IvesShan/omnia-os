#!/usr/bin/env python3
"""Test script: First run of Skill Forge v0.1.
Detects patterns from memory and generates SKILL.md drafts."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.skill_forge.detector import PatternDetector
from core.skill_forge.generator import SkillGenerator


def main():
    print("=" * 60)
    print("Skill Forge v0.1 — First Run")
    print("=" * 60)

    pd = PatternDetector(memory_dir=PROJECT_ROOT / ".." / "memory")
    patterns = pd.detect()

    print(f"\nScanned {len(pd._list_files())} memory files.")
    print(f"Detected {len(patterns)} pattern(s).\n")

    sg = SkillGenerator()
    generated_dir = PROJECT_ROOT / ".tmp_skills"
    generated_dir.mkdir(exist_ok=True)

    for p in patterns:
        print(f"[{p.pattern_id}] {p.pattern_name}")
        print(f"  confidence={p.confidence:.2f} | frequency={p.frequency}")

        dest = sg.write(p, out_dir=generated_dir)
        print(f"  → {dest}\n")

    print("=" * 60)
    print(f"All drafts written to: {generated_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
