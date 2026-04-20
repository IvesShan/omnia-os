"""Working Memory - L1 short-term context for Omnia."""

from pathlib import Path
from datetime import datetime
from typing import Optional


def load_working_memory(project_root: Path) -> Optional[str]:
    """Load L1 working memory (essential.md).
    
    This is loaded on EVERY request to maintain short-term context.
    """
    essential_path = project_root / "memory" / "working" / "essential.md"
    if not essential_path.exists():
        return None
    
    try:
        content = essential_path.read_text(encoding="utf-8")
        # Truncate to avoid token bloat (keep first 1000 chars)
        if len(content) > 1000:
            content = content[:1000] + "\n... (truncated)"
        return content
    except Exception:
        return None


def load_current_task(project_root: Path) -> Optional[str]:
    """Load current task state.
    
    Only returns content if there's an active task.
    """
    task_path = project_root / "memory" / "working" / "current_task.md"
    if not task_path.exists():
        return None
    
    try:
        content = task_path.read_text(encoding="utf-8")
        # Only load if there's an active task
        if "**任务 ID**: -" in content or "**任务 ID**:-" in content:
            return None  # No active task
        return content
    except Exception:
        return None


def update_essential_context(
    project_root: Path,
    task_status: str = "-",
    task_description: str = "-",
    recent_summary: str = "-"
) -> None:
    """Update essential.md with current context."""
    essential_path = project_root / "memory" / "working" / "essential.md"
    if not essential_path.exists():
        return
    
    try:
        content = essential_path.read_text(encoding="utf-8")
        lines = content.split("\n")
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        in_section = None
        
        for i, line in enumerate(lines):
            # Track current section
            if line.startswith("## "):
                section_title = line[3:].strip().lower()
                if "当前任务" in section_title:
                    in_section = "task"
                elif "最近对话" in section_title:
                    in_section = "recent"
                elif "最后更新" in line.lower():
                    in_section = None
                else:
                    in_section = None
            
            # Update task section
            if in_section == "task":
                if "**状态**:" in line:
                    lines[i] = f"**状态**: {task_status}"
                elif "**任务**:" in line:
                    lines[i] = f"**任务**: {task_description}"
            
            # Update recent summary
            elif in_section == "recent":
                if line.startswith("- ") and recent_summary != "-":
                    lines[i] = f"- {recent_summary}"
            
            # Update timestamp
            if "*最后更新:" in line:
                lines[i] = f"*最后更新: {now}*"
        
        essential_path.write_text("\n".join(lines), encoding="utf-8")
    except Exception:
        pass


def start_task(
    project_root: Path,
    task_id: str,
    description: str,
    steps: list
) -> None:
    """Start a new task and update working memory."""
    task_path = project_root / "memory" / "working" / "current_task.md"
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    steps_text = "\n".join(f"- [ ] {step}" for step in steps)
    
    content = f"""# Current Task - 当前任务状态

## 活跃任务

**任务 ID**: {task_id}
**描述**: {description}
**创建时间**: {now}
**最后更新**: {now}

## 已完成步骤

- [ ] (暂无)

## 待完成步骤

{steps_text}

## 阻塞项

**阻塞原因**: -
**需要用户输入**: 否
**等待中**: -

---

*此文件会在任务开始、进度更新、任务完成时自动更新*
"""
    task_path.write_text(content, encoding="utf-8")
    update_essential_context(project_root, "执行中", description)


def complete_task(project_root: Path) -> None:
    """Complete current task and clear working memory."""
    task_path = project_root / "memory" / "working" / "current_task.md"
    
    template = """# Current Task - 当前任务状态

## 活跃任务

**任务 ID**: -
**描述**: -
**创建时间**: -
**最后更新**: -

## 已完成步骤

- [ ] (暂无)

## 待完成步骤

- [ ] (暂无)

---

*此文件会在任务开始、进度更新、任务完成时自动更新*
"""
    task_path.write_text(template, encoding="utf-8")
    update_essential_context(project_root, "空闲", "-")
