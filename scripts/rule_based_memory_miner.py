#!/usr/bin/env python3
"""Rule-based memory miner — fast, precise, zero hallucination."""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from core.memory_palace.memory_palace import MemoryPalace

MEMORY_DIR = PROJECT_ROOT.parent / "memory"
DB_PATH = PROJECT_ROOT.parent / ".omnia" / "memory_palace.db"


def gather() -> list[dict]:
    files = []
    for f in sorted(MEMORY_DIR.glob("2026-*.md")):
        text = f.read_text(encoding="utf-8")
        if len(text.strip()) < 20:
            continue
        m = re.search(r"(\d{4}-\d{2}-\d{2})", f.name)
        d = m.group(1) if m else ""
        files.append({"name": f.name, "date": d, "text": text})
    return files


def extract_code_blocks(text: str) -> list[tuple[str, str]]:
    """Yield (lang, code) pairs from markdown code fences."""
    for block in re.findall(r"```(\w*)\n(.*?)```", text, re.S):
        lang, code = block
        yield (lang.strip().lower(), code.strip())


def extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://[^\s\)\]\>\"'`]+", text)


def extract_colors(text: str) -> list[str]:
    return list(set(re.findall(r"#[a-fA-F0-9]{3,8}", text)))


def extract_file_paths(text: str) -> list[str]:
    # Common path patterns in our workspace
    paths = re.findall(r"`~?[\w\-/.]+\.(?:py|js|html|css|md|json|xml|sh|txt|sql|vpy)`", text)
    # Also catch bare paths like drone-repair-website/index.html or omnia-os/src/...
    bare = re.findall(r"(?:/~)?[\w\-]+(?:/[\w\-]+)+\.[\w]+", text)
    combined = [p.strip("`") for p in paths] + bare
    return list(set(combined))


def extract_commands(text: str) -> list[str]:
    cmds = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(("python3 ", "python ", "pip ", "cd ", "git ", "curl ", "wget ", "rsync ", "systemctl ", "nohup ", "rm ", "cp ", "mv ", "mkdir ", "cat ", "grep ", "find ", "ls ", "code ", "openclaw ", "edgeone ")):
            cmds.append(line)
        elif line.startswith(("- ", "* ")) and any(k in line for k in ["python3", "curl", "git", "systemctl", "nohup"]):
            cmds.append(line.lstrip("-* ").strip())
    return cmds


def extract_prferences_and_decisions(text: str) -> list[dict]:
    habits = []
    preference_patterns = [
        r"用户(?:明确)?(?:说|表示|要求|偏好|喜欢|选择|决定|确认|定|批)(.*?)(?:\n|$)",
        r"(?:偏好|原则|态度|风格)[：:\s]+(.*?)(?:\n|$)",
        r"用户不(.*?)(?:\n|$)",
        r"(?:共识|约定)[：:\s]+(.*?)(?:\n|$)",
    ]
    for pat in preference_patterns:
        for m in re.finditer(pat, text):
            sentence = m.group(1).strip("。.\n`")
            if len(sentence) > 3:
                habits.append({"pattern": sentence, "evidence": "extracted from diary", "certainty": 0.85})
    return habits


def extract_status_lines(text: str) -> list[dict]:
    facts = []
    # Table rows like | feature | ✅ done |
    for line in text.splitlines():
        if "|" in line and any(e in line for e in ["✅", "⏳", "⚠️", "🔄", "❌"]):
            facts.append({"key": line.strip("| "), "value": "project status snapshot", "category": "project_status", "strength": 0.9})
        # Inline status badges
        m = re.search(r"([\w\-\.]+)\s*[:\-]?\s*(✅|⏳|⚠️|❌|🔄)\s*(.+)", line)
        if m:
            facts.append({"key": f"{m.group(1)}: {m.group(3).strip()}", "value": m.group(2), "category": "project_status", "strength": 0.9})
    return facts


def extract_milestones(text: str, file_date: str) -> list[dict]:
    events = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("### "):
            title = line.lstrip("# ").strip()
            if len(title) > 3:
                events.append({
                    "event_date": file_date,
                    "event_type": "milestone",
                    "title": title,
                    "description": "",
                    "tags": ["diary_milestone"],
                })
    return events


def extract_api_endpoints(text: str) -> list[str]:
    return list(set(re.findall(r"(?:GET|POST|PUT|DELETE)\s+(/api/[^\s\)`\"]+)", text)))


def extract_commit_hashes(text: str) -> list[str]:
    return re.findall(r"`[a-f0-9]{7,40}`", text)


def main():
    files = gather()
    print(f"[miner] {len(files)} files to scan")

    mp = MemoryPalace(str(DB_PATH))
    mp.initialize()

    all_facts = 0
    all_habits = 0
    all_events = 0

    for f in files:
        name = f["name"]
        date_str = f["date"]
        text = f["text"]

        # 1. Code blocks -> facts
        for lang, code in extract_code_blocks(text):
            snippet = code.replace("\n", " ")[:300]
            cat = "code_snippet" if not lang else f"code_{lang}"
            mp.remember_fact(cat, f"{name}:{snippet[:80]}", snippet, "rule_miner", 0.85)
            all_facts += 1

        # 2. URLs -> facts
        for url in extract_urls(text):
            mp.remember_fact("url", url, url, "rule_miner", 0.9)
            all_facts += 1

        # 3. Colors -> facts
        for c in extract_colors(text):
            mp.remember_fact("design_color", c, f"color value found in {name}", "rule_miner", 0.85)
            all_facts += 1

        # 4. File paths -> facts
        for p in extract_file_paths(text):
            if len(p) < 200:
                mp.remember_fact("file_path", p, f"mentioned in {name}", "rule_miner", 0.85)
                all_facts += 1

        # 5. Shell commands -> facts
        for cmd in extract_commands(text):
            mp.remember_fact("command", cmd[:120], f"from {name}", "rule_miner", 0.85)
            all_facts += 1

        # 6. API endpoints -> facts
        for ep in extract_api_endpoints(text):
            mp.remember_fact("api_endpoint", ep, f"from {name}", "rule_miner", 0.9)
            all_facts += 1

        # 7. Commit hashes -> facts
        for h in extract_commit_hashes(text):
            mp.remember_fact("git_commit", h.strip("`"), f"from {name}", "rule_miner", 0.8)
            all_facts += 1

        # 8. Status lines -> facts
        for st in extract_status_lines(text):
            mp.remember_fact(st["category"], st["key"], st["value"], "rule_miner", st["strength"])
            all_facts += 1

        # 9. Habits/preferences
        for hab in extract_prferences_and_decisions(text):
            mp.observe_habit("preference", hab["pattern"], hab["evidence"], hab["certainty"])
            all_habits += 1

        # 10. Milestones -> timeline
        for ev in extract_milestones(text, date_str):
            try:
                ed = date.fromisoformat(ev["event_date"]) if ev["event_date"] else date.today()
            except Exception:
                ed = date.today()
            mp.record_event(ed, ev["event_type"], ev["title"], ev["description"], ev["tags"], "rule_miner_2026-04-11")
            all_events += 1

    # Cross-file synthetic facts: deduplicate colors with contexts
    # (optional enhancement left simple)

    print(f"[miner] Injected: facts+={all_facts} habits+={all_habits} events+={all_events}")
    print("[miner] Done. Omnia's memory palace is now densely populated.")


if __name__ == "__main__":
    main()
