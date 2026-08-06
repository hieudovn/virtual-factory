"""Discrete simulation engine — deterministic, synchronous, domain-neutral.

M2-S01: lifecycle only — no controller, service, transport, or domain.
M2-S04: RUNNING/PAUSED transitions, step from active states, stop from RUNNING/PAUSED.
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
from virtual_factory.discrete.trace import (
    EventTraceBuffer,
    EventTraceEntry,
    RuntimeDiagnostics,
)


class DiscreteSimulationEngineError(RuntimeError):
    """Raised when an engine lifecycle invariant is violated."""


_NON_TERMINAL = {RunStatus.CREATED, RunStatus.READY, RunStatus.RUNNING, RunStatus.PAUSED}
_ACTIVE_STEP = {RunStatus.READY, RunStatus.RUNNING, RunStatus.PAUSED}
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
        *,
        trace_capacity: int = 128,
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
        self._trace = EventTraceBuffer(capacity=trace_capacity)
        self._trace_seq: int = 0

    # ------------------------------------------------------------------
    # Public read-only
    # ------------------------------------------------------------------

    @property
    def run_id(self) -> str:
        """Return the run_id from the run context (read-only)."""
        return self._run_context.run_id

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
            recent_events=self._trace.entries,
            diagnostics=RuntimeDiagnostics(
                failure_detail=st.diagnostics.get("failure_detail"),
                trace_capacity=self._trace.capacity,
                trace_size=self._trace.size,
                trace_total_entries=self._trace.total_entries,
                trace_dropped_entries=self._trace.dropped_entries,
            ),
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
        """Pop, dispatch, and commit one event.  Records trace entry.

        Valid from READY, RUNNING, or PAUSED.
        Non-terminal step preserves the status before the step.
        """
        if self._state.status not in _ACTIVE_STEP:
            raise DiscreteSimulationEngineError(
                f"step_event valid from READY/RUNNING/PAUSED, "
                f"current={self._state.status.value}"
            )
        assert self._scheduler is not None  # guaranteed by initialize

        # Capture status before step
        status_before = self._state.status

        # 1. Pop
        try:
            event = self._scheduler.pop_next()
        except FutureEventSchedulerError as exc:
            return self._fail("scheduler_pop_error", str(exc), snapshot=True)
        # No trace for scheduler-pop failure (no event received)

        # 2. Empty → COMPLETED
        if event is None:
            return self._complete("scheduler_empty")
        # No trace for empty completion

        # 3. Sync time
        self._state.simulation_time_s = self._scheduler.current_time_s

        # 4. Dispatch (catch unexpected exceptions)
        try:
            outcome = self._dispatcher.dispatch(event)
        except Exception as exc:
            return self._fail_with_trace(
                event, "dispatcher_exception", str(exc),
            )

        # 5. Validate outcome
        if not isinstance(outcome, HandlerOutcome):
            return self._fail_with_trace(
                event, "invalid_outcome",
                f"expected HandlerOutcome, got {type(outcome).__name__}",
            )

        if outcome.event_id != event.event_id:
            return self._fail_with_trace(
                event, "outcome_event_id_mismatch",
                f"expected {event.event_id!r}, got {outcome.event_id!r}",
            )

        # 6. Unsuccessful → FAILED
        if not outcome.success:
            return self._fail_with_trace(
                event,
                outcome.error_code or "unknown_error",
                outcome.error_detail,
                state_changes=outcome.state_changes,
            )

        # 7. Schedule follow-ups
        requested = len(outcome.follow_up_events)
        scheduled_count = 0
        for follow_up in outcome.follow_up_events:
            try:
                self._scheduler.schedule(follow_up)
                scheduled_count += 1
            except FutureEventSchedulerError as exc:
                # Partial scheduling failure — trace and fail
                self._sync_scheduler_state()
                self._state.status = RunStatus.FAILED
                self._state.failure_error = "schedule_error"
                self._state.diagnostics["failure_detail"] = str(exc)
                self._state.snapshot_sequence += 1

                self._trace_seq += 1
                self._trace.append(EventTraceEntry(
                    trace_sequence=self._trace_seq,
                    event_id=event.event_id,
                    event_type=event.event_type,
                    target_id=event.target_id,
                    simulation_time_s=event.simulation_time_s,
                    priority=event.priority,
                    scheduler_sequence=event.sequence if event.sequence is not None else 0,
                    correlation_id=event.correlation_id,
                    causation_id=event.causation_id,
                    result="failed",
                    error_code="schedule_error",
                    error_detail=str(exc),
                    state_changes=outcome.state_changes,
                    requested_follow_up_events=requested,
                    scheduled_follow_up_events=scheduled_count,
                    processed_events_after=self._state.processed_events,
                    pending_events_after=self._state.pending_events,
                ))
                return self.to_snapshot()

        # 8. Commit successful event
        self._state.processed_events += 1
        self._state.pending_events = self._scheduler.pending_count
        self._state.last_event_id = event.event_id
        self._state.snapshot_sequence += 1

        # Trace committed
        self._trace_seq += 1
        seq = event.sequence if event.sequence is not None else 0
        self._trace.append(EventTraceEntry(
            trace_sequence=self._trace_seq,
            event_id=event.event_id,
            event_type=event.event_type,
            target_id=event.target_id,
            simulation_time_s=event.simulation_time_s,
            priority=event.priority,
            scheduler_sequence=seq,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            result="committed",
            error_code=None,
            error_detail=None,
            state_changes=outcome.state_changes,
            requested_follow_up_events=requested,
            scheduled_follow_up_events=requested,
            processed_events_after=self._state.processed_events,
            pending_events_after=self._state.pending_events,
        ))

        # 9. Check completion
        if self._scheduler.is_empty:
            return self._complete("scheduler_empty")

        # 10. Preserve status before step (READY/RUNNING/PAUSED)
        self._state.status = status_before
        return self.to_snapshot()

    # ------------------------------------------------------------------
    # Lifecycle — RUNNING / PAUSED transitions (M2-S04)
    # ------------------------------------------------------------------

    def start_running(self) -> RuntimeSnapshot:
        """Transition READY → RUNNING.

        Increments snapshot_sequence once. No trace entry.
        Does not change simulation_time or counters.
        """
        if self._state.status is not RunStatus.READY:
            raise DiscreteSimulationEngineError(
                f"start_running valid only from READY, "
                f"current={self._state.status.value}"
            )
        self._state.status = RunStatus.RUNNING
        self._state.snapshot_sequence += 1
        return self.to_snapshot()

    def pause(self) -> RuntimeSnapshot:
        """Transition RUNNING → PAUSED.

        Increments snapshot_sequence once. No trace entry.
        Does not change simulation_time or counters.
        """
        if self._state.status is not RunStatus.RUNNING:
            raise DiscreteSimulationEngineError(
                f"pause valid only from RUNNING, "
                f"current={self._state.status.value}"
            )
        self._state.status = RunStatus.PAUSED
        self._state.snapshot_sequence += 1
        return self.to_snapshot()

    def resume(self) -> RuntimeSnapshot:
        """Transition PAUSED → RUNNING.

        Increments snapshot_sequence once. No trace entry.
        Does not change simulation_time or counters.
        """
        if self._state.status is not RunStatus.PAUSED:
            raise DiscreteSimulationEngineError(
                f"resume valid only from PAUSED, "
                f"current={self._state.status.value}"
            )
        self._state.status = RunStatus.RUNNING
        self._state.snapshot_sequence += 1
        return self.to_snapshot()

    # ------------------------------------------------------------------
    # Lifecycle — stop
    # ------------------------------------------------------------------

    def stop(self, reason: str = "stopped") -> RuntimeSnapshot:
        """Stop the engine. Valid from CREATED, READY, RUNNING, or PAUSED."""
        if self._state.status in _TERMINAL:
            raise DiscreteSimulationEngineError(
                f"stop invalid from terminal state {self._state.status.value}"
            )
        if self._state.status not in _NON_TERMINAL:
            raise DiscreteSimulationEngineError(
                f"stop valid only from CREATED/READY/RUNNING/PAUSED, "
                f"current={self._state.status.value}"
            )
        if not isinstance(reason, str) or not reason.strip():
            raise DiscreteSimulationEngineError(
                "stop reason must be a non-empty string"
            )

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
        self._sync_scheduler_state()
        self._state.status = RunStatus.FAILED
        self._state.failure_error = error_code
        if error_detail:
            self._state.diagnostics["failure_detail"] = error_detail
        if snapshot:
            self._state.snapshot_sequence += 1
        return self.to_snapshot()

    def _sync_scheduler_state(self) -> None:
        """Sync pending_events from the scheduler when it exists."""
        if self._scheduler is not None:
            self._state.pending_events = self._scheduler.pending_count

    def _fail_with_trace(
        self,
        event: ScheduledEvent,
        error_code: str,
        error_detail: str | None = None,
        *,
        state_changes: tuple[str, ...] = (),
    ) -> RuntimeSnapshot:
        """Transition to FAILED and record a failed trace entry."""
        self._sync_scheduler_state()
        self._state.status = RunStatus.FAILED
        self._state.failure_error = error_code
        if error_detail:
            self._state.diagnostics["failure_detail"] = error_detail
        self._state.snapshot_sequence += 1

        self._trace_seq += 1
        seq = event.sequence if event.sequence is not None else 0
        self._trace.append(EventTraceEntry(
            trace_sequence=self._trace_seq,
            event_id=event.event_id,
            event_type=event.event_type,
            target_id=event.target_id,
            simulation_time_s=event.simulation_time_s,
            priority=event.priority,
            scheduler_sequence=seq,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            result="failed",
            error_code=error_code,
            error_detail=error_detail,
            state_changes=state_changes,
            requested_follow_up_events=0,
            scheduled_follow_up_events=0,
            processed_events_after=self._state.processed_events,
            pending_events_after=self._state.pending_events,
        ))
        return self.to_snapshot()
