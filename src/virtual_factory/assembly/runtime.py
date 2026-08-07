"""Assembly runtime state — WIP registry and buffer occupancy.

M3-S02: Minimal runtime state for the vertical assembly flow.
Separate from immutable domain primitives.
"""

from __future__ import annotations

from collections import deque

from virtual_factory.assembly.primitives import Buffer
from virtual_factory.assembly.wip import WipId, WipState, WipStatus


class RuntimeStateError(RuntimeError):
    """Raised when a runtime state invariant is violated."""


class AssemblyRuntimeState:
    """Mutable runtime state for the assembly vertical flow.

    Owns WIP registry and buffer occupancy queues.
    Not a general factory-state framework.
    """

    def __init__(self) -> None:
        self._wips: dict[str, WipState] = {}
        self._buffer_queues: dict[str, deque[WipId]] = {}

    # -- WIP registry --

    @property
    def wip_count(self) -> int:
        return len(self._wips)

    def get_wip(self, wip_id: WipId) -> WipState | None:
        return self._wips.get(wip_id.id)

    def add_wip(self, state: WipState) -> None:
        if state.wip_id.id in self._wips:
            raise RuntimeStateError(f"WIP {state.wip_id} already registered")
        self._wips[state.wip_id.id] = state

    def all_wips(self) -> tuple[WipState, ...]:
        return tuple(self._wips.values())

    # -- Buffer occupancy --

    def ensure_buffer(self, buffer: Buffer) -> None:
        if buffer.primitive_id not in self._buffer_queues:
            self._buffer_queues[buffer.primitive_id] = deque()

    def buffer_enqueue(self, buffer_id: str, wip_id: WipId, capacity: int) -> None:
        q = self._buffer_queues.get(buffer_id)
        if q is None:
            raise RuntimeStateError(f"Buffer {buffer_id} not initialised")
        if len(q) >= capacity:
            raise RuntimeStateError(
                f"Buffer {buffer_id} full (capacity={capacity}, size={len(q)})"
            )
        q.append(wip_id)

    def buffer_dequeue(self, buffer_id: str) -> WipId:
        q = self._buffer_queues.get(buffer_id)
        if q is None or not q:
            raise RuntimeStateError(f"Buffer {buffer_id} empty or not initialised")
        return q.popleft()

    def buffer_size(self, buffer_id: str) -> int:
        q = self._buffer_queues.get(buffer_id)
        return len(q) if q else 0
