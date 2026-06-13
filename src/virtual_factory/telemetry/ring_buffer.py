"""Telemetry ring buffer skeleton."""

from collections import deque
from dataclasses import dataclass, field
from typing import Any


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
