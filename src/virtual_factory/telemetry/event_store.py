"""Event store skeleton."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class EventStore:
    """Stores future industrial and diagnostic events."""

    events: list[dict[str, Any]] = field(default_factory=list)

    def append(self, event: dict[str, Any]) -> None:
        """Append an event to the in-memory store."""
        self.events.append(event)
