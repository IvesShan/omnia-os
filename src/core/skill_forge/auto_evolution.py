"""Self-Evolution Module - Automatic skill creation and learning

Implements the self-evolution capability from Omnia 2.0 Architecture.
This module activates the CORE_SELF_EVOLUTION feature flag.

Features:
- Pattern detection from conversation history
- Automatic skill generation
- Skill vetting and approval
- Learning from user feedback
- Skill lifecycle management

Usage:
    from core.skill_forge.auto_evolution import SelfEvolutionEngine
    
    engine = SelfEvolutionEngine()
    await engine.run_evolution_cycle()
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..feature.flags import FeatureFlags as FF
from .detector import PatternDetector, DetectedPattern
from .generator import SkillGenerator
from .vetter import SkillVetter


@dataclass
class EvolutionStats:
    """Statistics for self-evolution"""
    total_patterns_detected: int = 0
    total_skills_generated: int = 0
    total_skills_approved: int = 0
    total_skills_rejected: int = 0
    last_evolution_run: Optional[datetime] = None
    evolution_cycles: int = 0
    
    def to_dict(self) -> dict:
        return {
            "total_patterns_detected": self.total_patterns_detected,
            "total_skills_generated": self.total_skills_generated,
            "total_skills_approved": self.total_skills_approved,
            "total_skills_rejected": self.total_skills_rejected,
            "last_evolution_run": str(self.last_evolution_run) if self.last_evolution_run else None,
            "evolution_cycles": self.evolution_cycles,
        }


@dataclass
class EvolutionResult:
    """Result of an evolution cycle"""
    cycle_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    patterns_found: List[DetectedPattern] = field(default_factory=list)
    skills_generated: List[str] = field(default_factory=list)
    skills_approved: List[str] = field(default_factory=list)
    skills_rejected: List[str] = field(default_factory=list)
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "cycle_id": self.cycle_id,
            "started_at": str(self.started_at),
            "finished_at": str(self.finished_at) if self.finished_at else None,
            "patterns_found": len(self.patterns_found),
            "skills_generated": self.skills_generated,
            "skills_approved": self.skills_approved,
            "skills_rejected": self.skills_rejected,
            "error": self.error,
        }


class SelfEvolutionEngine:
    """
    Self-evolution engine for automatic skill creation.
    
    This is the core of Omnia's learning capability. It:
    1. Scans conversation history for repeated patterns
    2. Detects potential skill candidates
    3. Generates skill definitions
    4. Vets skills for safety and quality
    5. Optionally auto-approves or queues for human review
    """
    
    def __init__(
        self,
        memory_dir: Optional[Path] = None,
        skills_dir: Optional[Path] = None,
        auto_approve: bool = False,  # If True, auto-approve vetted skills
        min_pattern_frequency: int = 3,  # Minimum occurrences to consider
        lookback_days: int = 14,  # How far back to analyze
    ):
        self.memory_dir = memory_dir or Path.home() / ".openclaw" / "workspace" / "omnia-os" / "memory"
        self.skills_dir = skills_dir or Path.home() / ".openclaw" / "workspace" / "omnia-os" / "skills"
        self.auto_approve = auto_approve
        self.min_pattern_frequency = min_pattern_frequency
        self.lookback_days = lookback_days
        
        # Initialize components
        self.detector = PatternDetector(
            memory_dir=str(self.memory_dir),
            lookback_days=lookback_days,
            min_evidence=min_pattern_frequency,
        )
        self.generator = SkillGenerator()
        self.vetter = SkillVetter(existing_skills_dir=str(self.skills_dir))
        
        # Statistics
        self.stats = EvolutionStats()
        
        # Evolution history
        self.history_file = self.skills_dir.parent / ".omnia" / "evolution_history.json"
        self._load_history()
    
    def is_enabled(self) -> bool:
        """Check if self-evolution is enabled"""
        return FF.is_enabled("CORE_SELF_EVOLUTION")
    
    async def run_evolution_cycle(self) -> EvolutionResult:
        """
        Run a complete evolution cycle.
        
        This is the main entry point for self-evolution.
        Call this periodically (e.g., daily) or on-demand.
        """
        import uuid
        
        cycle_id = f"evo_{uuid.uuid4().hex[:8]}"
        result = EvolutionResult(
            cycle_id=cycle_id,
            started_at=datetime.now(),
        )
        
        if not self.is_enabled():
            result.error = "Self-evolution is disabled (CORE_SELF_EVOLUTION flag is off)"
            result.finished_at = datetime.now()
            return result
        
        try:
            # Step 1: Detect patterns
            print(f"[SelfEvolution] Starting cycle {cycle_id}")
            patterns = self.detector.detect()
            result.patterns_found = patterns
            self.stats.total_patterns_detected += len(patterns)
            print(f"[SelfEvolution] Found {len(patterns)} patterns")
            
            # Step 2: Generate skills for each pattern
            for pattern in patterns:
                if pattern.frequency < self.min_pattern_frequency:
                    continue
                
                # Generate skill definition
                skill_draft = self.generator.generate(pattern)
                if not skill_draft:
                    continue
                
                result.skills_generated.append(pattern.pattern_id)
                self.stats.total_skills_generated += 1
                
                # Step 3: Vet the skill (write to temp file first)
                skill_path = self.skills_dir / f"{pattern.pattern_id}" / "SKILL.md"
                skill_path.parent.mkdir(parents=True, exist_ok=True)
                skill_path.write_text(skill_draft, encoding="utf-8")
                vetting_report = self.vetter.vet(skill_path)
                
                if vetting_report.passed:
                    # Save the skill
                    skill_path.parent.mkdir(parents=True, exist_ok=True)
                    skill_path.write_text(skill_draft, encoding="utf-8")
                    
                    result.skills_approved.append(pattern.pattern_id)
                    self.stats.total_skills_approved += 1
                    print(f"[SelfEvolution] Approved skill: {pattern.pattern_id}")
                    
                else:
                    result.skills_rejected.append(pattern.pattern_id)
                    self.stats.total_skills_rejected += 1
                    # Remove the failed skill file
                    if skill_path.exists():
                        skill_path.unlink()
                    print(f"[SelfEvolution] Rejected skill: {pattern.pattern_id}")
                    print(f"  Reasons: {', '.join(vetting_report.errors)}")
            
            # Update stats
            self.stats.last_evolution_run = datetime.now()
            self.stats.evolution_cycles += 1
            
            result.finished_at = datetime.now()
            self._save_history()
            
            print(f"[SelfEvolution] Cycle {cycle_id} completed: {len(result.skills_approved)} skills approved")
            
        except Exception as e:
            result.error = str(e)
            result.finished_at = datetime.now()
            print(f"[SelfEvolution] Cycle {cycle_id} failed: {e}")
        
        return result
    
    def get_pending_skills(self) -> List[Dict[str, Any]]:
        """
        Get skills pending human review.
        
        Returns a list of generated skills that need approval.
        """
        pending_dir = self.skills_dir.parent / ".tmp_skills"
        if not pending_dir.exists():
            return []
        
        pending = []
        for skill_dir in pending_dir.iterdir():
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    pending.append({
                        "name": skill_dir.name,
                        "path": str(skill_file),
                        "created": datetime.fromtimestamp(skill_file.stat().st_mtime),
                    })
        
        return pending
    
    def approve_skill(self, skill_name: str) -> bool:
        """Approve a pending skill"""
        pending_dir = self.skills_dir.parent / ".tmp_skills" / skill_name
        approved_dir = self.skills_dir / skill_name
        
        if not pending_dir.exists():
            return False
        
        try:
            # Move to approved directory
            approved_dir.parent.mkdir(parents=True, exist_ok=True)
            pending_dir.rename(approved_dir)
            
            self.stats.total_skills_approved += 1
            self._save_history()
            
            print(f"[SelfEvolution] Skill approved: {skill_name}")
            return True
            
        except Exception as e:
            print(f"[SelfEvolution] Failed to approve skill: {e}")
            return False
    
    def reject_skill(self, skill_name: str) -> bool:
        """Reject and delete a pending skill"""
        pending_dir = self.skills_dir.parent / ".tmp_skills" / skill_name
        
        if not pending_dir.exists():
            return False
        
        try:
            import shutil
            shutil.rmtree(pending_dir)
            
            self.stats.total_skills_rejected += 1
            self._save_history()
            
            print(f"[SelfEvolution] Skill rejected: {skill_name}")
            return True
            
        except Exception as e:
            print(f"[SelfEvolution] Failed to reject skill: {e}")
            return False
    
    def get_stats(self) -> EvolutionStats:
        """Get evolution statistics"""
        return self.stats
    
    def _load_history(self):
        """Load evolution history from file"""
        if not self.history_file.exists():
            return
        
        try:
            data = json.loads(self.history_file.read_text(encoding="utf-8"))
            self.stats = EvolutionStats(**data.get("stats", {}))
        except Exception as e:
            print(f"[SelfEvolution] Failed to load history: {e}")
    
    def _save_history(self):
        """Save evolution history to file"""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "stats": self.stats.to_dict(),
                "updated_at": str(datetime.now()),
            }
            self.history_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"[SelfEvolution] Failed to save history: {e}")


# ============================================================================
# Background Evolution Task
# ============================================================================

async def run_background_evolution(interval_hours: int = 24):
    """
    Run self-evolution in the background.
    
    Args:
        interval_hours: How often to run evolution cycles
    """
    engine = SelfEvolutionEngine()
    
    while True:
        try:
            if engine.is_enabled():
                result = await engine.run_evolution_cycle()
                print(f"[BackgroundEvolution] Cycle completed: {result.to_dict()}")
            else:
                print("[BackgroundEvolution] Self-evolution is disabled")
        except Exception as e:
            print(f"[BackgroundEvolution] Error: {e}")
        
        await asyncio.sleep(interval_hours * 3600)


def start_evolution_daemon():
    """Start the evolution daemon as a background process"""
    import threading
    
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_background_evolution())
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


# ============================================================================
# CLI Interface
# ============================================================================

def cli_main():
    """CLI entry point for self-evolution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Omnia Self-Evolution Engine")
    parser.add_argument("command", choices=["run", "stats", "pending", "approve", "reject"])
    parser.add_argument("--skill-name", help="Skill name for approve/reject")
    parser.add_argument("--enable", action="store_true", help="Enable self-evolution")
    
    args = parser.parse_args()
    
    # Enable feature flag if requested
    if args.enable:
        FF.set("CORE_SELF_EVOLUTION", True)
        print("✅ Self-evolution enabled")
    
    engine = SelfEvolutionEngine()
    
    if args.command == "run":
        if not engine.is_enabled():
            print("❌ Self-evolution is disabled. Use --enable to enable.")
            return
        
        result = asyncio.run(engine.run_evolution_cycle())
        print(json.dumps(result.to_dict(), indent=2))
    
    elif args.command == "stats":
        stats = engine.get_stats()
        print(json.dumps(stats.to_dict(), indent=2))
    
    elif args.command == "pending":
        pending = engine.get_pending_skills()
        print(json.dumps(pending, indent=2))
    
    elif args.command == "approve":
        if not args.skill_name:
            print("❌ --skill-name is required")
            return
        success = engine.approve_skill(args.skill_name)
        print("✅ Approved" if success else "❌ Failed")
    
    elif args.command == "reject":
        if not args.skill_name:
            print("❌ --skill-name is required")
            return
        success = engine.reject_skill(args.skill_name)
        print("✅ Rejected" if success else "❌ Failed")


if __name__ == "__main__":
    cli_main()
