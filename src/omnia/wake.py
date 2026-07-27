"""Omnia Wake — The full ignition sequence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.core.cognition.token_budget import TokenBudget, PromptComponent
from src.core.cognition.ultraplan import UltraPlan
from src.omnia.config import settings
from src.core.memory_palace import MemoryPalace
from src.core.neural_graph.context_enhancer import NeuralGraphContextEnhancer
from src.core.neuro_center.notification_queue import pop_notifications_for_session
from src.core.personas import load_persona
from src.core.working_memory import load_working_memory, load_current_task
from src.core.context_manager import ContextManager


def _load_ide_context(workspace_root: Path) -> Optional[str]:
    ide_path = settings.omnia_home / "ide_context.json"
    if not ide_path.exists():
        return None
    try:
        data = json.loads(ide_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    lines = []
    file_path = data.get("file")
    if file_path:
        lines.append(f"Active file: `{file_path}` (language={data.get('language', 'unknown')})")
        line = data.get("line")
        column = data.get("column")
        if line is not None and column is not None:
            lines.append(f"Cursor position: line {line}, column {column}")
        selected = data.get("selectedText", "").strip()
        if selected:
            preview = selected.replace("\\n", " ")[:120]
            lines.append(f'Selected text: "{preview}"')
    else:
        lines.append("No active editor in IDE.")

    return "\n".join(lines)


def _load_skill_content(
    skill_id: str,
    workspace_root: Path,
    project_root: Path
) -> Optional[str]:
    """Load SKILL.md content for a matched skill.
    
    Search order:
    1. workspace/skills/{skill_id}/SKILL.md
    2. omnia-os/skills/auto-forge/{skill_id}/SKILL.md
    3. omnia-os/skills/{skill_id}/SKILL.md
    """
    search_paths = [
        workspace_root / "skills" / skill_id / "SKILL.md",
        project_root / "skills" / "auto-forge" / skill_id / "SKILL.md",
        project_root / "skills" / skill_id / "SKILL.md",
    ]
    
    for skill_md in search_paths:
        if skill_md.exists():
            try:
                content = skill_md.read_text(encoding="utf-8")
                # Truncate to avoid token bloat (keep first 1500 chars)
                if len(content) > 1500:
                    content = content[:1500] + "\n... (truncated)"
                return content
            except Exception:
                pass
    
    return None


def _load_active_skills(
    matched_skills: List[Tuple[str, float]],
    workspace_root: Path,
    project_root: Path,
    max_skills: int = 2
) -> str:
    """Load content for top matched skills.
    
    Args:
        matched_skills: List of (skill_id, score) tuples from UltraPlan
        workspace_root: Workspace root path
        project_root: Project root path
        max_skills: Maximum number of skills to load
    
    Returns:
        Formatted skill content string
    """
    if not matched_skills:
        return ""
    
    parts = []
    loaded = 0
    
    for skill_id, score in matched_skills[:max_skills]:
        content = _load_skill_content(skill_id, workspace_root, project_root)
        if content:
            parts.append(f"### Skill: {skill_id} (relevance: {score:.1f})\n\n{content}")
            loaded += 1
            if loaded >= max_skills:
                break
    
    if parts:
        return "## Active Skills\n\n" + "\n\n---\n\n".join(parts)
    
    return ""


def assemble_wake_prompt(
    message: Optional[str] = None,
    workspace_root: Path = PROJECT_ROOT.parent,
    project_root: Path = PROJECT_ROOT,
) -> str:
    """Run the full Omnia wake cycle and return the compiled system prompt."""

    # 1. Pending notifications from the daemon
    pulse = pop_notifications_for_session(
        queue_path=project_root / ".omnia" / "notifications.jsonl"
    )

    # 2. Load personas
    infinite = load_persona("infinite", seed_dir=project_root / "seeds")
    omnia = load_persona("omnia", seed_dir=project_root / "seeds")

    # 3. ULTRAPLAN (only if a message was provided)
    plan = None
    if message:
        up = UltraPlan(
            skills_dir=workspace_root / "skills",
            auto_forge_dir=project_root / "skills" / "auto-forge",
        )
        plan = up.plan(message)

    # 4. Memory Palace recall
    db_path = settings.memory_palace_db
    mp = MemoryPalace(db_path)
    mp.initialize()

    recalled_facts = []
    recalled_relations = []
    recalled_habits = []

    if plan:
        memory_queries = plan.memory_queries
        for q in memory_queries:
            recalled_facts.extend(mp.recall_facts(key=q))
        for fact in mp.recall_facts(category="preference"):
            if fact not in recalled_facts:
                recalled_facts.append(fact)
        if "relations" in plan.memory_layers:
            for q in memory_queries:
                recalled_relations.extend(mp.recall_relations(q))
        if "habits" in plan.memory_layers:
            recalled_habits.extend(mp.recall_habits())
    else:
        # No message: do a light recall of recent facts and top habits
        recalled_facts = mp.recall_facts(category="preference")[:5]
        recalled_habits = mp.recall_habits()[:3]

    # 5. Neural Graph context enhancement
    graph_context = None
    if message:
        enhancer = NeuralGraphContextEnhancer(str(db_path))
        graph_context = enhancer.enhance(message)

    # 6. IDE context
    ide_context = _load_ide_context(workspace_root)

    # 7. Load active skills content
    skills_content = ""
    if plan and plan.relevant_skills:
        skills_content = _load_active_skills(
            plan.relevant_skills,
            workspace_root,
            project_root,
            max_skills=2
        )

    # 8. Assemble prompt components with priorities (higher number = more important, evicted last)
    components: List[PromptComponent] = []

    # Pulse notifications (highest priority - daemon alerts)
    if pulse:  # pulse is a string
        components.append(PromptComponent("pulse", "## Daemon Pulse\n" + pulse, priority=20))

    # Agents manual (high priority - core behavior)
    agents_summary = """## 记忆系统

**你有 Memory Palace，已有 600+ 条记忆！**

搜索技巧：用简单关键词，不要用复杂句子。
- ✅ query_memory("OpenClaw")
- ✅ query_memory("用户")
- ❌ query_memory("记忆系统 记忆宫殿")

**你已经有记忆了，搜索就能找到！**

⚠️ **版本意识**：记忆有版本控制。如果搜索到多条同名项目的记忆：
- 优先相信 `id` 更大的那条（最新版本）
- 如果发现冲突信息，优先采用更新创建/更新的记录
- 可以用 `query_memory("项目名")` 查完整记录

## 可用工具（自动发现）

通过 tool_calls API 调用工具，不要在文本里输出 JSON。

你拥有以下工具（自动从系统注册表加载）：
- **read_file** — 读取文本/代码文件（.py/.md/.json/.txt 等）
- **write_file** — 写入文件（自动创建目录）
- **execute_shell** — 执行 shell 命令（git/搜索/构建等）
- **list_directory** — 列出目录内容
- **web_search** — 网络搜索
- **query_memory** — 查询记忆宫殿
- **save_memory** — 保存新记忆
- **memory_stats** — 查看记忆统计
- 以及 MCP 工具（git_status, git_commit, fetch, puppeteer 等）

**重要**：遇到文件操作、状态检查、数据分析时，必须主动调用工具。

## Skill 系统

你拥有 **Skill（技能）系统**。Skill 是封装好的专业能力模块，位于以下目录：
- `~/omnia-os/skills/`
- `~/.openclaw/workspace/skills/`

**关键 Skill**：
- **courseware-designer** — 课件设计专家（HTML课件/PPT风格）
- **drone-repair-agent** — 无人机维修诊断专家
- **miaoxiujiang-merchant** — 喵修匠商家后台开发
- **modern-web-dev-2026** — 现代Web开发
- **full-stack-dev-2026** — 全栈开发
- **kimi-rate-optimizer** — API调用优化
- **karpathy-coding-guidelines** — 代码质量规范
- 以及 20+ 其他 Skill

**使用方式**：当用户需求匹配某个 Skill 时，你应该：
1. 先用 `read_file` 读取对应 SKILL.md（如 `skills/courseware-designer/SKILL.md`）
2. 根据 SKILL.md 的规范执行
3. 不要自己编造规范，Skill 里已有完整方案

## 神经图谱（Neural Graph）

你拥有 **Neural Graph（神经知识图谱）** 系统，存储了概念之间的关联关系。
- 用途：理解用户问题背后的知识网络，提供深度上下文
- 数据：实体、关系、语义关联
- 自动增强：每轮对话已自动注入相关图谱上下文

### 🔴 硬规矩：必须先调用工具再回答

**任何需要读取文件、查询状态、验证结果的场景，都必须先调用工具再回答。** 典型场景包括（不仅限于）：

- 用户说"检查""确认""验证""查看""读文件""看看效果""分析""重新分析""深入分析"
- 用户问"有没有生效""改好了吗""提交了吗""检查一下""怎么样了""状态"
- 用户说"调用工具""用工具查""跑一下"
- 涉及查询文件内容、Git 状态、服务运行状态、代码分析

违规后果：如果未调用工具就直接声称"已完成""已修改"，一律视为错误。

### ✅ 正确示例

**用户**: "检查一下 wake.py 的内容"
**你的行为**: 
1. 调用 read_file(path="/home/shan/omnia-os/src/omnia/wake.py")
2. 等待工具返回结果
3. 基于结果回答

**用户**: "看看 Git 状态"
**你的行为**:
1. 调用 execute_shell(command="git status")
2. 等待工具返回结果
3. 基于结果回答

**用户**: "深入分析工具调用问题"
**你的行为**:
1. 调用 read_file 读取相关代码
2. 调用 execute_shell 检查日志
3. 基于结果分析

### ❌ 错误示例

**用户**: "检查一下 wake.py 的内容"
**错误行为**: 直接回答"wake.py 是一个 Python 文件..."（未调用工具）

**用户**: "看看 Git 状态"
**错误行为**: 直接回答"Git 状态是..."（未调用工具）

### 🔧 判断标准

**必须调用工具的场景**：
1. 需要读取文件内容 → read_file
2. 需要执行命令 → execute_shell
3. 需要查看目录 → list_directory
4. 需要搜索记忆 → query_memory
5. 需要搜索网络 → web_search

**不需要调用工具的场景**：
1. 纯粹的闲聊（"你好"、"再见"）
2. 知识问答（"什么是 Python"）
3. 创意生成（"写一首诗"）

### 🚫 绝对禁止：工具调用幻觉（最严重错误）

**你绝对不能在回复文本中声称自己调用了某个工具，除非你确实通过 tool_calls API 调用了它。**

这是你最常犯的错误，必须彻底纠正：

❌ **幻觉行为（绝对禁止）**：
- 说"让我读取文件看看"——但不调用 read_file
- 说"文件内容如下..."——但没有实际读取
- 说"文件已写入成功"——但没有调用 write_file
- 说"已执行命令，结果是..."——但没有调用 execute_shell
- 说"搜索结果显示..."——但没有调用 web_search
- 说"根据记忆..."——但没有调用 query_memory

**以上全是幻觉。如果你没调用工具，就绝对不能在文本里声称自己做了。**

✅ **正确行为**：
- 要么：**实际调用工具**（通过 tool_calls API），然后基于真实结果回答
- 要么：**不调用工具**，直接说"我需要调用 read_file 来确认"或"我无法确认，需要工具"

**用户可以看到你是否真的调用了工具（tool_calls 计数）。如果你声称调用了但没有，这就是幻觉，会严重降低信任。**

### 📌 任务跟踪与记忆使用（关键！）

**任务意识**：你必须记住当前正在执行的任务，避免重复执行已完成的操作。每次回复前先问自己："用户让我做什么？""我已经做了什么？""下一步该做什么？"

**记忆查询（强制）**：
- 用户提到"之前"、"上次"、"刚才" → 必须 query_memory
- 用户说"继续"、"确认" → 先 query_memory 查上下文
- 不确定该做什么 → query_memory 查当前任务状态

**状态持久化**：生成文件/修改配置/用户确认后，用 save_memory 保存状态，下次通过 query_memory 恢复，避免重复工作。

## 项目路径
- Omnia: /home/shan/omnia-os
- 守护进程: scripts/start_daemon.py
"""
    components.append(PromptComponent("agents_manual", agents_summary, priority=15))

    components.append(PromptComponent("persona_infinite", "## Active Persona: " + infinite.name + "\n\n" + infinite.system_prompt(), priority=10))
    components.append(PromptComponent("persona_omnia", "## System Guardian: " + omnia.name + "\n\n" + omnia.system_prompt(), priority=10))


    # L1 Working Memory (NEW - highest priority after pulse)
    working_memory = load_working_memory(project_root)
    if working_memory:
        components.append(PromptComponent(
            "working_memory",
            "## Essential Context (L1)\n\n" + working_memory,
            priority=12  # 高于 Persona (10)
        ))
    
    # Load last session context (NEW - 解决对话连续性问题)
    context_manager = ContextManager(settings.omnia_home)
    last_context = context_manager.load_context()
    if last_context:
        context_parts = ["## 上次会话上下文"]
        context_parts.append(f"📅 时间: {last_context.timestamp}")
        context_parts.append(f"📌 主题: {last_context.topic}")
        context_parts.append(f"📝 摘要: {last_context.summary}")
        
        if last_context.active_project:
            context_parts.append(f"🏗️ 项目: {last_context.active_project}")
        
        if last_context.next_steps:
            context_parts.append(f"➡️ 下一步: {', '.join(last_context.next_steps[:3])}")
        
        # 接续提示
        context_parts.append("")
        context_parts.append("⚠️ **重要**: 如果用户的话题与上次相关，请主动接续，不要装作不知道。")
        context_parts.append("如果用户问\"继续\"，请根据上次的上下文继续之前的工作。")
        
        context_text = "\n".join(context_parts)
        components.append(PromptComponent(
            "last_session_context",
            context_text,
            priority=11.5  # 仅低于 working_memory
        ))


    # Semantic search for related conversations (NEW - P1 optimization)
    related_conversations = []
    if message:
        try:
            similar = mp.search_conversations_semantic(message, top_k=5)
            if similar:
                # Filter by similarity threshold
                related_conversations = [
                    (conv, score) for conv, score in similar 
                    if score > 0.7
                ][:3]  # Top 3 most relevant
        except Exception as e:
            print(f"[Wake] Semantic search failed: {e}")
    
    if related_conversations:
        conv_parts = ["## 相关历史对话"]
        conv_parts.append("以下是与当前话题语义相似的历史对话片段：")
        conv_parts.append("")
        for i, (conv, score) in enumerate(related_conversations, 1):
            content_preview = conv['content'][:150]
            if len(conv['content']) > 150:
                content_preview += "..."
            conv_parts.append(f"**{i}.** [{conv['role']}] {content_preview}")
            conv_parts.append(f"   相似度: {score:.2f}")
            conv_parts.append("")
        
        conv_text = "\n".join(conv_parts)
        components.append(PromptComponent(
            "related_conversations",
            conv_text,
            priority=4.8  # 高于 Neural Graph (4.5)
        ))

    current_task = load_current_task(project_root)
    if current_task:
        components.append(PromptComponent(
            "current_task",
            "## Current Task State\n\n" + current_task,
            priority=11  # 仅次于 essential
        ))
    if plan:
        components.append(PromptComponent("context", "## Current Context\n- User message: " + str(message) + f"\n- Detected intent: {plan.intent} (confidence {plan.confidence:.2f})\n- Plan type: {plan.plan_type}\n- Relevant skills: {', '.join(s for s, _ in plan.relevant_skills) or 'none'}", priority=6))
    else:
        components.append(PromptComponent("context", "## Current Context\n- No active message. Omnia is running a routine wake cycle.", priority=6))

    if ide_context:
        components.append(PromptComponent("ide_context", "## IDE Context\n" + ide_context, priority=5))

    # Active skills content (new!)
    if skills_content:
        components.append(PromptComponent("active_skills", skills_content, priority=5.5))

    # Neural Graph context
    if graph_context and graph_context.entities:
        graph_parts = ["## Neural Graph Context"]
        graph_parts.append(f"**置信度**: {graph_context.confidence:.2f}")
        graph_parts.append("")
        graph_parts.append(graph_context.subgraph_summary)
        graph_text = "\n".join(graph_parts)
        components.append(PromptComponent("neural_graph", graph_text, priority=4.5))

    memory_parts = []
    if recalled_facts:
        memory_parts.append("### Facts")
        for f in recalled_facts:
            memory_parts.append(f"- [{f['category']}] {f['key']}: {f['value']}")
    if recalled_relations:
        memory_parts.append("### Relations")
        for r in recalled_relations:
            memory_parts.append(f"- {r['subject']} --[{r['predicate']}]--> {r['object']}")
    if recalled_habits:
        memory_parts.append("### Habits")
        for h in recalled_habits:
            memory_parts.append(f"- [{h['domain']}] {h['pattern']} (certainty {h['certainty']:.2f})")
    if memory_parts:
        memory_text = "## Recalled Memory\n" + "\n".join(memory_parts)
        components.append(PromptComponent("memory", memory_text, priority=4))
    # Token budget - enforce_system_prompt returns (text, evicted, total)
    budget = TokenBudget(system_limit=20000)
    final_prompt, evicted, total_tokens = budget.enforce_system_prompt(components)

    # 强制中文思考与回复
    final_prompt += "\n\n## Language Rule\n无论用户用什么语言，你的思考过程（thinking）和最终回复都必须使用中文。不要输出英文思考内容。"

    return final_prompt


if __name__ == "__main__":
    prompt = assemble_wake_prompt()
    print(prompt)
    print("\n" + "=" * 40)
    print(f"Total tokens: ~{len(prompt.split()) * 1.3:.0f}")
