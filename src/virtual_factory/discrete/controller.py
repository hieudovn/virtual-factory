"""Discrete run controller — execution modes, command queue, safe-point.

M2-S04: manual/automatic/hybrid stepping, control command processing,
allowed_actions projection, pacing policy storage.
No async loop, no WebSocket, no REST, no domain logic, no wall-clock sleep.
"""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass
from typing import Iterable

from virtual_factory.discrete.commands import (
    ControlCommandQueue,
    ControlCommandResult,
    RunControlCommand,
)
from virtual_factory.discrete.engine import (
    DiscreteSimulationEngine,
    DiscreteSimulationEngineError,
)
from virtual_factory.discrete.events import ScheduledEvent
from virtual_factory.discrete.snapshot import RuntimeSnapshot
from virtual_factory.discrete.state import RunStatus


# ──────────────────────────────────────────────
# ExecutionMode
# ──────────────────────────────────────────────


class ExecutionMode(str, enum.Enum):
    """Controller pacing mode — immutable after construction in M2-S04."""

    MANUAL = "manual"
    AUTOMATIC = "automatic"
    HYBRID = "hybrid"


# ──────────────────────────────────────────────
# ControllerPacingPolicy
# ──────────────────────────────────────────────


class ControllerPacingPolicyError(ValueError):
    """Raised when a ControllerPacingPolicy invariant is violated."""


@dataclass(frozen=True, slots=True)
class ControllerPacingPolicy:
    """Immutable validated pacing configuration.

    M2-S04 stores but does not apply — M2-S07 service will use it.
    """

    speed_factor: float = 1.0
    max_events_per_second: int = 1000
    snapshot_broadcast_max_hz: int = 10

    def __post_init__(self) -> None:
        # speed_factor
        if isinstance(self.speed_factor, bool):
            raise ControllerPacingPolicyError("speed_factor must be numeric, not bool")
        if not isinstance(self.speed_factor, (int, float)):
            raise ControllerPacingPolicyError(
                f"speed_factor must be numeric, got {type(self.speed_factor).__name__}"
            )
        if math.isnan(self.speed_factor) or math.isinf(self.speed_factor):
            raise ControllerPacingPolicyError("speed_factor must be finite")
        if self.speed_factor <= 0:
            raise ControllerPacingPolicyError(
                f"speed_factor must be > 0, got {self.speed_factor}"
            )

        # max_events_per_second
        if isinstance(self.max_events_per_second, bool):
            raise ControllerPacingPolicyError(
                "max_events_per_second must be int, not bool"
            )
        if not isinstance(self.max_events_per_second, int):
            raise ControllerPacingPolicyError(
                f"max_events_per_second must be int, "
                f"got {type(self.max_events_per_second).__name__}"
            )
        if self.max_events_per_second <= 0:
            raise ControllerPacingPolicyError(
                f"max_events_per_second must be > 0, "
                f"got {self.max_events_per_second}"
            )

        # snapshot_broadcast_max_hz
        if isinstance(self.snapshot_broadcast_max_hz, bool):
            raise ControllerPacingPolicyError(
                "snapshot_broadcast_max_hz must be int, not bool"
            )
        if not isinstance(self.snapshot_broadcast_max_hz, int):
            raise ControllerPacingPolicyError(
                f"snapshot_broadcast_max_hz must be int, "
                f"got {type(self.snapshot_broadcast_max_hz).__name__}"
            )
        if self.snapshot_broadcast_max_hz <= 0:
            raise ControllerPacingPolicyError(
                f"snapshot_broadcast_max_hz must be > 0, "
                f"got {self.snapshot_broadcast_max_hz}"
            )


# ──────────────────────────────────────────────
# Allowed actions projection
# ──────────────────────────────────────────────


def _compute_allowed_actions(
    engine_status: RunStatus,
    mode: ExecutionMode,
) -> tuple[str, ...]:
    """Compute immutable sorted allowed_actions from engine status + mode.

    Sorted in documented deterministic order.
    """
    status_val = engine_status.value

    if status_val == "created":
        return ("initialize", "stop")

    if status_val == "ready":
        if mode == ExecutionMode.MANUAL:
            return ("step_event", "stop")
        elif mode == ExecutionMode.AUTOMATIC:
            return ("auto_run", "stop")
        else:  # HYBRID
            return ("auto_run", "step_event", "stop")

    if status_val == "running":
        return ("pause", "stop")

    if status_val == "paused":
        if mode == ExecutionMode.MANUAL:
            return ("step_event", "stop")
        elif mode == ExecutionMode.AUTOMATIC:
            return ("resume", "stop")
        else:  # HYBRID
            return ("resume", "step_event", "stop")

    # Terminal: completed, stopped, failed
    return ()


# ──────────────────────────────────────────────
# DiscreteRunController
# ──────────────────────────────────────────────


class DiscreteRunControllerError(RuntimeError):
    """Raised when a controller invariant is violated."""


class DiscreteRunController:
    """Owns mode, pacing policy, command queue.  Delegates lifecycle to engine.

    - Manual mode: step_once() allowed from READY/PAUSED.
    - Automatic mode: start_automatic() → RUNNING, then run_cycle().
    - Hybrid mode: both manual stepping and automatic start/cycle.
    - Safe-point: queued commands applied before next event.
    """

    def __init__(
        self,
        engine: DiscreteSimulationEngine,
        *,
        mode: ExecutionMode = ExecutionMode.MANUAL,
        command_queue_capacity: int = 1024,
        pacing_policy: ControllerPacingPolicy | None = None,
    ) -> None:
        if not isinstance(engine, DiscreteSimulationEngine):
            raise DiscreteRunControllerError(
                f"engine must be DiscreteSimulationEngine, "
                f"got {type(engine).__name__}"
            )
        if not isinstance(mode, ExecutionMode):
            raise DiscreteRunControllerError(
                f"mode must be ExecutionMode, got {type(mode).__name__}"
            )

        self._engine = engine
        self._mode = mode
        self._queue = ControlCommandQueue(capacity=command_queue_capacity)
        self._pacing = pacing_policy

    # ----------------------------------------------------------------
    # Read-only properties
    # ----------------------------------------------------------------

    @property
    def mode(self) -> ExecutionMode:
        return self._mode

    @property
    def allowed_actions(self) -> tuple[str, ...]:
        return _compute_allowed_actions(self._engine.status, self._mode)

    # ----------------------------------------------------------------
    # Snapshot
    # ----------------------------------------------------------------

    def to_snapshot(self) -> RuntimeSnapshot:
        """Return engine snapshot with controller-projected allowed_actions."""
        snap = self._engine.to_snapshot()
        return RuntimeSnapshot(
            run_id=snap.run_id,
            model_id=snap.model_id,
            model_version=snap.model_version,
            scenario_id=snap.scenario_id,
            scenario_version=snap.scenario_version,
            status=snap.status,
            simulation_time_s=snap.simulation_time_s,
            stop_reason=snap.stop_reason,
            failure_error=snap.failure_error,
            processed_events=snap.processed_events,
            pending_events=snap.pending_events,
            last_event_id=snap.last_event_id,
            snapshot_sequence=snap.snapshot_sequence,
            schema_version=snap.schema_version,
            recent_events=snap.recent_events,
            diagnostics=snap.diagnostics,
            allowed_actions=self.allowed_actions,
        )

    # ----------------------------------------------------------------
    # Initialize
    # ----------------------------------------------------------------

    def initialize(
        self,
        initial_events: Iterable[ScheduledEvent] = (),
    ) -> RuntimeSnapshot:
        """Delegate to engine, then return controller snapshot."""
        self._engine.initialize(initial_events)
        return self.to_snapshot()

    # ----------------------------------------------------------------
    # Command submission
    # ----------------------------------------------------------------

    def submit_command(
        self,
        command: RunControlCommand,
    ) -> ControlCommandResult:
        """Validate, accept (or reject) a control command.

        Acceptance does NOT mutate engine state or snapshot_sequence.
        Rejected commands are never queued.
        """
        return self._queue.try_accept(
            command,
            engine_status=self._engine.status.value,
            engine_run_id=self._engine._run_context.run_id,
        )

    # ----------------------------------------------------------------
    # Safe-point — apply queued commands
    # ----------------------------------------------------------------

    def _apply_commands(self) -> tuple[ControlCommandResult, ...]:
        """Apply all queued commands in FIFO order, revalidating after each.

        Returns results for all processed commands.
        """
        commands = self._queue.pop_all()
        results: list[ControlCommandResult] = []

        for cmd in commands:
            engine_status = self._engine.status.value

            # Revalidate — earlier commands may have changed state
            if cmd.command_type.value == "pause":
                if engine_status != "running":
                    results.append(ControlCommandResult(
                        command_id=cmd.command_id,
                        command_sequence=cmd.command_sequence,
                        command_type=cmd.command_type.value,
                        status="rejected",
                        snapshot_sequence=None,
                        rejection_code="invalid_for_status",
                        rejection_detail=(
                            f"Cannot pause when status is {engine_status!r}"
                        ),
                    ))
                    continue
                try:
                    self._engine.pause()
                    results.append(ControlCommandResult(
                        command_id=cmd.command_id,
                        command_sequence=cmd.command_sequence,
                        command_type=cmd.command_type.value,
                        status="applied",
                        snapshot_sequence=self._engine.to_snapshot().snapshot_sequence,
                        rejection_code=None,
                        rejection_detail=None,
                    ))
                except DiscreteSimulationEngineError as exc:
                    results.append(ControlCommandResult(
                        command_id=cmd.command_id,
                        command_sequence=cmd.command_sequence,
                        command_type=cmd.command_type.value,
                        status="failed",
                        snapshot_sequence=None,
                        rejection_code="engine_error",
                        rejection_detail=str(exc),
                    ))

            elif cmd.command_type.value == "resume":
                if engine_status != "paused":
                    results.append(ControlCommandResult(
                        command_id=cmd.command_id,
                        command_sequence=cmd.command_sequence,
                        command_type=cmd.command_type.value,
                        status="rejected",
                        snapshot_sequence=None,
                        rejection_code="invalid_for_status",
                        rejection_detail=(
                            f"Cannot resume when status is {engine_status!r}"
                        ),
                    ))
                    continue
                try:
                    self._engine.resume()
                    results.append(ControlCommandResult(
                        command_id=cmd.command_id,
                        command_sequence=cmd.command_sequence,
                        command_type=cmd.command_type.value,
                        status="applied",
                        snapshot_sequence=self._engine.to_snapshot().snapshot_sequence,
                        rejection_code=None,
                        rejection_detail=None,
                    ))
                except DiscreteSimulationEngineError as exc:
                    results.append(ControlCommandResult(
                        command_id=cmd.command_id,
                        command_sequence=cmd.command_sequence,
                        command_type=cmd.command_type.value,
                        status="failed",
                        snapshot_sequence=None,
                        rejection_code="engine_error",
                        rejection_detail=str(exc),
                    ))

            elif cmd.command_type.value == "stop":
                if engine_status in ("completed", "stopped", "failed"):
                    results.append(ControlCommandResult(
                        command_id=cmd.command_id,
                        command_sequence=cmd.command_sequence,
                        command_type=cmd.command_type.value,
                        status="rejected",
                        snapshot_sequence=None,
                        rejection_code="invalid_for_status",
                        rejection_detail=(
                            f"Cannot stop from terminal status {engine_status!r}"
                        ),
                    ))
                    continue
                try:
                    self._engine.stop(reason=cmd.reason or "stopped_by_command")
                    results.append(ControlCommandResult(
                        command_id=cmd.command_id,
                        command_sequence=cmd.command_sequence,
                        command_type=cmd.command_type.value,
                        status="applied",
                        snapshot_sequence=self._engine.to_snapshot().snapshot_sequence,
                        rejection_code=None,
                        rejection_detail=None,
                    ))
                except DiscreteSimulationEngineError as exc:
                    results.append(ControlCommandResult(
                        command_id=cmd.command_id,
                        command_sequence=cmd.command_sequence,
                        command_type=cmd.command_type.value,
                        status="failed",
                        snapshot_sequence=None,
                        rejection_code="engine_error",
                        rejection_detail=str(exc),
                    ))

        return tuple(results)

    # ----------------------------------------------------------------
    # Manual stepping
    # ----------------------------------------------------------------

    def step_once(self) -> RuntimeSnapshot:
        """Apply queued commands at safe-point, then process at most one event.

        Valid from READY or PAUSED in MANUAL/HYBRID mode.
        Does NOT force status to RUNNING.
        """
        status = self._engine.status.value
        if self._mode == ExecutionMode.AUTOMATIC:
            raise DiscreteRunControllerError(
                f"step_once not allowed in AUTOMATIC mode"
            )
        if status not in ("ready", "running", "paused"):
            raise DiscreteRunControllerError(
                f"step_once requires ready/running/paused, got {status!r}"
            )

        # 1. Safe-point: apply queued commands
        self._apply_commands()

        # 2. If terminal or paused, do not pop event
        current = self._engine.status.value
        if current in ("completed", "stopped", "failed", "paused"):
            return self.to_snapshot()

        # 3. Process exactly one event
        self._engine.step_event()
        return self.to_snapshot()

    # ----------------------------------------------------------------
    # Automatic mode
    # ----------------------------------------------------------------

    def start_automatic(self) -> RuntimeSnapshot:
        """Transition to RUNNING. Valid from READY or PAUSED.

        In MANUAL mode this is rejected.
        """
        if self._mode == ExecutionMode.MANUAL:
            raise DiscreteRunControllerError(
                "start_automatic not allowed in MANUAL mode"
            )

        status = self._engine.status.value
        if status == "ready":
            self._engine.start_running()
        elif status == "paused":
            self._engine.resume()
        else:
            raise DiscreteRunControllerError(
                f"start_automatic requires ready or paused, got {status!r}"
            )

        return self.to_snapshot()

    def run_cycle(self) -> RuntimeSnapshot:
        """Apply queued commands at safe-point, then process at most one event.

        Valid only from RUNNING.  No while-loop, no sleep.
        """
        if self._mode not in (ExecutionMode.AUTOMATIC, ExecutionMode.HYBRID):
            raise DiscreteRunControllerError(
                f"run_cycle requires AUTOMATIC or HYBRID mode, got {self._mode.value}"
            )

        # 1. Safe-point: apply queued commands
        self._apply_commands()

        # 2. If no longer RUNNING, do not step
        current = self._engine.status.value
        if current != "running":
            # Drain any commands that arrived during dispatch
            drained = self._queue.drain_and_reject(
                "engine_not_running",
                f"Engine status is {current!r}, cannot process events",
            )
            # drained results are returned for audit — not attached to snapshot
            _ = drained
            return self.to_snapshot()

        # 3. Call engine.step_event() once
        self._engine.step_event()

        # 4. If event became terminal, drain/reject remaining commands
        current = self._engine.status.value
        if current in ("completed", "stopped", "failed"):
            drained = self._queue.drain_and_reject(
                "engine_terminal",
                f"Engine reached terminal status {current!r}",
            )
            _ = drained

        return self.to_snapshot()
