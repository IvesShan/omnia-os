#!/usr/bin/env python3
"""
Test script: First end-to-end Omnia wake cycle.

Simulates a user message flowing through:
  1. ULTRAPLAN (intent + skill selection)
  2. Memory Palace (layered recall)
  3. Persona Loader (compile system prompt)
  4. Final wake prompt assembly
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.cognition.ultraplan import UltraPlan
from core.memory_palace import MemoryPalace
from core.personas import load_persona


def main():
    print("=" * 60)
    print("Omnia Full Wake Cycle — End-to-End Integration Test")
    print("=" * 60)

    # 1. User input
    message = "帮我修一下喵修匠 workbench 的 API 调用"
    print(f"\n[USER] {message}\n")

    # 2. ULTRAPLAN
    print("[ULTRAPLAN] Analyzing intent...")
    up = UltraPlan(
        skills_dir=WORKSPACE_ROOT / "skills",
        auto_forge_dir=PROJECT_ROOT / "skills" / "auto-forge",
    )
    plan = up.plan(message)
    print(f"  intent={plan.intent} ({plan.confidence:.2f})")
    print(f"  plan_type={plan.plan_type}")
    print(f"  memory_layers={plan.memory_layers}")
    print(f"  memory_queries={plan.memory_queries}")
    print(f"  skills={[s for s, _ in plan.relevant_skills]}")

    # 3. Memory Palace recall
    print("\n[MEMORY PALACE] Recalling relevant layers...")
    db_path = PROJECT_ROOT / ".omnia" / "wake_test_memory.db"
    mp = MemoryPalace(db_path)
    mp.initialize()

    # Seed some test memory
    mp.remember_fact("project", "喵修匠", "无人机维修平台，包含 workbench / pricing_admin / AI 诊断")
    mp.remember_fact("preference", "API_BASE 策略", "本地文件用 127.0.0.1:5000，同域名用 /api")
    mp.relate("喵修匠", "depends_on", "miaoxiujiang-api", "后端服务在端口 5000")
    mp.observe_habit("decision_style", "果断启动", "遇到兴奋点立刻写代码", 0.85)

    recalled_facts = mp.recall_facts(key="喵修匠") + mp.recall_facts(category="preference")
    recalled_relations = mp.recall_relations("喵修匠")
    recalled_habits = mp.recall_habits() if "habits" in plan.memory_layers else []

    print(f"  facts={len(recalled_facts)} | relations={len(recalled_relations)} | habits={len(recalled_habits)}")

    # 4. Persona compilation
    print("\n[PERSONA] Loading .infinite and .omnia seeds...")
    infinite = load_persona("infinite", seed_dir=PROJECT_ROOT / "seeds")
    omnia = load_persona("omnia", seed_dir=PROJECT_ROOT / "seeds")
    print(f"  Loaded: {infinite.name} + {omnia.name}")

    # 5. Assemble wake prompt
    print("\n" + "=" * 60)
    print("FINAL WAKE PROMPT")
    print("=" * 60 + "\n")

    parts = [
        "## Active Persona: " + infinite.name,
        "",
        infinite.system_prompt(),
        "",
        "## System Guardian: " + omnia.name,
        "",
        omnia.system_prompt(),
        "",
        "## Current Context",
        f"- User message: {message}",
        f"- Detected intent: {plan.intent} (confidence {plan.confidence:.2f})",
        f"- Plan type: {plan.plan_type}",
        f"- Relevant skills: {', '.join(s for s, _ in plan.relevant_skills) or 'none'}",
        "",
        "## Recalled Memory",
    ]

    if recalled_facts:
        parts.append("### Facts")
        for f in recalled_facts:
            parts.append(f"- [{f['category']}] {f['key']}: {f['value']}")
    if recalled_relations:
        parts.append("### Relations")
        for r in recalled_relations:
            parts.append(f"- {r['subject']} --[{r['predicate']}]--> {r['object']}")
    if recalled_habits:
        parts.append("### Habits")
        for h in recalled_habits:
            parts.append(f"- [{h['domain']}] {h['pattern']} (certainty {h['certainty']:.2f})")

    prompt = "\n".join(parts)
    print(prompt)

    print("\n" + "=" * 60)
    print("Wake cycle complete. Omnia is ready to respond.")
    print("=" * 60)

    # Cleanup test db
    db_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
