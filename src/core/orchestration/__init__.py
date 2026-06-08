"""Orchestration Layer - Workflow Engine, Agent Swarm, Scheduling, Event Bus, and Heartbeat

This module implements Layer 5 of Omnia's architecture:
- EventBus: Pub/sub nervous system for module communication
- NervousSystem: Autonomous behavior engine (event-driven reactions)
- HeartbeatLoop: Autonomous heartbeat for periodic self-checks
- WorkflowEngine: Multi-step task orchestration
- AgentSwarm: Parallel execution of sub-agents
- Scheduler: Cron-based task scheduling
"""

from .event_bus import EventBus, Event, get_event_bus
from .nervous_system import NervousSystem, get_nervous_system, start_nervous_system
from .heartbeat_loop import HeartbeatLoop, HeartbeatConfig, get_heartbeat_loop, start_heartbeat_loop
from .workflow_engine import WorkflowEngine, WorkflowStep, WorkflowContext
from .scheduler import Scheduler, ScheduledTask

__all__ = [
    "EventBus",
    "Event",
    "get_event_bus",
    "NervousSystem",
    "get_nervous_system",
    "start_nervous_system",
    "HeartbeatLoop",
    "HeartbeatConfig",
    "get_heartbeat_loop",
    "start_heartbeat_loop",
    "WorkflowEngine",
    "WorkflowStep",
    "WorkflowContext",
    "Scheduler",
    "ScheduledTask",
]
