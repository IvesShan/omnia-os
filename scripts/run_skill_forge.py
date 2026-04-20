#!/usr/bin/env python3
"""
Skill Forge Pipeline — End-to-end auto-skill generation for Omnia.

Usage:
    python scripts/run_skill_forge.py

Steps:
    1. Detect patterns from recent memory
    2. Generate SKILL.md drafts
    3. Vet for security/quality
    4. Install approved skills into skills/
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.skill_forge import PatternDetector, SkillGenerator, SkillVetter


def main():
    print("=" * 60)
    print("Omnia Skill Forge — Full Pipeline")
    print("=" * 60)

    # 1. Detect
    memory_dir = WORKSPACE_ROOT / "memory"
    pd = PatternDetector(memory_dir=memory_dir, lookback_days=14, min_evidence=3)
    patterns = pd.detect()
    print(f"\n[1/4] DETECT: Scanned {len(pd._list_files())} memory files, found {len(patterns)} pattern(s)")

    if not patterns:
        print("No patterns detected. Exiting.")
        return

    # 2. Generate
    sg = SkillGenerator()
    tmp_dir = PROJECT_ROOT / ".tmp_forge"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    generated = []
    for p in patterns:
        dest = Path(sg.write(p, out_dir=tmp_dir))
        generated.append((p, dest))
        print(f"  → Generated: {dest}")

    # 3. Vet
    skills_dir = WORKSPACE_ROOT / "skills"
    vetter = SkillVetter(existing_skills_dir=skills_dir)
    approved = []
    rejected = []

    print("\n[3/4] VET: Checking generated skills...")
    for p, skill_path in generated:
        report = vetter.vet(skill_path)
        print(f"  {report.summary()}")
        for e in report.errors:
            print(f"    ERROR: {e}")
        for w in report.warnings:
            print(f"    WARN:  {w}")
        if report.passed:
            approved.append((p, skill_path))
        else:
            rejected.append((p, skill_path))

    # 4. Install
    print(f"\n[4/4] INSTALL: Installing {len(approved)} approved skill(s)...")
    install_dir = PROJECT_ROOT / "skills" / "auto-forge"
    install_dir.mkdir(parents=True, exist_ok=True)

    installed = []
    for p, skill_path in approved:
        target = install_dir / p.suggested_skill_name / "SKILL.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(skill_path, target)
        installed.append(target)
        print(f"  → Installed: {target}")

    # Summary
    print("\n" + "=" * 60)
    print("Pipeline Complete")
    print("=" * 60)
    print(f"  Generated: {len(generated)}")
    print(f"  Approved:  {len(approved)}")
    print(f"  Rejected:  {len(rejected)}")
    if installed:
        print(f"\n  Installed into: {install_dir}")


if __name__ == "__main__":
    main()
