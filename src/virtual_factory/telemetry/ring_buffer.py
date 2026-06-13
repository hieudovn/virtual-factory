"""Telemetry ring buffer skeleton."""

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from virtual_factory.telemetry.signal_value import SignalValue


@dataclass(slots=True)
class RingBuffer:
    """Fixed-size in-memory buffer for future telemetry samples."""

    maxlen: int = 1000
    _items: deque[Any] = field(init=False)

    def __post_init__(self) -> None:
        self._items = deque(maxlen=self.maxlen)

    def append(self, item: Any) -> None:
        """Append one item to the buffer."""
        self._items.append(item)

    def snapshot(self) -> list[Any]:
        """Return a list copy of buffered items."""
        return list(self._items)


@dataclass(slots=True)
class RingBufferTelemetryStore:
    """Short-term telemetry frame store for UI and protocol gateways."""

    maxlen: int = 3600
    _frames: deque[list[SignalValue]] = field(init=False)

    def __post_init__(self) -> None:
        self._frames = deque(maxlen=self.maxlen)

    def append_frame(self, frame: list[SignalValue]) -> None:
        """Append one telemetry frame."""
        self._frames.append(list(frame))

    def latest(self) -> list[SignalValue]:
        """Return the latest telemetry frame."""
        return list(self._frames[-1]) if self._frames else []

    def all(self) -> list[list[SignalValue]]:
        """Return all buffered telemetry frames."""
        return [list(frame) for frame in self._frames]
