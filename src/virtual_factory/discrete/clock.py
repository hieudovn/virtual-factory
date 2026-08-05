"""Discrete-time monotonic clock — scheduler-owned, never exposed mutably.

Independent of the continuous ``TimeManager``.  Time is finite,
non-negative and never moves backward.
"""

from __future__ import annotations

import math


class DiscreteClockError(ValueError):
    """Raised when a clock invariant is violated."""


class DiscreteClock:
    """A monotonic clock for discrete-event simulation.

    Rules:
    - Initial time defaults to ``0.0``.
    - Time must be int or float (not bool), finite, non-negative.
    - Time never moves backward.
    - Advancing to the current time is allowed.
    """

    def __init__(self, initial_time_s: float = 0.0) -> None:
        self._validate_time(initial_time_s, label="initial_time_s")
        self._current_time_s = float(initial_time_s)

    # ------------------------------------------------------------------
    # Read-only access
    # ------------------------------------------------------------------

    @property
    def current_time_s(self) -> float:
        return self._current_time_s

    def now(self) -> float:
        """Return the current simulation time in seconds."""
        return self._current_time_s

    # ------------------------------------------------------------------
    # Mutation — only called by the owning scheduler
    # ------------------------------------------------------------------

    def advance_to(self, target_time_s: float) -> float:
        """Advance the clock to *target_time_s*.

        Returns the new current time.

        Raises:
            DiscreteClockError: If *target_time_s* is NaN, infinite,
                earlier than the current time, or of unsupported type.
        """
        self._validate_time(target_time_s, label="target_time_s")
        if target_time_s < self._current_time_s:
            raise DiscreteClockError(
                f"Cannot advance backward: current={self._current_time_s} "
                f"target={target_time_s}"
            )
        self._current_time_s = float(target_time_s)
        return self._current_time_s

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_time(value: object, *, label: str) -> None:
        if isinstance(value, bool):
            raise DiscreteClockError(f"{label} must be numeric, got bool")
        if not isinstance(value, (int, float)):
            raise DiscreteClockError(
                f"{label} must be numeric, got {type(value).__name__}"
            )
        v = float(value)
        if math.isnan(v):
            raise DiscreteClockError(f"{label} must be finite, got NaN")
        if math.isinf(v):
            raise DiscreteClockError(f"{label} must be finite, got infinite")
        if v < 0.0:
            raise DiscreteClockError(f"{label} must be non-negative, got {v}")
