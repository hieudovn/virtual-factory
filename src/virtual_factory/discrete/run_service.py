"""Discrete run service — domain-neutral one-run application façade.

M2-S07: Owns at most one DiscreteRunController → DiscreteSimulationEngine.
Coordinates lifecycle, exposes snapshot/allowed-actions, forwards commands
through the controller.  No multi-run, no persistence, no transport.
"""

from __future__ import annotations

from typing import Iterable

from virtual_factory.discrete.commands import ControlCommandResult, RunControlCommand
from virtual_factory.discrete.controller import (
    DiscreteRunController,
    DiscreteRunControllerError,
    ExecutionMode,
)
from virtual_factory.discrete.dispatcher import EventDispatcherProtocol
from virtual_factory.discrete.engine import DiscreteSimulationEngine
from virtual_factory.discrete.events import ScheduledEvent
from virtual_factory.discrete.run_context import RunContext
from virtual_factory.discrete.snapshot import RuntimeSnapshot


class DiscreteRunServiceError(RuntimeError):
    """Raised when a service lifecycle invariant is violated."""


class DiscreteRunService:
    """Domain-neutral one-run service façade.

    Owns at most one ``DiscreteRunController`` at a time.
    Coordinates lifecycle without reimplementing controller or engine logic.

    Lifecycle::

        no run
          ↓ create_run()
        owned run (READY / RUNNING / PAUSED)
          ↓ commands / step / run_cycle
        active lifecycle
          ↓
        completed / stopped / failed  (terminal)
          ↓ reset()
        no run
    """

    def __init__(self) -> None:
        self._controller: DiscreteRunController | None = None

    # ------------------------------------------------------------------
    # Read-only
    # ------------------------------------------------------------------

    @property
    def has_run(self) -> bool:
        """True when a run is currently owned (not None)."""
        return self._controller is not None

    @property
    def snapshot(self) -> RuntimeSnapshot | None:
        """Current controller snapshot, or None before initialization."""
        if self._controller is None:
            return None
        return self._controller.to_snapshot()

    @property
    def allowed_actions(self) -> tuple[str, ...]:
        """Controller-projected allowed actions, or () before initialization."""
        if self._controller is None:
            return ()
        return self._controller.allowed_actions

    @property
    def mode(self) -> ExecutionMode | None:
        """Controller execution mode, or None if no run."""
        if self._controller is None:
            return None
        return self._controller.mode

    # ------------------------------------------------------------------
    # Lifecycle — create / initialize
    # ------------------------------------------------------------------

    def create_run(
        self,
        run_context: RunContext,
        dispatcher: EventDispatcherProtocol,
        *,
        initial_events: Iterable[ScheduledEvent] = (),
        mode: ExecutionMode = ExecutionMode.MANUAL,
        trace_capacity: int = 128,
        max_processed_events: int | None = None,
        max_same_time_events: int = 100,
        command_queue_capacity: int = 1024,
    ) -> RuntimeSnapshot:
        """Create and initialize exactly one run.

        Raises ``DiscreteRunServiceError`` if a run is already owned.
        """
        if self._controller is not None:
            raise DiscreteRunServiceError(
                "Cannot create run: a run is already owned. "
                "Use reset() to discard the current run first."
            )

        engine = DiscreteSimulationEngine(
            run_context,
            dispatcher,
            trace_capacity=trace_capacity,
            max_processed_events=max_processed_events,
            max_same_time_events=max_same_time_events,
        )
        controller = DiscreteRunController(
            engine,
            mode=mode,
            command_queue_capacity=command_queue_capacity,
        )

        try:
            snapshot = controller.initialize(initial_events)
        except Exception:
            # Initialization failed — do not own a broken run
            raise

        self._controller = controller
        return snapshot

    # ------------------------------------------------------------------
    # Step / run
    # ------------------------------------------------------------------

    def step_once(self) -> RuntimeSnapshot:
        """Forward step_once to controller.  Valid only when run is owned."""
        self._require_run("step_once")
        return self._controller.step_once()  # type: ignore[union-attr]

    def start_automatic(self) -> RuntimeSnapshot:
        """Forward start_automatic to controller."""
        self._require_run("start_automatic")
        return self._controller.start_automatic()  # type: ignore[union-attr]

    def run_cycle(self) -> RuntimeSnapshot:
        """Forward run_cycle to controller."""
        self._require_run("run_cycle")
        return self._controller.run_cycle()  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def submit_command(self, command: RunControlCommand) -> ControlCommandResult:
        """Forward command to controller.  Valid only when run is owned."""
        self._require_run("submit_command")
        return self._controller.submit_command(command)  # type: ignore[union-attr]

    def drain_results(self) -> tuple[ControlCommandResult, ...]:
        """Drain command results from the controller outbox."""
        if self._controller is None:
            return ()
        return self._controller.drain_command_results()

    # ------------------------------------------------------------------
    # Lifecycle — reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Discard the current run and return to no-run state.

        Idempotent: safe to call when no run is owned.
        """
        self._controller = None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _require_run(self, operation: str) -> None:
        """Raise if no run is owned."""
        if self._controller is None:
            raise DiscreteRunServiceError(
                f"Cannot {operation}: no run is owned. "
                f"Use create_run() to initialize a run first."
            )
