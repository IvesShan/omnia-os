"""Skill Discovery - 动态发现和展示技能

参考 Hermes 的 Skill Registry 和 FreeCode 的 Skills 系统
"""

from pathlib import Path
from typing import List, Dict
import re


def discover_skills(workspace_root: Path = None) -> List[Dict]:
    """发现所有可用的技能
    
    Args:
        workspace_root: 工作区根目录
    
    Returns:
        [{"name": str, "description": str, "location": str}, ...]
    """
    if workspace_root is None:
        workspace_root = Path.home() / ".openclaw" / "workspace"
    
    skills = []
    
    # 1. 主技能目录
    main_skills_dir = workspace_root / "skills"
    if main_skills_dir.exists():
        for skill_dir in main_skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    skill_info = parse_skill_md(skill_md)
                    if skill_info:
                        skills.append(skill_info)
    
    # 2. Omnia 内置技能
    omnia_skills_dir = workspace_root / "omnia-os" / "skills"
    if omnia_skills_dir.exists():
        for skill_dir in omnia_skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    skill_info = parse_skill_md(skill_md)
                    if skill_info:
                        skills.append(skill_info)
    
    # 3. Auto-forge 技能（临时技能）
    tmp_skills_dirs = [
        workspace_root / "omnia-os" / ".tmp_skills",
        workspace_root / "omnia-os" / ".tmp_forge",
    ]
    
    for tmp_dir in tmp_skills_dirs:
        if tmp_dir.exists():
            for skill_dir in tmp_dir.iterdir():
                if skill_dir.is_dir():
                    skill_md = skill_dir / "SKILL.md"
                    if skill_md.exists():
                        skill_info = parse_skill_md(skill_md)
                        if skill_info:
                            skill_info["auto_generated"] = True
                            skills.append(skill_info)
    
    return skills


def parse_skill_md(skill_md: Path) -> Dict:
    """解析 SKILL.md 文件
    
    Args:
        skill_md: SKILL.md 文件路径
    
    Returns:
        {"name": str, "description": str, "location": str}
    """
    try:
        content = skill_md.read_text(encoding="utf-8")
        
        # 提取名称（第一个标题或 name 字段）
        name = None
        
        # 尝试从 frontmatter 提取
        name_match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
        if name_match:
            name = name_match.group(1).strip()
        else:
            # 尝试从第一个标题提取
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            if title_match:
                name = title_match.group(1).strip()
        
        # 提取描述
        description = None
        desc_match = re.search(r'^description:\s*(.+)$', content, re.MULTILINE)
        if desc_match:
            description = desc_match.group(1).strip()
        else:
            # 尝试从第一个段落提取
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('#') and not line.startswith('name:') and not line.startswith('description:'):
                    description = line.strip()
                    break
        
        if name:
            return {
                "name": name,
                "description": description or "无描述",
                "location": str(skill_md.parent.relative_to(skill_md.parents[3]))
            }
    
    except Exception as e:
        print(f"[SkillDiscovery] Failed to parse {skill_md}: {e}")
    
    return None


def format_skills_for_prompt(skills: List[Dict]) -> str:
    """格式化技能列表用于系统提示
    
    Args:
        skills: 技能列表
    
    Returns:
        格式化的字符串
    """
    if not skills:
        return "**技能**: 暂无"
    
    lines = [f"**技能** ({len(skills)} 个):"]
    
    for skill in skills:
        name = skill.get("name", "Unknown")
        desc = skill.get("description", "")[:60]  # 限制长度
        auto = " [自动生成]" if skill.get("auto_generated") else ""
        lines.append(f"- {name}{auto}: {desc}")
    
    return "\n".join(lines)


def get_skills_summary() -> str:
    """获取技能摘要（用于系统提示）
    
    Returns:
        格式化的技能摘要
    """
    skills = discover_skills()
    return format_skills_for_prompt(skills)
