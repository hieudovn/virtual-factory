import copy
from datetime import datetime, timezone

import pytest

from virtual_factory.factory import (
    CausalPhase,
    CheckpointError,
    EventProposal,
    FactoryHeader,
    FactoryRunContext,
    ISimulationModule,
    LifecycleState,
    ModuleCapability,
    ModuleManifest,
    ProposalError,
    SerialFactoryCoordinator,
    SimTick,
)

HEADER = FactoryHeader(
    workspace_digest="sha256:workspace",
    config_digest="sha256:config",
    seed=11,
    model_revision="model-r1",
    epoch_utc=datetime(2026, 1, 1, tzinfo=timezone.utc),
)

ALL_CAPABILITIES = frozenset(ModuleCapability)


def _manifest(module_id):
    return ModuleManifest(
        module_id=module_id,
        version="1.0",
        fidelity="synthetic",
        input_ports=(),
        output_ports=(),
        capabilities=ALL_CAPABILITIES,
        ownership="test",
    )


def _running_coordinator(module):
    ctx = FactoryRunContext("run-1", HEADER)
    ctx.validate()
    ctx.initialize()
    coordinator = SerialFactoryCoordinator(ctx)
    coordinator.register_module(module)
    coordinator.initialize()
    ctx.mark_ready()
    ctx.start()
    return coordinator


class PurityModule(ISimulationModule):
    def __init__(self):
        self.manifest = _manifest("purity-module")
        self._committed = []

    def initialize(self):
        return None

    def next_event_time(self, horizon):
        return SimTick(10) if not self._committed else None

    def propose(self, horizon, read_snapshot):
        return (
            EventProposal(
                tick=SimTick(10),
                causal_phase=CausalPhase.PROCESS,
                module_id=self.manifest.module_id,
                local_sequence=0,
                event_id="purity-event",
                event_type="purity",
                definition_digest="fixture-v1",
                payload={"value": 1},
            ),
        )

    def apply_committed(self, event, read_snapshot):
        self._committed.append(event.event_id)

    def snapshot(self):
        return {"committed": list(self._committed)}

    def restore(self, state):
        self._committed = list(state["committed"])


class ExplodingModule(ISimulationModule):
    def __init__(self):
        self.manifest = _manifest("exploding-module")
        self._committed = []

    def initialize(self):
        return None

    def next_event_time(self, horizon):
        return SimTick(10)

    def propose(self, horizon, read_snapshot):
        raise RuntimeError("controlled proposal failure")

    def apply_committed(self, event, read_snapshot):
        self._committed.append(event.event_id)

    def snapshot(self):
        return {"committed": list(self._committed)}

    def restore(self, state):
        self._committed = list(state["committed"])


class CounterModule(ISimulationModule):
    def __init__(self, total=3):
        self.manifest = _manifest("counter-module")
        self._total = total
        self._applied = []

    def initialize(self):
        return None

    def next_event_time(self, horizon):
        if len(self._applied) >= self._total:
            return None
        tick = SimTick(10 * (len(self._applied) + 1))
        return tick if tick <= horizon else None

    def propose(self, horizon, read_snapshot):
        index = len(self._applied)
        return (
            EventProposal(
                tick=SimTick(10 * (index + 1)),
                causal_phase=CausalPhase.PROCESS,
                module_id=self.manifest.module_id,
                local_sequence=index,
                event_id=f"counter-{index}",
                event_type="counted",
                definition_digest="fixture-v1",
                payload={"index": index},
            ),
        )

    def apply_committed(self, event, read_snapshot):
        self._applied.append(event.event_id)

    def snapshot(self):
        return {"applied": list(self._applied)}

    def restore(self, state):
        self._applied = list(state["applied"])


def test_proposals_are_pure_and_snapshots_are_immutable():
    module = PurityModule()
    coordinator = _running_coordinator(module)
    snapshot = coordinator.read_snapshot()
    before = module.snapshot()
    proposals = module.propose(SimTick(10), snapshot)
    assert module.snapshot() == before
    assert coordinator.ledger.cursor == 0
    assert snapshot.events == ()
    with pytest.raises(TypeError):
        proposals[0].payload["value"] = 2
    with pytest.raises(TypeError):
        snapshot.events[0] = proposals[0]


def test_controlled_module_exception_creates_no_partial_event():
    module = ExplodingModule()
    coordinator = _running_coordinator(module)
    before = module.snapshot()
    with pytest.raises(ProposalError):
        coordinator.run_until(SimTick(10))
    assert coordinator.ledger.cursor == 0
    assert coordinator.ledger.trace() == ()
    assert module.snapshot() == before


def test_pause_checkpoint_restore_preserves_order_cursor_and_replay():
    coordinator = _running_coordinator(CounterModule())
    coordinator.run_until(SimTick(20))
    coordinator.context.pause()
    checkpoint = coordinator.checkpoint()
    saved_trace = coordinator.ledger.trace()
    saved_digest = coordinator.ledger.digest()
    assert coordinator.ledger.cursor == 2

    coordinator.context.resume()
    coordinator.run_until(SimTick(30))
    coordinator.context.pause()
    full_trace = coordinator.ledger.trace()
    full_digest = coordinator.ledger.digest()
    assert coordinator.ledger.cursor == 3

    coordinator.restore(checkpoint)
    assert coordinator.context.state is LifecycleState.PAUSED
    assert coordinator.context.tick_us == 20
    assert coordinator.ledger.cursor == 2
    assert coordinator.ledger.trace() == saved_trace
    assert coordinator.ledger.digest() == saved_digest

    coordinator.context.resume()
    coordinator.run_until(SimTick(30))
    assert coordinator.ledger.trace() == full_trace
    assert coordinator.ledger.digest() == full_digest


def test_checkpoint_rejects_wrong_generation_and_revision():
    coordinator = _running_coordinator(CounterModule())
    coordinator.run_until(SimTick(10))
    coordinator.context.pause()
    checkpoint = coordinator.checkpoint()

    wrong_generation = copy.deepcopy(checkpoint)
    wrong_generation["generation"] += 1
    with pytest.raises(CheckpointError):
        coordinator.restore(wrong_generation)

    wrong_revision = copy.deepcopy(checkpoint)
    wrong_revision["model_revision"] = "model-r2"
    with pytest.raises(CheckpointError):
        coordinator.restore(wrong_revision)
