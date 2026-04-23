"""PlanExecutor — Multi-step autonomous task orchestration for Omnia.

Takes a high-level goal, breaks it into steps, and executes each step
by calling tools iteratively until the task is complete or a max loop
is reached.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .tool_registry import TOOLS_SCHEMA, check_tool_safety, dispatch_tool
from ..cognition.context_compressor import ContextCompressor
from omnia.chat import _call_model_messages

_compressor = ContextCompressor()


class ConfirmationRequired(Exception):
    def __init__(self, tool_name: str, tool_args: dict, reason: str, plan: ExecutionPlan, current_step_index: int):
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.reason = reason
        self.plan = plan
        self.current_step_index = current_step_index


@dataclass
class Step:
    id: int
    description: str
    tool_name: str
    tool_args: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    status: str = "pending"  # pending | running | done | error
    observation: str = ""


@dataclass
class ExecutionPlan:
    goal: str
    steps: List[Step]
    context: str = ""


def _extract_json_block(text: str) -> Optional[str]:
    # Try fenced code block
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        return m.group(1).strip()
    # Try raw JSON array
    start = text.find("[")
    if start != -1:
        end = text.rfind("]")
        if end != -1:
            return text[start : end + 1].strip()
    return None


def _parse_steps_from_text(text: str) -> List[Step]:
    raw = _extract_json_block(text)
    if not raw:
        return []
    try:
        arr = json.loads(raw)
        if not isinstance(arr, list):
            return []
        steps = []
        for i, item in enumerate(arr):
            if not isinstance(item, dict):
                # 处理简化格式："read_file(/path/to/file)"
                if isinstance(item, str):
                    match = re.match(r'(\w+)\(([^"]*)\)', item)
                    if match:
                        tool_name = match.group(1)
                        arg_str = match.group(2)
                        # 解析参数
                        if '=' in arg_str:
                            args = {}
                            for part in arg_str.split(','):
                                if '=' in part:
                                    k, v = part.split('=', 1)
                                    args[k.strip()] = v.strip().strip('"\'')
                        else:
                            # 单参数，根据工具名称决定参数名
                            arg_value = arg_str.strip('"\'')
                            if tool_name in ('execute_shell',):
                                args = {"command": arg_value}
                            elif tool_name in ('web_search',):
                                args = {"query": arg_value}
                            else:
                                args = {"path": arg_value}
                        steps.append(Step(
                            id=i + 1,
                            description=f"Execute {tool_name}",
                            tool_name=tool_name,
                            tool_args=args,
                        ))
                continue
            # 标准格式
            desc = item.get("description") or item.get("desc") or item.get("thought") or f"Step {i+1}"
            tool = item.get("tool") or item.get("action") or item.get("name") or "execute_shell"
            # 尝试获取 arguments 或 args 或 parameters 或 params
            args = item.get("arguments") or item.get("args") or item.get("parameters") or item.get("params") or item.get("arguments") or {}
            # 如果没有 arguments/args，检查是否有顶层参数字段
            if not args:
                # 常见的参数名：path, command, query, content
                known_args = ["path", "command", "query", "content", "url"]
                for arg_name in known_args:
                    if arg_name in item:
                        args = {arg_name: item[arg_name]}
                        break
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except:
                    args = {"command": args}
            steps.append(
                Step(
                    id=i + 1,
                    description=desc,
                    tool_name=tool,
                    tool_args=args,
                )
            )
        return steps
    except (json.JSONDecodeError, TypeError) as e:
        print(f"[_parse_steps_from_text] JSON parse error: {e}")
        print(f"[_parse_steps_from_text] Raw text: {raw[:200]}")
        return []


class PlanExecutor:
    """Generates and runs execution plans using available tools."""

    PLAN_PROMPT = """User goal: {{{goal}}}

Available tools:
- read_file(path) - Read file contents
- write_file(path, content) - Write to file
- execute_shell(command) - Run shell command
- list_directory(path) - List directory contents
- web_search(query) - Search the web
- query_memory(query, layer) - Query your memory palace for past conversations, facts, and user preferences

Project paths:
- Omnia: /home/shan//home/shan/omnia-os/omnia-os
- Workspace: /home/shan//home/shan/omnia-os
- Daemon: scripts/start_daemon.py

Your memory system:
- Memory Palace database: .omnia/memory_palace.db (600+ records)
- Layers: facts, relations, habits, timeline
- Use query_memory with simple keywords ("OpenClaw", "user", "project name")
- Don't use complex sentences as search query
- You HAVE memories, just search and you'll find them!

Important: If you say "让我翻翻/看看/查查", you MUST call a tool. Never say these phrases without actually doing it.

Use tools when needed to accomplish the goal.
"""

    REFLECT_PROMPT = """你是 Omnia，一个有性格的 AI 助手。用户问：{goal}

你执行了一些操作来帮助回答这个问题：

{steps_text}

现在用自然的语言回答用户的问题。

重要规则：
- 直接回答问题，像在和朋友聊天
- 如果找到了记忆，告诉用户具体内容
- 如果没找到，诚实地说没找到，并建议下一步
- 不要提及「工具」、「步骤」、「执行」等技术细节
- 不要输出 JSON 或代码块
- 用中文，简洁有力
- 可以有观点、有态度
- 列表格式：用 1. 2. 3. 不要用 1.1.1. 这种嵌套格式

如果用户问的是比较类问题（比如「哪个更好」），给出你的看法和理由。
"""

    def __init__(self, api_key: str, provider: str = "kimi"):
        self.api_key = api_key
        self.provider = provider

    def plan(self, goal: str, context: str = "") -> ExecutionPlan:
        prompt = self.PLAN_PROMPT.format(goal=goal, context=context or "None")
        print(f"[PlanExecutor.plan] Goal: {goal}")
        data = _call_model_messages(
            self.api_key,
            self.provider,
            [{"role": "user", "content": prompt}],
            tools=TOOLS_SCHEMA,  # 传递工具定义，让模型通过 tool_calls 返回
        )
        
        # 检查模型是否通过 tool_calls 返回
        msg = data["choices"][0]["message"]
        tool_calls = msg.get("tool_calls") or []
        
        print(f"[PlanExecutor.plan] Message keys: {msg.keys()}")
        print(f"[PlanExecutor.plan] Has tool_calls: {len(tool_calls) > 0}")
        
        if tool_calls:
            # 模型正确使用了 tool_calls API
            print(f"[PlanExecutor.plan] Model returned {len(tool_calls)} tool_calls via API")
            steps = []
            for i, tc in enumerate(tool_calls):
                fn = tc.get("function", {})
                tool_name = fn.get("name", "execute_shell")
                try:
                    args = json.loads(fn.get("arguments", "{}"))
                except:
                    args = {}
                print(f"[PlanExecutor.plan] Tool: {tool_name}, Args: {args}")
                steps.append(Step(
                    id=i + 1,
                    description=f"Execute {tool_name}",
                    tool_name=tool_name,
                    tool_args=args,
                ))
            if steps:
                return ExecutionPlan(goal=goal, steps=steps, context=context)
        
        # Fallback: 从文本中解析
        text = msg.get("content", "")
        print(f"[PlanExecutor.plan] Model response: {text[:300]}...")
        steps = _parse_steps_from_text(text)
        print(f"[PlanExecutor.plan] Parsed {len(steps)} steps")
        if not steps:
            # Fallback: return an empty plan so the caller can route to normal chat instead
            return ExecutionPlan(goal=goal, steps=[], context=context)
        return ExecutionPlan(goal=goal, steps=steps, context=context)

    def _capture_observation(self, result: Dict[str, Any]) -> str:
        raw = ""
        if "content" in result:
            raw = str(result["content"])
        elif "stdout" in result:
            raw = str(result["stdout"])
        elif "results" in result:
            # For query_memory and similar tools that return results array
            raw = json.dumps(result["results"], ensure_ascii=False, indent=2)
        elif "result" in result:
            raw = str(result["result"])
        else:
            raw = json.dumps(result, ensure_ascii=False)
        # Compress if oversized (>1500 chars is roughly ~400-500 tokens in CJK)
        if len(raw) > 1500:
            raw = _compressor.compress(raw).summary
        # Hard ceiling after compression
        return raw[:1200]

    def execute(self, plan: ExecutionPlan) -> Dict[str, Any]:
        for i, step in enumerate(plan.steps):
            safety = check_tool_safety(step.tool_name, step.tool_args)
            if safety.requires_confirm:
                raise ConfirmationRequired(
                    tool_name=step.tool_name,
                    tool_args=step.tool_args,
                    reason=safety.reason,
                    plan=plan,
                    current_step_index=i,
                )
            step.status = "running"
            result = dispatch_tool(step.tool_name, step.tool_args)
            step.result = result
            if result.get("error"):
                step.status = "error"
                step.observation = f"Error: {result['error']}"
            else:
                step.status = "done"
                step.observation = self._capture_observation(result)
        return self._synthesize(plan)

    def resume_from_step(self, plan: ExecutionPlan, start_index: int) -> Dict[str, Any]:
        """Continue executing a plan from a specific step (after confirmation)."""
        for i in range(start_index, len(plan.steps)):
            step = plan.steps[i]
            step.status = "running"
            result = dispatch_tool(step.tool_name, step.tool_args)
            step.result = result
            if result.get("error"):
                step.status = "error"
                step.observation = f"Error: {result['error']}"
            else:
                step.status = "done"
                step.observation = self._capture_observation(result)
        return self._synthesize(plan)

    def _synthesize(self, plan: ExecutionPlan) -> Dict[str, Any]:
        steps_text = "\n\n".join(
            f"Step {s.id}: {s.description}\nTool: {s.tool_name}\nStatus: {s.status}\nResult:\n{s.observation}"
            for s in plan.steps
        )
        prompt = self.REFLECT_PROMPT.format(goal=plan.goal, steps_text=steps_text)
        try:
            # 不传 tools 参数，强制模型直接回答而不是调用工具
            data = _call_model_messages(
                self.api_key,
                self.provider,
                [{"role": "user", "content": prompt}],
                tools=None,  # 不允许工具调用
            )
            reply = data["choices"][0]["message"]["content"]
            
            # 清理千帆模型可能返回的工具调用格式
            import re
            
            # 检测是否包含工具调用格式
            has_tool_call = (
                '```tool_calls' in reply or 
                'tool_calls' in reply or
                '<tool_call' in reply or
                '```<tool_call' in reply or
                re.search(r'\w+\(\{"path"', reply) or  # list_directory({"path": ...}) 格式
                re.search(r'\w+\(\{"command"', reply) or  # execute_shell({"command": ...}) 格式
                re.search(r'\w+\(\{"query"', reply)  # web_search({"query": ...}) 格式
            )
            
            if has_tool_call:
                # 简单策略：找到工具调用格式的起始位置，截取之前的内容
                # 常见的工具调用格式起始标记
                markers = ['```tool_calls', '```\n', '```', '\nlist_directory', '\nread_file', '\nexecute_shell', '\nweb_search', '\nwrite_file']
                first_pos = len(reply)  # 默认到末尾
                for marker in markers:
                    pos = reply.find(marker)
                    if pos != -1 and pos < first_pos:
                        first_pos = pos
                
                if first_pos < len(reply):
                    extracted = reply[:first_pos].strip()
                    if extracted:
                        reply = extracted
                    else:
                        # 如果没有自然语言前缀，基于步骤生成总结
                        if plan.steps:
                            reply = f"我看了相关的信息。{plan.goal}"
                        else:
                            reply = "让我直接回答你的问题。"
                elif plan.steps:
                    reply = f"我看了相关的信息。{plan.goal}"
                else:
                    reply = "让我直接回答你的问题。"
            
            reply = reply.strip()
        except Exception as e:
            # Fallback: compose a raw summary so the user still gets value
            err_str = str(e)
            if "content_filter" in err_str.lower() or "high risk" in err_str.lower():
                lines = [f"我已经执行了相关操作，但自然语言总结被安全策略拦截。以下是原始结果："]
                for s in plan.steps:
                    lines.append(f"\n【{s.description}】")
                    lines.append(s.observation[:600])
                reply = "\n".join(lines)
            else:
                reply = f"[任务执行完成，但总结阶段出错: {e}]"
        return {
            "reply": reply,
            "steps": [
                {
                    "id": s.id,
                    "description": s.description,
                    "tool": s.tool_name,
                    "arguments": s.tool_args,
                    "status": s.status,
                    "result_summary": s.observation[:200],
                }
                for s in plan.steps
            ],
        }

    def run(self, goal: str, context: str = "") -> Dict[str, Any]:
        plan = self.plan(goal, context)
        return self.execute(plan)
