"""AgentSwarm — Omnia's parallel task execution layer.
from core.config import MEMORY_PALACE_DB

A single high-level goal is decomposed into 1-3 parallel subtasks,
each executed by a specialized subagent using concurrent workers.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .plan_executor import PlanExecutor
from .tool_registry import check_tool_safety
from ..memory_palace.memory_palace import MemoryPalace
from omnia.chat import _call_model_messages


@dataclass
class SubTask:
    role: str  # frontend | backend | devops | research | general
    goal: str
    context: str = ""


@dataclass
class SubAgentResult:
    role: str
    goal: str
    status: str  # running | done | error
    reply: str = ""
    steps: List[Dict[str, Any]] = None
    error: str = ""

    def __post_init__(self):
        if self.steps is None:
            self.steps = []


class SubAgent:
    """Lightweight specialist running PlanExecutor with a role-tuned system context."""

    ROLE_PROMPTS = {
        "frontend": (
            "You are FrontendAgent, a UI/UX specialist. You read and write HTML, CSS, JavaScript, and SVG. "
            "CRITICAL: every file path in your plan must be a REAL, LITERAL path. NEVER use placeholders like <path> or <css_file_path>. "
            "You prefer clean, modern design and validate syntax after edits. When planning, use read_file to inspect current code, "
            "then write_file to apply changes. Be concise and avoid unnecessary steps."
        ),
        "backend": (
            "You are BackendAgent, a Python/Flask/API specialist. You read and write Python, design JSON APIs, and validate logic. "
            "CRITICAL: every file path in your plan must be a REAL, LITERAL path. NEVER use placeholders like <path>. "
            "When planning, inspect files first, then use write_file for code and execute_shell to run quick checks (type hints, import smoke tests). "
            "Be concise."
        ),
        "devops": (
            "You are DevOpsAgent, a deployment and automation specialist. You use shell commands, git, systemd, and rsync. "
            "CRITICAL: for systemd you MUST use `systemctl --user` (never sudo). You validate before running destructive operations "
            "and always report the exact command you ran and its exit code."
        ),
        "research": (
            "You are ResearchAgent, a web intelligence specialist. You use web_search to gather up-to-date facts and summarize them. "
            "Cite sources briefly and stay factual."
        ),
        "general": (
            "You are a general-purpose execution agent. You use available tools efficiently and report results clearly. "
            "CRITICAL: every file path must be a REAL, LITERAL path. NEVER use placeholders."
        ),
    }

    def __init__(self, api_key: str, provider: str = "kimi", role: str = "general"):
        self.api_key = api_key
        self.provider = provider
        self.role = role
        self.executor = PlanExecutor(api_key, provider)

    def run(self, goal: str) -> SubAgentResult:
        context = self.ROLE_PROMPTS.get(self.role, self.ROLE_PROMPTS["general"])
        result = SubAgentResult(role=self.role, goal=goal, status="running")
        try:
            # Pre-flight safety sweep for ALL planned steps before executing
            plan = self.executor.plan(goal, context)
            for step in plan.steps:
                safety = check_tool_safety(step.tool_name, step.tool_args)
                if safety.requires_confirm:
                    # In swarm mode we DENY destructive ops automatically and report
                    result.status = "blocked"
                    result.error = f"Blocked by safety gate: {safety.reason} on {step.tool_name}"
                    result.reply = f"该步骤因安全策略被拦截：{safety.reason}。你可以在主对话中单独授权此操作。"
                    return result

            out = self.executor.execute(plan)
            result.status = "done"
            result.reply = out.get("reply", "")
            result.steps = out.get("steps", [])
        except Exception as e:
            err = str(e)
            if "timed out" in err.lower() or "timeout" in err.lower():
                result.status = "error"
                result.error = err
                result.reply = f"[{self.role}] 规划阶段超时（API 响应慢）。你可以稍后重试，或在主对话中分步执行。"
            else:
                result.status = "error"
                result.error = err
                result.reply = f"[{self.role}] 执行出错: {e}"
        return result


class SwarmOrchestrator:
    """Breaks a goal into parallel subtasks, runs them, and synthesizes the result."""

    DECOMPOSE_PROMPT = """You are Omnia's SwarmOrchestrator. Given a high-level user goal, decide whether it should be split into parallel subtasks for specialized agents.

Available agent roles:
- frontend: HTML/CSS/JS/SVG UI changes
- backend: Python/Flask/API/database changes
- devops: shell/git/systemd/deployment
- research: web search and fact gathering
- general: anything that does not fit above or is already atomic

Rules:
1. If the goal is simple and single-domain, return exactly 1 task with the appropriate role.
2. If the goal naturally spans multiple domains (e.g. "change the UI theme and deploy"), split into 2-3 parallel tasks.
3. Each subtask should be self-contained and runnable in parallel without file-lock conflicts (if possible).
4. Output ONLY a JSON array inside ```json ... ``` like:

```json
[
  {{"role": "frontend", "goal": "Modify web/styles.css to change chat background to dark blue glass"}},
  {{"role": "backend", "goal": "Ensure /api/status route in web_server.py has no dependency on chat CSS"}},
  {{"role": "devops", "goal": "Restart omnia.service after the CSS change"}}
]
```

User goal: {goal}
"""

    SYNTHESIZE_PROMPT = """You are Omnia. You dispatched parallel agents to handle the user's request:

User goal: {goal}

Here are the results from each agent:

{results_text}

Synthesize a single, natural-language summary for the user. Celebrate wins, mention any errors or blockages clearly, and provide next steps if needed. Keep it concise but informative.
"""

    def __init__(self, api_key: str, provider: str = "kimi"):
        self.api_key = api_key
        self.provider = provider

    def decompose(self, goal: str) -> List[SubTask]:
        prompt = self.DECOMPOSE_PROMPT.format(goal=goal)
        data = _call_model_messages(
            self.api_key,
            self.provider,
            [{"role": "user", "content": prompt}],
        )
        text = data["choices"][0]["message"]["content"]
        raw = self._extract_json_block(text)
        if not raw:
            # Fallback: single general task
            return [SubTask(role="general", goal=goal)]
        try:
            arr = json.loads(raw)
            tasks = []
            for item in arr:
                if isinstance(item, dict):
                    tasks.append(SubTask(role=item.get("role", "general"), goal=item.get("goal", goal)))
            return tasks if tasks else [SubTask(role="general", goal=goal)]
        except (json.JSONDecodeError, TypeError):
            return [SubTask(role="general", goal=goal)]

    def run(self, goal: str, persist_to_memory: bool = True) -> Dict[str, Any]:
        tasks = self.decompose(goal)
        results: List[SubAgentResult] = []

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(SubAgent(self.api_key, self.provider, t.role).run, t.goal): t
                for t in tasks
            }
            for future in as_completed(futures):
                task = futures[future]
                try:
                    res = future.result()
                except Exception as e:
                    res = SubAgentResult(
                        role=task.role,
                        goal=task.goal,
                        status="error",
                        error=str(e),
                        reply=f"[{task.role}] 子代理崩溃: {e}",
                    )
                results.append(res)

        # Sort results to match task order (stable presentation)
        results.sort(key=lambda r: next((i for i, t in enumerate(tasks) if t.role == r.role and t.goal == r.goal), 999))

        outcome = self._synthesize(goal, results)
        if persist_to_memory:
            ingested = self._ingest_to_memory_palace(goal, results, outcome["reply"])
            outcome["memory_ingested"] = ingested
        return outcome

    def _synthesize(self, goal: str, results: List[SubAgentResult]) -> Dict[str, Any]:
        parts = []
        for r in results:
            parts.append(f"[{r.role.upper()}] {r.goal}\nStatus: {r.status}\nResult: {r.reply}\nError: {r.error}\n")
        results_text = "\n---\n".join(parts)
        prompt = self.SYNTHESIZE_PROMPT.format(goal=goal, results_text=results_text)
        try:
            data = _call_model_messages(self.api_key, self.provider, [{"role": "user", "content": prompt}])
            reply = data["choices"][0]["message"]["content"]
        except Exception as e:
            reply = f"并行任务已完成，但汇总时出错: {e}"

        return {
            "reply": reply,
            "swarm": True,
            "agents": [
                {
                    "role": r.role,
                    "goal": r.goal,
                    "status": r.status,
                    "reply": r.reply,
                    "steps": r.steps,
                }
                for r in results
            ],
        }

    def _ingest_to_memory_palace(self, goal: str, results: List[SubAgentResult], synthesis: str) -> int:
        """Persist successful swarm outcomes into Memory Palace. Returns count of items written."""
        from datetime import date
        try:
            db_path = str(MEMORY_PALACE_DB)
            mp = MemoryPalace(str(db_path))
            mp.initialize()

            # Only ingest if at least one agent actually succeeded
            any_done = any(r.status == "done" for r in results)
            any_successful_steps = any(
                s.get("status") == "done"
                for r in results if r.status == "done"
                for s in r.steps
            )
            if not any_done or not any_successful_steps:
                return 0

            count = 0
            # Timeline event for the swarm mission
            mp.record_event(
                event_date=date.today(),
                event_type="milestone",
                title=f"AgentSwarm 任务: {goal[:60]}",
                description=synthesis[:400],
                tags=["agentswarm", "auto_ingest"],
                session_key="swarm_auto_ingest",
            )
            count += 1

            for r in results:
                if r.status != "done":
                    continue
                # Facts from tool steps
                for s in r.steps:
                    if s.get("tool") in ("write_file", "execute_shell") and s.get("status") == "done":
                        args = s.get("arguments", {})
                        summary = s.get("result_summary", "")
                        if isinstance(args, dict) and (args.get("path") or args.get("command")):
                            mp.remember_fact(
                                category="agentswarm_action",
                                key=f"{r.role}:{args.get('path') or args.get('command', '')[:80]}",
                                value=f"Swarm task '{goal[:40]}' -> {summary[:200]}",
                                source="agentswarm_auto_ingest",
                                strength=0.85,
                            )
                            count += 1

                # Habit: if a role keeps succeeding, reinforce the pattern
                mp.observe_habit(
                    domain="agentswarm",
                    pattern=f"{r.role} 成功执行并行任务",
                    evidence=f"goal={r.goal[:80]}",
                    certainty=0.8,
                )
                count += 1

            return count
        except Exception:
            return 0

    @staticmethod
    def _extract_json_block(text: str) -> Optional[str]:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            return m.group(1).strip()
        start = text.find("[")
        if start != -1:
            end = text.rfind("]")
            if end != -1:
                return text[start : end + 1].strip()
        return None
