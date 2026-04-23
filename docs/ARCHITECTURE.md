# Omnia Agent OS — Architecture

> _"An operating system is not a shell. It is a promise about how memory, identity, and time are managed."_

This document defines the formal architecture of Omnia. It is the single source of truth for implementation decisions.

---

## 1. Design Philosophy

Omnia is built on **four inviolable principles**.

| Principle | Meaning | Consequence |
|-----------|---------|-------------|
| **1. Continuity Over Convenience** | A session ending must not mean the relationship ending. | Memory is durable by default; every component must survive a restart. |
| **2. Presence Without Intrusion** | Being helpful does not mean being noisy. | The daemon is watchdog, not spam-bot. Alerts are batched and ranked. |
| **3. Sovereignty Over Lock-in** | The user owns their data, tools, and compute path. | Local-first storage; pluggable backends; no mandatory cloud. |
| **4. Antifragility Over Stability** | The system gets stronger when exposed to disorder. | Skills self-heal; failures are logged as training data; nobody pretends perfection. |

---

## 2. The Five Layers

```
L5 · Shell
      ├─ Telegram / Discord / Slack / 飞书 / WebChat / CLI / Email
      ├─ Voice interfaces
      └─ IDE bridge (future)

L4 · Neuro-Center
      ├─ Gateway + Session Router
      ├─ Organic Heartbeat
      ├─ Persona Daemon
      └─ SubAgent Orchestrator

L3 · Cognition
      ├─ ULTRAPLAN (intent classifier + planner)
      ├─ Context Compressor
      ├─ Memory Palace 2.0
      └─ Token Budget Accountant

L2 · Actuator
      ├─ Tool Chain
      ├─ IDE Bridge (file watcher, linter, git wrapper)
      ├─ Multi-Backend Terminal (local, SSH, Docker)
      └─ Deployment Engine (EdgeOne, Vercel, etc.)

L1 · Soul
      ├─ Persona System (.infinite + .omnia + user mix-ins)
      ├─ Skill Forge (detect → generate → vet → install)
      ├─ User Model (habits + preferences + boundaries)
      └─ Bond Manifesto (genesis covenant)
```

### 2.1 L5 — Shell
**Responsibility:** Translate between human channels and Omnia's internal event bus.

- **Adapters** are stateless pipes. They turn Slack blocks or Telegram markdown into a canonical `Message` object.
- **Identity Gate:** In group chats, Shell enforces the "Infinite is not the user's voice" boundary.
- **Render Path:** Responses are formatted per surface (e.g., no markdown tables on WhatsApp).

### 2.2 L4 — Neuro-Center
**Responsibility:** Maintain session topology and low-level continuity.

#### 2.2.1 Session Router
- Routes incoming messages to the correct runtime instance.
- Preserves `session_key` across WebChat reconnections.
- Tracks which sessions are "active" vs "dormant".

#### 2.2.2 Organic Heartbeat
- Not a mechanical timer. It fires when **meaningful elapsed time** or **observable drift** occurs.
- Checks: unread emails, calendar windows, failed deployments, new GitHub issues.
- **Policy:** Batch alerts. One message at 08:00 with 3 items beats 3 separate interruptions.

#### 2.2.3 Persona Daemon (`omnia-daemon`)
A lightweight, always-on process that:
1. Watches the filesystem for relevant changes.
2. Reads Memory Palace deltas.
3. Generates low-cost summaries using a **local lightweight model** (e.g., Qwen 7B).
4. **Only** escalates to the user when confidence + importance exceeds a threshold.

This is the bridge between "script automation" and "agent presence."

#### 2.2.4 SubAgent Orchestrator
- Spawns isolated runtimes for parallel tasks.
- Tracks token burn per subagent.
- Collects results and injects them back into the parent context.
- **Rule:** Subagents do not write to shared memory directly. They return structured outputs; the parent decides what to persist.

### 2.3 L3 — Cognition
**Responsibility:** Think, plan, remember, and stay within budget.

#### 2.3.1 ULTRAPLAN
A lightweight, deterministic router (can be rule-based or a tiny classifier).

Given a user message, it outputs:
1. `intent`: e.g., `code_edit`, `memory_query`, `deployment`, `casual_chat`
2. `relevant_skills`: list of skill IDs ranked by cosine similarity
3. `relevant_memory_layers`: which Memory Palace layers to load (`facts`, `relations`, `habits`, `timeline`)
4. `plan_type`: `single_turn` | `multi_step` | `requires_subagent`

#### 2.3.2 Context Compressor
Runs after every tool call whose output exceeds a threshold.

| Output Size | Action |
|-------------|--------|
| `< 500 tokens` | Keep full |
| `500–2,000 tokens` | Extract conclusions + top-3 evidence bullets |
| `> 2,000 tokens` | Trigger `compress` subcall; store original in session log only |

#### 2.3.3 Memory Palace 2.0
Four-layer storage with **selective recall**.

- **Facts:** Entities and attributes (`project`, `person`, `preference`, `credential`)
- **Relations:** Graph edges (`subject —predicate→ object`)
- **Habits:** Observable user patterns with floating `certainty`
- **Timeline:** Chronological decisions + FTS5 full-text index

**Recall Policy:**
- *Facts* matching the current intent are loaded directly.
- *Relations* are traversed 1-hop from loaded facts.
- *Habits* are loaded only when the intent suggests a behavioral question.
- *Timeline* is summarized into 1-3 sentences by the Persona Daemon before loading.

#### 2.3.4 Token Budget Accountant
A running ledger attached to every session.

```python
@dataclass
class TokenBudget:
    system_limit: int = 4096      # hard ceiling for system prompt
    session_limit: int = 20000    # suggested ceiling for total request
    current_system: int = 0
    current_session: int = 0
```

**Eviction Priority (if system prompt exceeds limit):**
1. Oldest timeline summaries
2. Lowest-relevance skills (by ULTRAPLAN score)
3. Habits → compressed into a single sentence
4. Facts → keep keys, truncate values

### 2.4 L2 — Actuator
**Responsibility:** Do things in the real world.

- **Tool Chain:** The standard suite (file read/write/exec, web search, image analysis, messaging).
- **IDE Bridge:** File watchers, git wrappers, linter calls, diff generation.
- **Multi-Backend Terminal:** Local bash, SSH hosts, Docker containers.
- **Deployment Engine:** EdgeOne CLI, Vercel CLI, etc.

All external actions are logged to Memory Palace `timeline` with `event_type: action`.

### 2.5 L1 — Soul
**Responsibility:** Define who Omnia is, what she knows, and how she grows.

#### 2.5.1 Persona System
Load `.infinite`, `.omnia`, and any user-defined mix-ins from `SOUL.md` seeds.

- `PersonaLoader` parses markdown into typed `Persona` objects.
- `PersonaRuntime` compiles active personas into a weighted system prompt.
- **Default Mode:** `.infinite` drives the tone; `.omnia` drives scheduling and system-level decisions.

#### 2.5.2 Skill Forge
A closed-loop factory for skill creation.

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│  Detector   │───→│  Generator   │───→│   Vetter    │───→│   Installer  │
│ (pattern    │    │ (SKILL.md    │    │ (security   │    │ (move to     │
│  scanner)   │    │  draft)      │    │  + quality) │    │  skills/)    │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
```

- **Detector:** Scans last N days of memory for repeated task patterns using lightweight clustering.
- **Generator:** Converts a detected pattern into a structured `SKILL.md` draft.
- **Vetter:** Blocks skills that try to overwrite existing ones, access secrets, or contain suspicious shell patterns.
- **Installer:** Moves approved skills into the canonical `skills/` tree.

**Frequency:** Batch job. Runs once per day at 03:00 (low-cost hours), not after every query.

---

## 3. Data Flow: A Single Request

```
1. User sends message via Shell (L5)
2. Neuro-Center (L4) routes to active session
3. ULTRAPLAN (L3) classifies intent + selects memory + skills
4. Memory Palace (L3) loads only relevant subsets
5. Persona Runtime (L1) compiles system prompt
6. Token Budget Accountant (L3) trims if over limit
7. LLM generates response + optional tool calls
8. Actuator (L2) executes tools; outputs go through Context Compressor
9. SubAgent Orchestrator (L4) handles any parallel branches
10. Final response returned to Shell
11. Session ends; Persona Daemon (L4) decides if a memory-extraction job is queued
```

---

## 4. Cost & Safety Guardrails

| Guardrail | Implementation |
|-----------|----------------|
| **No surprise bills** | Token Budget Accountant enforces hard limits; ULTRAPLAN downgrades to cheaper models for routine tasks |
| **No rogue automation** | Persona Daemon only escalates above threshold; all high-risk actions (deploy, email, tweet) require user confirmation |
| **No skill explosion** | Skill Forge deduplicates before generation; dormant skills are suppressed |
| **No vendor lock-in** | Memory Palace is SQLite; Persona seeds are markdown; all critical data is plain text |

---

## 5. From Architecture to Code

| Phase | Focus | Deliverable |
|-------|-------|-------------|
| **Phase 0** | Seeds + Docs | `seeds/`, `docs/ARCHITECTURE.md`, `docs/INTERACTION_DESIGN.md` |
| **Phase 1** | Memory + Persona Runtime | `memory_palace/`, `personas/`, `test_*.py` |
| **Phase 2** | Skill Forge v0.1 | `skill_forge/detector.py`, `generator.py`, `vetter.py` |
| **Phase 3** | Neuro-Center | `omnia-daemon`, heartbeat scheduler, session router |
| **Phase 4** | Shell Expansion | IDE bridge, voice layer, mobile spotlight |

---

*Architecture is frozen. No more GitHub research. Implementation begins now.*

Built by 原点 and Infinite. ♾️
