"""Concrete handler registry — deterministic, domain-neutral.

M2-S02: registration, dispatch, duplicate policy, unknown-event policy,
handler exception normalization, invalid-result normalization.

Does NOT own: scheduler, state, domain, RNG, I/O.
"""

from __future__ import annotations

from typing import Callable

from virtual_factory.discrete.dispatcher import (
    EventDispatcherProtocol,
    HandlerOutcome,
    HandlerOutcomeError,
)
from virtual_factory.discrete.events import ScheduledEvent

# ──────────────────────────────────────────────
# Handler function signature
# ──────────────────────────────────────────────

EventHandlerFn = Callable[[ScheduledEvent], HandlerOutcome]

# ──────────────────────────────────────────────
# Exceptions
# ──────────────────────────────────────────────


class HandlerRegistryError(ValueError):
    """Base for handler registry errors."""


class HandlerRegistrationError(HandlerRegistryError):
    """Raised when handler registration fails validation."""


class DuplicateHandlerError(HandlerRegistrationError):
    """Raised when registering an already-registered event_type."""


# ──────────────────────────────────────────────
# HandlerRegistry
# ──────────────────────────────────────────────


class HandlerRegistry:
    """Concrete, deterministic, domain-neutral event handler registry.

    Satisfies ``EventDispatcherProtocol``.
    Owns: handler map, registration policy, dispatch normalization.

    Does NOT own: scheduler, run state, assembly state, RNG, I/O.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, EventHandlerFn] = {}

    # ----------------------------------------------------------------
    # Registration
    # ----------------------------------------------------------------

    def register(self, event_type: str, handler: EventHandlerFn) -> None:
        """Register a handler for *event_type*.

        Args:
            event_type: Non-empty string. Matching is exact and case-sensitive.
            handler: Callable ``EventHandlerFn``.

        Raises:
            HandlerRegistrationError: *event_type* is not a non-empty string.
            HandlerRegistrationError: *handler* is not callable.
            DuplicateHandlerError: *event_type* is already registered.
                The original handler is preserved; no replacement occurs.
        """
        # --- Validate event_type ---
        if not isinstance(event_type, str):
            raise HandlerRegistrationError(
                f"event_type must be str, got {type(event_type).__name__!r}"
            )
        stripped = event_type.strip()
        if not stripped:
            raise HandlerRegistrationError(
                "event_type must be non-empty after stripping whitespace"
            )
        # Store original, not stripped

        # --- Validate handler ---
        if not callable(handler):
            raise HandlerRegistrationError(
                f"handler must be callable, got {type(handler).__name__!r}"
            )

        # --- Duplicate check ---
        if event_type in self._handlers:
            raise DuplicateHandlerError(
                f"Handler already registered for event_type {event_type!r}"
            )

        # --- Register ---
        self._handlers[event_type] = handler

    # ----------------------------------------------------------------
    # Inspection
    # ----------------------------------------------------------------

    def is_registered(self, event_type: str) -> bool:
        """Return True if *event_type* has a registered handler.

        Matching is exact and case-sensitive.
        """
        return event_type in self._handlers

    @property
    def registered_event_types(self) -> tuple[str, ...]:
        """Return sorted immutable tuple of registered event types."""
        return tuple(sorted(self._handlers.keys()))

    # ----------------------------------------------------------------
    # Dispatch  (satisfies EventDispatcherProtocol)
    # ----------------------------------------------------------------

    def dispatch(self, event: ScheduledEvent) -> HandlerOutcome:
        """Dispatch *event* to its registered handler.

        - Known event_type: call handler, validate result.
        - Unknown event_type: return failed outcome (``no_handler``).
        - Handler raises: normalize to ``handler_error``.
        - Invalid handler result: normalize to ``handler_error``.
        - Outcome event_id mismatch: normalize to ``handler_error``.

        Does NOT schedule follow-up events — the engine owns scheduling.
        Does NOT mutate the input event.
        """
        event_type = event.event_type

        # --- Unknown event ---
        handler = self._handlers.get(event_type)
        if handler is None:
            return HandlerOutcome(
                event_id=event.event_id,
                success=False,
                follow_up_events=(),
                state_changes=(),
                error_code="no_handler",
                error_detail=f"No handler registered for event_type {event_type!r}",
            )

        # --- Known event: call handler ---
        try:
            outcome = handler(event)
        except Exception as exc:
            # Normalize handler exception (do not catch BaseException)
            return HandlerOutcome(
                event_id=event.event_id,
                success=False,
                follow_up_events=(),
                state_changes=(),
                error_code="handler_error",
                error_detail=f"{type(exc).__name__}: {exc}",
            )

        # --- Validate handler result ---
        if not isinstance(outcome, HandlerOutcome):
            return HandlerOutcome(
                event_id=event.event_id,
                success=False,
                follow_up_events=(),
                state_changes=(),
                error_code="handler_error",
                error_detail=(
                    f"Handler for {event_type!r} returned "
                    f"{type(outcome).__name__!r} instead of HandlerOutcome"
                ),
            )

        # --- Event-ID mismatch ---
        if outcome.event_id != event.event_id:
            return HandlerOutcome(
                event_id=event.event_id,
                success=False,
                follow_up_events=(),
                state_changes=(),
                error_code="handler_error",
                error_detail=(
                    f"Handler for {event_type!r} returned outcome for "
                    f"{outcome.event_id!r} instead of {event.event_id!r}"
                ),
            )

        # --- Valid outcome ---
        return outcome
