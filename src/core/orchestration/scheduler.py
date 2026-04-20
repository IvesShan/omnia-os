"""Scheduler - Cron-based task scheduling

Implements the Scheduler component from Omnia 2.0 Architecture.
Supports:
- Cron expression parsing
- One-time and recurring tasks
- Task persistence and recovery
- Integration with WorkflowEngine

Usage:
    from core.orchestration import Scheduler, ScheduledTask
    
    scheduler = Scheduler()
    
    # Add a recurring task
    task = ScheduledTask(
        name="daily_backup",
        cron="0 2 * * *",  # Every day at 2 AM
        action=backup_database,
    )
    scheduler.add_task(task)
    
    # Start the scheduler
    scheduler.start()
"""

from __future__ import annotations

import asyncio
import json
import time
try:
    from croniter import croniter
    CRONITER_AVAILABLE = True
except ImportError:
    CRONITER_AVAILABLE = False
    croniter = None
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from core.config import SCHEDULER_TASKS_FILE, OMNIA_HOME
from typing import Any, Callable, Dict, List, Optional, Union
import threading
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """A scheduled task definition"""
    name: str
    action: Callable  # async or sync function
    cron: Optional[str] = None  # Cron expression for recurring tasks
    interval_seconds: Optional[float] = None  # Simple interval (alternative to cron)
    run_once: bool = False  # One-time task
    run_at: Optional[datetime] = None  # Specific time for one-time task
    enabled: bool = True
    max_retries: int = 3
    retry_delay: float = 60.0  # seconds
    last_run: Optional[datetime] = None
    last_result: Optional[str] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self._calculate_next_run()
    
    def _calculate_next_run(self) -> Optional[datetime]:
        """Calculate the next run time based on cron or interval"""
        now = datetime.now()
        
        if self.run_once and self.run_at:
            self.next_run = self.run_at
            return self.next_run
        
        if self.cron:
            if not CRONITER_AVAILABLE:
                logger.warning("croniter not installed, cron expressions not supported")
                return None
            try:
                cron = croniter(self.cron, now)
                self.next_run = cron.get_next(datetime)
                return self.next_run
            except Exception as e:
                logger.error(f"Invalid cron expression '{self.cron}': {e}")
                return None
        
        if self.interval_seconds:
            if self.last_run:
                self.next_run = self.last_run + timedelta(seconds=self.interval_seconds)
            else:
                self.next_run = now + timedelta(seconds=self.interval_seconds)
            return self.next_run
        
        return None
    
    def should_run(self, now: datetime) -> bool:
        """Check if the task should run now"""
        if not self.enabled or not self.next_run:
            return False
        
        return now >= self.next_run
    
    def mark_completed(self, result: str = "success"):
        """Mark the task as completed and calculate next run"""
        self.last_run = datetime.now()
        self.last_result = result
        self.run_count += 1
        
        if self.run_once:
            self.enabled = False
            self.next_run = None
        else:
            self._calculate_next_run()
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "cron": self.cron,
            "interval_seconds": self.interval_seconds,
            "run_once": self.run_once,
            "enabled": self.enabled,
            "last_run": str(self.last_run) if self.last_run else None,
            "last_result": self.last_result,
            "next_run": str(self.next_run) if self.next_run else None,
            "run_count": self.run_count,
        }


class Scheduler:
    """
    Cron-based task scheduler.
    
    Features:
    - Cron expression support (via croniter)
    - Simple interval-based scheduling
    - One-time tasks at specific time
    - Task persistence (JSON-based)
    - Automatic retry on failure
    - Thread-safe operation
    """
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        check_interval: float = 60.0,  # Check every 60 seconds
    ):
        self.storage_path = storage_path or OMNIA_HOME / "scheduler_tasks.json"
        self.check_interval = check_interval
        self.tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Load existing tasks
        self._load_tasks()
    
    def add_task(self, task: ScheduledTask) -> bool:
        """Add a new scheduled task"""
        with self._lock:
            if task.name in self.tasks:
                logger.warning(f"Task '{task.name}' already exists, updating")
            self.tasks[task.name] = task
            self._save_tasks()
            logger.info(f"Added task: {task.name}, next run: {task.next_run}")
            return True
    
    def remove_task(self, name: str) -> bool:
        """Remove a scheduled task"""
        with self._lock:
            if name in self.tasks:
                del self.tasks[name]
                self._save_tasks()
                logger.info(f"Removed task: {name}")
                return True
            return False
    
    def enable_task(self, name: str) -> bool:
        """Enable a task"""
        with self._lock:
            if name in self.tasks:
                self.tasks[name].enabled = True
                self.tasks[name]._calculate_next_run()
                self._save_tasks()
                return True
            return False
    
    def disable_task(self, name: str) -> bool:
        """Disable a task"""
        with self._lock:
            if name in self.tasks:
                self.tasks[name].enabled = False
                self._save_tasks()
                return True
            return False
    
    def get_task(self, name: str) -> Optional[ScheduledTask]:
        """Get a task by name"""
        return self.tasks.get(name)
    
    def list_tasks(self) -> List[ScheduledTask]:
        """List all scheduled tasks"""
        return list(self.tasks.values())
    
    def start(self):
        """Start the scheduler (non-blocking)"""
        if self._running:
            logger.warning("Scheduler is already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Scheduler stopped")
    
    def _run_loop(self):
        """Main scheduler loop"""
        while self._running:
            try:
                self._check_and_run_tasks()
            except Exception as e:
                logger.error(f"Scheduler error: {e}", exc_info=True)
            
            time.sleep(self.check_interval)
    
    def _check_and_run_tasks(self):
        """Check all tasks and run any that are due"""
        now = datetime.now()
        
        with self._lock:
            tasks_to_run = [
                task for task in self.tasks.values()
                if task.should_run(now)
            ]
        
        for task in tasks_to_run:
            self._run_task(task)
    
    def _run_task(self, task: ScheduledTask):
        """Execute a scheduled task with retry logic"""
        logger.info(f"Running task: {task.name}")
        
        for attempt in range(task.max_retries + 1):
            try:
                # Run the action
                if asyncio.iscoroutinefunction(task.action):
                    # Create new event loop for async task
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(task.action())
                    finally:
                        loop.close()
                else:
                    result = task.action()
                
                # Success
                with self._lock:
                    task.mark_completed(str(result) if result else "success")
                    self._save_tasks()
                
                logger.info(f"Task '{task.name}' completed successfully")
                return
                
            except Exception as e:
                logger.error(f"Task '{task.name}' failed (attempt {attempt + 1}/{task.max_retries + 1}): {e}")
                
                if attempt < task.max_retries:
                    time.sleep(task.retry_delay)
                else:
                    # All retries exhausted
                    with self._lock:
                        task.last_run = datetime.now()
                        task.last_result = f"failed: {e}"
                        task._calculate_next_run()
                        self._save_tasks()
    
    def _load_tasks(self):
        """Load tasks from storage"""
        if not self.storage_path.exists():
            return
        
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            # Note: We can't restore the action functions, just metadata
            # Tasks need to be re-registered in code
            logger.info(f"Loaded {len(data.get('tasks', []))} task definitions from storage")
        except Exception as e:
            logger.error(f"Failed to load tasks: {e}")
    
    def _save_tasks(self):
        """Save tasks to storage"""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "tasks": [task.to_dict() for task in self.tasks.values()],
                "updated_at": str(datetime.now()),
            }
            self.storage_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            logger.error(f"Failed to save tasks: {e}")


# ============================================================================


# ============================================================================
# Common Scheduled Tasks
# ============================================================================

def create_memory_extraction_task() -> ScheduledTask:
    """Create a task for automatic memory extraction"""
    async def extract_memories():
        """Run memory extraction script"""
        import subprocess
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "auto_memory_extraction.py"
        if script_path.exists():
            result = subprocess.run(
                ["python3", str(script_path)],
                capture_output=True,
                text=True,
            )
            return result.stdout
        return "Script not found"
    
    return ScheduledTask(
        name="memory_extraction",
        action=extract_memories,
        cron="0 */4 * * *",  # Every 4 hours
        metadata={"description": "Extract memories from verbatim"},
    )


def create_backup_task() -> ScheduledTask:
    """Create a daily backup task"""
    async def backup():
        """Backup Omnia data"""
        import shutil
        
        omnia_dir = OMNIA_HOME
        backup_dir = Path.home() / ".omnia" / "backups" / datetime.now().strftime("%Y%m%d")
        
        if omnia_dir.exists():
            backup_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(omnia_dir, backup_dir, dirs_exist_ok=True)
            return f"Backup created: {backup_dir}"
        return "Nothing to backup"
    
    return ScheduledTask(
        name="daily_backup",
        action=backup,
        cron="0 2 * * *",  # Every day at 2 AM
        metadata={"description": "Daily backup of Omnia data"},
    )
