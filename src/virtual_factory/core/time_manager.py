"""Time management primitives for future simulation scans."""

from dataclasses import dataclass


@dataclass(slots=True)
class TimeManager:
    """Tracks simulation time and fixed-step scan settings."""

    current_time_s: float = 0.0
    step_s: float = 1.0

    def now(self) -> float:
        """Return the current simulation time in seconds."""
        return self.current_time_s

    def advance(self) -> float:
        """Advance time by one configured step and return the new time."""
        self.current_time_s += self.step_s
        return self.current_time_s
