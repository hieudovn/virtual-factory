"""In-memory ring-buffer output adapter — used by the API."""

from __future__ import annotations

from simulators.vf2.simulation_loop import Measurement

from .base import OutputAdapter


class MemoryOutput(OutputAdapter):
    """Stores frames in an in-memory ring buffer.

    Args:
        max_frames: Maximum number of frames to keep (oldest dropped).
    """

    def __init__(self, max_frames: int = 3600) -> None:
        self.frames: list[list[Measurement]] = []
        self.max_frames = max_frames

    def write(self, frame: list[Measurement]) -> None:
        self.frames.append(frame)
        if len(self.frames) > self.max_frames:
            self.frames.pop(0)

    def close(self) -> None:
        pass

    def get_latest(self) -> list[Measurement] | None:
        """Return the most recent frame, or ``None``."""
        return self.frames[-1] if self.frames else None

    def get_all(self) -> list[list[Measurement]]:
        """Return a copy of all stored frames."""
        return list(self.frames)
