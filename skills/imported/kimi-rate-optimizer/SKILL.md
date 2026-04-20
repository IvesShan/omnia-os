---
name: kimi-rate-optimizer
description: Optimize task execution for Kimi Coding model with RPM (requests per minute) rate limiting. Use when the user is experiencing API rate limit errors, wants to maximize throughput for course development or complex tasks, or needs strategies to reduce request count while maximizing token utilization per request.
---

# Kimi Coding Rate Optimizer

Kimi Coding has **RPM (requests per minute) limiting**, not TPM (tokens per minute) limiting. This means:
- ✅ You can send large payloads in one request
- ❌ You cannot make many small requests rapidly

## Core Strategy: Minimize Requests, Maximize Tokens per Request

## 1. Task Batching Patterns

### Single Message Multi-Step
Instead of:
```
User: "Write intro"
User: "Write body"
User: "Write conclusion"
```

Do:
```
User: "Write a complete article with:
1. Intro (100 words)
2. Body with 3 sections (300 words each)
3. Conclusion (100 words)"
```

### Course Development Batching
For course content, structure requests as:
```
"Create Module X with:
- Learning objectives (bullet list)
- Content outline (numbered)
- 3 practical exercises
- Knowledge check questions
- Required equipment list"
```

## 2. Thinking Mode Optimization

Use appropriate thinking depth to balance quality and speed:

| Task Type | Command | Use When |
|-----------|---------|----------|
| Simple/repetitive | `/thinking off` | File ops, shell commands, formatting |
| Standard work | `/thinking low` (default) | Most coding, writing, analysis |
| Complex problems | `/thinking high` | Architecture design, debugging, complex logic |

**Rule of thumb**: Start with `low`, escalate only when needed.

## 3. Local Execution Priority

**Never ask the model for:**
- File reading/writing/editing
- Shell command execution
- Directory listing
- Git operations
- Simple text transformations

**Do these directly**, then only ask the model for analysis/decisions based on results.

## 4. Complete Context in One Go

Bad pattern:
```
"Here's part 1 of the requirements..."
[wait]
"Also need part 2..."
[wait]
"One more thing..."
```

Good pattern:
```
"Complete requirements:
- Req A: ...
- Req B: ...
- Req C: ...
- Constraint X: ...
- Output format: ..."
```

## 5. Sub-Agent Strategy (Use Sparingly)

**Default: Single Agent Direct Processing**

For most coding/course development tasks, **single agent is superior**:
- ✅ Maintains architectural coherence
- ✅ Consistent style and patterns
- ✅ Lower token overhead (no context duplication)
- ✅ No spawn/wait coordination costs

**When to Use Sub-Agents:**
- Parallel research tasks (independent topics)
- Multi-angle code review (different reviewers)
- Truly independent module generation (no dependencies)

**When NOT to Use:**
- Architecture design (needs global view)
- Core module development (needs consistency)
- Complex debugging (needs cross-module tracking)
- Simple sequential tasks (overhead > benefit)

See [references/subagent-patterns.md](references/subagent-patterns.md) for specific patterns

## Quick Reference: Course Development Optimization

| Scenario | Optimization Strategy |
|----------|----------------------|
| **Architecture/Design** | Single agent, `/thinking high`, complete spec in one request |
| **Content Generation** | Batch: Generate 3-5 sections in one request using templates |
| **Multi-module Creation** | Single agent with structured template, not parallel agents |
| **Code Review** | Optional: Spawn 2-3 agents for different review angles |
| **Research + Coding** | Parallel: Agent 1 researches while Agent 2 codes base structure |
| **Independent Units** | Parallel: Generate unrelated lessons simultaneously |

## Batch vs Parallel Decision Tree

```
Are the tasks independent?
├── NO (dependencies exist)
│   └── Use SINGLE AGENT with batching
│       → Better coherence
│       → Lower token cost
│       → Faster coordination
│
└── YES (truly independent)
    └── Are there 3+ tasks?
        ├── NO (1-2 tasks)
        │   └── Use SINGLE AGENT sequentially
        │       → Spawn overhead not worth it
        │
        └── YES (3+ tasks)
            └── Use SUB-AGENTS in parallel
                → Better RPM utilization
                → True time savings
```

## Emergency Rate Limit Recovery

If you hit rate limit:
1. Wait 60 seconds (typical reset window)
2. Combine pending requests into one message
3. Use `/thinking low` or `off` for faster response
4. Consider spawning sub-agent if task is parallelizable

## See Also

- [Course Development Templates](references/course-templates.md) - Pre-structured batch formats
- [Sub-Agent Patterns](references/subagent-patterns.md) - When and how to parallelize