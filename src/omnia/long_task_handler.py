"""LongTaskHandler — 长任务处理器

集成 PlanExecutor + PlanStore + 流式输出
支持：
- 任务自动分解
- 状态持久化
- 断点续传
- 进度实时反馈
"""

from __future__ import annotations

import json
import uuid
from typing import Generator, Dict, Any, List
from dataclasses import dataclass

from core.actuator.plan_store import PlanStore, Plan, Step, StepStatus, get_plan_store
from core.actuator.tool_registry import dispatch_tool
from omnia.smart_pauser import SmartPauser, get_pauser, PauseReason


@dataclass
class TaskProgress:
    """任务进度"""
    plan_id: str
    goal: str
    total_steps: int
    completed_steps: int
    current_step: str
    status: str  # running, paused, completed, failed
    percentage: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "current_step": self.current_step,
            "status": self.status,
            "percentage": round(self.percentage, 1),
        }


class LongTaskHandler:
    """长任务处理器"""
    
    def __init__(self, api_key: str, provider: str):
        self.api_key = api_key
        self.provider = provider
        self.store = get_plan_store()
        self.pauser = get_pauser()
        self.current_plan: Plan = None
    
    def analyze_task_complexity(self, message: str) -> Dict[str, Any]:
        """分析任务复杂度，决定是否需要分解"""
        import re
        
        # 统计任务步骤数 - 更智能的识别
        # 1. 数字编号格式：1) 2) 3) 或 1. 2. 3.
        numbered_steps = len(re.findall(r'\d[)\.]\s*', message))
        
        # 2. 分隔符：和、然后、接着、之后、再
        separator_steps = message.count("和") + message.count("然后") + message.count("接着") + message.count("之后")
        
        # 3. 动词数量（读取、列出、执行、显示等）
        action_verbs = ["读取", "列出", "执行", "显示", "查看", "检查", "分析", "生成", "发送", "创建", "删除", "修改", "搜索", "下载", "上传"]
        action_count = sum(1 for verb in action_verbs if verb in message)
        
        # 取最大值
        estimated_steps = max(numbered_steps, separator_steps + 1, action_count)
        
        # 复杂关键词检测
        complex_keywords = [
            "同时", "然后", "接着", "之后", "完成", "全部", "所有",
            "批量", "多个", "一系列", "逐步", "按顺序", "依次",
            "分析", "整理", "汇总", "生成报告", "完整"
        ]
        
        is_complex = any(kw in message for kw in complex_keywords) or estimated_steps > 3
        
        # 长任务阈值：预估步骤超过 5 步就使用长任务处理器
        should_decompose = estimated_steps > 5 or is_complex
        
        return {
            "is_complex": is_complex,
            "estimated_steps": estimated_steps,
            "should_decompose": should_decompose,
            "numbered_steps": numbered_steps,
            "action_count": action_count,
        }
    
    def create_plan(self, goal: str, steps: List[Dict]) -> Plan:
        """创建执行计划"""
        plan_id = uuid.uuid4().hex[:8]
        
        plan_steps = []
        for idx, step_data in enumerate(steps):
            step = Step(
                id=f"{plan_id}_step_{idx}",
                description=step_data.get("description", ""),
                tool_name=step_data.get("tool_name", "unknown"),
                tool_args=step_data.get("tool_args", {}),
                status=StepStatus.PENDING.value,
                dependencies=step_data.get("dependencies", []),
            )
            plan_steps.append(step)
        
        plan = Plan(
            id=plan_id,
            goal=goal,
            steps=plan_steps,
        )
        
        return plan
    
    def generate_plan_with_llm(self, goal: str) -> Plan:
        """使用 LLM 生成执行计划"""
        from omnia.chat import _call_model_messages
        import traceback
        
        # 发送规划开始事件（让前端知道正在进行）
        print(f"[LongTaskHandler] 开始规划任务: {goal[:50]}...")
        
        prompt = f"""你是一个任务规划专家。请将以下目标分解为具体的执行步骤。

目标：{goal}

请以 JSON 格式返回步骤列表，每个步骤包含：
- description: 步骤描述
- tool_name: 要使用的工具（read_file, write_file, execute_shell, list_directory, web_search）
- tool_args: 工具参数
- dependencies: 依赖的步骤索引列表（可选）

返回格式示例：
{{
    "steps": [
        {{
            "description": "读取配置文件",
            "tool_name": "read_file",
            "tool_args": {{"path": "config.json"}},
            "dependencies": []
        }},
        {{
            "description": "根据配置执行命令",
            "tool_name": "execute_shell",
            "tool_args": {{"command": "..."}},
            "dependencies": [0]
        }}
    ]
}}

只返回 JSON，不要其他内容。"""

        messages = [
            {"role": "system", "content": "你是一个任务规划专家，擅长将复杂目标分解为可执行的步骤。"},
            {"role": "user", "content": prompt}
        ]
        
        try:
            data = _call_model_messages(self.api_key, self.provider, messages, tools=None)
            content = data["choices"][0]["message"].get("content", "")
            
            print(f"[LongTaskHandler] LLM 响应: {content[:200]}...")
            
            # 提取 JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                plan_data = json.loads(json_match.group())
                return self.create_plan(goal, plan_data.get("steps", []))
            else:
                print(f"[LongTaskHandler] 未找到 JSON，创建默认计划")
        except Exception as e:
            print(f"[LongTaskHandler] Plan generation failed: {e}")
            print(traceback.format_exc())
        
        # 降级：创建简单计划
        return self.create_plan(goal, [
            {"description": f"执行: {goal}", "tool_name": "execute_shell", "tool_args": {"command": f"echo 'Task: {goal}'"}}
        ])
    
    def execute_plan_stream(self, plan: Plan, session_id: str = None) -> Generator[str, None, None]:
        """流式执行计划，支持断点续传 + 智能暂停 + 进度可视化"""
        self.current_plan = plan
        
        # 保存初始计划
        self.store.save_plan(plan, session_id)
        
        # 发送计划开始事件
        yield f"data: {json.dumps({'type': 'plan_start', 'plan_id': plan.id, 'total_steps': len(plan.steps)})}\n\n"
        
        # 发送进度条初始化
        yield from self._emit_progress(plan, 0)
        
        # 从断点继续
        start_index = plan.current_step_index
        
        for idx in range(start_index, len(plan.steps)):
            step = plan.steps[idx]
            
            # 🔍 智能暂停检测（长任务默认不暂停，直接执行）
            # pause_context = self.pauser.should_pause(step.to_dict(), idx, len(plan.steps))
            # if pause_context:
            #     yield f"data: {json.dumps({'type': 'pause', 'context': pause_context.to_dict()})}\n\n"
            #     self.pauser.last_pause = pause_context
            #     return  # 暂停执行
            
            # 更新状态
            step.status = StepStatus.RUNNING.value
            plan.current_step_index = idx
            self.store.save_plan(plan, session_id)
            
            # 发送步骤开始事件
            yield f"data: {json.dumps({'type': 'step_start', 'step_index': idx, 'total_steps': len(plan.steps), 'description': step.description})}\n\n"
            
            # 发送进度更新
            yield from self._emit_progress(plan, idx)
            
            # 执行步骤
            try:
                result = dispatch_tool(step.tool_name, step.tool_args)
                step.status = StepStatus.COMPLETED.value
                step.result = result
                step.observation = str(result)[:500] if result else ""
                
                # 更新步骤状态
                self.store.update_step(plan.id, step.id, 
                    status=step.status, 
                    result=step.result, 
                    observation=step.observation
                )
                
                yield f"data: {json.dumps({'type': 'step_complete', 'step_index': idx, 'success': True, 'result_preview': step.observation[:200]})}\n\n"
                
            except Exception as e:
                step.status = StepStatus.FAILED.value
                step.observation = str(e)
                
                self.store.update_step(plan.id, step.id, 
                    status=step.status, 
                    observation=step.observation
                )
                
                yield f"data: {json.dumps({'type': 'step_failed', 'step_index': idx, 'error': str(e)})}\n\n"
                
                # 错误恢复：询问是否继续
                yield f"data: {json.dumps({'type': 'error_recovery', 'step_index': idx, 'message': f'步骤 {idx+1} 失败: {e}', 'options': [{'id': 'continue', 'label': '跳过继续'}, {'id': 'retry', 'label': '重试'}, {'id': 'abort', 'label': '中止任务'}]})}\n\n"
            
            plan.current_step_index = idx + 1
        
        # 标记完成
        self.store.mark_plan_completed(plan.id, "completed")
        
        # 发送完成进度
        yield from self._emit_progress(plan, len(plan.steps), completed=True)
        
        # 生成最终总结
        summary = self._generate_summary(plan)
        
        # 发送 plan_complete 事件
        yield f"data: {json.dumps({'type': 'plan_complete', 'plan_id': plan.id, 'summary': summary}, ensure_ascii=False)}\n\n"
        
        # 发送 done 事件（前端需要这个事件来结束流）
        yield f"data: {json.dumps({'type': 'done', 'full_content': summary}, ensure_ascii=False)}\n\n"
    
    def _emit_progress(self, plan: Plan, current_step: int, completed: bool = False) -> Generator[str, None, None]:
        """发送进度更新事件"""
        total = len(plan.steps)
        completed_steps = sum(1 for s in plan.steps[:current_step] if s.status == StepStatus.COMPLETED.value)
        percentage = (current_step / total * 100) if total > 0 else 0
        
        progress = TaskProgress(
            plan_id=plan.id,
            goal=plan.goal,
            total_steps=total,
            completed_steps=completed_steps,
            current_step=plan.steps[current_step].description if current_step < total else "已完成",
            status="completed" if completed else "running",
            percentage=percentage,
        )
        
        yield f"data: {json.dumps({'type': 'progress', 'progress': progress.to_dict()})}\n\n"
    
    def resume_plan(self, plan_id: str = None, session_id: str = None) -> Generator[str, None, None]:
        """恢复执行中断的计划"""
        plan = self.store.load_plan(plan_id, session_id)
        
        if not plan:
            yield f"data: {json.dumps({'type': 'error', 'message': 'No plan found to resume'})}\n\n"
            return
        
        yield f"data: {json.dumps({'type': 'plan_resume', 'plan_id': plan.id, 'current_step': plan.current_step_index})}\n\n"
        
        yield from self.execute_plan_stream(plan, session_id)
    
    def get_progress(self) -> TaskProgress:
        """获取当前进度"""
        if not self.current_plan:
            return None
        
        completed = sum(1 for s in self.current_plan.steps if s.status == StepStatus.COMPLETED.value)
        current = self.current_plan.steps[self.current_plan.current_step_index] if self.current_plan.current_step_index < len(self.current_plan.steps) else None
        
        return TaskProgress(
            plan_id=self.current_plan.id,
            goal=self.current_plan.goal,
            total_steps=len(self.current_plan.steps),
            completed_steps=completed,
            current_step=current.description if current else "completed",
            status="running" if self.current_plan.current_step_index < len(self.current_plan.steps) else "completed",
        )
    
    def _generate_summary(self, plan: Plan) -> str:
        """生成执行总结"""
        completed = sum(1 for s in plan.steps if s.status == StepStatus.COMPLETED.value)
        failed = sum(1 for s in plan.steps if s.status == StepStatus.FAILED.value)
        
        summary = f"任务完成: {plan.goal}\n"
        summary += f"总步骤: {len(plan.steps)}\n"
        summary += f"成功: {completed}, 失败: {failed}\n"
        
        if failed > 0:
            summary += "\n失败的步骤:\n"
            for s in plan.steps:
                if s.status == StepStatus.FAILED.value:
                    summary += f"  - {s.description}: {s.observation}\n"
        
        return summary


# 便捷函数
def handle_long_task_stream(
    message: str, 
    api_key: str, 
    provider: str,
    session_id: str = None
) -> Generator[str, None, None]:
    """处理长任务的入口函数"""
    handler = LongTaskHandler(api_key, provider)
    
    try:
        # 分析任务复杂度
        analysis = handler.analyze_task_complexity(message)
        
        yield f"data: {json.dumps({'type': 'analysis', 'complexity': analysis}, ensure_ascii=False)}\n\n"
        
        # 生成计划
        yield f"data: {json.dumps({'type': 'status', 'message': '📋 正在规划任务...'}, ensure_ascii=False)}\n\n"
        
        plan = handler.generate_plan_with_llm(message)
        
        if not plan or not plan.steps:
            yield f"data: {json.dumps({'type': 'error', 'message': '无法生成执行计划'}, ensure_ascii=False)}\n\n"
            return
        
        yield f"data: {json.dumps({'type': 'plan_created', 'plan_id': plan.id, 'steps': len(plan.steps)}, ensure_ascii=False)}\n\n"
        
        # 执行计划
        yield from handler.execute_plan_stream(plan, session_id)
        
    except Exception as e:
        import traceback
        error_msg = f"长任务执行失败: {str(e)}\n{traceback.format_exc()}"
        print(f"[LongTaskHandler] {error_msg}")
        yield f"data: {json.dumps({'type': 'error', 'message': error_msg}, ensure_ascii=False)}\n\n"
