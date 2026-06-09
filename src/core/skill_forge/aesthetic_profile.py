"""Skill Forge — Aesthetic Profile

Omnia 的视觉品味档案系统。

灵感来源：
- 80x24/aesthetic-profile：通过 100 个问题构建视觉审美档案
- pbakaus/impeccable：设计语言 + 23 个命令 + 41 个检测规则

核心理念：
- 将隐性审美偏好显性化
- 将视觉品味编码为可执行的设计决策
- 与 MemoryPalace 集成，从对话历史中提取视觉偏好
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ─── 设计检测规则（Impeccable 风格） ─────────────────────────────

@dataclass
class DesignRule:
    """单个设计检测规则"""
    rule_id: str
    name: str
    category: str  # accessibility | performance | theming | responsive | anti_patterns
    description: str
    severity: str  # error | warning | info
    check_fn: Optional[str] = None  # 函数名（字符串）


# 41 个检测规则（简化版，聚焦最实用的）
DESIGN_RULES: List[DesignRule] = [
    # Accessibility
    DesignRule("wcag_contrast", "WCAG 对比度", "accessibility", "文字和背景的对比度是否符合 WCAG AA 标准", "error"),
    DesignRule("aria_labels", "ARIA 标签", "accessibility", "交互元素是否有合适的 ARIA 标签", "warning"),
    DesignRule("keyboard_nav", "键盘导航", "accessibility", "所有交互元素是否可通过键盘访问", "warning"),
    DesignRule("semantic_html", "语义化 HTML", "accessibility", "是否使用了正确的 HTML 语义标签", "info"),
    DesignRule("touch_targets", "触摸目标", "accessibility", "移动端触摸目标是否至少 44x44px", "warning"),

    # Performance
    DesignRule("layout_thrashing", "布局抖动", "performance", "是否有频繁的重排操作", "warning"),
    DesignRule("lazy_loading", "懒加载", "performance", "图片和组件是否使用了懒加载", "info"),
    DesignRule("bundle_size", "包大小", "performance", "前端资源包是否过大", "warning"),

    # Theming
    DesignRule("hard_coded_colors", "硬编码颜色", "theming", "是否直接使用了硬编码的颜色值", "warning"),
    DesignRule("dark_mode", "深色模式", "theming", "是否支持深色模式切换", "info"),
    DesignRule("token_consistency", "设计令牌一致性", "theming", "是否使用了统一的设计令牌（颜色、间距、圆角）", "info"),

    # Responsive
    DesignRule("breakpoint_behavior", "断点行为", "responsive", "关键断点下布局是否正确", "warning"),
    DesignRule("mobile_viewport", "移动视口", "responsive", "是否设置了正确的 viewport meta", "warning"),

    # Anti-patterns（AI slop 常见问题）
    DesignRule("overused_fonts", "滥用字体", "anti_patterns", "是否过度使用 Inter/Arial/system defaults", "warning"),
    DesignRule("gray_on_colored", "灰底彩色字", "anti_patterns", "是否在彩色背景上使用灰色文字", "warning"),
    DesignRule("pure_black_gray", "纯黑灰配色", "anti_patterns", "是否使用了过于生硬的纯黑+灰色组合", "info"),
    DesignRule("card_nesting", "卡片嵌套", "anti_patterns", "是否过度嵌套卡片组件", "warning"),
    DesignRule("bounce_easing", "弹跳缓动", "anti_patterns", "是否使用了不自然的弹跳缓动曲线", "info"),
]


# ─── Aesthetic Profile 数据结构 ─────────────────────────────────

@dataclass
class ColorPalette:
    """色彩偏好"""
    primary: str = "#3B82F6"
    secondary: str = "#10B981"
    accent: str = "#8B5CF6"
    background: str = "#FFFFFF"
    surface: str = "#F9FAFB"
    text_primary: str = "#111827"
    text_secondary: str = "#6B7280"
    success: str = "#10B981"
    warning: str = "#F59E0B"
    error: str = "#EF4444"
    banned_colors: List[str] = field(default_factory=lambda: ["#FF00FF", "#00FF00", "#FFFF00"])
    preferences: Dict[str, str] = field(default_factory=dict)  # 从对话中提取的偏好


@dataclass
class Typography:
    """字体偏好"""
    heading_font: str = "Inter, system-ui, sans-serif"
    body_font: str = "Inter, system-ui, sans-serif"
    mono_font: str = "JetBrains Mono, monospace"
    base_size: str = "16px"
    scale_ratio: float = 1.25  # Major Third
    line_height: float = 1.6
    preferences: Dict[str, str] = field(default_factory=dict)


@dataclass
class Composition:
    """构图与布局偏好"""
    grid_system: str = "12-column"
    spacing_unit: str = "8px"
    border_radius: str = "8px"
    max_width: str = "1200px"
    preferences: Dict[str, str] = field(default_factory=dict)


@dataclass
class MoodProfile:
    """情绪与氛围偏好"""
    primary_mood: str = "professional"  # professional | playful | minimal | bold | warm
    secondary_mood: str = "clean"
    avoided_moods: List[str] = field(default_factory=lambda: ["cluttered", "flashy"])
    preferences: Dict[str, str] = field(default_factory=dict)


@dataclass
class AntiAesthetic:
    """禁止清单（反审美）"""
    banned_elements: List[str] = field(default_factory=lambda: [
        "neon colors",
        "Comic Sans",
        "auto-playing videos",
        "excessive animations",
        "pop-up modals on load",
    ])
    banned_patterns: List[str] = field(default_factory=lambda: [
        "card-in-card-in-card nesting",
        "gray text on colored backgrounds",
        "pure black (#000000) on pure white (#FFFFFF)",
        "center-aligned long text",
        "justified text without hyphenation",
    ])


@dataclass
class AestheticProfile:
    """Omnia 的完整视觉品味档案"""

    # 基础信息
    profile_id: str = "omnia-default"
    profile_name: str = "Omnia Default Aesthetic"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # 五大维度
    colors: ColorPalette = field(default_factory=ColorPalette)
    typography: Typography = field(default_factory=Typography)
    composition: Composition = field(default_factory=Composition)
    mood: MoodProfile = field(default_factory=MoodProfile)
    anti_aesthetic: AntiAesthetic = field(default_factory=AntiAesthetic)

    # 文化参考
    references: List[str] = field(default_factory=lambda: [
        "Apple Keynote",
        "Stripe Dashboard",
        "Linear App",
        "Vercel Documentation",
    ])

    # 置信度（0-1，越高越确定）
    confidence: float = 0.3  # 默认低置信度，需要通过对话逐步提升

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "profile_id": self.profile_id,
            "profile_name": self.profile_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "colors": self.colors.__dict__,
            "typography": self.typography.__dict__,
            "composition": self.composition.__dict__,
            "mood": self.mood.__dict__,
            "anti_aesthetic": self.anti_aesthetic.__dict__,
            "references": self.references,
            "confidence": self.confidence,
        }

    def to_markdown(self) -> str:
        """导出为 Markdown 格式（类似 AESTHETICS.md）"""
        banned_colors = ", ".join(self.anti_aesthetic.banned_elements[:5])
        banned_patterns = "\n".join(f"- {p}" for p in self.anti_aesthetic.banned_patterns)
        refs = "\n".join(f"- {r}" for r in self.references)

        return f"""# Aesthetic Profile: {self.profile_name}

> Generated: {self.updated_at} | Confidence: {self.confidence:.0%}

## Color Palette

| Role | Hex |
|------|-----|
| Primary | `{self.colors.primary}` |
| Secondary | `{self.colors.secondary}` |
| Accent | `{self.colors.accent}` |
| Background | `{self.colors.background}` |
| Surface | `{self.colors.surface}` |
| Text Primary | `{self.colors.text_primary}` |
| Text Secondary | `{self.colors.text_secondary}` |

**Banned Colors:** {banned_colors}

## Typography

- **Headings:** {self.typography.heading_font}
- **Body:** {self.typography.body_font}
- **Monospace:** {self.typography.mono_font}
- **Base Size:** {self.typography.base_size}
- **Scale Ratio:** {self.typography.scale_ratio}
- **Line Height:** {self.typography.line_height}

## Composition

- **Grid:** {self.composition.grid_system}
- **Spacing:** {self.composition.spacing_unit}
- **Border Radius:** {self.composition.border_radius}
- **Max Width:** {self.composition.max_width}

## Mood & Atmosphere

- **Primary:** {self.mood.primary_mood}
- **Secondary:** {self.mood.secondary_mood}
- **Avoided:** {', '.join(self.mood.avoided_moods)}

## Anti-Aesthetic (Banned)

{banned_patterns}

## Cultural References

{refs}

---
*Auto-generated by Omnia Aesthetic Profile v1.0*
"""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AestheticProfile":
        """从字典恢复"""
        profile = cls(
            profile_id=data.get("profile_id", "omnia-default"),
            profile_name=data.get("profile_name", "Omnia Default Aesthetic"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            confidence=data.get("confidence", 0.3),
            references=data.get("references", []),
        )
        if "colors" in data:
            profile.colors = ColorPalette(**{k: v for k, v in data["colors"].items() if k in ColorPalette.__dataclass_fields__})
        if "typography" in data:
            profile.typography = Typography(**{k: v for k, v in data["typography"].items() if k in Typography.__dataclass_fields__})
        if "composition" in data:
            profile.composition = Composition(**{k: v for k, v in data["composition"].items() if k in Composition.__dataclass_fields__})
        if "mood" in data:
            profile.mood = MoodProfile(**{k: v for k, v in data["mood"].items() if k in MoodProfile.__dataclass_fields__})
        if "anti_aesthetic" in data:
            profile.anti_aesthetic = AntiAesthetic(**{k: v for k, v in data["anti_aesthetic"].items() if k in AntiAesthetic.__dataclass_fields__})
        return profile


# ─── AestheticExtractor：从 MemoryPalace 提取视觉偏好 ──────────

class AestheticExtractor:
    """从 MemoryPalace 的对话历史中提取视觉偏好"""

    # 视觉相关关键词
    COLOR_KEYWORDS = [
        "颜色", "色彩", "配色", "色调", "主题色", "背景色", "深色", "浅色",
        "暗色", "亮色", "黑色", "白色", "蓝色", "绿色", "红色", "紫色",
        "color", "theme", "dark", "light", "palette", "background",
    ]

    FONT_KEYWORDS = [
        "字体", "字号", "排版", "字重", "行高", "间距", "标题", "正文",
        "font", "typography", "heading", "body", "size", "weight", "line-height",
    ]

    LAYOUT_KEYWORDS = [
        "布局", "网格", "间距", "圆角", "对齐", "居中", "响应式", "移动端",
        "layout", "grid", "spacing", "border-radius", "responsive", "mobile",
    ]

    MOOD_KEYWORDS = [
        "风格", "感觉", "氛围", "简洁", "干净", "专业", "活泼", "大胆",
        "温暖", "科技感", "现代", "复古", "极简",
        "style", "mood", "clean", "minimal", "professional", "playful", "bold",
    ]

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(Path.home() / ".omnia" / "memory_palace.db")

    def extract_from_memory(self) -> Dict[str, Any]:
        """从 MemoryPalace 提取视觉偏好信号"""
        preferences = {
            "colors": [],
            "fonts": [],
            "layouts": [],
            "moods": [],
            "raw_signals": [],
        }

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 检查有哪些表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

            # 1. 从 conversation_logs 提取
            if "conversation_logs" in tables:
                cursor.execute(
                    "SELECT content FROM conversation_logs ORDER BY created_at DESC LIMIT 500"
                )
                for (content,) in cursor.fetchall():
                    if not content:
                        continue
                    self._extract_signals(content, preferences)

            # 2. 从 facts 提取
            if "facts" in tables:
                cursor.execute("SELECT key, value FROM facts ORDER BY updated_at DESC LIMIT 200")
                for key, value in cursor.fetchall():
                    text = f"{key} {value or ''}"
                    self._extract_signals(text, preferences)

            # 3. 从 habits 提取
            if "habits" in tables:
                cursor.execute("SELECT pattern, evidence FROM habits ORDER BY updated_at DESC LIMIT 100")
                for pattern, evidence in cursor.fetchall():
                    text = f"{pattern} {evidence or ''}"
                    self._extract_signals(text, preferences)

            conn.close()

        except Exception as e:
            logger.warning(f"[AestheticExtractor] Failed to extract from memory: {e}")

        return preferences

    def _extract_signals(self, text: str, preferences: Dict[str, Any]):
        """从文本中提取视觉信号"""
        lower = text.lower()

        # 提取颜色信号
        for kw in self.COLOR_KEYWORDS:
            if kw in lower:
                preferences["colors"].append({
                    "keyword": kw,
                    "context": text[:200],
                    "timestamp": datetime.now().isoformat(),
                })
                break

        # 提取字体信号
        for kw in self.FONT_KEYWORDS:
            if kw in lower:
                preferences["fonts"].append({
                    "keyword": kw,
                    "context": text[:200],
                    "timestamp": datetime.now().isoformat(),
                })
                break

        # 提取布局信号
        for kw in self.LAYOUT_KEYWORDS:
            if kw in lower:
                preferences["layouts"].append({
                    "keyword": kw,
                    "context": text[:200],
                    "timestamp": datetime.now().isoformat(),
                })
                break

        # 提取情绪信号
        for kw in self.MOOD_KEYWORDS:
            if kw in lower:
                preferences["moods"].append({
                    "keyword": kw,
                    "context": text[:200],
                    "timestamp": datetime.now().isoformat(),
                })
                break

    def build_profile(self, existing_profile: Optional[AestheticProfile] = None) -> AestheticProfile:
        """从记忆中构建或更新审美档案"""
        preferences = self.extract_from_memory()
        profile = existing_profile or AestheticProfile()

        # 根据提取的信号更新置信度
        signal_count = sum(len(v) for v in preferences.values() if isinstance(v, list))
        if signal_count > 0:
            # 信号越多，置信度越高
            profile.confidence = min(0.95, 0.3 + signal_count * 0.02)

        # 更新偏好记录
        profile.colors.preferences = {
            "color_signals": len(preferences["colors"]),
            "top_contexts": [s["context"][:100] for s in preferences["colors"][:3]],
        }
        profile.typography.preferences = {
            "font_signals": len(preferences["fonts"]),
            "top_contexts": [s["context"][:100] for s in preferences["fonts"][:3]],
        }
        profile.composition.preferences = {
            "layout_signals": len(preferences["layouts"]),
            "top_contexts": [s["context"][:100] for s in preferences["layouts"][:3]],
        }
        profile.mood.preferences = {
            "mood_signals": len(preferences["moods"]),
            "top_keywords": list(set(s["keyword"] for s in preferences["moods"][:10])),
        }

        profile.updated_at = datetime.now().isoformat()

        logger.info(
            f"[AestheticExtractor] Built profile with {signal_count} signals "
            f"(colors={len(preferences['colors'])}, fonts={len(preferences['fonts'])}, "
            f"layouts={len(preferences['layouts'])}, moods={len(preferences['moods'])})"
        )

        return profile


# ─── DesignQualityChecker：Impeccable 风格的 41 规则检测 ────────

class DesignQualityChecker:
    """基于 Impeccable 的设计质量检测器"""

    def __init__(self, rules: Optional[List[DesignRule]] = None):
        self.rules = rules or DESIGN_RULES

    def audit_code(self, code: str, file_type: str = "html") -> List[Dict[str, Any]]:
        """对代码进行设计质量审计"""
        issues = []
        lower = code.lower()

        # Anti-patterns 检测
        if file_type in ("html", "css", "tsx", "jsx"):
            # 硬编码颜色
            import re
            hex_colors = re.findall(r'#[0-9a-fA-F]{3,8}', code)
            if hex_colors and "var(--" not in code and "theme" not in lower:
                issues.append({
                    "rule_id": "hard_coded_colors",
                    "severity": "warning",
                    "message": f"发现 {len(hex_colors)} 个硬编码颜色值，建议使用设计令牌",
                    "colors": hex_colors[:5],
                })

            # 纯黑灰色
            if "#000000" in code or "#000" in code:
                issues.append({
                    "rule_id": "pure_black_gray",
                    "severity": "info",
                    "message": "使用了纯黑色 (#000000)，建议使用深灰色 (#111827) 以减少视觉疲劳",
                })

            # 缺少 viewport
            if file_type == "html" and "viewport" not in lower:
                issues.append({
                    "rule_id": "mobile_viewport",
                    "severity": "warning",
                    "message": "缺少 viewport meta 标签，移动端可能无法正确缩放",
                })

            # 缺少 lang 属性
            if file_type == "html" and "<html" in code and 'lang=' not in code.lower():
                issues.append({
                    "rule_id": "semantic_html",
                    "severity": "info",
                    "message": "HTML 标签缺少 lang 属性",
                })

            # ARIA 标签
            if "<button" in code and "aria-label" not in code and "aria-labelledby" not in code:
                issues.append({
                    "rule_id": "aria_labels",
                    "severity": "warning",
                    "message": "按钮元素缺少 ARIA 标签",
                })

            # 弹跳缓动
            if "bounce" in lower or "elastic" in lower:
                issues.append({
                    "rule_id": "bounce_easing",
                    "severity": "info",
                    "message": "使用了弹跳缓动曲线，可能影响用户体验",
                })

            # 卡片嵌套
            card_count = code.lower().count("card")
            if card_count > 3:
                issues.append({
                    "rule_id": "card_nesting",
                    "severity": "warning",
                    "message": f"检测到 {card_count} 次 'card' 引用，可能存在过度嵌套",
                })

        return issues

    def get_rules_summary(self) -> Dict[str, List[Dict[str, str]]]:
        """获取所有规则的摘要"""
        summary = {}
        for rule in self.rules:
            if rule.category not in summary:
                summary[rule.category] = []
            summary[rule.category].append({
                "rule_id": rule.rule_id,
                "name": rule.name,
                "description": rule.description,
                "severity": rule.severity,
            })
        return summary


# ─── AestheticProfileManager：管理审美档案的生命周期 ──────────

class AestheticProfileManager:
    """审美档案管理器"""

    def __init__(self, profile_dir: Optional[str] = None, db_path: Optional[str] = None):
        self.profile_dir = Path(profile_dir or Path.home() / ".omnia" / "aesthetic")
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path or str(Path.home() / ".omnia" / "memory_palace.db")
        self._profile: Optional[AestheticProfile] = None
        self._extractor = AestheticExtractor(db_path=self.db_path)
        self._checker = DesignQualityChecker()

    @property
    def profile(self) -> AestheticProfile:
        """懒加载审美档案"""
        if self._profile is None:
            self._profile = self.load_or_create()
        return self._profile

    def load_or_create(self) -> AestheticProfile:
        """加载或创建审美档案"""
        profile_path = self.profile_dir / "AESTHETICS.json"
        if profile_path.exists():
            try:
                data = json.loads(profile_path.read_text(encoding="utf-8"))
                self._profile = AestheticProfile.from_dict(data)
                logger.info(f"[AestheticProfile] Loaded profile: {self._profile.profile_id}")
                return self._profile
            except Exception as e:
                logger.warning(f"[AestheticProfile] Failed to load profile: {e}")

        # 创建默认档案
        self._profile = AestheticProfile()
        self.save()
        logger.info("[AestheticProfile] Created default profile")
        return self._profile

    def save(self):
        """保存审美档案"""
        profile_path = self.profile_dir / "AESTHETICS.json"
        profile_path.write_text(
            json.dumps(self.profile.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 同时保存 Markdown 版本
        md_path = self.profile_dir / "AESTHETICS.md"
        md_path.write_text(self.profile.to_markdown(), encoding="utf-8")

        logger.info(f"[AestheticProfile] Saved profile to {profile_path}")

    def update_from_memory(self) -> AestheticProfile:
        """从 MemoryPalace 更新审美档案"""
        self._profile = self._extractor.build_profile(self.profile)
        self.save()
        return self._profile

    def audit_code(self, code: str, file_type: str = "html") -> Dict[str, Any]:
        """审计代码的设计质量"""
        issues = self._checker.audit_code(code, file_type)

        # 计算质量分数
        error_count = sum(1 for i in issues if i["severity"] == "error")
        warning_count = sum(1 for i in issues if i["severity"] == "warning")
        info_count = sum(1 for i in issues if i["severity"] == "info")

        score = max(0, 100 - error_count * 20 - warning_count * 5 - info_count * 1)

        return {
            "score": score,
            "issues": issues,
            "summary": {
                "errors": error_count,
                "warnings": warning_count,
                "info": info_count,
                "total": len(issues),
            },
            "profile_applied": self.profile.profile_id,
        }

    def get_design_context(self) -> str:
        """获取当前设计上下文（用于生成代码时应用审美偏好）"""
        profile = self.profile
        return f"""## Design Context (Aesthetic Profile)

### Colors
- Primary: {profile.colors.primary}
- Secondary: {profile.colors.secondary}
- Accent: {profile.colors.accent}
- Background: {profile.colors.background}
- Surface: {profile.colors.surface}
- Text: {profile.colors.text_primary} / {profile.colors.text_secondary}
- Banned: {', '.join(profile.colors.banned_colors[:3])}

### Typography
- Headings: {profile.typography.heading_font}
- Body: {profile.typography.body_font}
- Base: {profile.typography.base_size}
- Scale: {profile.typography.scale_ratio}
- Line Height: {profile.typography.line_height}

### Layout
- Grid: {profile.composition.grid_system}
- Spacing: {profile.composition.spacing_unit}
- Radius: {profile.composition.border_radius}
- Max Width: {profile.composition.max_width}

### Mood
- {profile.mood.primary_mood} + {profile.mood.secondary_mood}
- Avoid: {', '.join(profile.mood.avoided_moods[:3])}

### References
{chr(10).join(f'- {r}' for r in profile.references[:4])}

### Anti-Aesthetic
{chr(10).join(f'- ❌ {p}' for p in profile.anti_aesthetic.banned_patterns[:5])}

### Confidence: {profile.confidence:.0%}
"""

    def status(self) -> Dict[str, Any]:
        """获取审美档案状态"""
        profile = self.profile
        return {
            "profile_id": profile.profile_id,
            "profile_name": profile.profile_name,
            "confidence": profile.confidence,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
            "dimensions": {
                "colors": len(profile.colors.__dict__),
                "typography": len(profile.typography.__dict__),
                "composition": len(profile.composition.__dict__),
                "mood": len(profile.mood.__dict__),
                "anti_aesthetic": len(profile.anti_aesthetic.banned_elements),
            },
            "references": len(profile.references),
            "design_rules": len(DESIGN_RULES),
        }


# ─── 全局单例 ─────────────────────────────────────────────────

_global_manager: Optional[AestheticProfileManager] = None


def get_aesthetic_manager() -> AestheticProfileManager:
    """获取全局审美档案管理器"""
    global _global_manager
    if _global_manager is None:
        _global_manager = AestheticProfileManager()
    return _global_manager


# ─── CLI 入口 ──────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    manager = get_aesthetic_manager()

    if len(sys.argv) > 1 and sys.argv[1] == "update":
        profile = manager.update_from_memory()
        print(f"✅ Profile updated: confidence={profile.confidence:.0%}")
        print(f"   Colors signals: {profile.colors.preferences.get('color_signals', 0)}")
        print(f"   Font signals: {profile.typography.preferences.get('font_signals', 0)}")
        print(f"   Layout signals: {profile.composition.preferences.get('layout_signals', 0)}")
        print(f"   Mood signals: {profile.mood.preferences.get('mood_signals', 0)}")
    elif len(sys.argv) > 1 and sys.argv[1] == "status":
        print(json.dumps(manager.status(), ensure_ascii=False, indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "markdown":
        print(manager.profile.to_markdown())
    else:
        print("Usage:")
        print("  python aesthetic_profile.py update    # 从 MemoryPalace 更新档案")
        print("  python aesthetic_profile.py status    # 查看档案状态")
        print("  python aesthetic_profile.py markdown  # 导出 Markdown")
