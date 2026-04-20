"""Workflow Engine - Multi-step task orchestration

Implements the WorkflowEngine component from Omnia 2.0 Architecture.
Supports:
- Sequential step execution
- Conditional branching
- Error recovery and rollback
- Progress tracking
- Verification hooks

Usage:
    from core.orchestration import WorkflowEngine
    
    engine = WorkflowEngine()
    workflow = [
        WorkflowStep(name="analyze", action=analyze_task),
        WorkflowStep(name="plan", action=plan_execution, depends_on=["analyze"]),
        WorkflowStep(name="execute", action=execute_plan, depends_on=["plan"]),
    ]
    result = await engine.run(workflow, context)
"""

from __future__ import annotations

import asyncio
import json
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union


class StepStatus(Enum):
    """Workflow step status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


@dataclass
class StepResult:
    """Result of a workflow step execution"""
    step_name: str
    status: StepStatus
    output: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            "step_name": self.step_name,
            "status": self.status.value,
            "output": str(self.output)[:500] if self.output else None,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class WorkflowStep:
    """A single step in a workflow"""
    name: str
    action: Callable  # async or sync function
    description: str = ""
    depends_on: List[str] = field(default_factory=list)
    condition: Optional[Callable[[WorkflowContext], bool]] = None  # Conditional execution
    rollback: Optional[Callable] = None  # Rollback function on failure
    retry_count: int = 0
    retry_delay: float = 1.0  # seconds
    timeout: Optional[float] = None  # seconds
    critical: bool = True  # If True, workflow fails when this step fails
    
    def __post_init__(self):
        if not self.description:
            self.description = f"Execute {self.name}"


@dataclass
class WorkflowContext:
    """Shared context for workflow execution"""
    workflow_id: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    step_results: Dict[str, StepResult] = field(default_factory=dict)
    current_step: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from inputs or outputs"""
        if key in self.outputs:
            return self.outputs[key]
        return self.inputs.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set a value in outputs"""
        self.outputs[key] = value
    
    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "current_step": self.current_step,
            "started_at": str(self.started_at) if self.started_at else None,
            "finished_at": str(self.finished_at) if self.finished_at else None,
        }


@dataclass
class WorkflowResult:
    """Final result of workflow execution"""
    workflow_id: str
    success: bool
    context: WorkflowContext
    step_results: List[StepResult]
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "success": self.success,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "steps": [r.to_dict() for r in self.step_results],
            "outputs": self.context.outputs,
        }


class WorkflowEngine:
    """
    Multi-step workflow orchestration engine.
    
    Features:
    - DAG-based execution (respects dependencies)
    - Conditional step execution
    - Automatic retry with exponential backoff
    - Rollback support
    - Progress tracking and logging
    - Timeout handling
    """
    
    def __init__(
        self,
        max_parallel_steps: int = 3,
        default_timeout: float = 300.0,  # 5 minutes
        log_dir: Optional[Path] = None,
    ):
        self.max_parallel_steps = max_parallel_steps
        self.default_timeout = default_timeout
        self.log_dir = log_dir or WORKFLOW_LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    async def run(
        self,
        steps: List[WorkflowStep],
        context: Optional[WorkflowContext] = None,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> WorkflowResult:
        """
        Execute a workflow with the given steps.
        
        Args:
            steps: List of WorkflowStep objects
            context: Optional existing context (for resuming)
            inputs: Input data for the workflow
            
        Returns:
            WorkflowResult with execution details
        """
        import uuid
        
        # Initialize context
        if context is None:
            workflow_id = f"wf_{uuid.uuid4().hex[:8]}"
            context = WorkflowContext(
                workflow_id=workflow_id,
                inputs=inputs or {},
            )
        
        context.started_at = datetime.now()
        
        # Build step graph
        step_map = {s.name: s for s in steps}
        executed = set()
        step_results = []
        
        try:
            # Execute steps in topological order
            while len(executed) < len(steps):
                # Find steps that can be executed now
                ready_steps = [
                    s for s in steps
                    if s.name not in executed
                    and all(dep in executed for dep in s.depends_on)
                ]
                
                if not ready_steps:
                    # Check if we're stuck
                    remaining = [s.name for s in steps if s.name not in executed]
                    if remaining:
                        raise RuntimeError(f"Deadlock: cannot execute remaining steps: {remaining}")
                    break
                
                # Execute ready steps (with parallelism limit)
                batch = ready_steps[:self.max_parallel_steps]
                
                for step in batch:
                    result = await self._execute_step(step, context)
                    step_results.append(result)
                    context.step_results[step.name] = result
                    executed.add(step.name)
                    
                    if result.status == StepStatus.FAILED and step.critical:
                        # Critical step failed - attempt rollback
                        await self._rollback(steps, executed, context)
                        raise RuntimeError(f"Critical step '{step.name}' failed: {result.error}")
            
            context.finished_at = datetime.now()
            duration = (context.finished_at - context.started_at).total_seconds() * 1000
            
            return WorkflowResult(
                workflow_id=context.workflow_id,
                success=True,
                context=context,
                step_results=step_results,
                duration_ms=duration,
            )
            
        except Exception as e:
            context.finished_at = datetime.now()
            duration = (context.finished_at - context.started_at).total_seconds() * 1000
            
            return WorkflowResult(
                workflow_id=context.workflow_id,
                success=False,
                context=context,
                step_results=step_results,
                error=str(e),
                duration_ms=duration,
            )
        
        finally:
            # Save workflow log
            self._save_workflow_log(context, step_results)
    
    async def _execute_step(
        self,
        step: WorkflowStep,
        context: WorkflowContext,
    ) -> StepResult:
        """Execute a single workflow step"""
        context.current_step = step.name
        started_at = datetime.now()
        
        # Check condition
        if step.condition and not step.condition(context):
            return StepResult(
                step_name=step.name,
                status=StepStatus.SKIPPED,
                started_at=started_at,
                finished_at=datetime.now(),
            )
        
        # Execute with retry
        last_error = None
        for attempt in range(step.retry_count + 1):
            try:
                # Run the action
                if asyncio.iscoroutinefunction(step.action):
                    if step.timeout:
                        output = await asyncio.wait_for(
                            step.action(context),
                            timeout=step.timeout,
                        )
                    else:
                        output = await asyncio.wait_for(
                            step.action(context),
                            timeout=self.default_timeout,
                        )
                else:
                    # Sync function - run in executor
                    output = await asyncio.get_event_loop().run_in_executor(
                        None,
                        step.action,
                        context,
                    )
                
                # Success
                finished_at = datetime.now()
                duration = (finished_at - started_at).total_seconds() * 1000
                
                # Store output if it's a dict
                if isinstance(output, dict):
                    context.outputs.update(output)
                
                return StepResult(
                    step_name=step.name,
                    status=StepStatus.COMPLETED,
                    output=output,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_ms=duration,
                )
                
            except asyncio.TimeoutError:
                last_error = f"Step timed out after {step.timeout or self.default_timeout}s"
            except Exception as e:
                last_error = f"{type(e).__name__}: {str(e)}"
            
            # Retry delay
            if attempt < step.retry_count:
                await asyncio.sleep(step.retry_delay * (2 ** attempt))
        
        # All retries failed
        finished_at = datetime.now()
        duration = (finished_at - started_at).total_seconds() * 1000
        
        return StepResult(
            step_name=step.name,
            status=StepStatus.FAILED,
            error=last_error,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration,
        )
    
    async def _rollback(
        self,
        steps: List[WorkflowStep],
        executed: set,
        context: WorkflowContext,
    ):
        """Execute rollback for completed steps"""
        # Rollback in reverse order
        for step in reversed(steps):
            if step.name in executed and step.rollback:
                try:
                    if asyncio.iscoroutinefunction(step.rollback):
                        await step.rollback(context)
                    else:
                        step.rollback(context)
                    
                    result = context.step_results.get(step.name)
                    if result:
                        result.status = StepStatus.ROLLED_BACK
                        
                except Exception as e:
                    # Log rollback failure but don't raise
                    print(f"[WorkflowEngine] Rollback failed for {step.name}: {e}")
    
    def _save_workflow_log(self, context: WorkflowContext, results: List[StepResult]):
        """Save workflow execution log"""
        try:
            log_file = self.log_dir / f"{context.workflow_id}.json"
            log_data = {
                "workflow_id": context.workflow_id,
                "started_at": str(context.started_at),
                "finished_at": str(context.finished_at),
                "inputs": context.inputs,
                "outputs": context.outputs,
                "steps": [r.to_dict() for r in results],
            }
            log_file.write_text(json.dumps(log_data, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"[WorkflowEngine] Failed to save log: {e}")


# ============================================================================
# Common Workflow Patterns
# ============================================================================

def create_deployment_workflow() -> List[WorkflowStep]:
    """Create a standard deployment workflow"""
    async def analyze(context: WorkflowContext):
        # Analyze project structure
        return {"project_type": "web", "framework": "nextjs"}
    
    async def build(context: WorkflowContext):
        # Build the project
        return {"build_output": "dist/"}
    
    async def test(context: WorkflowContext):
        # Run tests
        return {"tests_passed": True}
    
    async def deploy(context: WorkflowContext):
        # Deploy to production
        return {"deployed_url": "https://example.com"}
    
    return [
        WorkflowStep(name="analyze", action=analyze, description="Analyze project structure"),
        WorkflowStep(name="build", action=build, depends_on=["analyze"], description="Build project"),
        WorkflowStep(name="test", action=test, depends_on=["build"], description="Run tests"),
        WorkflowStep(name="deploy", action=deploy, depends_on=["test"], description="Deploy to production"),
    ]


def create_data_processing_workflow() -> List[WorkflowStep]:
    """Create a data processing workflow"""
    async def extract(context: WorkflowContext):
        return {"records": 1000}
    
    async def transform(context: WorkflowContext):
        return {"transformed": 950}
    
    async def load(context: WorkflowContext):
        return {"loaded": 950}
    
    return [
        WorkflowStep(name="extract", action=extract, description="Extract data from source"),
        WorkflowStep(name="transform", action=transform, depends_on=["extract"], description="Transform data"),
        WorkflowStep(name="load", action=load, depends_on=["transform"], description="Load to destination"),
    ]
