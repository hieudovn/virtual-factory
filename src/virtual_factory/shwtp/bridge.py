"""SH-WTP G21 plant-slice / X2 whole-plant execution bridge (VF-vNEXT-G22 / VF-SHW-X2).

An :class:`~virtual_factory.runcontrol.ExecutionBridge` over an accepted SH-WTP
model (the G21 :class:`~virtual_factory.shwtp.expansion.ShwtpPlantSlice` or the
X2 :class:`~virtual_factory.shwtp.whole_plant.WholePlantX2Runtime`), so the G7
run-lifecycle seam can drive SH-WTP exactly like it drives TIPA ASSY.

This module lives in the SH-WTP package (NOT in ``runcontrol``) to preserve the
frozen G7 boundary: the generic run-control package never references SH-WTP.

- ``natural_next_boundary`` = the next deterministic communication window.
- ``advance`` prepares every participant and runs one coordinator window at the
  exact requested boundary (fail closed on any mismatch).
- ``reset`` rebuilds a fresh model (fresh runtimes) for the SAME run attempt —
  it never creates a new run identity.

The bridge is orchestration-only: the model runtimes remain the domain-truth
owners; the bridge never mutates cross-scope state directly.
"""

from __future__ import annotations

from typing import Callable

from virtual_factory.runcontrol.lifecycle import StepResult


class ShwtpExecutionBridge:
    """Execution bridge over one deterministic SH-WTP model.

    ``model_builder`` returns the SH-WTP model (plant slice or X2 whole plant).
    The model must expose ``communication_step_s``, ``participants`` and
    ``coordinator``; nothing else about its domain surface is assumed.
    """

    def __init__(self, model_builder: Callable[[], object]) -> None:
        if not callable(model_builder):
            raise TypeError("model_builder must be callable")
        self._builder = model_builder
        self._model = model_builder()
        self._window_seq = 0

    @property
    def supports_reset(self) -> bool:
        return True

    @property
    def model(self) -> object:
        return self._model

    @property
    def slice(self) -> object:
        """Backward-compatible alias for the accepted G21 slice callers."""
        return self._model

    def natural_next_boundary(self, scope_ids: tuple[str, ...]) -> float:
        if not tuple(scope_ids):
            raise ValueError("no executable scopes to advance")
        return (self._window_seq + 1) * self._model.communication_step_s

    def advance(
        self,
        target_time_s: float,
        scope_ids: tuple[str, ...],
        window_id: str,
    ) -> StepResult:
        expected = (self._window_seq + 1) * self._model.communication_step_s
        if target_time_s != expected:
            raise ValueError(
                f"SH-WTP bridge expected boundary {expected!r}, got "
                f"{target_time_s!r}"
            )
        self._window_seq += 1
        model_driven = bool(getattr(self._model, "model_driven_windows", False)) and callable(
            getattr(self._model, "run_window", None)
        )
        if model_driven:
            # model-owned window entry (X2 whole plant: C1 evaluation + participants)
            outcome = self._model.run_window(window_id)
        else:
            for participant in self._model.participants.values():
                participant.prepare_window(window_id)
            outcome = self._model.coordinator.run_window(window_id, target_time_s)
        if outcome.target_time_s != target_time_s:
            raise ValueError(
                f"SH-WTP model landed on {outcome.target_time_s!r}, expected "
                f"boundary {target_time_s!r}"
            )
        return StepResult(
            status=outcome.status,
            target_time_s=outcome.target_time_s,
            participants=outcome.participants,
            committed=outcome.committed,
            failure=outcome.failure,
        )

    def reset(self, scope_ids: tuple[str, ...]) -> None:
        # In-context reset: rebuild a fresh deterministic model (fresh runtimes)
        # for the SAME run attempt. Never creates a new run identity.
        self._model = self._builder()
        self._window_seq = 0
