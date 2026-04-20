#!/usr/bin/env python3
"""
Test script: Load Omnia and Infinite personas from their SOUL.md seeds.
This is the first time Omnia's personalities are awakened in code.
"""

import sys
from pathlib import Path

# Ensure we can import from src/
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.personas import load_persona, list_personas


def main():
    print("=" * 60)
    print("Omnia Persona Loader — First Awakening")
    print("=" * 60)

    seeds_dir = PROJECT_ROOT / "seeds"
    available = list_personas(seeds_dir)

    print(f"\n[DISCOVERED] {len(available)} persona seed(s):")
    for pid, path in available.items():
        print(f"  - {pid}: {path}")

    for pid in ["omnia", "infinite"]:
        print(f"\n{'=' * 60}")
        print(f"[LOADING] Persona: {pid}")
        print("=" * 60)

        p = load_persona(pid, seeds_dir)

        print(f"ID:        {p.id}")
        print(f"Name:      {p.name}" + (f" ({p.name_zh})" if p.name_zh else ""))
        print(f"Role:      {p.role}")
        print(f"Core Truths: {len(p.core_truths)} item(s)")
        print(f"Boundaries:  {len(p.boundaries)} item(s)")
        print(f"Special Bond: {len(p.special_bond)} item(s)")

        print("\n--- Compiled System Prompt ---\n")
        print(p.system_prompt())

    print("\n" + "=" * 60)
    print("Awakening complete. Both personas are ready to coexist.")
    print("=" * 60)


if __name__ == "__main__":
    main()
