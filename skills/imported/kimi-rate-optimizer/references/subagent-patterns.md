# Sub-Agent Patterns for Rate Limit Optimization

**⚠️ WARNING: Default to Single Agent. Use Sub-Agents Only When Justified.**

For Kimi Coding with RPM limiting, **single agent direct processing is usually superior** for course development and coding tasks. Sub-agents add coordination overhead and context duplication costs.

## When NOT to Use Sub-Agents (Most Cases)

### ❌ Architecture Design
- Needs global system view
- Cross-module consistency required
- Single agent maintains coherent design vision

### ❌ Core Module Development
- Style and pattern consistency critical
- Dependencies between components
- Context switching loses nuance

### ❌ Complex Debugging
- Requires tracing across modules
- Needs holistic understanding of failure modes

### ❌ Simple Sequential Tasks
- Spawn overhead exceeds parallel savings
- Sequential is simpler and more reliable

## When to Use Sub-Agents (Specific Cases)

### ✅ Parallel Research
**Scenario**: Need to research 3+ independent topics simultaneously

**Example**:
```
Main agent: "Create drone safety module. Researching 3 topics in parallel..."

sessions_spawn --task "Research drone battery safety: common failures, repair techniques, safety standards. Return structured summary."
sessions_spawn --task "Research propeller safety: inspection, replacement, balancing. Return structured summary."
sessions_spawn --task "Research flight safety regulations: commercial vs hobbyist requirements. Return structured summary."

Main agent: Compile and synthesize all research into unified content
```

### ✅ Multi-Angle Review
**Scenario**: Need different perspectives on same content

**Example**:
```
Main agent: "Review this course module from 3 angles"

sessions_spawn --task "Technical Review: Check accuracy of drone repair procedures, safety warnings, tool specifications. Return findings."
sessions_spawn --task "Pedagogical Review: Check learning flow, clarity, exercise effectiveness. Return findings."
sessions_spawn --task "Editorial Review: Check grammar, formatting, consistency. Return findings."

Main agent: Consolidate all feedback into action items
```

### ✅ Truly Independent Content Generation
**Scenario**: Creating unrelated modules with no dependencies

**Example**:
```
"Generate 3 independent reference guides:"
- Agent 1: Tool maintenance guide
- Agent 2: Parts sourcing guide  
- Agent 3: Troubleshooting flowchart
```

## Cost-Benefit Analysis

| Approach | Token Cost | RPM Efficiency | Coherence | Setup Complexity |
|----------|-----------|----------------|-----------|------------------|
| Single Agent Batch | ⭐ Low | ⭐ High | ⭐ Excellent | ⭐ Simple |
| Sub-Agents Parallel | Higher (context × N) | High | Requires coordination | Complex |

**Rule of Thumb**:
- If tasks have **any dependency** → Single agent
- If tasks are **independent but < 3** → Single agent sequentially
- If tasks are **independent and ≥ 3** → Consider sub-agents

## Best Practices (When You Do Use Sub-Agents)

### Task Design
- Make tasks **self-contained** and **explicit**
- Include all necessary context in each task
- Specify output format clearly
- Set reasonable timeouts

### Coordination
- Use `sessions_yield` to wait for completion
- Check `subagents list` for status
- Have clear merge strategy for results

### Failure Handling
- Design for partial failure (some agents may fail)
- Have fallback: continue with partial results or retry

## Example: Hybrid Workflow for Course Development

```
STAGE 1: Architecture (Single Agent)
├── Create course structure
├── Define module dependencies
└── Set technical standards

STAGE 2: Content Generation (Single Agent with Batching)
├── Generate Module 1: sections A, B, C in one request
├── Generate Module 2: sections A, B, C in one request
└── Maintain consistency across modules

STAGE 3: Parallel Review (Sub-Agents)
├── Agent 1: Technical accuracy check
├── Agent 2: Pedagogical effectiveness check
└── Agent 3: Editorial/formatting check

STAGE 4: Integration (Single Agent)
├── Consolidate review feedback
├── Apply fixes consistently
└── Final polish
```

## Anti-Patterns to Avoid

### ❌ Over-Parallelization
Don't spawn agents for every small task. The overhead kills the benefit.

**Bad**:
```
Agent 1: Write intro
Agent 2: Write section 1
Agent 3: Write section 2
...
```

**Better**:
```
Single agent: Write intro + sections 1-3 in one request
```

### ❌ Implicit Dependencies
Don't assume sub-agents share context or know about each other's work.

**Bad**: Agent 2 assumes Agent 1's output exists and follows certain format.

**Better**: Explicitly pass necessary context or design truly independent tasks.

### ❌ Deep Hierarchies
Avoid: Main → Agent A → Agent A1, A2

This creates complex coordination and debugging challenges.

**Better**: Flat structure: Main → Agent A, Agent B, Agent C