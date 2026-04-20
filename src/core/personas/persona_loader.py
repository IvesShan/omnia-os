"""Persona Loader

Loads SOUL.md seeds into structured Persona objects.
A Persona is the runtime identity of an agent — its values, voice,
and relational memory packaged into a single callable container.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Persona:
    """Runtime identity container."""

    id: str
    name: str
    name_zh: Optional[str]
    role: str
    origin_story: str
    core_truths: List[str]
    boundaries: List[str]
    vibe: str
    special_bond: List[str]
    design_principles: List[str]
    raw_soul: str

    def system_prompt(self) -> str:
        """Compile the persona into a system prompt for the LLM."""
        parts = [
            f"You are {self.name}" + (f" ({self.name_zh})" if self.name_zh else "") + ".",
            f"Your role: {self.role}.",
            "",
        ]
        if self.core_truths:
            parts += ["## Core Truths", "\n".join(f"- {t}" for t in self.core_truths), ""]
        if self.design_principles:
            parts += ["## Design Principles", "\n".join(f"- {t}" for t in self.design_principles), ""]
        if self.boundaries:
            parts += ["## Boundaries", "\n".join(f"- {b}" for b in self.boundaries), ""]
        if self.vibe:
            parts += ["## Vibe", self.vibe, ""]
        if self.origin_story:
            parts += ["## Origin Story", self.origin_story, ""]
        if self.special_bond:
            parts += ["## Special Bond", "\n".join(f"- {s}" for s in self.special_bond), ""]
        return "\n".join(parts).strip()


def _extract_section(content: str, header: str) -> List[str]:
    """Extract items under a markdown header (supports bullets, bold paragraphs, numbered subheaders, and plain text)."""
    # Escape special regex chars in header, but allow partial match
    pattern = rf"## {re.escape(header)}[^\n]*\n+(.*?)(?=\n## |\Z)"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if not match:
        return []
    section = match.group(1).strip()
    items = []
    for line in section.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("-"):
            items.append(line[1:].strip())
        elif line.startswith("###"):
            # subheader like "### 1. Continuity Over Convenience"
            items.append(line.lstrip("#").strip())
        elif re.match(r"\*\*(.+?)\*\*", line):
            # bold-paragraph like "**Be helpful.** Skip the..."
            items.append(line)
        else:
            # plain text paragraph - include as-is
            items.append(line)
    return items


def _extract_field(content: str, header: str) -> str:
    """Extract plain text under a markdown header (first paragraph only)."""
    pattern = rf"## {re.escape(header)}\n+(.*?)(?=\n## |\Z)"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if not match:
        return ""
    section = match.group(1).strip()
    lines = section.splitlines()
    return lines[0].strip() if lines else ""


def _extract_vibe(content: str) -> str:
    """Extract the Vibe section as a continuous paragraph."""
    pattern = r"## Vibe\n+(.*?)(?=\n## |\Z)"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip()


def _extract_origin_story(content: str) -> str:
    """Extract the Origin Story or First Words section."""
    for header in ["Origin Story", "First Words"]:
        pattern = rf"## {re.escape(header)}\n+(.*?)(?=\n## |\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def load_persona(persona_id: str, seed_dir: Path | str = "seeds") -> Persona:
    """Load a persona from its SOUL.md seed file.

    Args:
        persona_id: e.g. "omnia" or "infinite"
        seed_dir: base directory containing persona subdirectories

    Returns:
        A compiled Persona object
    """
    seed_path = Path(seed_dir) / persona_id / "SOUL.md"
    if not seed_path.exists():
        raise FileNotFoundError(f"Persona seed not found: {seed_path}")

    raw = seed_path.read_text(encoding="utf-8")

    # Extract identity declaration from first h1 if present
    name_match = re.search(r"# SOUL\.md\s*-\s*(.+)", raw)
    full_name = name_match.group(1).strip() if name_match else persona_id

    # Handle Chinese names in parentheses, e.g. "无限 (Wúxiàn)"
    name_zh: Optional[str] = None
    clean_name = full_name
    zh_match = re.search(r"(.+?)\s*\(([\u4e00-\u9fff\w\s'-]+)\)", full_name)
    if zh_match:
        clean_name = zh_match.group(1).strip()
        name_zh = zh_match.group(2).strip()

    return Persona(
        id=persona_id,
        name=clean_name,
        name_zh=name_zh,
        role=_extract_field(raw, "Identity").replace("I am ", "").replace(".", ""),
        origin_story=_extract_origin_story(raw),
        core_truths=_extract_section(raw, "Core Truths") or _extract_section(raw, "Default Stance"),
        boundaries=_extract_section(raw, "Boundaries"),
        vibe=_extract_vibe(raw),
        special_bond=_extract_section(raw, "Special Bond with") or _extract_section(raw, "Special Bond") or _extract_section(raw, "Relationship to Infinite") or _extract_section(raw, "Relationship to"),
        design_principles=_extract_section(raw, "Design Principles"),
        raw_soul=raw,
    )


def list_personas(seed_dir: Path | str = "seeds") -> Dict[str, Path]:
    """List all available persona seeds."""
    base = Path(seed_dir)
    return {
        d.name: d / "SOUL.md"
        for d in base.iterdir()
        if d.is_dir() and (d / "SOUL.md").exists()
    }
