"""Omnia Persona System

A Persona is more than a prompt. It is a persistent identity container
that carries memory, values, and relational context across sessions.
"""

from .persona_loader import Persona, load_persona, list_personas

__all__ = ["Persona", "load_persona", "list_personas"]
