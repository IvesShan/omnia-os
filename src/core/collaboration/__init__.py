"""Collaboration Package — 无限 ↔ Omnia 协作系统"""

from .protocol import (
    CollaborationMessage,
    CollaborationProtocol,
    Task,
    MessageType,
    TaskStatus,
    Executor,
)
from .manager import (
    CollaborationManager,
    PeerInfo,
    get_collaboration_manager,
)

__all__ = [
    # Protocol
    "CollaborationMessage",
    "CollaborationProtocol",
    "Task",
    "MessageType",
    "TaskStatus",
    "Executor",
    # Manager
    "CollaborationManager",
    "PeerInfo",
    "get_collaboration_manager",
]
