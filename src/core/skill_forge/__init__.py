"""Skill Forge v0.1 — Omnia's self-improvement engine.

Transforms repeated task patterns from memory into structured, vetted skills.

Usage:
    from core.skill_forge import PatternDetector, SkillGenerator, SkillVetter
    
    # Or use the high-level self-evolution engine
    from core.skill_forge import SelfEvolutionEngine
    
    engine = SelfEvolutionEngine()
    result = await engine.run_evolution_cycle()
"""

from .detector import PatternDetector, DetectedPattern
from .generator import SkillGenerator
from .vetter import SkillVetter, VettingReport
from .auto_evolution import (
    SelfEvolutionEngine,
    EvolutionStats,
    EvolutionResult,
    run_background_evolution,
    start_evolution_daemon,
)

__all__ = [
    # Core components
    "PatternDetector",
    "DetectedPattern",
    "SkillGenerator",
    "SkillVetter",
    "VettingReport",
    # Self-evolution
    "SelfEvolutionEngine",
    "EvolutionStats",
    "EvolutionResult",
    "run_background_evolution",
    "start_evolution_daemon",
]

# Export EvolutionScheduler
from .evolution_scheduler import EvolutionScheduler

