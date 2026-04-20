"""Neuro-Center — Omnia's low-level continuity substrate.

Includes session routing, organic heartbeat, and the Persona Daemon.
"""

from .persona_daemon import PersonaDaemon, DaemonConfig

__all__ = ["PersonaDaemon", "DaemonConfig"]
