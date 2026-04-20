"""Notification Queue — Bridge between ambient daemon and interactive sessions.

The Persona Daemon writes notifications here.
When a new interactive session starts, the Session Router pops them
into the system prompt or greeting.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from core.config import OMNIA_HOME


@dataclass
class Notification:
    id: str
    level: str           # info | warning | alert
    source: str          # daemon | cron | system
    title: str
    body: str
    created_at: str
    popped: bool = False


class NotificationQueue:
    def __init__(self, queue_path: str | Path = None):
        self.path = Path(queue_path) if queue_path else OMNIA_HOME / "notifications.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load_all(self) -> List[Notification]:
        if not self.path.exists():
            return []
        items = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                items.append(Notification(**data))
            except (json.JSONDecodeError, TypeError):
                continue
        return items

    def push(self, level: str, source: str, title: str, body: str = "") -> None:
        note = Notification(
            id=datetime.now().isoformat(timespec="seconds"),
            level=level,
            source=source,
            title=title,
            body=body,
            created_at=datetime.now().isoformat(timespec="seconds"),
            popped=False,
        )
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(note), ensure_ascii=False) + "\n")

    def pop_pending(self, limit: int = 10, mark_popped: bool = True) -> List[Notification]:
        all_notes = self._load_all()
        pending = [n for n in all_notes if not n.popped][:limit]
        if mark_popped and pending:
            # Rewrite the whole queue (acceptable for low-frequency notifications)
            ids = {n.id for n in pending}
            updated = []
            for n in all_notes:
                if n.id in ids:
                    n.popped = True
                updated.append(asdict(n))
            self.path.write_text(
                "".join(json.dumps(u, ensure_ascii=False) + "\n" for u in updated),
                encoding="utf-8",
            )
        return pending

    def summary(self, pending: Optional[List[Notification]] = None) -> str:
        notes = pending or self.pop_pending(mark_popped=False)
        if not notes:
            return ""
        lines = [f"[{n.level.upper()}] {n.title}" for n in notes]
        return "\n".join(lines)


def pop_notifications_for_session(
    queue_path: str | Path = None,
) -> str:
    """Convenience function: returns a formatted pulse string for the LLM."""
    q = NotificationQueue(queue_path)
    notes = q.pop_pending(limit=5)
    if not notes:
        return ""
    pulse = " while you were away:\n" + "\n".join(
        f"• [{n.level}] {n.title}" + (f" — {n.body}" if n.body else "")
        for n in notes
    )
    return pulse
