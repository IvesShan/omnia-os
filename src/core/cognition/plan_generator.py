"""Plan Generator - Decomposes complex tasks into executable steps.

Part of the Cognitive Layer (Layer 4) in Omnia 2.0 architecture.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.logging_config import get_logger

logger = get_logger(__name__)


class StepStatus(str, Enum):
    """Status of a plan step."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepType(str, Enum):
    """Type of plan step."""
    TOOL_CALL = "tool_call"
    LLM_THINKING = "llm_thinking"
    DECISION = "decision"
    PARALLEL = "parallel"
    LOOP = "loop"


@dataclass
class PlanStep:
    """A single step in the execution plan."""
    step_id: int
    description: str
    step_type: StepType
    action: Dict[str, Any]  # Tool name, parameters, etc.
    dependencies: List[int] = field(default_factory=list)  # Step IDs that must complete first
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    estimated_time: Optional[float] = None  # seconds
    
    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "description": self.description,
            "step_type": self.step_type.value,
            "action": self.action,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "estimated_time": self.estimated_time
        }


@dataclass
class ExecutionPlan:
    """A complete execution plan for a complex task."""
    plan_id: str
    goal: str
    steps: List[PlanStep]
    created_at: datetime = field(default_factory=datetime.now)
    current_step: int = 0
    status: str = "created"  # created, running, completed, failed
    
    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at.isoformat(),
            "current_step": self.current_step,
            "status": self.status
        }
    
    def get_next_step(self) -> Optional[PlanStep]:
        """Get the next executable step."""
        for step in self.steps:
            if step.status == StepStatus.PENDING:
                # Check if all dependencies are met
                if all(
                    self.steps[dep_id].status in [StepStatus.SUCCESS, StepStatus.SKIPPED]
                    for dep_id in step.dependencies
                ):
                    return step
        return None
    
    def get_progress(self) -> Tuple[int, int, float]:
        """Get progress: (completed_steps, total_steps, percentage)."""
        completed = sum(
            1 for s in self.steps
            if s.status in [StepStatus.SUCCESS, StepStatus.SKIPPED]
        )
        total = len(self.steps)
        percentage = (completed / total * 100) if total > 0 else 0
        return completed, total, percentage


class PlanGenerator:
    """
    Decomposes complex tasks into executable plans.
    
    Features:
    - Task complexity analysis
    - Step decomposition
    - Dependency management
    - Parallel execution opportunities
    - Error recovery strategies
    """
    
    def __init__(self, llm_client=None, tool_registry=None):
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self._plan_counter = 0
    
    def _generate_plan_id(self) -> str:
        """Generate a unique plan ID."""
        self._plan_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"plan_{timestamp}_{self._plan_counter}"
    
    def analyze_complexity(self, task: str) -> Dict[str, Any]:
        """
        Analyze task complexity to determine if planning is needed.
        
        Returns:
            {
                "complexity": "simple" | "medium" | "complex",
                "estimated_steps": int,
                "requires_planning": bool,
                "suggested_approach": str
            }
        """
        task_lower = task.lower()
        
        # Simple heuristics for complexity detection
        simple_indicators = [
            "读取", "查看", "显示", "获取", "列出",  # Single operations
            "what is", "show me", "get", "list", "read"
        ]
        
        medium_indicators = [
            "然后", "之后", "并且", "同时",  # Sequential or parallel
            "then", "after", "and", "also"
        ]
        
        complex_indicators = [
            "分析", "比较", "评估", "优化", "设计",  # Multi-step reasoning
            "如果", "否则", "根据", "条件",  # Conditional logic
            "循环", "重复", "遍历",  # Iteration
            "analyze", "compare", "evaluate", "optimize", "design",
            "if", "else", "when", "condition",
            "loop", "repeat", "iterate"
        ]
        
        simple_count = sum(1 for ind in simple_indicators if ind in task_lower)
        medium_count = sum(1 for ind in medium_indicators if ind in task_lower)
        complex_count = sum(1 for ind in complex_indicators if ind in task_lower)
        
        # Determine complexity
        if complex_count >= 2 or (complex_count >= 1 and medium_count >= 1):
            complexity = "complex"
            estimated_steps = 5 + complex_count * 2
            requires_planning = True
            suggested_approach = "multi_stage_with_branching"
        elif complex_count >= 1 or medium_count >= 2:
            complexity = "medium"
            estimated_steps = 3 + medium_count
            requires_planning = True
            suggested_approach = "sequential_with_checkpoints"
        else:
            complexity = "simple"
            estimated_steps = 1
            requires_planning = False
            suggested_approach = "direct_execution"
        
        return {
            "complexity": complexity,
            "estimated_steps": estimated_steps,
            "requires_planning": requires_planning,
            "suggested_approach": suggested_approach,
            "indicators": {
                "simple": simple_count,
                "medium": medium_count,
                "complex": complex_count
            }
        }
    
    async def generate_plan(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionPlan:
        """
        Generate an execution plan for a complex task.
        
        Args:
            task: The task description
            context: Additional context (available tools, user preferences, etc.)
            
        Returns:
            ExecutionPlan with decomposed steps
        """
        plan_id = self._generate_plan_id()
        
        # Analyze task
        complexity = self.analyze_complexity(task)
        
        # Generate steps based on complexity
        if complexity["complexity"] == "simple":
            # Direct execution
            steps = [
                PlanStep(
                    step_id=0,
                    description=f"Execute: {task}",
                    step_type=StepType.TOOL_CALL,
                    action={"task": task}
                )
            ]
        
        elif complexity["complexity"] == "medium":
            # Sequential steps
            steps = await self._generate_sequential_steps(task, context)
        
        else:
            # Complex: use LLM to decompose
            steps = await self._generate_complex_steps(task, context)
        
        plan = ExecutionPlan(
            plan_id=plan_id,
            goal=task,
            steps=steps
        )
        
        logger.info(f"[PlanGenerator] Generated plan {plan_id} with {len(steps)} steps")
        return plan
    
    async def _generate_sequential_steps(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[PlanStep]:
        """Generate sequential steps for medium complexity tasks."""
        # Simple rule-based decomposition
        steps = []
        
        # Step 1: Understand/Analyze
        steps.append(PlanStep(
            step_id=0,
            description="Understand the task requirements",
            step_type=StepType.LLM_THINKING,
            action={"prompt": f"Analyze this task and identify key requirements: {task}"}
        ))
        
        # Step 2: Gather information (if needed)
        if any(word in task.lower() for word in ["文件", "数据", "信息", "file", "data", "info"]):
            steps.append(PlanStep(
                step_id=1,
                description="Gather necessary information",
                step_type=StepType.TOOL_CALL,
                action={"operation": "gather_info"},
                dependencies=[0]
            ))
        
        # Step 3: Execute main action
        steps.append(PlanStep(
            step_id=len(steps),
            description="Execute main action",
            step_type=StepType.TOOL_CALL,
            action={"task": task},
            dependencies=[len(steps) - 1]
        ))
        
        # Step 4: Verify result
        steps.append(PlanStep(
            step_id=len(steps),
            description="Verify execution result",
            step_type=StepType.DECISION,
            action={"check": "success"},
            dependencies=[len(steps) - 1]
        ))
        
        return steps
    
    async def _generate_complex_steps(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[PlanStep]:
        """Generate complex steps with branching and parallelization."""
        # Use LLM to decompose complex tasks
        if self.llm_client is None:
            # Fallback to rule-based
            logger.warning("[PlanGenerator] No LLM client, using rule-based decomposition")
            return await self._generate_sequential_steps(task, context)
        
        try:
            prompt = f"""Decompose this complex task into executable steps:

Task: {task}

Available tools: {context.get('tools', []) if context else 'various'}

Output a JSON array of steps:
[
  {{
    "step_id": 0,
    "description": "...",
    "type": "tool_call|llm_thinking|decision",
    "action": {{"...": "..."}},
    "dependencies": []
  }}
]

Requirements:
1. Each step should be atomic and clear
2. Specify dependencies between steps
3. Identify opportunities for parallel execution
4. Include decision points for conditional logic
"""
            
            # Call LLM
            response = await self.llm_client.chat(prompt)
            
            # Parse response
            steps_data = json.loads(response)
            
            steps = []
            for step_dict in steps_data:
                steps.append(PlanStep(
                    step_id=step_dict["step_id"],
                    description=step_dict["description"],
                    step_type=StepType(step_dict.get("type", "tool_call")),
                    action=step_dict["action"],
                    dependencies=step_dict.get("dependencies", [])
                ))
            
            return steps
            
        except Exception as e:
            logger.error(f"[PlanGenerator] LLM decomposition failed: {e}")
            # Fallback to sequential
            return await self._generate_sequential_steps(task, context)
    
    def optimize_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Optimize a plan for parallel execution.
        
        Identifies steps that can run in parallel and groups them.
        """
        # Build dependency graph
        dependency_graph = {}
        for step in plan.steps:
            dependency_graph[step.step_id] = set(step.dependencies)
        
        # Find parallel opportunities
        # Steps with same dependencies can potentially run in parallel
        parallel_groups = []
        processed = set()
        
        for step in plan.steps:
            if step.step_id in processed:
                continue
            
            # Find all steps with same dependencies
            same_deps = [
                s for s in plan.steps
                if set(s.dependencies) == set(step.dependencies) and s.step_id not in processed
            ]
            
            if len(same_deps) > 1:
                # These can run in parallel
                parallel_groups.append([s.step_id for s in same_deps])
                processed.update(s.step_id for s in same_deps)
            else:
                processed.add(step.step_id)
        
        # Create parallel steps if found
        if parallel_groups:
            logger.info(f"[PlanGenerator] Found {len(parallel_groups)} parallel opportunities")
            # Could create PARALLEL type steps here
        
        return plan
    
    def estimate_execution_time(self, plan: ExecutionPlan) -> float:
        """Estimate total execution time in seconds."""
        # Simple estimation based on step types
        time_estimates = {
            StepType.TOOL_CALL: 2.0,  # Average tool call
            StepType.LLM_THINKING: 5.0,  # LLM thinking
            StepType.DECISION: 0.5,  # Quick decision
            StepType.PARALLEL: 3.0,  # Parallel execution
            StepType.LOOP: 10.0  # Loop (conservative)
        }
        
        # For sequential execution, sum all times
        total = sum(
            time_estimates.get(step.step_type, 2.0)
            for step in plan.steps
        )
        
        # For parallel execution, would be less
        # This is a simple estimation; real implementation would analyze dependencies
        
        return total


# Export
__all__ = ["PlanGenerator", "ExecutionPlan", "PlanStep", "StepStatus", "StepType"]
