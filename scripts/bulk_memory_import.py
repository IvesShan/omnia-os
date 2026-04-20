#!/usr/bin/env python3
"""Deep memory miner — batched LLM extraction from all diaries."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from core.memory_palace.memory_palace import MemoryPalace

API_KEY = os.environ.get("MOONSHOT_API_KEY", "")
if not API_KEY:
    for ep in [PROJECT_ROOT / ".env", PROJECT_ROOT.parent / ".env"]:
        if ep.exists():
            for line in ep.read_text(encoding="utf-8").splitlines():
                if line.startswith("MOONSHOT_API_KEY="):
                    API_KEY = line.split("=", 1)[1].strip().strip('"')
                    break
        if API_KEY:
            break

MEMORY_DIR = PROJECT_ROOT.parent / "memory"
DB_PATH = PROJECT_ROOT.parent / ".omnia" / "memory_palace.db"
LOG_PATH = PROJECT_ROOT.parent / ".omnia" / "memory_import.log"


def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line)
    print(line, end="")


def extract_date(name: str) -> str:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", name)
    return m.group(1) if m else ""


def gather() -> list[dict]:
    sources = []
    for f in sorted(MEMORY_DIR.glob("2026-*.md")):
        text = f.read_text(encoding="utf-8")
        if len(text.strip()) < 20:
            continue
        sources.append({"filename": f.name, "date": extract_date(f.name), "text": text})
    return sources


def build_prompt(batch: list[dict]) -> str:
    parts = [
        "You are Omnia's deep memory miner. Read these diary entries and extract EVERY durable technical fact, preference, decision, URL, command, API endpoint, file path, architecture choice, deployment step, design spec, and milestone.",
        "Output ONLY a compact JSON object with keys: facts[], habits[], relations[], timeline_events[].",
        "Be exhaustive but concise. Omit casual banter. Prioritize actionable knowledge.",
        "file-level dates are approximate event dates.",
    ]
    for s in batch:
        parts.append(f"\n--- {s['filename']} ({s['date']}) ---\n{s['text']}")
    return "\n".join(parts)


def call_kimi(prompt: str) -> dict:
    import requests

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "Kilo-Code/1.0",
    }
    payload = {
        "model": "kimi-latest",
        "messages": [
            {
                "role": "system",
                "content": "Extract structured memory from markdown diaries. Output pure compact JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }
    resp = requests.post(
        "https://api.kimi.com/coding/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=300,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def chunked(lst: list, n: int):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def commit(mp: MemoryPalace, data: dict):
    for f in data.get("facts", []):
        try:
            mp.remember_fact(
                category=f.get("category", "general"),
                key=f.get("key", ""),
                value=f.get("value", ""),
                source=f.get("source", "diary_miner"),
                strength=float(f.get("strength", 0.9)),
            )
        except Exception:
            pass
    for h in data.get("habits", []):
        try:
            mp.observe_habit(
                domain=h.get("domain", "general"),
                pattern=h.get("pattern", ""),
                evidence=h.get("evidence", ""),
                certainty=float(h.get("certainty", 0.7)),
            )
        except Exception:
            pass
    for r in data.get("relations", []):
        try:
            mp.relate(
                subject=r.get("subject", ""),
                predicate=r.get("predicate", ""),
                object=r.get("object", ""),
                context=r.get("context", ""),
                strength=float(r.get("strength", 0.9)),
            )
        except Exception:
            pass
    for e in data.get("timeline_events", []):
        try:
            ed = e.get("event_date", "")
            event_date = date.fromisoformat(ed) if ed else date.today()
        except Exception:
            event_date = date.today()
        try:
            mp.record_event(
                event_date=event_date,
                event_type=e.get("event_type", "milestone"),
                title=e.get("title", ""),
                description=e.get("description", ""),
                tags=e.get("tags", []),
                session_key="deep_memory_miner_2026-04-11",
            )
        except Exception:
            pass


def main():
    sources = gather()
    total = len(sources)
    log(f"Started. {total} files to mine.")
    if not total:
        return

    mp = MemoryPalace(str(DB_PATH))
    mp.initialize()

    batch_size = 2
    batches = list(chunked(sources, batch_size))

    for idx, batch in enumerate(batches, 1):
        log(f"Batch {idx}/{len(batches)} → {', '.join(b['filename'] for b in batch)}")
        prompt = build_prompt(batch)
        try:
            data = call_kimi(prompt)
            log(
                f"  OK  facts={len(data.get('facts', []))} "
                f"habits={len(data.get('habits', []))} "
                f"relations={len(data.get('relations', []))} "
                f"events={len(data.get('timeline_events', []))}"
            )
            commit(mp, data)
        except Exception as e:
            log(f"  FAIL {e}")
            continue

    log("Finished deep memory mining.")


if __name__ == "__main__":
    main()
