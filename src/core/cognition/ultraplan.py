"""ULTRAPLAN — Intent Router + Memory Selector + Skill Ranker

A lightweight, deterministic planner for Omnia.
V0.1 uses keyword scoring instead of LLM calls to keep latency and cost low.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class PlanResult:
    """The output of ULTRAPLAN for a single user message."""

    intent: str
    confidence: float
    memory_layers: List[str]
    memory_queries: List[str]
    relevant_skills: List[Tuple[str, float]]
    plan_type: str


@dataclass
class _IntentProfile:
    intent_id: str
    keywords: List[str]
    memory_layers: List[str]
    base_queries: List[str]
    plan_type_default: str
    weight: float = 1.0


INTENT_PROFILES: List[_IntentProfile] = [
    _IntentProfile(
        intent_id="code_task",
        keywords=[
            "写", "修", "改", "部署", "bug", "报错", "代码", "脚本", "function",
            "创建", "生成脚本", "修复", "调试", "refactor", "deploy", "build",
            "error", "fix", "code", "script", "api", "backend", "frontend",
            "html", "css", "js", "vue", "react", "server", "database", "sql",
        ],
        memory_layers=["facts", "timeline", "relations"],
        base_queries=["project", "preference"],
        plan_type_default="multi_step",
    ),
    _IntentProfile(
        intent_id="memory_query",
        keywords=[
            "记得", "之前", "上次", "说过", "查一下", "回忆", "想起",
            "我们之前", "以前", "那时候", "remember", "previously", "last time",
            "did we", "what did", "告诉我关于",
        ],
        memory_layers=["facts", "timeline", "habits"],
        base_queries=["person", "preference"],
        plan_type_default="single_turn",
    ),
    _IntentProfile(
        intent_id="creative_work",
        keywords=[
            "设计", "生成", "写文案", "课件", "内容", "theme", "style",
            "配色", "排版", "海报", "presentation", "slide", "copywriting",
            "creative", "design", "content", "文案", "文章", "小红书", "知乎", "抖音",
            "seo", "social", "landing page", "website",
        ],
        memory_layers=["facts", "timeline", "habits"],
        base_queries=["preference", "project"],
        plan_type_default="multi_step",
    ),
    _IntentProfile(
        intent_id="system_status",
        keywords=[
            "状态", "健康", "检查了没", "日志", "跑了没", "Status",
            "pipeline", "cron", "backup", "deploy status", "health",
            "error log", "正常吗", "怎么样", "结果",
        ],
        memory_layers=["timeline", "facts"],
        base_queries=["project"],
        plan_type_default="single_turn",
    ),
    _IntentProfile(
        intent_id="casual_chat",
        keywords=[
            "好吗", "怎么样", "吃了吗", "晚安", "早安", "谢谢", "哈哈", "你好",
            "morning", "night", "thanks", "hi", "hello", "ok", "好的", "行",
            "睡", "累", "休息", "加油",
        ],
        memory_layers=["habits", "facts"],
        base_queries=["person"],
        plan_type_default="single_turn",
    ),
]


MULTI_STEP_HINTS = [
    "然后", "接着", "再", "顺便", "还有", "以及", "和", "并",
    "first", "then", "next", "after that", "also", "and", "plus",
]

SUBAGENT_HINTS = [
    "批量", "全部", "所有", "每一个", "批量处理", "并行",
    "batch", "all files", "every", "parallel", "concurrent",
]


@dataclass
class _SkillIndex:
    skill_id: str
    skill_path: Path
    triggers: List[str]
    capabilities: List[str]


class UltraPlan:
    """Deterministic intent router for Omnia."""

    def __init__(
        self,
        skills_dir: str | Path = "skills",
        auto_forge_dir: str | Path = "omnia-os/skills/auto-forge",
    ):
        self.skills_dir = Path(skills_dir)
        self.auto_forge_dir = Path(auto_forge_dir)
        self._skill_index: List[_SkillIndex] = []
        self._build_skill_index()

    def _build_skill_index(self) -> None:
        """Parse all installed SKILL.md files into a searchable index."""
        candidates: List[Path] = []
        if self.skills_dir.exists():
            candidates += [
                p / "SKILL.md"
                for p in self.skills_dir.iterdir()
                if p.is_dir() and (p / "SKILL.md").exists()
            ]
        if self.auto_forge_dir.exists():
            candidates += [
                p / "SKILL.md"
                for p in self.auto_forge_dir.iterdir()
                if p.is_dir() and (p / "SKILL.md").exists()
            ]

        for skill_md in candidates:
            text = skill_md.read_text(encoding="utf-8").lower()
            triggers = self._extract_section(text, "when to activate")
            capabilities = self._extract_section(text, "capabilities")
            self._skill_index.append(
                _SkillIndex(
                    skill_id=skill_md.parent.name,
                    skill_path=skill_md,
                    triggers=triggers,
                    capabilities=capabilities,
                )
            )

    @staticmethod
    def _extract_section(text: str, header: str) -> List[str]:
        """Extract bullet lines under a markdown header."""
        pattern = rf"## {re.escape(header)}\n+(.*?)(?=\n## |\Z)"
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            return []
        section = match.group(1).strip()
        return [line.strip()[2:] for line in section.splitlines() if line.strip().startswith("-")]

    @staticmethod
    def _score_keywords(message: str, keywords: List[str]) -> float:
        """Simple keyword overlap scorer."""
        lower = message.lower()
        hits = sum(1 for kw in keywords if kw.lower() in lower)
        # Boost for exact multi-character Chinese hits to reduce noise
        boost = sum(1.5 for kw in keywords if len(kw) >= 4 and kw.lower() in lower)
        return hits + boost

    def classify(self, message: str) -> Tuple[str, float]:
        """Return the best matching intent and confidence score."""
        scores: List[Tuple[str, float]] = []
        for profile in INTENT_PROFILES:
            raw_score = self._score_keywords(message, profile.keywords)
            # Normalize by keyword list length to keep scores comparable-ish
            normalized = raw_score / max(1, len(profile.keywords) * 0.2)
            scores.append((profile.intent_id, normalized))

        scores.sort(key=lambda x: x[1], reverse=True)
        
        # 边界检查：如果 scores 为空，返回默认值
        if not scores:
            return "general_task", 0.2
        
        best_intent, best_score = scores[0]

        # Softmax-like confidence clamping
        confidence = min(0.99, best_score / (best_score + 0.5))
        if confidence < 0.10:
            # Fallback if nothing matches strongly
            best_intent = "general_task"
            confidence = 0.2

        return best_intent, confidence

    def select_skills(self, message: str, top_n: int = 3) -> List[Tuple[str, float]]:
        """Rank skills by keyword overlap with triggers and capabilities."""
        lower = message.lower()
        scores: Dict[str, float] = {}
        for skill in self._skill_index:
            text = " ".join(skill.triggers + skill.capabilities)
            score = sum(1 for kw in lower.split() if kw in text)
            # Action verb bonus
            score += sum(1 for verb in [
                "写", "修", "改", "生成", "部署", "设计", "创建", "fix", "build", "generate", "deploy"
            ] if verb in text and verb in lower)
            # Entity-to-skill name bonus (e.g. "喵修匠" → miaoxiujiang_dev)
            skill_aliases = {
                "miaoxiujiang_dev": ["喵修", "喵修匠", "miaoxiujiang", "维修", "工单", "workbench"],
                "content_generation": ["文案", "内容", "小红书", "知乎", "抖音", "seo", "social", "content"],
                "deployment_devops": ["部署", "cron", "自动化", "pipeline", "edgeone", "devops", "deploy"],
            }
            for alias in skill_aliases.get(skill.skill_id, []):
                if alias in lower:
                    score += 3.0
            if score > 0:
                scores[skill.skill_id] = score

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_n]

    def _derive_plan_type(self, message: str, intent_id: str) -> str:
        """Decide if this is a single turn, multi-step, or subagent task."""
        lower = message.lower()
        if any(h in lower for h in SUBAGENT_HINTS):
            return "requires_subagent"
        if any(h in lower for h in MULTI_STEP_HINTS):
            return "multi_step"
        profile = next((p for p in INTENT_PROFILES if p.intent_id == intent_id), None)
        if profile:
            return profile.plan_type_default
        return "single_turn"

    def plan(self, message: str) -> PlanResult:
        """Full ULTRAPLAN pipeline."""
        intent, confidence = self.classify(message)
        skills = self.select_skills(message, top_n=3)
        plan_type = self._derive_plan_type(message, intent)

        profile = next((p for p in INTENT_PROFILES if p.intent_id == intent),
                       _IntentProfile("general_task", [], ["facts", "timeline"], [""], "single_turn"))

        # Derive targeted memory queries from message entities + profile base queries
        queries = list(profile.base_queries)
        # Simple entity extraction: capitalize phrases or known project names
        known_projects = ["喵修匠", "miaoxiujiang", "njuosun", "omnia", "懂机帝", "dongjidi"]
        for proj in known_projects:
            if proj.lower() in message.lower():
                queries.append(proj)

        return PlanResult(
            intent=intent,
            confidence=confidence,
            memory_layers=profile.memory_layers,
            memory_queries=list(set(queries)),
            relevant_skills=skills,
            plan_type=plan_type,
        )


if __name__ == "__main__":

    up = UltraPlan()
    samples = [
        "帮我修一下喵修匠 workbench 的 API 调用",
        "我们之前说好的 white theme 方案是什么来着？",
        "生成一个适合抖音的文案",
        "今天早上 cron 跑了吗？",
        "早安",
        "把所有课件批量转换成 CutCut 风格",
    ]
    for s in samples:
        plan = up.plan(s)
        print(f"\nInput: {s}")
        print(f"  intent={plan.intent} ({plan.confidence:.2f})")
        print(f"  plan_type={plan.plan_type}")
        print(f"  memory={plan.memory_layers} | queries={plan.memory_queries}")
        print(f"  skills={[id for id, _ in plan.relevant_skills]}")
