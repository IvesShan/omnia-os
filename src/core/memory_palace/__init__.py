"""Memory Palace 2.0 — The persistent memory substrate of Omnia.

Provides six layers of memory:
  - facts:              entities and attributes
  - relations:          connections between entities
  - habits:             user behavior patterns
  - timeline:           chronological events and decisions
  - conversation_logs:  complete dialogue history
  - tool_logs:          complete tool invocation history
"""

from .memory_palace import MemoryPalace
from .auto_logger import (
    AutoLogger,
    get_auto_logger,
    log_user_message,
    log_assistant_message,
    log_tool_invocation,
    new_session,
)

__all__ = [
    "MemoryPalace",
    "AutoLogger",
    "get_auto_logger",
    "log_user_message",
    "log_assistant_message",
    "log_tool_invocation",
    "new_session",
]
