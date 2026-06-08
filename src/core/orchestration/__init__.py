"""Orchestration Layer - Workflow Engine, Agent Swarm, Scheduling, and Event Bus

This module implements Layer 5 of Omnia's architecture:
- EventBus: Pub/sub nervous system for module communication
- NervousSystem: Autonomous behavior engine (event-driven reactions)
- WorkflowEngine: Multi-step task orchestration
- AgentSwarm: Parallel execution of sub-agents
- Scheduler: Cron-based task scheduling
"""

from .event_bus import EventBus, Event, get_event_bus
from .nervous_system import NervousSystem, get_nervous_system, start_nervous_system
from .workflow_engine import WorkflowEngine, WorkflowStep, WorkflowContext
from .scheduler import Scheduler, ScheduledTask

__all__ = [
    "EventBus",
    "Event",
    "get_event_bus",
    "NervousSystem",
    "get_nervous_system",
    "start_nervous_system",
    "WorkflowEngine",
    "WorkflowStep",
    "WorkflowContext",
    "Scheduler",
    "ScheduledTask",
]
