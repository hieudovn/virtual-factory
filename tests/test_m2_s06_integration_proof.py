"""M2-S06 — Domain-Neutral Integration Proof.

Proves that all discrete-runtime components (M2-S01 through M2-S05)
operate together as one coherent deterministic observable safe runtime:
  scheduler → handler registry → dispatcher → handler → state change →
  follow-up event → trace → snapshot → deterministic completion.

Uses a generic 3-step job-processing flow:
  JOB_START → JOB_PROCESS → JOB_CHECK → complete
"""

import pytest
from virtual_factory.discrete.handler_registry import HandlerRegistry
from virtual_factory.discrete.dispatcher import EventDispatcherProtocol, HandlerOutcome
from virtual_factory.discrete.engine import DiscreteSimulationEngine
from virtual_factory.discrete.events import ScheduledEvent
from virtual_factory.discrete.run_context import RunContext


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _rc(**kw):
    defaults = {"run_id": "m2s06-proof", "model_id": "generic-integration"}
    defaults.update(kw)
    return RunContext(**defaults)


def _evt(event_id, simulation_time_s=0.0, event_type="test", **kw):
    return ScheduledEvent(
        event_id=event_id, simulation_time_s=simulation_time_s, event_type=event_type, **kw
    )


# ──────────────────────────────────────────────
# Generic integration domain — 3-step job flow
# ──────────────────────────────────────────────

def _build_job_registry(job_id: str = "job-001"):
    """Build a HandlerRegistry for a generic 3-step job flow."""
    state: dict[str, str] = {}

    def start_handler(event: ScheduledEvent) -> HandlerOutcome:
        state[job_id] = "started"
        return HandlerOutcome(
            event_id=event.event_id, success=True,
            follow_up_events=(_evt(f"{job_id}-process", simulation_time_s=1.0, event_type="JOB_PROCESS"),),
            state_changes=(f"{job_id}:created→started",),
        )

    def process_handler(event: ScheduledEvent) -> HandlerOutcome:
        state[job_id] = "processed"
        return HandlerOutcome(
            event_id=event.event_id, success=True,
            follow_up_events=(_evt(f"{job_id}-check", simulation_time_s=2.0, event_type="JOB_CHECK"),),
            state_changes=(f"{job_id}:started→processed",),
        )

    def check_handler(event: ScheduledEvent) -> HandlerOutcome:
        state[job_id] = "completed"
        return HandlerOutcome(
            event_id=event.event_id, success=True,
            follow_up_events=(),
            state_changes=(f"{job_id}:processed→completed",),
        )

    reg = HandlerRegistry()
    reg.register("JOB_START", start_handler)
    reg.register("JOB_PROCESS", process_handler)
    reg.register("JOB_CHECK", check_handler)
    return reg, state


# ──────────────────────────────────────────────
# Integration Proof Tests
# ──────────────────────────────────────────────


class TestIntegrationHappyPath:
    """M2-S06-A: Full runtime chain — start → process → check → complete."""

    def test_full_chain_completes(self):
        reg, state = _build_job_registry()
        engine = DiscreteSimulationEngine(_rc(), reg)
        engine.initialize([_evt("job-001-start", simulation_time_s=0.0, event_type="JOB_START")])

        snap = None
        for _ in range(10):
            if engine.status.value in ("completed", "stopped", "failed"):
                break
            snap = engine.step_event()
            if snap.status == "completed":
                break

        assert snap is not None
        assert snap.status == "completed"
        assert state["job-001"] == "completed"

    def test_processed_event_count_exact(self):
        reg, _ = _build_job_registry()
        engine = DiscreteSimulationEngine(_rc(), reg)
        engine.initialize([_evt("start", simulation_time_s=0.0, event_type="JOB_START")])

        for _ in range(10):
            if engine.status.value in ("completed", "stopped", "failed"):
                break
            engine.step_event()

        snap = engine.to_snapshot()
        # JOB_START + JOB_PROCESS + JOB_CHECK = 3 events
        assert snap.processed_events == 3

    def test_simulation_time_progresses(self):
        reg, _ = _build_job_registry()
        engine = DiscreteSimulationEngine(_rc(), reg)
        engine.initialize([_evt("start", simulation_time_s=0.0, event_type="JOB_START")])

        for _ in range(10):
            if engine.status.value in ("completed", "stopped", "failed"):
                break
            engine.step_event()

        snap = engine.to_snapshot()
        assert snap.simulation_time_s == 2.0  # JOB_CHECK at t=2.0

    def test_state_changes_reflect_execution(self):
        reg, state = _build_job_registry()
        engine = DiscreteSimulationEngine(_rc(), reg)
        engine.initialize([_evt("start", simulation_time_s=0.0, event_type="JOB_START")])

        for _ in range(10):
            if engine.status.value in ("completed", "stopped", "failed"):
                break
            engine.step_event()

        assert state["job-001"] == "completed"


class TestTraceAndSnapshot:
    """M2-S06-E: Trace and snapshot proof."""

    def test_trace_order_matches_execution(self):
        reg, _ = _build_job_registry()
        engine = DiscreteSimulationEngine(_rc(), reg, trace_capacity=10)
        engine.initialize([_evt("start", simulation_time_s=0.0, event_type="JOB_START")])

        for _ in range(10):
            if engine.status.value in ("completed", "stopped", "failed"):
                break
            engine.step_event()

        snap = engine.to_snapshot()
        trace = snap.recent_events
        assert len(trace) == 3
        # Event types in order: JOB_START, JOB_PROCESS, JOB_CHECK
        assert [t.event_type for t in trace] == ["JOB_START", "JOB_PROCESS", "JOB_CHECK"]

    def test_pending_events_zero_at_completion(self):
        reg, _ = _build_job_registry()
        engine = DiscreteSimulationEngine(_rc(), reg)
        engine.initialize([_evt("start", simulation_time_s=0.0, event_type="JOB_START")])

        for _ in range(10):
            if engine.status.value in ("completed", "stopped", "failed"):
                break
            engine.step_event()

        snap = engine.to_snapshot()
        assert snap.pending_events == 0

    def test_diagnostics_contain_replay_metadata(self):
        reg, _ = _build_job_registry()
        engine = DiscreteSimulationEngine(_rc(random_seed=42), reg, max_processed_events=100, max_same_time_events=50)
        engine.initialize([_evt("start", simulation_time_s=0.0, event_type="JOB_START")])

        for _ in range(10):
            if engine.status.value in ("completed", "stopped", "failed"):
                break
            engine.step_event()

        d = engine.to_snapshot().diagnostics
        assert d.random_seed == 42
        assert d.max_processed_events_limit == 100
        assert d.same_time_event_limit == 50

    def test_state_changes_preserved_in_trace(self):
        """M2-S06-C01: HandlerOutcome.state_changes preserved in trace entries."""
        reg, _ = _build_job_registry()
        engine = DiscreteSimulationEngine(_rc(), reg, trace_capacity=10)
        engine.initialize([_evt("start", simulation_time_s=0.0, event_type="JOB_START")])

        for _ in range(10):
            if engine.status.value in ("completed", "stopped", "failed"):
                break
            engine.step_event()

        trace = engine.to_snapshot().recent_events
        assert len(trace) == 3

        # JOB_START → job-001:created→started
        assert trace[0].event_type == "JOB_START"
        assert "job-001:created→started" in trace[0].state_changes

        # JOB_PROCESS → job-001:started→processed
        assert trace[1].event_type == "JOB_PROCESS"
        assert "job-001:started→processed" in trace[1].state_changes

        # JOB_CHECK → job-001:processed→completed
        assert trace[2].event_type == "JOB_CHECK"
        assert "job-001:processed→completed" in trace[2].state_changes

        # Full chain verification
        all_changes = [sc for t in trace for sc in t.state_changes]
        assert all_changes == [
            "job-001:created→started",
            "job-001:started→processed",
            "job-001:processed→completed",
        ]


class TestDeterminism:
    """M2-S06-F: Deterministic replay equivalence."""

    def test_same_input_same_result(self):
        def _run(seed):
            reg, state = _build_job_registry()
            engine = DiscreteSimulationEngine(_rc(random_seed=seed, run_id="det-run"), reg)
            engine.initialize([_evt("start", simulation_time_s=0.0, event_type="JOB_START")])
            for _ in range(10):
                if engine.status.value in ("completed", "stopped", "failed"):
                    break
                engine.step_event()
            snap = engine.to_snapshot()
            return (snap.processed_events, snap.simulation_time_s, snap.status,
                    snap.pending_events, state["job-001"])

        r1 = _run(42)
        r2 = _run(42)
        assert r1 == r2

    def test_trace_identical_on_rerun(self):
        def _run():
            reg, _ = _build_job_registry()
            engine = DiscreteSimulationEngine(_rc(random_seed=1), reg, trace_capacity=10)
            engine.initialize([_evt("start", simulation_time_s=0.0, event_type="JOB_START")])
            for _ in range(10):
                if engine.status.value in ("completed", "stopped", "failed"):
                    break
                engine.step_event()
            return [t.event_type for t in engine.to_snapshot().recent_events]

        assert _run() == _run()


class TestSafetyCompatibility:
    """M2-S06-G: S05 safety limits don't block legitimate execution."""

    def test_max_events_not_triggered(self):
        reg, _ = _build_job_registry()
        engine = DiscreteSimulationEngine(_rc(), reg, max_processed_events=10)
        engine.initialize([_evt("start", simulation_time_s=0.0, event_type="JOB_START")])

        for _ in range(10):
            if engine.status.value in ("completed", "stopped", "failed"):
                break
            engine.step_event()

        snap = engine.to_snapshot()
        assert snap.status == "completed"  # NOT "stopped" by max-events guard

    def test_no_progress_not_triggered(self):
        reg, _ = _build_job_registry()
        engine = DiscreteSimulationEngine(_rc(), reg, max_same_time_events=5)
        engine.initialize([_evt("start", simulation_time_s=0.0, event_type="JOB_START")])

        for _ in range(10):
            if engine.status.value in ("completed", "stopped", "failed"):
                break
            engine.step_event()

        snap = engine.to_snapshot()
        assert snap.status == "completed"  # NOT "stopped" by no-progress guard


class TestSchedulerOrdering:
    """M2-S06-B: Scheduler ordering honored."""

    def test_time_order_honored(self):
        """Follow-up at later time executes after immediate events."""
        reg = HandlerRegistry()
        order = []

        def record_handler(event: ScheduledEvent) -> HandlerOutcome:
            order.append(event.event_id)
            return HandlerOutcome(event_id=event.event_id, success=True, follow_up_events=(), state_changes=())

        reg.register("boot", lambda e: HandlerOutcome(
            event_id=e.event_id, success=True,
            follow_up_events=(
                _evt("later", simulation_time_s=5.0, event_type="step"),
                _evt("sooner", simulation_time_s=2.0, event_type="step"),
            ), state_changes=(),
        ))
        reg.register("step", record_handler)

        engine = DiscreteSimulationEngine(_rc(), reg)
        engine.initialize([_evt("boot", simulation_time_s=1.0, event_type="boot")])

        for _ in range(10):
            if engine.status.value in ("completed", "stopped", "failed"):
                break
            engine.step_event()

        assert order == ["sooner", "later"]
