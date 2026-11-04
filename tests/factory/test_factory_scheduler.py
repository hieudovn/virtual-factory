from datetime import datetime, timezone

import pytest

from virtual_factory.factory import (
    CausalPhase,
    DuplicateEventError,
    EventProposal,
    FactoryHeader,
    FactoryRunContext,
    IdempotencyConflictError,
    ISimulationModule,
    ModuleCapability,
    ModuleManifest,
    PastEventError,
    SameTickBoundError,
    SchedulerError,
    SerialFactoryCoordinator,
    SimTick,
    UnsupportedCapabilityError,
)

HEADER = FactoryHeader(
    workspace_digest="sha256:workspace",
    config_digest="sha256:config",
    seed=7,
    model_revision="model-r1",
    epoch_utc=datetime(2026, 1, 1, tzinfo=timezone.utc),
)

ALL_CAPABILITIES = frozenset(ModuleCapability)


def _manifest(module_id, capabilities=ALL_CAPABILITIES):
    return ModuleManifest(
        module_id=module_id,
        version="1.0",
        fidelity="synthetic",
        input_ports=(),
        output_ports=(),
        capabilities=frozenset(capabilities),
        ownership="test",
    )


def _running_coordinator(modules, *, max_events_per_tick=1000):
    ctx = FactoryRunContext("run-1", HEADER)
    ctx.validate()
    ctx.initialize()
    coordinator = SerialFactoryCoordinator(
        ctx, max_events_per_tick=max_events_per_tick
    )
    for module in modules:
        coordinator.register_module(module)
    coordinator.initialize()
    ctx.mark_ready()
    ctx.start()
    return coordinator


class StaticProducer(ISimulationModule):
    def __init__(
        self,
        module_id,
        tick_us,
        event_id,
        *,
        phase=CausalPhase.PROCESS,
        payload=None,
        capabilities=ALL_CAPABILITIES,
    ):
        self.manifest = _manifest(module_id, capabilities)
        self._tick = SimTick(tick_us)
        self._event_id = event_id
        self._phase = phase
        self._payload = payload or {}
        self._committed = []

    def initialize(self):
        return None

    def next_event_time(self, horizon):
        if self._committed:
            return None
        return self._tick if self._tick <= horizon else None

    def propose(self, horizon, read_snapshot):
        if self._committed:
            return ()
        return (
            EventProposal(
                tick=self._tick,
                causal_phase=self._phase,
                module_id=self.manifest.module_id,
                local_sequence=0,
                event_id=self._event_id,
                event_type="produced",
                definition_digest="fixture-v1",
                payload=self._payload,
            ),
        )

    def apply_committed(self, event, read_snapshot):
        self._committed.append(event.event_id)

    def snapshot(self):
        return {"committed": list(self._committed)}

    def restore(self, state):
        self._committed = list(state["committed"])


class CausalReceiver(ISimulationModule):
    def __init__(self, module_id, tick_us, upstream_id):
        self.manifest = _manifest(module_id)
        self._tick = SimTick(tick_us)
        self._upstream_id = upstream_id
        self._committed = False
        self.seen_upstream = False

    def initialize(self):
        return None

    def next_event_time(self, horizon):
        if self._committed:
            return None
        return self._tick if self._tick <= horizon else None

    def propose(self, horizon, read_snapshot):
        if self._committed:
            return ()
        return (
            EventProposal(
                tick=self._tick,
                causal_phase=CausalPhase.INTAKE,
                module_id=self.manifest.module_id,
                local_sequence=0,
                event_id="event-B",
                event_type="started",
                definition_digest="fixture-v1",
                causation_id=self._upstream_id,
            ),
        )

    def apply_committed(self, event, read_snapshot):
        self.seen_upstream = read_snapshot.has_event(self._upstream_id)
        self._committed = True

    def snapshot(self):
        return {
            "committed": self._committed,
            "seen_upstream": self.seen_upstream,
        }

    def restore(self, state):
        self._committed = bool(state["committed"])
        self.seen_upstream = bool(state["seen_upstream"])


class RepeatingModule(ISimulationModule):
    def __init__(self, module_id, tick_us, local_sequence_mode):
        self.manifest = _manifest(module_id)
        self._tick = SimTick(tick_us)
        self._mode = local_sequence_mode
        self._count = 0

    def initialize(self):
        return None

    def next_event_time(self, horizon):
        return self._tick if self._tick <= horizon else None

    def propose(self, horizon, read_snapshot):
        local_sequence = 0 if self._mode == "fixed" else self._count
        return (
            EventProposal(
                tick=self._tick,
                causal_phase=CausalPhase.PROCESS,
                module_id=self.manifest.module_id,
                local_sequence=local_sequence,
                event_id=f"{self.manifest.module_id}-{self._count}",
                event_type="repeated",
                definition_digest="fixture-v1",
                payload={"count": self._count},
            ),
        )

    def apply_committed(self, event, read_snapshot):
        self._count += 1

    def snapshot(self):
        return {"count": self._count}

    def restore(self, state):
        self._count = int(state["count"])


class PastModule(ISimulationModule):
    def __init__(self, tick_us):
        self.manifest = _manifest("past-module")
        self._tick = SimTick(tick_us)

    def initialize(self):
        return None

    def next_event_time(self, horizon):
        return self._tick

    def propose(self, horizon, read_snapshot):
        return (
            EventProposal(
                tick=self._tick,
                causal_phase=CausalPhase.PROCESS,
                module_id=self.manifest.module_id,
                local_sequence=0,
                event_id="past-event",
                event_type="past",
                definition_digest="fixture-v1",
            ),
        )

    def apply_committed(self, event, read_snapshot):
        return None

    def snapshot(self):
        return {}

    def restore(self, state):
        return None


class EmptyModule(ISimulationModule):
    def __init__(self, tick_us):
        self.manifest = _manifest("empty-module")
        self._tick = SimTick(tick_us)

    def initialize(self):
        return None

    def next_event_time(self, horizon):
        return self._tick

    def propose(self, horizon, read_snapshot):
        return ()

    def apply_committed(self, event, read_snapshot):
        return None

    def snapshot(self):
        return {}

    def restore(self, state):
        return None


def test_shuffled_registration_order_yields_identical_trace_and_digest():
    first = _running_coordinator(
        [
            StaticProducer("module-a", 10, "event-a"),
            StaticProducer("module-b", 10, "event-b"),
        ]
    )
    second = _running_coordinator(
        [
            StaticProducer("module-b", 10, "event-b"),
            StaticProducer("module-a", 10, "event-a"),
        ]
    )
    first.run_until(SimTick(10))
    second.run_until(SimTick(10))
    assert first.ledger.trace() == second.ledger.trace()
    assert first.ledger.digest() == second.ledger.digest()
    assert [event["event_id"] for event in first.ledger.trace()] == [
        "event-a",
        "event-b",
    ]


def test_causal_receipt_precedes_dependent_start_despite_phase_priority():
    upstream = StaticProducer(
        "module-a", 10, "event-A", phase=CausalPhase.PROCESS
    )
    receiver = CausalReceiver("module-b", 10, "event-A")
    coordinator = _running_coordinator([receiver, upstream])
    coordinator.run_until(SimTick(10))
    trace = coordinator.ledger.trace()
    assert [event["event_id"] for event in trace] == ["event-A", "event-B"]
    assert trace[1]["causation_id"] == "event-A"
    assert receiver.seen_upstream is True


def test_past_event_is_rejected():
    ctx = FactoryRunContext("run-1", HEADER)
    ctx.validate()
    ctx.initialize()
    coordinator = SerialFactoryCoordinator(ctx)
    coordinator.register_module(PastModule(4))
    coordinator.initialize()
    ctx.mark_ready()
    ctx.start()
    ctx.advance_to(SimTick(5))
    with pytest.raises(PastEventError):
        coordinator.run_until(SimTick(10))


def test_no_progress_at_current_tick_fails_closed():
    coordinator = _running_coordinator([EmptyModule(10)])
    with pytest.raises(SchedulerError):
        coordinator.run_until(SimTick(10))
    assert coordinator.ledger.cursor == 0


def test_duplicate_event_id_raises_and_does_not_commit_twice():
    coordinator = _running_coordinator(
        [
            StaticProducer("module-a", 10, "same-event"),
            StaticProducer("module-b", 10, "same-event"),
        ]
    )
    with pytest.raises(DuplicateEventError):
        coordinator.run_until(SimTick(10))
    assert coordinator.ledger.cursor == 1


def test_conflicting_idempotency_key_raises():
    coordinator = _running_coordinator(
        [RepeatingModule("module-a", 10, "fixed")]
    )
    with pytest.raises(IdempotencyConflictError):
        coordinator.run_until(SimTick(10))
    assert coordinator.ledger.cursor == 1


def test_unsupported_capability_fails_closed():
    module = StaticProducer(
        "module-a",
        10,
        "event-a",
        capabilities=frozenset(
            {
                ModuleCapability.PROPOSE,
                ModuleCapability.APPLY,
                ModuleCapability.SNAPSHOT,
            }
        ),
    )
    ctx = FactoryRunContext("run-1", HEADER)
    coordinator = SerialFactoryCoordinator(ctx)
    with pytest.raises(UnsupportedCapabilityError):
        coordinator.register_module(module)


def test_bounded_zero_tick_cycle_fails_closed():
    coordinator = _running_coordinator(
        [RepeatingModule("module-a", 10, "unique")],
        max_events_per_tick=3,
    )
    with pytest.raises(SameTickBoundError):
        coordinator.run_until(SimTick(10))
    assert coordinator.ledger.cursor == 3
