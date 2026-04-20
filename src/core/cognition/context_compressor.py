"""Context Compressor — Shrinks oversized tool outputs before they bloat the prompt.

V0.1 uses rule-based extraction; future versions may call a lightweight local model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class CompressionResult:
    original_tokens: int   # estimated
    compressed_tokens: int # estimated
    summary: str
    preserved_evidence: List[str]
    method: str


def estimate_tokens(text: str) -> int:
    """Very rough token estimator: ~4 chars per token for CJK, ~4 for English too."""
    if not text:
        return 0
    return max(1, len(text) // 3)


def extract_key_lines(text: str, n: int = 5) -> List[str]:
    """Pull out lines that look like conclusions, errors, or important data."""
    keywords = ["error", "fail", "success", "result", "summary", "total", "found", "created", "deleted", "warning", "exception", "traceback"]
    scored = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        score = 0
        lower = line.lower()
        for kw in keywords:
            if kw in lower:
                score += 1
        # Boost lines that look like file paths, numbers, or structured data
        if re.search(r"\b\d+\b", line):
            score += 1
        if re.search(r"[\w/\-]+\.(py|js|md|html|css|json|xml|txt)", line):
            score += 1
        scored.append((score, line))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [line for _, line in scored[:n]]


class ContextCompressor:
    """Compresses text based on size thresholds."""

    def __init__(
        self,
        keep_full_threshold: int = 500,
        medium_threshold: int = 2000,
        local_compressor: Optional[Callable[[str], str]] = None,
    ):
        self.keep_full_threshold = keep_full_threshold
        self.medium_threshold = medium_threshold
        self.local_compressor = local_compressor

    def compress(self, text: str, label: str = "tool_output") -> CompressionResult:
        original = estimate_tokens(text)
        if original <= self.keep_full_threshold:
            return CompressionResult(
                original_tokens=original,
                compressed_tokens=original,
                summary=text,
                preserved_evidence=[],
                method="keep_full",
            )

        if original <= self.medium_threshold:
            evidence = extract_key_lines(text, n=5)
            summary = f"[{label}] {len(text.splitlines())} lines. Key findings:\n" + "\n".join(f"- {e}" for e in evidence)
            return CompressionResult(
                original_tokens=original,
                compressed_tokens=estimate_tokens(summary),
                summary=summary,
                preserved_evidence=evidence,
                method="extract_key_lines",
            )

        # Large output: try local compressor, else aggressive truncation
        if self.local_compressor:
            try:
                compressed = self.local_compressor(text)
                return CompressionResult(
                    original_tokens=original,
                    compressed_tokens=estimate_tokens(compressed),
                    summary=compressed,
                    preserved_evidence=[],
                    method="local_model",
                )
            except Exception:
                pass

        evidence = extract_key_lines(text, n=10)
        summary = (
            f"[{label}] Very large output ({original} est. tokens). "
            f"Aggressively compressed to top evidence lines:\n"
            + "\n".join(f"- {e}" for e in evidence)
        )
        return CompressionResult(
            original_tokens=original,
            compressed_tokens=estimate_tokens(summary),
            summary=summary,
            preserved_evidence=evidence,
            method="aggressive_evidence",
        )
