"""
Auto Skill Learner - Omnia 2.0

参考：Hermes 的自学习循环
创新：自动从成功任务中提取技能模式

工作流程：
1. 分析对话轨迹
2. 提取可复用模式
3. 评估复用价值
4. 生成技能文件
5. 注册到技能库

Usage:
    from core.capability.auto_learner import AutoSkillLearner
    
    learner = AutoSkillLearner()
    skill = await learner.analyze_and_create(messages, tools_used)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
import json
import re


@dataclass
class ToolCallPattern:
    """工具调用模式"""
    tool_name: str
    arguments: dict
    result_summary: str
    success: bool


@dataclass
class TaskPattern:
    """任务模式"""
    name: str
    description: str
    trigger_keywords: list[str]
    tool_sequence: list[ToolCallPattern]
    success_rate: float
    sample_count: int = 1
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Skill:
    """技能定义"""
    name: str
    description: str
    triggers: list[str]  # 触发关键词
    procedure: list[dict]  # 执行步骤
    examples: list[str]
    metadata: dict = field(default_factory=dict)
    
    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        md = f"""# {self.name}

{self.description}

## 触发条件

"""
        for trigger in self.triggers:
            md += f"- {trigger}\n"
        
        md += "\n## 执行步骤\n\n"
        for i, step in enumerate(self.procedure, 1):
            md += f"{i}. **{step.get('action', 'Unknown')}**: {step.get('description', '')}\n"
        
        if self.examples:
            md += "\n## 示例\n\n"
            for ex in self.examples[:3]:
                md += f"- {ex}\n"
        
        return md


class AutoSkillLearner:
    """
    自动技能学习器
    
    从成功的任务执行中自动提取可复用的技能模式
    """
    
    # 最小样本数（少于此数量不创建技能）
    MIN_SAMPLES = 1
    
    # 最小成功率
    MIN_SUCCESS_RATE = 0.7
    
    # 工具调用模式缓存
    _pattern_cache: dict[str, list[TaskPattern]] = {}
    
    def __init__(
        self,
        skill_dir: Path | str = ".omnia/skills",
        llm_caller: Callable | None = None
    ):
        self.skill_dir = Path(skill_dir)
        self.skill_dir.mkdir(parents=True, exist_ok=True)
        self.llm_caller = llm_caller
    
    async def analyze_trajectory(
        self,
        messages: list[dict],
        tools_used: list[dict]
    ) -> TaskPattern | None:
        """
        分析对话轨迹，提取任务模式
        
        Args:
            messages: 对话消息
            tools_used: 工具调用记录
        
        Returns:
            TaskPattern if extractable, None otherwise
        """
        if not tools_used:
            return None
        
        # 1. 提取用户意图
        user_message = self._extract_user_intent(messages)
        if not user_message:
            return None
        
        # 2. 分析工具调用序列
        tool_patterns = []
        success = True
        
        for tool_call in tools_used:
            pattern = ToolCallPattern(
                tool_name=tool_call.get("name", "unknown"),
                arguments=tool_call.get("arguments", {}),
                result_summary=str(tool_call.get("result", ""))[:200],
                success=not tool_call.get("error")
            )
            tool_patterns.append(pattern)
            if not pattern.success:
                success = False
        
        # 3. 只有成功的任务才创建模式
        if not success:
            return None
        
        # 4. 生成模式名称和描述
        name = self._generate_name(user_message, tool_patterns)
        description = self._generate_description(user_message, tool_patterns)
        triggers = self._extract_triggers(user_message)
        
        return TaskPattern(
            name=name,
            description=description,
            trigger_keywords=triggers,
            tool_sequence=tool_patterns,
            success_rate=1.0,
            sample_count=1
        )
    
    async def evaluate_reuse_value(self, pattern: TaskPattern) -> float:
        """
        评估模式的复用价值
        
        Returns:
            0.0 - 1.0 的复用价值分数
        """
        score = 0.0
        
        # 1. 工具序列长度（2-4 个工具最佳）
        tool_count = len(pattern.tool_sequence)
        if 2 <= tool_count <= 4:
            score += 0.3
        elif tool_count == 1:
            score += 0.1  # 单工具模式复用价值较低
        else:
            score += 0.2  # 过于复杂
        
        # 2. 触发关键词通用性
        generic_keywords = ["帮我", "检查", "查看", "分析", "整理", "创建"]
        generic_count = sum(1 for t in pattern.trigger_keywords if any(g in t for g in generic_keywords))
        score += min(generic_count * 0.1, 0.3)
        
        # 3. 成功率
        score += pattern.success_rate * 0.3
        
        # 4. 样本数（多次成功的模式更有价值）
        score += min(pattern.sample_count * 0.05, 0.1)
        
        return min(score, 1.0)
    
    async def create_skill(self, pattern: TaskPattern) -> Skill:
        """
        从任务模式创建技能
        
        Args:
            pattern: 任务模式
        
        Returns:
            Skill 对象
        """
        # 生成执行步骤
        procedure = []
        for i, tool in enumerate(pattern.tool_sequence, 1):
            step = {
                "action": tool.tool_name,
                "description": f"调用 {tool.tool_name} 工具",
                "arguments_template": tool.arguments
            }
            procedure.append(step)
        
        # 生成示例
        examples = [
            f"用户说 '{pattern.trigger_keywords[0] if pattern.trigger_keywords else '...'}'",
            f"系统执行了 {len(pattern.tool_sequence)} 个步骤",
            f"任务成功完成"
        ]
        
        skill = Skill(
            name=pattern.name,
            description=pattern.description,
            triggers=pattern.trigger_keywords,
            procedure=procedure,
            examples=examples,
            metadata={
                "created_at": datetime.now().isoformat(),
                "sample_count": pattern.sample_count,
                "success_rate": pattern.success_rate,
                "tool_count": len(pattern.tool_sequence)
            }
        )
        
        return skill
    
    async def save_skill(self, skill: Skill) -> Path:
        """
        保存技能到文件
        
        Args:
            skill: 技能对象
        
        Returns:
            技能文件路径
        """
        skill_file = self.skill_dir / f"{skill.name}.md"
        
        # 写入 Markdown
        skill_file.write_text(skill.to_markdown(), encoding="utf-8")
        
        # 同时写入 JSON 元数据
        meta_file = self.skill_dir / f"{skill.name}.json"
        meta_file.write_text(json.dumps({
            "name": skill.name,
            "description": skill.description,
            "triggers": skill.triggers,
            "procedure": skill.procedure,
            "metadata": skill.metadata
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        
        return skill_file
    
    async def analyze_and_create(
        self,
        messages: list[dict],
        tools_used: list[dict]
    ) -> Skill | None:
        """
        完整流程：分析 → 评估 → 创建 → 保存
        
        Args:
            messages: 对话消息
            tools_used: 工具调用记录
        
        Returns:
            Skill if created, None otherwise
        """
        # 1. 分析轨迹
        pattern = await self.analyze_trajectory(messages, tools_used)
        if not pattern:
            return None
        
        # 2. 评估复用价值
        reuse_value = await self.evaluate_reuse_value(pattern)
        if reuse_value < 0.5:
            print(f"[AutoLearner] Pattern '{pattern.name}' has low reuse value: {reuse_value:.2f}")
            return None
        
        # 3. 创建技能
        skill = await self.create_skill(pattern)
        
        # 4. 保存
        skill_path = await self.save_skill(skill)
        print(f"[AutoLearner] Created skill: {skill_path}")
        
        return skill
    
    def _extract_user_intent(self, messages: list[dict]) -> str | None:
        """提取用户意图"""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg.get("content", "")
        return None
    
    def _generate_name(self, intent: str, patterns: list[ToolCallPattern]) -> str:
        """生成技能名称"""
        # 从意图中提取关键词
        words = re.findall(r'[\u4e00-\u9fa5a-zA-Z]+', intent)
        
        # 优先使用动词
        verbs = ["查看", "检查", "分析", "创建", "删除", "修改", "整理", "部署"]
        for word in words:
            if word in verbs:
                # 组合动词和对象
                other_words = [w for w in words if w != word][:2]
                return "_".join([word] + other_words)
        
        # 没有动词，使用工具名
        if patterns:
            return f"auto_{patterns[0].tool_name}"
        
        return f"auto_skill_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _generate_description(self, intent: str, patterns: list[ToolCallPattern]) -> str:
        """生成技能描述"""
        tool_names = [p.tool_name for p in patterns]
        
        if len(tool_names) == 1:
            return f"自动创建的技能：使用 {tool_names[0]} 完成 '{intent[:30]}...'"
        else:
            return f"自动创建的技能：依次调用 {', '.join(tool_names)} 完成 '{intent[:30]}...'"
    
    def _extract_triggers(self, intent: str) -> list[str]:
        """提取触发关键词"""
        triggers = []
        
        # 提取动词
        verbs = ["帮我", "查看", "检查", "分析", "创建", "删除", "修改", "整理", "部署"]
        for verb in verbs:
            if verb in intent:
                triggers.append(verb)
        
        # 提取关键词
        keywords = re.findall(r'[\u4e00-\u9fa5]{2,4}', intent)
        triggers.extend(keywords[:3])
        
        return list(set(triggers))[:5]
    
    def list_skills(self) -> list[dict]:
        """列出所有已创建的技能"""
        skills = []
        for meta_file in self.skill_dir.glob("*.json"):
            try:
                data = json.loads(meta_file.read_text(encoding="utf-8"))
                skills.append(data)
            except:
                continue
        return skills
    
    def get_skill(self, name: str) -> Skill | None:
        """获取技能"""
        meta_file = self.skill_dir / f"{name}.json"
        if not meta_file.exists():
            return None
        
        try:
            data = json.loads(meta_file.read_text(encoding="utf-8"))
            return Skill(
                name=data["name"],
                description=data["description"],
                triggers=data["triggers"],
                procedure=data["procedure"],
                metadata=data.get("metadata", {})
            )
        except:
            return None


# ============================================================================
# Skill Matcher - 匹配用户输入到已有技能
# ============================================================================

class SkillMatcher:
    """
    技能匹配器
    
    根据用户输入匹配已有技能
    """
    
    def __init__(self, skill_dir: Path | str = ".omnia/skills"):
        self.skill_dir = Path(skill_dir)
        self._skills: list[Skill] | None = None
    
    def _load_skills(self) -> list[Skill]:
        """加载所有技能"""
        if self._skills is not None:
            return self._skills
        
        skills = []
        for meta_file in self.skill_dir.glob("*.json"):
            try:
                data = json.loads(meta_file.read_text(encoding="utf-8"))
                skills.append(Skill(
                    name=data["name"],
                    description=data["description"],
                    triggers=data["triggers"],
                    procedure=data["procedure"],
                    metadata=data.get("metadata", {})
                ))
            except:
                continue
        
        self._skills = skills
        return skills
    
    def match(self, user_input: str) -> Skill | None:
        """
        匹配用户输入到技能
        
        Args:
            user_input: 用户输入
        
        Returns:
            匹配的 Skill，如果没有匹配返回 None
        """
        skills = self._load_skills()
        if not skills:
            return None
        
        input_lower = user_input.lower()
        
        for skill in skills:
            # 检查触发关键词
            for trigger in skill.triggers:
                if trigger.lower() in input_lower:
                    return skill
        
        return None
    
    def get_skill_hints(self, user_input: str) -> list[str]:
        """获取技能提示（用于推荐）"""
        skills = self._load_skills()
        hints = []
        
        input_lower = user_input.lower()
        
        for skill in skills:
            for trigger in skill.triggers:
                if trigger.lower() in input_lower:
                    hints.append(f"可以执行技能: {skill.name}")
                    break
        
        return hints
