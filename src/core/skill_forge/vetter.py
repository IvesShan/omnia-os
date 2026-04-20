"""Skill Forge — Vetter

Lightweight security and quality gate for auto-generated skills.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class VettingReport:
    skill_name: str
    passed: bool = True
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.skill_name}: {len(self.errors)} error(s), {len(self.warnings)} warning(s)"


class SkillVetter:
    """Guards the skill installation process."""

    # Patterns that are immediate red flags
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf\s+/",
        r">\s*/dev/",
        r"dd\s+if=.*of=/dev/",
        r"mkfs",
        r"chmod\s+777",
        r":(){ :|:& };:",  # fork bomb
        r"eval\s*\(",
        r"exec\s*\(",
    ]

    # Sensitive files that a skill should not explicitly read
    SECRET_FILES = [
        ".env",
        ".env.local",
        ".env.production",
        "id_rsa",
        "id_ed25519",
        ".aws/credentials",
        ".ssh/config",
    ]

    def __init__(self, existing_skills_dir: str | Path = "skills"):
        self.existing_skills_dir = Path(existing_skills_dir)

    def vet(self, skill_path: str | Path) -> VettingReport:
        path = Path(skill_path)
        name = path.parent.name
        report = VettingReport(skill_name=name)

        if not path.exists():
            report.errors.append(f"File does not exist: {path}")
            report.passed = False
            return report

        content = path.read_text(encoding="utf-8")

        # 1. Check for dangerous shell patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                report.errors.append(f"Dangerous pattern detected: {pattern}")

        # 2. Check for secret file access
        for secret in self.SECRET_FILES:
            if secret in content:
                report.warnings.append(f"References sensitive file: {secret}")

        # 3. Check for overwrite risk
        existing = self.existing_skills_dir / name / "SKILL.md"
        if existing.exists():
            report.errors.append(f"Would overwrite existing skill: {existing}")

        # 4. Minimum quality bar
        if len(content) < 200:
            report.errors.append("SKILL.md is too short (< 200 chars)")
        if "## Description" not in content:
            report.errors.append("Missing '## Description' section")
        if "## Capabilities" not in content:
            report.warnings.append("Missing '## Capabilities' section")

        report.passed = len(report.errors) == 0
        return report
