"""Skill Forge — Pattern Detector

Scans memory markdown files AND MemoryPalace SQLite for repeated task patterns.
Uses lightweight keyword bucketing instead of heavy NLP.

v0.2: 增强版 — 读取 MemoryPalace 关系记忆 + NeuralGraph 图谱
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

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
    """Lightweight pattern scanner for memory markdown files + MemoryPalace SQLite."""

    def __init__(
        self,
        memory_dir: str | Path = "memory",
        lookback_days: int = 14,
        min_evidence: int = 3,
        memory_db: Optional[str] = None,  # MemoryPalace SQLite path
    ):
        self.memory_dir = Path(memory_dir)
        self.lookback_days = lookback_days
        self.min_evidence = min_evidence
        self.cutoff = datetime.now() - timedelta(days=lookback_days)
        self.memory_db = memory_db

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
        """Scan memory markdown files AND MemoryPalace SQLite for patterns."""
        # 1. 扫描 markdown 文件（原有逻辑）
        files = self._list_files()
        bucket_evidence: Dict[str, List[str]] = defaultdict(list)

        for md in files:
            text = md.read_text(encoding="utf-8")
            for line in self._extract_action_lines(text):
                bucket_id = self._classify_line(line)
                if bucket_id:
                    bucket_evidence[bucket_id].append(line)

        # 2. 扫描 MemoryPalace SQLite（新增）
        self._scan_memory_palace(bucket_evidence)

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

    # ─── MemoryPalace 增强 ─────────────────────────────────────────

    def _scan_memory_palace(self, bucket_evidence: Dict[str, List[str]]):
        """从 MemoryPalace SQLite 中提取行为模式证据。

        读取 facts + relations + conversation_logs 表，提取用户的行为模式。
        """
        db_path = self._find_memory_db()
        if not db_path:
            logger.debug("[PatternDetector] MemoryPalace DB not found, skipping")
            return

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # 检查有哪些表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

            # 1. 从 facts 表提取（key/value 结构）
            if "facts" in tables:
                cutoff_iso = self.cutoff.isoformat()
                cursor.execute(
                    """
                    SELECT key, value, category, created_at
                    FROM facts
                    WHERE created_at >= ?
                    ORDER BY created_at DESC
                    LIMIT 200
                    """,
                    (cutoff_iso,),
                )

                rows = cursor.fetchall()
                for key, value, category, created_at in rows:
                    if not value:
                        continue

                    # 从 value 中提取行动线索
                    for line in value.split("\n"):
                        line = line.strip()
                        if not line:
                            continue

                        # 清理 markdown 标记
                        line = re.sub(r"^[-*#\s]+", "", line).strip()

                        # 检查是否匹配已知模式
                        bucket_id = self._classify_line(line)
                        if bucket_id:
                            bucket_evidence[bucket_id].append(
                                f"[MemoryPalace:facts:{category}] {line}"
                            )

                    # 也检查 key
                    bucket_id = self._classify_line(key)
                    if bucket_id:
                        bucket_evidence[bucket_id].append(
                            f"[MemoryPalace:facts:key] {key}"
                        )

                logger.info(f"[PatternDetector] Scanned {len(rows)} facts entries")

            # 2. 从 relations 表提取（subject/predicate/object 结构）
            if "relations" in tables:
                cutoff_iso = self.cutoff.isoformat()
                cursor.execute(
                    """
                    SELECT subject, predicate, object, context, created_at
                    FROM relations
                    WHERE created_at >= ?
                    ORDER BY created_at DESC
                    LIMIT 200
                    """,
                    (cutoff_iso,),
                )

                rows = cursor.fetchall()
                for subject, predicate, obj, context, created_at in rows:
                    # 从 subject + predicate + object 中提取行动线索
                    relation_text = f"{subject} {predicate} {obj}"
                    bucket_id = self._classify_line(relation_text)
                    if bucket_id:
                        bucket_evidence[bucket_id].append(
                            f"[MemoryPalace:relation] {relation_text}"
                        )

                    # 也检查 context
                    if context:
                        bucket_id = self._classify_line(context)
                        if bucket_id:
                            bucket_evidence[bucket_id].append(
                                f"[MemoryPalace:relation:context] {context}"
                            )

                logger.info(f"[PatternDetector] Scanned {len(rows)} relations entries")

            # 3. 从 conversation_logs 表提取
            if "conversation_logs" in tables:
                cutoff_iso = self.cutoff.isoformat()
                cursor.execute(
                    """
                    SELECT content, metadata, created_at
                    FROM conversation_logs
                    WHERE created_at >= ?
                    ORDER BY created_at DESC
                    LIMIT 300
                    """,
                    (cutoff_iso,),
                )

                rows = cursor.fetchall()
                for content, metadata_json, created_at in rows:
                    if not content:
                        continue

                    # 尝试解析 JSON
                    try:
                        meta = json.loads(metadata_json) if metadata_json else {}
                    except (json.JSONDecodeError, TypeError):
                        meta = {}

                    # 从 content 中提取行动线索
                    for line in content.split("\n"):
                        line = line.strip()
                        if not line:
                            continue

                        line = re.sub(r"^[-*#\s]+", "", line).strip()
                        bucket_id = self._classify_line(line)
                        if bucket_id:
                            bucket_evidence[bucket_id].append(
                                f"[MemoryPalace:conv] {line}"
                            )

                    # 从 metadata 中提取工具调用模式
                    tool_calls = meta.get("tool_calls", [])
                    if isinstance(tool_calls, list):
                        for tc in tool_calls:
                            if isinstance(tc, dict):
                                tool_name = tc.get("name", "")
                                if tool_name:
                                    bucket_id = self._classify_line(tool_name)
                                    if bucket_id:
                                        bucket_evidence[bucket_id].append(
                                            f"[ToolCall] {tool_name}"
                                        )

                logger.info(f"[PatternDetector] Scanned {len(rows)} conversation_logs entries")

            conn.close()

        except Exception as e:
            logger.warning(f"[PatternDetector] MemoryPalace scan failed: {e}")

    def _find_memory_db(self) -> Optional[Path]:
        """查找 MemoryPalace SQLite 数据库文件"""
        if self.memory_db:
            return Path(self.memory_db)

        # 按优先级查找：生产数据库 > 项目数据库 > 旧数据库
        candidates = [
            # 生产数据库（最高优先级）
            Path.home() / ".omnia" / "memory_palace.db",
            # 项目数据库
            Path("data/memory_palace.db"),
            Path("memory.db"),
            Path(".omnia/memory.db"),
            # 旧数据库
            Path.home() / ".openclaw" / "workspace" / "omnia-os" / ".omnia" / "memory.db",
            Path.home() / ".openclaw" / "workspace" / "omnia-os" / "memory.db",
            Path.home() / ".openclaw" / "workspace" / "omnia-os" / "data" / "memory_palace.db",
        ]

        for candidate in candidates:
            if candidate.exists():
                logger.info(f"[PatternDetector] Found memory DB: {candidate}")
                return candidate

        return None


if __name__ == "__main__":

    # Quick smoke test when run directly
    pd = PatternDetector()
    patterns = pd.detect()
    print(f"Scanned {len(pd._list_files())} memory files.")
    print(f"Detected {len(patterns)} pattern(s).")
    for p in patterns:
        print(f"\n[{p.pattern_id}] {p.pattern_name} — freq={p.frequency}, conf={p.confidence:.2f}")
        for e in p.evidence[:5]:
            print(f"  • {e}")
