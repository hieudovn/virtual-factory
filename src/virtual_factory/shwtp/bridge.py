"""SH-WTP G21 plant-slice execution bridge (VF-vNEXT-G22).

An :class:`~virtual_factory.runcontrol.ExecutionBridge` over the accepted G21
:class:`~virtual_factory.shwtp.expansion.ShwtpPlantSlice`, so the G7
run-lifecycle seam can drive SH-WTP exactly like it drives TIPA ASSY.

This module lives in the SH-WTP package (NOT in ``runcontrol``) to preserve the
frozen G7 boundary: the generic run-control package never references SH-WTP.

- ``natural_next_boundary`` = the next deterministic communication window.
- ``advance`` prepares every participant and runs one coordinator window at the
  exact requested boundary (fail closed on any mismatch).
- ``reset`` rebuilds a fresh slice (fresh runtimes) for the SAME run attempt —
  it never creates a new run identity.

The bridge is orchestration-only: the slice runtimes remain the domain-truth
owners; the bridge never mutates cross-scope state directly.
"""

from __future__ import annotations

from typing import Callable

from virtual_factory.runcontrol.lifecycle import StepResult
from virtual_factory.shwtp.expansion import ShwtpPlantSlice


class ShwtpExecutionBridge:
    """Execution bridge over one deterministic SH-WTP plant slice."""

    def __init__(self, slice_builder: Callable[[], ShwtpPlantSlice]) -> None:
        if not callable(slice_builder):
            raise TypeError("slice_builder must be callable")
        self._builder = slice_builder
        self._slice = slice_builder()
        self._window_seq = 0

    @property
    def supports_reset(self) -> bool:
        return True

    @property
    def slice(self) -> ShwtpPlantSlice:
        return self._slice

    def natural_next_boundary(self, scope_ids: tuple[str, ...]) -> float:
        if not tuple(scope_ids):
            raise ValueError("no executable scopes to advance")
        return (self._window_seq + 1) * self._slice.communication_step_s

    def advance(
        self,
        target_time_s: float,
        scope_ids: tuple[str, ...],
        window_id: str,
    ) -> StepResult:
        expected = (self._window_seq + 1) * self._slice.communication_step_s
        if target_time_s != expected:
            raise ValueError(
                f"SH-WTP bridge expected boundary {expected!r}, got "
                f"{target_time_s!r}"
            )
        self._window_seq += 1
        for participant in self._slice.participants.values():
            participant.prepare_window(window_id)
        outcome = self._slice.coordinator.run_window(window_id, target_time_s)
        return StepResult(
            status=outcome.status,
            target_time_s=outcome.target_time_s,
            participants=outcome.participants,
            committed=outcome.committed,
            failure=outcome.failure,
        )

    def reset(self, scope_ids: tuple[str, ...]) -> None:
        # In-context reset: rebuild a fresh deterministic slice (fresh runtimes)
        # for the SAME run attempt. Never creates a new run identity.
        self._slice = self._builder()
        self._window_seq = 0
