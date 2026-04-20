"""Evolution Scheduler - Periodic self-evolution for Omnia Daemon

Integrates SelfEvolutionEngine into PersonaDaemon for automatic skill learning.
"""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from .auto_evolution import SelfEvolutionEngine, EvolutionResult


class EvolutionScheduler:
    """
    Schedules and runs periodic self-evolution cycles.
    
    Usage:
        scheduler = EvolutionScheduler(
            memory_dir=Path("/path/to/memory"),
            skills_dir=Path("/path/to/skills"),
            interval_hours=24,
        )
        scheduler.start()
    """
    
    def __init__(
        self,
        memory_dir: Path,
        skills_dir: Path,
        interval_hours: float = 24.0,
        on_evolution_complete: Optional[Callable[[EvolutionResult], None]] = None,
    ):
        self.memory_dir = memory_dir
        self.skills_dir = skills_dir
        self.interval_hours = interval_hours
        self.on_evolution_complete = on_evolution_complete
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_run: Optional[datetime] = None
        self._engine: Optional[SelfEvolutionEngine] = None
        
    def start(self) -> None:
        """Start the evolution scheduler in background."""
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            
    def run_now(self) -> EvolutionResult:
        """Run an evolution cycle immediately."""
        if not self._engine:
            self._engine = SelfEvolutionEngine(
                memory_dir=self.memory_dir,
                skills_dir=self.skills_dir,
            )
        
        # Run async in sync context
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(self._engine.run_evolution_cycle())
            self._last_run = datetime.now()
            
            if self.on_evolution_complete:
                self.on_evolution_complete(result)
                
            return result
        finally:
            loop.close()
            
    def _run_loop(self) -> None:
        """Background loop that runs evolution periodically."""
        import time
        
        while self._running:
            try:
                # Run evolution
                result = self.run_now()
                print(f"[EvolutionScheduler] Cycle complete: {len(result.skills_approved)} skills approved")
            except Exception as e:
                print(f"[EvolutionScheduler] Error: {e}")
                
            # Sleep for interval
            time.sleep(self.interval_hours * 3600)
            
    def get_status(self) -> dict:
        """Get scheduler status."""
        return {
            "running": self._running,
            "interval_hours": self.interval_hours,
            "last_run": str(self._last_run) if self._last_run else None,
            "memory_dir": str(self.memory_dir),
            "skills_dir": str(self.skills_dir),
        }
