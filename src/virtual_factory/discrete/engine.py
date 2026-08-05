"""Discrete simulation engine — deterministic, synchronous, domain-neutral.

M2-S01: lifecycle only — no controller, service, transport, or domain.
"""

from __future__ import annotations

from typing import Iterable

from virtual_factory.discrete.dispatcher import (
    EventDispatcherProtocol,
    HandlerOutcome,
)
from virtual_factory.discrete.events import ScheduledEvent
from virtual_factory.discrete.run_context import RunContext
from virtual_factory.discrete.scheduler import (
    FutureEventScheduler,
    FutureEventSchedulerError,
)
from virtual_factory.discrete.snapshot import RuntimeSnapshot
from virtual_factory.discrete.state import DiscreteRunState, RunStatus


class DiscreteSimulationEngineError(RuntimeError):
    """Raised when an engine lifecycle invariant is violated."""


_NON_TERMINAL = {RunStatus.CREATED, RunStatus.READY}
_TERMINAL = {RunStatus.COMPLETED, RunStatus.STOPPED, RunStatus.FAILED}


class DiscreteSimulationEngine:
    """Deterministic, synchronous, domain-neutral simulation engine.

    Owns a ``FutureEventScheduler`` and ``DiscreteRunState``.
    Depends on an injected ``EventDispatcherProtocol``.
    Does NOT contain asyncio, I/O, domain logic, or transport.
    """

    def __init__(
        self,
        run_context: RunContext,
        dispatcher: EventDispatcherProtocol,
    ) -> None:
        if not isinstance(run_context, RunContext):
            raise DiscreteSimulationEngineError(
                f"run_context must be RunContext, got {type(run_context).__name__}"
            )
        if not isinstance(dispatcher, EventDispatcherProtocol):
            raise DiscreteSimulationEngineError(
                "dispatcher must satisfy EventDispatcherProtocol"
            )

        self._run_context = run_context
        self._dispatcher = dispatcher
        self._scheduler: FutureEventScheduler | None = None
        self._state = DiscreteRunState(run_id=run_context.run_id)

    # ------------------------------------------------------------------
    # Public read-only
    # ------------------------------------------------------------------

    @property
    def status(self) -> RunStatus:
        return self._state.status

    def to_snapshot(self) -> RuntimeSnapshot:
        """Return an immutable snapshot of the current engine state."""
        ctx = self._run_context
        st = self._state
        return RuntimeSnapshot(
            run_id=st.run_id,
            model_id=ctx.model_id,
            model_version=ctx.model_version,
            scenario_id=ctx.scenario_id,
            scenario_version=ctx.scenario_version,
            status=st.status.value,
            simulation_time_s=st.simulation_time_s,
            stop_reason=st.stop_reason,
            failure_error=st.failure_error,
            processed_events=st.processed_events,
            pending_events=st.pending_events,
            last_event_id=st.last_event_id,
            snapshot_sequence=st.snapshot_sequence,
        )

    # ------------------------------------------------------------------
    # Lifecycle — initialize
    # ------------------------------------------------------------------

    def initialize(
        self,
        initial_events: Iterable[ScheduledEvent] = (),
    ) -> RuntimeSnapshot:
        """Schedule bootstrap events and transition to READY.

        Atomic: if any event is invalid, the engine stays CREATED.
        ``initial_events`` is materialised exactly once.
        """
        if self._state.status is not RunStatus.CREATED:
            raise DiscreteSimulationEngineError(
                f"initialize valid only from CREATED, current={self._state.status.value}"
            )

        # Materialise once
        events = tuple(initial_events)

        # Validate
        for i, evt in enumerate(events):
            if not isinstance(evt, ScheduledEvent):
                raise DiscreteSimulationEngineError(
                    f"initial_events[{i}] must be ScheduledEvent, "
                    f"got {type(evt).__name__}"
                )
            if evt.sequence is not None:
                raise DiscreteSimulationEngineError(
                    f"initial_events[{i}] must have sequence=None"
                )

        # Build a local scheduler — only commit on success
        scheduler = FutureEventScheduler()
        for evt in events:
            try:
                scheduler.schedule(evt)
            except FutureEventSchedulerError as exc:
                raise DiscreteSimulationEngineError(
                    f"Failed to schedule initial event {evt.event_id!r}: {exc}"
                ) from exc

        # Commit
        self._scheduler = scheduler
        self._state.status = RunStatus.READY
        self._state.simulation_time_s = scheduler.current_time_s
        self._state.pending_events = scheduler.pending_count
        self._state.snapshot_sequence += 1
        return self.to_snapshot()

    # ------------------------------------------------------------------
    # Lifecycle — step
    # ------------------------------------------------------------------

    def step_event(self) -> RuntimeSnapshot:
        """Pop, dispatch, and commit one event.

        Valid only from READY.
        """
        if self._state.status is not RunStatus.READY:
            raise DiscreteSimulationEngineError(
                f"step_event valid only from READY, current={self._state.status.value}"
            )
        assert self._scheduler is not None  # guaranteed by initialize

        # 1. Pop
        try:
            event = self._scheduler.pop_next()
        except FutureEventSchedulerError as exc:
            return self._fail("scheduler_pop_error", str(exc), snapshot=True)

        # 2. Empty → COMPLETED
        if event is None:
            return self._complete("scheduler_empty")

        # 3. Sync time
        self._state.simulation_time_s = self._scheduler.current_time_s

        # 4. Dispatch (catch unexpected exceptions)
        try:
            outcome = self._dispatcher.dispatch(event)
        except Exception as exc:
            return self._fail("dispatcher_exception", str(exc), snapshot=True)

        # 5. Validate outcome
        if not isinstance(outcome, HandlerOutcome):
            return self._fail(
                "invalid_outcome",
                f"expected HandlerOutcome, got {type(outcome).__name__}",
                snapshot=True,
            )

        if outcome.event_id != event.event_id:
            return self._fail(
                "outcome_event_id_mismatch",
                f"expected {event.event_id!r}, got {outcome.event_id!r}",
                snapshot=True,
            )

        # 6. Unsuccessful → FAILED
        if not outcome.success:
            return self._fail(
                outcome.error_code or "unknown_error",
                outcome.error_detail,
                snapshot=True,
            )

        # 7. Schedule follow-ups
        for follow_up in outcome.follow_up_events:
            try:
                self._scheduler.schedule(follow_up)
            except FutureEventSchedulerError as exc:
                return self._fail("schedule_error", str(exc), snapshot=True)

        # 8. Commit successful event
        self._state.processed_events += 1
        self._state.pending_events = self._scheduler.pending_count
        self._state.last_event_id = event.event_id
        self._state.snapshot_sequence += 1

        # 9. Check completion
        if self._scheduler.is_empty:
            return self._complete("scheduler_empty")

        return self.to_snapshot()

    # ------------------------------------------------------------------
    # Lifecycle — stop
    # ------------------------------------------------------------------

    def stop(self, reason: str = "stopped") -> RuntimeSnapshot:
        """Stop the engine. Valid from CREATED or READY."""
        if self._state.status in _TERMINAL:
            raise DiscreteSimulationEngineError(
                f"stop invalid from terminal state {self._state.status.value}"
            )
        if self._state.status not in _NON_TERMINAL:
            raise DiscreteSimulationEngineError(
                f"stop valid only from CREATED or READY, "
                f"current={self._state.status.value}"
            )
        if not reason or not reason.strip():
            raise DiscreteSimulationEngineError("stop reason must be non-empty")

        self._state.status = RunStatus.STOPPED
        self._state.stop_reason = reason
        if self._scheduler is not None:
            self._state.pending_events = self._scheduler.pending_count
        self._state.snapshot_sequence += 1
        return self.to_snapshot()

    # ------------------------------------------------------------------
    # Internal transitions
    # ------------------------------------------------------------------

    def _complete(self, reason: str) -> RuntimeSnapshot:
        self._state.status = RunStatus.COMPLETED
        self._state.stop_reason = reason
        self._state.pending_events = (
            self._scheduler.pending_count if self._scheduler else 0
        )
        self._state.snapshot_sequence += 1
        return self.to_snapshot()

    def _fail(
        self,
        error_code: str,
        error_detail: str | None = None,
        *,
        snapshot: bool = False,
    ) -> RuntimeSnapshot:
        self._state.status = RunStatus.FAILED
        self._state.failure_error = error_code
        if error_detail:
            self._state.diagnostics["failure_detail"] = error_detail
        if snapshot:
            self._state.snapshot_sequence += 1
        return self.to_snapshot()
