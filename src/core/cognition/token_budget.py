"""Token Budget Accountant — Hard ceilings for Omnia's prompt economy.

Tracks token burn and enforces eviction policies to keep system prompt
and total request under configurable limits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .context_compressor import ContextCompressor, estimate_tokens


@dataclass
class BudgetReport:
    system_tokens: int
    session_tokens: int
    limit_system: int
    limit_session: int
    evicted: List[str]
    status: str   # ok | warning | exceeded


@dataclass
class PromptComponent:
    name: str
    text: str
    priority: int   # higher = more important, evicted last


class TokenBudget:
    """Running ledger and enforcer for prompt token limits."""

    def __init__(
        self,
        system_limit: int = 4096,
        session_limit: int = 20000,
        compressor: Optional[ContextCompressor] = None,
    ):
        self.system_limit = system_limit
        self.session_limit = session_limit
        self.compressor = compressor or ContextCompressor()

    def _tokens(self, text: str) -> int:
        return estimate_tokens(text)

    def enforce_system_prompt(
        self,
        components: List[PromptComponent],
    ) -> str:
        """Sort by priority descending, evict lowest-priority items if over budget."""
        sorted_components = sorted(components, key=lambda c: c.priority, reverse=True)
        kept: List[PromptComponent] = []
        evicted: List[str] = []
        total = 0

        for comp in sorted_components:
            cost = self._tokens(comp.text)
            if total + cost <= self.system_limit:
                kept.append(comp)
                total += cost
            else:
                evicted.append(comp.name)

        kept.sort(key=lambda c: c.priority, reverse=True)
        return "\n\n".join(c.text for c in kept), evicted, total

    def check_session(self, system_text: str, history_text: str = "") -> BudgetReport:
        """Estimate total request size and flag if near or over limit."""
        system_toks = self._tokens(system_text)
        history_toks = self._tokens(history_text)
        total = system_toks + history_toks

        if total > self.session_limit:
            status = "exceeded"
        elif total > self.session_limit * 0.85:
            status = "warning"
        else:
            status = "ok"

        return BudgetReport(
            system_tokens=system_toks,
            session_tokens=total,
            limit_system=self.system_limit,
            limit_session=self.session_limit,
            evicted=[],
            status=status,
        )

    def compress_tool_output(self, text: str, label: str = "tool_output") -> str:
        """Convenience wrapper: always return a string summary."""
        return self.compressor.compress(text, label=label).summary
