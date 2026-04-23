# Omnia 工作记忆改进方案

> 解决「上下文截断导致失忆」问题
> 创建时间: 2026-04-20
> 状态: 待实施

---

## 问题诊断

### 症状
- Omnia 在长输出后「忘记」当前任务
- 需要用户重新解释上下文
- 记忆系统有数据，但模型当前看不到

### 根本原因

| 问题 | OpenClaw | Omnia 现状 |
|------|----------|-----------|
| **L1 强制注入** | `essential.md` 每次必载 | ❌ 无 |
| **当前任务状态** | `session_status` 实时维护 | ❌ 无 |
| **任务断点保存** | 写入文件系统 | ❌ 无 |
| **短期记忆优先** | 最近对话权重 ×3 | ❌ 无权重机制 |
| **主动确认** | 长输出前确认任务 | ❌ 无 |

---

## 解决方案：分层工作记忆

### 架构设计

```
memory/
├── working/              # 新增：工作记忆层（L1）
│   ├── essential.md      # 每次请求必载（关键上下文）
│   ├── current_task.md   # 当前任务状态（断点保存）
│   └── session_log.md    # 最近 5 轮对话摘要
├── palace/               # 现有：长期记忆（L3）
│   ├── facts.json
│   ├── relations.json
│   └── timeline.json
└── omnia.db             # 现有：SQLite 数据库
```

### 分层加载策略

| 层级 | 内容 | 加载时机 | 优先级 |
|------|------|----------|--------|
| **L0** | SOUL.md（Persona） | 每次请求必载 | 10 |
| **L1** | essential.md（工作记忆） | **每次请求必载** | **12** |
| **L2** | 项目索引（按需） | 相关时加载 | 5 |
| **L3** | 历史记忆（搜索） | 关键词召回 | 4 |

---

## 实施步骤

### 步骤 1: 创建工作记忆文件

已创建：
- ✅ `memory/working/essential.md`
- ✅ `memory/working/current_task.md`

### 步骤 2: 修改 `wake.py`

在 `assemble_wake_prompt()` 函数中增加 L1 加载：

```python
def _load_working_memory(project_root: Path) -> Optional[str]:
    """Load L1 working memory (essential.md)."""
    essential_path = project_root / "memory" / "working" / "essential.md"
    if not essential_path.exists():
        return None
    
    content = essential_path.read_text(encoding="utf-8")
    # 截断到前 1000 字符，避免 token 膨胀
    if len(content) > 1000:
        content = content[:1000] + "\n... (truncated)"
    return content

def _load_current_task(project_root: Path) -> Optional[str]:
    """Load current task state."""
    task_path = project_root / "memory" / "working" / "current_task.md"
    if not task_path.exists():
        return None
    
    content = task_path.read_text(encoding="utf-8")
    # 只加载有活跃任务的部分
    if "**任务 ID**: -" in content:
        return None  # 无活跃任务
    return content
```

在 `assemble_wake_prompt()` 中添加组件：

```python
# 在 Persona 组件后添加（优先级 12）
working_memory = _load_working_memory(project_root)
if working_memory:
    components.append(PromptComponent(
        "working_memory",
        "## Essential Context (L1)\n\n" + working_memory,
        priority=12  # 高于 Persona
    ))

current_task = _load_current_task(project_root)
if current_task:
    components.append(PromptComponent(
        "current_task",
        "## Current Task State\n\n" + current_task,
        priority=11  # 仅次于 essential
    ))
```

### 步骤 3: 创建任务状态管理器

创建 `src/core/working_memory/task_manager.py`：

```python
"""Task State Manager - 维护当前任务状态"""

from pathlib import Path
from datetime import datetime
from typing import List, Optional

class TaskManager:
    """管理当前任务状态，支持断点续传"""
    
    def __init__(self, working_dir: Path):
        self.task_file = working_dir / "current_task.md"
        self.essential_file = working_dir / "essential.md"
    
    def start_task(self, task_id: str, description: str, steps: List[str]):
        """开始新任务"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"""# Current Task - 当前任务状态

## 活跃任务

**任务 ID**: {task_id}
**描述**: {description}
**创建时间**: {now}
**最后更新**: {now}

## 已完成步骤

- [ ] (暂无)

## 待完成步骤

{chr(10).join(f"- [ ] {step}" for step in steps)}

## 阻塞项

**阻塞原因**: -
**需要用户输入**: 否
**等待中**: -

---

*此文件会在任务开始、进度更新、任务完成时自动更新*
"""
        self.task_file.write_text(content, encoding="utf-8")
        self._update_essential_task(task_id, description)
    
    def update_progress(self, step_index: int, completed: bool = True):
        """更新任务进度"""
        if not self.task_file.exists():
            return
        
        content = self.task_file.read_text(encoding="utf-8")
        lines = content.split("\n")
        
        # 更新时间戳
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for i, line in enumerate(lines):
            if "**最后更新**:" in line:
                lines[i] = f"**最后更新**: {now}"
        
        # 更新步骤状态（简化版）
        # TODO: 实现更精确的步骤更新
        
        self.task_file.write_text("\n".join(lines), encoding="utf-8")
    
    def complete_task(self):
        """完成任务"""
        content = self.task_file.read_text(encoding="utf-8")
        # 重置为空闲状态
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
        self.task_file.write_text(template, encoding="utf-8")
        self._update_essential_task("-", "空闲")
    
    def _update_essential_task(self, task_id: str, description: str):
        """更新 essential.md 中的任务状态"""
        if not self.essential_file.exists():
            return
        
        content = self.essential_file.read_text(encoding="utf-8")
        lines = content.split("\n")
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        in_task_section = False
        
        for i, line in enumerate(lines):
            if "## 当前任务" in line:
                in_task_section = True
            elif in_task_section and line.startswith("## "):
                in_task_section = False
            elif in_task_section:
                if "**状态**:" in line:
                    lines[i] = f"**状态**: {'执行中' if task_id != '-' else '空闲'}"
                elif "**任务**:" in line:
                    lines[i] = f"**任务**: {description}"
                elif "**开始时间**:" in line:
                    lines[i] = f"**开始时间**: {now if task_id != '-' else '-'}"
                elif "**进度**:" in line:
                    lines[i] = f"**进度**: 0%"
        
        # 更新最后更新时间
        for i, line in enumerate(lines):
            if "*最后更新:" in line:
                lines[i] = f"*最后更新: {now}*"
        
        self.essential_file.write_text("\n".join(lines), encoding="utf-8")
```

### 步骤 4: 集成到对话流程

在 `chat.py` 中集成：

```python
from core.working_memory.task_manager import TaskManager

# 在长输出前检查
def _check_long_output(message: str, estimated_tokens: int = 2000):
    """长输出前主动确认"""
    if estimated_tokens > 2000:
        # 加载当前任务
        task_manager = TaskManager(...)
        # 如果有活跃任务，确认是否继续
        # ...
```

---

## 使用示例

### 场景 1: 长任务执行

**用户**: "帮我部署 Gemma 模型到 RX 6800"

**Omnia**:
1. 创建任务状态：
   ```python
   task_manager.start_task(
       task_id="deploy-gemma-20260420",
       description="部署 Gemma-4-26B-AWQ 到 RX 6800",
       steps=["安装 ROCm", "安装 vLLM", "下载模型", "启动 API"]
   )
   ```

2. `essential.md` 自动更新：
   ```markdown
   ## 当前任务
   **状态**: 执行中
   **任务**: 部署 Gemma-4-26B-AWQ 到 RX 6800
   **开始时间**: 2026-04-20 14:30:00
   **进度**: 0%
   ```

3. 即使上下文截断，下次请求也能看到任务状态

### 场景 2: 上下文截断后恢复

**用户**: "继续"

**Omnia**:
- 从 `essential.md` 看到：当前任务 = 部署 Gemma
- 从 `current_task.md` 看到：已完成步骤 1，阻塞在 sudo 密码
- 无需用户重新解释，直接继续

---

## 预期效果

| 指标 | 改进前 | 改进后 |
|------|--------|--------|
| **长任务成功率** | ~30% | ~90% |
| **用户重复解释次数** | 2-3 次 | 0 次 |
| **上下文截断恢复时间** | 5-10 分钟 | < 10 秒 |
| **记忆召回准确率** | ~50% | ~85% |

---

## 下一步

1. ✅ 创建工作记忆文件
2. ⏳ 修改 `wake.py` 增加 L1 加载
3. ⏳ 创建 `TaskManager` 类
4. ⏳ 集成到对话流程
5. ⏳ 测试长任务场景

---

*此方案基于 OpenClaw 的分层记忆架构，适配 Omnia 的现有系统*
