"""Event dispatcher protocol and immutable handler outcome.

M2-S01: protocol only — concrete HandlerRegistry in M2-S02.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from virtual_factory.discrete.events import ScheduledEvent


@runtime_checkable
class EventDispatcherProtocol(Protocol):
    """Injected port for event dispatch.

    Receives only the event — no scheduler, engine, or run state.
    """

    def dispatch(self, event: ScheduledEvent) -> HandlerOutcome:
        """Dispatch one event and return an immutable outcome."""
        ...


class HandlerOutcomeError(ValueError):
    """Raised when a ``HandlerOutcome`` invariant is violated."""


@dataclass(frozen=True, slots=True)
class HandlerOutcome:
    """Immutable result of dispatching one event."""

    event_id: str
    success: bool
    follow_up_events: tuple[ScheduledEvent, ...]
    state_changes: tuple[str, ...]
    error_code: str | None = None
    error_detail: str | None = None

    def __post_init__(self) -> None:
        # --- event_id ---
        if not self.event_id or not self.event_id.strip():
            raise HandlerOutcomeError("event_id must be non-empty")

        # --- success vs error ---
        if self.success and (self.error_code or self.error_detail):
            raise HandlerOutcomeError(
                "successful outcome must not carry error_code or error_detail"
            )
        if not self.success and not self.error_code:
            raise HandlerOutcomeError(
                "failed outcome must carry a non-empty error_code"
            )

        # --- follow_up_events ---
        if not isinstance(self.follow_up_events, tuple):
            raise HandlerOutcomeError("follow_up_events must be a tuple")
        for i, evt in enumerate(self.follow_up_events):
            # Deferred import to avoid circular dependency at module level
            from virtual_factory.discrete.events import ScheduledEvent as SE

            if not isinstance(evt, SE):
                raise HandlerOutcomeError(
                    f"follow_up_events[{i}] must be ScheduledEvent, "
                    f"got {type(evt).__name__}"
                )
            if evt.sequence is not None:
                raise HandlerOutcomeError(
                    f"follow_up_events[{i}] must have sequence=None, "
                    f"got {evt.sequence}"
                )

        # --- state_changes ---
        if not isinstance(self.state_changes, tuple):
            raise HandlerOutcomeError("state_changes must be a tuple")
