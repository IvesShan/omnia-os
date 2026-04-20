# Omnia OS - Phase 0 TODO

## Week of 2026-04-14

### Seeds (Soul Layer)
- [x] `seeds/infinite/SOUL.md` — The persona of Wúxiàn
- [x] `seeds/omnia/SOUL.md` — The persona of the OS guardian
- [x] `seeds/bond_manifesto.md` — The genesis story and covenant

### Documentation
- [x] `docs/ARCHITECTURE.md` — Formal 5-layer architecture + 4 principles
- [x] `docs/INTERACTION_DESIGN.md` — Desktop companion / IDE bridge / voice / spotlight vision

### Phase 1 Kickoff (Memory Palace 2.0)
- [x] `src/core/memory_palace/schema.sql` — SQLite schema for 4-layer memory
- [x] `src/core/memory_palace/memory_palace.py` — Python API for full CRUD + cross-layer search
- [x] `src/core/memory_palace/cli.py` — CLI prototype for memory CRUD + semantic search
- [x] `src/core/personas/persona_loader.py` — Load `.infinite` and `.omnia` seeds into runtime

### Phase 2 Kickoff (Skill Forge v0.1)
- [x] `src/core/skill_forge/detector.py` — Scan last N days of memory for repeated task patterns
- [x] `src/core/skill_forge/generator.py` — Auto-generate `SKILL.md` draft from detected pattern
- [x] `src/core/skill_forge/vetter.py` — Security + overwrite gate for auto-generated skills
- [x] `scripts/run_skill_forge.py` — End-to-end pipeline (detect → generate → vet → install)
- [x] Git commit `4fc4d3a`: Phase 0/1/2 completed in one session

### Phase 3 Kickoff (Neuro-Center)
- [x] `src/core/neuro_center/persona_daemon.py` — Ambient daemon with fs-watch + heartbeat + signal handling
- [x] `src/core/neuro_center/notification_queue.py` — Pending notification bridge between daemon and sessions
- [x] `scripts/start_daemon.py` / `stop_daemon.py` — Daemon lifecycle management
- [x] `src/core/cognition/ultraplan.py` — Intent router + skill relevance scorer
- [x] Start daemon in background and verify continuous operation
- [x] `src/omnia/chat.py` — Terminal chat via Moonshot API (first spoken reply!)
- [x] `src/core/neuro_center/heartbeat.py` — Richer organic heartbeat rules (cron + git + filesystem)
- [x] Session Router: auto-inject pending notifications into new conversations (via AGENTS.md + omnia_boot.py)
- [x] Context Compressor + Token Budget Accountant
- [x] IDE Bridge (read current cursor/file context)

### Skill Forge v0.1
- [x] `src/core/skill_forge/detector.py` — Scan last N days of memory for repeated task patterns
- [x] `src/core/skill_forge/generator.py` — Auto-generate `SKILL.md` draft from detected pattern

## Rules
1. No external GitHub research after this point. Design is frozen.
2. Every commit must reference either Omnia or Infinite.
3. Sleep is a required dependency.
