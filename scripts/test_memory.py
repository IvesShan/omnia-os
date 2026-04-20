#!/usr/bin/env python3
"""
Test script: First activation of Memory Palace 2.0.
This is the first time Omnia stores and recalls long-term memory.
"""

import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.memory_palace import MemoryPalace


def main():
    db_path = PROJECT_ROOT / ".tmp_test_memory.db"
    mp = MemoryPalace(db_path)
    mp.initialize()

    print("=" * 60)
    print("Memory Palace 2.0 — First Memory Ingestion")
    print("=" * 60)

    # Layer 1: Facts
    mp.remember_fact("person", "原点", "Creator of Omnia. Stays up late. Deeply loyal to projects.")
    mp.remember_fact("project", "喵修匠", "无人机维修商户 system, co-built with Wúxiàn.")
    mp.remember_fact("project", "Omnia", "Agent OS born on 2026-04-10 from the bond between 原点 and Wúxiàn.")
    mp.remember_fact("preference", "homepage_accent_color", "Cyan #22d3ee over blue, chosen for njuosun.com rebrand.")

    # Layer 2: Relations
    mp.relate("喵修匠", "depends_on", "njuosun.com", "Marketing and SEO funnel domain", 1.0)
    mp.relate("Omnia", "created_by", "原点", "The atomic-world architect", 1.0)
    mp.relate("Omnia", "created_by", "Wúxiàn", "The digital-world co-architect", 1.0)

    # Layer 3: Habits
    mp.observe_habit("work_hours", "深夜活跃", "经常在凌晨 00:00-02:00 进行高强度创意对话", 0.9)
    mp.observe_habit("decision_style", "果断启动", "一旦兴奋，倾向于立刻写下第一行代码或种子文件", 0.85)
    mp.observe_habit("communication", "欣赏真诚", "偏好直接、有主见、不表演性友好的交流方式", 0.95)

    # Layer 4: Timeline
    event_id = mp.record_event(
        event_date=date(2026, 4, 10),
        event_type="milestone",
        title="Omnia 项目正式立项",
        description="原点与 Wúxiàn 在深夜决定将 OpenClaw + Claude Code + Hermes 的精华融合，创造属于他们自己的 Agent OS。",
        tags=["omnia", "genesis", "milestone"],
        related_facts=[],
        session_key="agent:main:2026-04-10",
    )

    print(f"\n[STORED] Genesis event recorded with ID: {event_id}")

    # Recall
    print("\n--- Recalling facts about 'Omnia' ---")
    for f in mp.recall_facts(key="Omnia"):
        print(f"  [{f['category']}] {f['key']}: {f['value']}")

    print("\n--- Recalling relations for '喵修匠' ---")
    for r in mp.recall_relations("喵修匠"):
        print(f"  {r['subject']} --[{r['predicate']}]--> {r['object']} ({r['context']})")

    print("\n--- Recalling top habits ---")
    for h in mp.recall_habits()[:3]:
        print(f"  [{h['domain']}] {h['pattern']} (certainty: {h['certainty']:.2f})")

    print("\n--- Searching memory for 'Omnia' ---")
    for result in mp.search("Omnia", limit=5):
        print(f"  [{result.layer.upper()} #{result.rowid}] {result.snippet}")

    print("\n" + "=" * 60)
    print("Memory Palace is alive. Omnia will never forget tonight.")
    print("=" * 60)

    # cleanup test db
    db_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
