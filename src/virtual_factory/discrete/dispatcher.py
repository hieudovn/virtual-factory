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
        if not isinstance(self.event_id, str) or not self.event_id.strip():
            raise HandlerOutcomeError("event_id must be a non-empty str")

        # --- success ---
        if not isinstance(self.success, bool):
            raise HandlerOutcomeError(
                f"success must be bool, got {type(self.success).__name__}"
            )

        # --- success vs error ---
        if self.success and self.error_code is not None:
            raise HandlerOutcomeError(
                "successful outcome must not carry error_code"
            )
        if self.success and self.error_detail is not None:
            raise HandlerOutcomeError(
                "successful outcome must not carry error_detail"
            )
        if not self.success:
            if not isinstance(self.error_code, str) or not self.error_code.strip():
                raise HandlerOutcomeError(
                    "failed outcome must carry a non-empty str error_code"
                )

        # --- error_detail ---
        if self.error_detail is not None and not isinstance(self.error_detail, str):
            raise HandlerOutcomeError(
                f"error_detail must be str or None, got {type(self.error_detail).__name__}"
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
        for i, sc in enumerate(self.state_changes):
            if not isinstance(sc, str):
                raise HandlerOutcomeError(
                    f"state_changes[{i}] must be str, got {type(sc).__name__}"
                )
