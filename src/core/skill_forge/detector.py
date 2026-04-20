"""Skill Forge — Pattern Detector

Scans memory markdown files for repeated task patterns.
Uses lightweight keyword bucketing instead of heavy NLP.
"""

from __future__ import annotations

import glob
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple


ACTION_VERBS = [
    "创建了", "修复了", "部署了", "更新了", "生成了", "转换了",
    "自动", "脚本", "pipeline", "重构了", "改写了", "添加了",
    "实现了", "完成了", "设计了", "优化了", "调整了", "统一了",
]

BUCKETS: List[Tuple[str, str, List[str]]] = [
    (
        "frontend-page-dev",
        "前端页面开发（HTML/CSS/JS）",
        ["html", "css", "js", "frontend", "页面", "网站", "theme", "dark", "light", "svg", "responsive", "课件"],
    ),
    (
        "deployment-devops",
        "部署与运维自动化",
        ["deploy", "部署", "pipeline", "cron", "edgeone", "vercel", "server", "backend", "api", "cli", "systemd"],
    ),
    (
        "data-processing",
        "数据导入与处理",
        ["import", "export", "csv", "xlsx", "数据", "parse", "extract", "sqlite", "json", "格式化"],
    ),
    (
        "content-generation",
        "内容与文案生成",
        ["生成", "content", "copy", "script", "文案", "article", "知乎", "小红书", "抖音", "seo", "social"],
    ),
    (
        "courseware-design",
        "课件与演示设计",
        ["课件", "courseware", "slide", "presentation", "keynote", "ppt", "讲义", "课程"],
    ),
    (
        "miaoxiujiang-dev",
        "喵修匠系统开发",
        ["喵修", "miaoxiujiang", "workbench", "维修", "order", "工单", "商户", "merchant", "发货", "报价"],
    ),
    (
        "system-fix",
        "系统修复与调试",
        ["fix", "修复", "debug", "bug", "error", "broken", "failed", "报错", "解决", "排查", "调整"],
    ),
]


@dataclass
class DetectedPattern:
    pattern_id: str
    pattern_name: str
    category: str  # actuator | cognition | shell | soul
    frequency: int
    confidence: float
    evidence: List[str] = field(default_factory=list)
    suggested_skill_name: str = ""


class PatternDetector:
    """Lightweight pattern scanner for memory markdown files."""

    def __init__(
        self,
        memory_dir: str | Path = "memory",
        lookback_days: int = 14,
        min_evidence: int = 3,
    ):
        self.memory_dir = Path(memory_dir)
        self.lookback_days = lookback_days
        self.min_evidence = min_evidence
        self.cutoff = datetime.now() - timedelta(days=lookback_days)

    def _list_files(self) -> List[Path]:
        """List memory markdown files within the lookback window."""
        files: List[Path] = []
        for md in sorted(self.memory_dir.glob("*.md")):
            # Try to parse date from filename: YYYY-MM-DD.md
            try:
                file_date = datetime.strptime(md.stem, "%Y-%m-%d")
            except ValueError:
                continue
            if file_date >= self.cutoff:
                files.append(md)
        return files

    def _extract_action_lines(self, text: str) -> List[str]:
        """Pull out lines that look like task descriptions."""
        lines: List[str] = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            # Markdown list items or headers
            if line.startswith(("- ", "* ", "### ", "## ")):
                line = re.sub(r"^[-*#\s]+", "", line).strip()
            # Must contain an action verb or strong task indicator
            if any(v in line for v in ACTION_VERBS):
                # Normalize whitespace
                line = re.sub(r"\s+", " ", line)
                lines.append(line)
        return lines

    def _classify_line(self, line: str) -> str | None:
        """Return bucket id if the line matches a known pattern."""
        lower = line.lower()
        for bucket_id, _name, keywords in BUCKETS:
            score = sum(1 for kw in keywords if kw in lower)
            if score >= 1:
                return bucket_id
        return None

    def detect(self) -> List[DetectedPattern]:
        """Scan memory and return patterns with sufficient evidence."""
        files = self._list_files()
        bucket_evidence: Dict[str, List[str]] = defaultdict(list)

        for md in files:
            text = md.read_text(encoding="utf-8")
            for line in self._extract_action_lines(text):
                bucket_id = self._classify_line(line)
                if bucket_id:
                    bucket_evidence[bucket_id].append(line)

        results: List[DetectedPattern] = []
        for bucket_id, bucket_name, keywords in BUCKETS:
            evidence = bucket_evidence.get(bucket_id, [])
            if len(evidence) < self.min_evidence:
                continue

            # Deduplicate near-identical lines
            unique_evidence = []
            seen = set()
            for e in evidence:
                normalized = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", e)
                if normalized not in seen:
                    seen.add(normalized)
                    unique_evidence.append(e)

            frequency = len(unique_evidence)
            confidence = min(0.95, 0.5 + (frequency * 0.05))
            skill_name = bucket_id.replace("-", "_")

            results.append(
                DetectedPattern(
                    pattern_id=f"auto-forge-{bucket_id}",
                    pattern_name=bucket_name,
                    category="actuator",
                    frequency=frequency,
                    confidence=confidence,
                    evidence=unique_evidence[:10],  # keep top 10
                    suggested_skill_name=skill_name,
                )
            )

        return results

    def detect_json(self) -> str:
        """Return detections as a JSON string."""
        patterns = self.detect()
        return json.dumps(
            [p.__dict__ for p in patterns],
            ensure_ascii=False,
            indent=2,
        )


if __name__ == "__main__":
    import sys

    # Quick smoke test when run directly
    pd = PatternDetector()
    patterns = pd.detect()
    print(f"Scanned {len(pd._list_files())} memory files.")
    print(f"Detected {len(patterns)} pattern(s).")
    for p in patterns:
        print(f"\n[{p.pattern_id}] {p.pattern_name} — freq={p.frequency}, conf={p.confidence:.2f}")
        for e in p.evidence[:5]:
            print(f"  • {e}")
