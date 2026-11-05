"""Crash, checkpoint and source-journal rebuild oracles."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from virtual_factory.factory import (
    CausalPhase,
    CommittedEvent,
    FactoryHeader,
    FactoryRunContext,
    LifecycleState,
    SerialFactoryCoordinator,
    SimTick,
)
from virtual_factory.factory.event_ledger import canonical_digest
from virtual_factory.factory.integration import (
    BridgeCheckpointError,
    BridgePolicy,
    MaterialBridge,
    MaterialIntent,
    MaterialOutcomeStatus,
    ProjectionStatus,
)
from virtual_factory.factory.material import (
    CorruptJournalError,
    MaterialFlowLedger,
)

RUN_ID = "run-1"
GENERATION = 1
DEFINITION_DIGEST = "sha256:material-definition"
HEADER = FactoryHeader(
    workspace_digest="sha256:workspace",
    config_digest="sha256:config",
    seed=7,
    model_revision="model-r1",
    epoch_utc=datetime(2026, 1, 1, tzinfo=timezone.utc),
)


def _new_ledger(tmp_path):
    return MaterialFlowLedger(
        tmp_path,
        factory_run_id=RUN_ID,
        generation=GENERATION,
        definition_digest=DEFINITION_DIGEST,
        config_digest=HEADER.config_digest,
        model_revision=HEADER.model_revision,
        seed=HEADER.seed,
        buffers={"buffer:line": {"capacity": None}},
        quality_fixture={"stator-1": "ACCEPTED"},
        scope_fixture={},
    )


def _new_bridge(ledger, *, start=False):
    context = FactoryRunContext(
        RUN_ID, HEADER, generation=GENERATION
    )
    context.validate()
    context.initialize()
    coordinator = SerialFactoryCoordinator(context)
    bridge = MaterialBridge(
        context,
        ledger,
        coordinator,
        definition_digest=DEFINITION_DIGEST,
        policy=BridgePolicy(),
    )
    if start:
        coordinator.initialize()
        context.mark_ready()
        context.start()
    return context, coordinator, bridge


def _bridge(tmp_path):
    ledger = _new_ledger(tmp_path)
    context, coordinator, bridge = _new_bridge(
        ledger, start=True
    )
    return context, ledger, coordinator, bridge


def _leg(material_id, *, quantity="1"):
    return {
        "material_id": material_id,
        "material_type": "part",
        "quantity": quantity,
        "unit": "EA",
        "from_location": "buffer:line",
        "to_location": None,
    }


def _tx(
    transaction_id,
    idempotency_key,
    tick_us,
    expected_version,
    transaction_type,
    legs,
    *,
    operation_execution_id=None,
    child_refs=None,
):
    return {
        "contract_version": "vf-material-transaction-v0.1",
        "factory_run_id": RUN_ID,
        "generation": GENERATION,
        "transaction_id": transaction_id,
        "idempotency_key": idempotency_key,
        "simulation_tick_us": tick_us,
        "ledger_expected_version": expected_version,
        "transaction_type": transaction_type,
        "operation_execution_id": operation_execution_id,
        "transfer_id": None,
        "recipe_revision": None,
        "legs": legs,
        "parent_refs": [],
        "child_refs": child_refs or [],
        "source_kind": "SIMULATED",
        "definition_provenance": "SYNTHETIC_ASSUMPTION",
    }


def _intent(transaction, *, origin_module_id="station:op10"):
    return MaterialIntent(
        run_id=RUN_ID,
        generation=GENERATION,
        tick_us=transaction["simulation_tick_us"],
        origin_module_id=origin_module_id,
        local_sequence=0,
        transaction_id=transaction["transaction_id"],
        idempotency_key=transaction["idempotency_key"],
        transaction=transaction,
        expected_ledger_version=transaction[
            "ledger_expected_version"
        ],
    )


def _seed(bridge):
    produce = _tx(
        "tx-produce",
        "key-produce",
        0,
        0,
        "PRODUCE",
        [
            {
                "material_id": "stator-1",
                "material_type": "part",
                "quantity": "1",
                "unit": "EA",
                "from_location": None,
                "to_location": "buffer:line",
            }
        ],
        child_refs=["stator-1"],
    )
    outcome = bridge.commit_material_intent(_intent(produce))
    assert outcome.status is MaterialOutcomeStatus.COMMITTED
    assert bridge.project_pending(0) is ProjectionStatus.UP_TO_DATE


def _reserve(
    *,
    tx_id="tx-reserve",
    key="key-reserve",
    tick=10,
    expected_version=1,
):
    return _tx(
        tx_id,
        key,
        tick,
        expected_version,
        "RESERVE",
        [_leg("stator-1")],
        operation_execution_id="op:1",
    )


def test_projection_exception_preserves_committed_material(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    outcome = bridge.commit_material_intent(_intent(_reserve()))
    assert outcome.status is MaterialOutcomeStatus.COMMITTED
    version = ledger.version
    state_digest = ledger.state_digest()
    outbox_ids = tuple(record.event_id for record in ledger.outbox)
    genealogy = tuple(ledger.genealogy)
    event_id = outcome.outbox_ids[0]

    original = bridge.projection.apply_committed

    def raising_apply(event, snapshot):
        raise RuntimeError("injected projection interruption")

    bridge.projection.apply_committed = raising_apply
    try:
        status = bridge.project_pending(10)
    finally:
        bridge.projection.apply_committed = original

    assert status is ProjectionStatus.PENDING
    assert ledger.version == version
    assert ledger.state_digest() == state_digest
    assert tuple(record.event_id for record in ledger.outbox) == outbox_ids
    assert tuple(ledger.genealogy) == genealogy
    assert coordinator.ledger.get_event(event_id) is None
    assert bridge.projection.source_cursor == 1

    assert bridge.project_pending(10) is ProjectionStatus.UP_TO_DATE
    assert coordinator.ledger.get_event(event_id) is not None
    assert (
        len(
            [
                item
                for item in coordinator.ledger.events
                if item.event_id == event_id
            ]
        )
        == 1
    )
    assert ledger.version == version
    assert len(ledger.outbox) == len(outbox_ids)


def test_post_commit_pre_projection_restart_rebuilds_once(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    outcome = bridge.commit_material_intent(_intent(_reserve()))
    assert outcome.status is MaterialOutcomeStatus.COMMITTED
    version = ledger.version
    state_digest = ledger.state_digest()
    outbox_ids = tuple(record.event_id for record in ledger.outbox)
    genealogy_digest = canonical_digest(
        [edge.to_dict() for edge in ledger.genealogy]
    )
    assert coordinator.ledger.get_event(outcome.outbox_ids[0]) is None

    ledger.close()
    reopened = _new_ledger(tmp_path)
    try:
        new_context, new_coordinator, rebuilt = _new_bridge(
            reopened, start=False
        )
        status = rebuilt.restore_or_rebuild()
        assert status is ProjectionStatus.UP_TO_DATE
        assert rebuilt.context.generation == GENERATION
        assert rebuilt.context.tick_us == 10
        assert reopened.version == version
        assert reopened.state_digest() == state_digest
        assert tuple(
            record.event_id for record in reopened.outbox
        ) == outbox_ids
        assert canonical_digest(
            [edge.to_dict() for edge in reopened.genealogy]
        ) == genealogy_digest
        projected_ids = [
            event.event_id
            for event in rebuilt.coordinator.ledger.events
            if event.module_id == rebuilt.projection.manifest.module_id
        ]
        assert projected_ids == list(outbox_ids)
        assert len(projected_ids) == len(set(projected_ids))
    finally:
        reopened.close()


def test_checkpoint_roundtrip_restores_projection_and_ledger(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    outcome = bridge.commit_material_intent(_intent(_reserve()))
    assert outcome.status is MaterialOutcomeStatus.COMMITTED
    assert bridge.project_pending(10) is ProjectionStatus.UP_TO_DATE
    context.pause()
    checkpoint = bridge.checkpoint()
    assert checkpoint.source_cursor == len(ledger.outbox)
    assert checkpoint.material_ledger_version == ledger.version
    assert checkpoint.identity == bridge.identity
    assert (
        checkpoint.projection_trace
        == bridge.projection.projected_items()
    )

    new_context, new_coordinator, new_bridge = _new_bridge(
        ledger, start=False
    )
    status = new_bridge.restore_or_rebuild(checkpoint.to_dict())
    assert status is ProjectionStatus.UP_TO_DATE
    assert new_bridge.context.state is LifecycleState.PAUSED
    assert new_bridge.context.tick_us == 10
    assert (
        new_bridge.coordinator.trace_digest()
        == coordinator.trace_digest()
    )
    assert (
        new_bridge.projection.projected_items()
        == bridge.projection.projected_items()
    )
    assert new_bridge.reconcile_committed_outbox() is (
        ProjectionStatus.UP_TO_DATE
    )


def test_checkpoint_rejects_running_or_pending_boundaries(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    with pytest.raises(BridgeCheckpointError):
        bridge.checkpoint()

    outcome = bridge.commit_material_intent(_intent(_reserve()))
    assert outcome.status is MaterialOutcomeStatus.COMMITTED
    context.pause()
    with pytest.raises(BridgeCheckpointError):
        bridge.checkpoint()
    context.resume()
    assert bridge.project_pending(10) is ProjectionStatus.UP_TO_DATE
    context.pause()
    checkpoint = bridge.checkpoint()
    assert checkpoint.source_cursor == 2


def test_tampered_checkpoint_is_rejected_before_restore(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    context.pause()
    checkpoint = bridge.checkpoint()
    data = checkpoint.to_dict()
    data["material_state_digest"] = "0" * 64
    data["checkpoint_digest"] = ""

    with pytest.raises(BridgeCheckpointError):
        bridge.restore_or_rebuild(data)
    assert context.state is LifecycleState.PAUSED
    assert bridge.reconcile_committed_outbox() is (
        ProjectionStatus.UP_TO_DATE
    )


def test_restore_rejects_identity_generation_mismatch(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    context.pause()
    checkpoint = bridge.checkpoint()
    data = checkpoint.to_dict()
    data["identity"]["generation"] = 2
    data["checkpoint_digest"] = ""
    data["identity_digest"] = ""
    with pytest.raises(BridgeCheckpointError):
        bridge.restore_or_rebuild(data)


def test_non_material_coordinator_events_require_recovery(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    foreign = CommittedEvent(
        factory_run_id=RUN_ID,
        generation=GENERATION,
        module_id="foreign-module",
        local_sequence=0,
        tick=SimTick(0),
        event_id="foreign-event",
        event_type="foreign",
        sequence=coordinator.ledger.cursor + 1,
        causal_phase=CausalPhase.PROCESS,
        definition_digest=DEFINITION_DIGEST,
    )
    coordinator.ledger.append(foreign)
    version = ledger.version
    assert bridge.restore_or_rebuild() is (
        ProjectionStatus.RECOVERY_REQUIRED
    )
    assert ledger.version == version
    assert "non-material events" in bridge.last_error


def test_corrupted_committed_journal_fails_closed_on_reopen(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    outcome = bridge.commit_material_intent(_intent(_reserve()))
    assert outcome.status is MaterialOutcomeStatus.COMMITTED
    journal = ledger.journal_path
    ledger.close()
    data = bytearray(journal.read_bytes())
    data[-1] ^= 0xFF
    journal.write_bytes(bytes(data))
    with pytest.raises(CorruptJournalError):
        _new_ledger(tmp_path)


def test_checkpoint_restore_revalidates_existing_projected_event_once(
    tmp_path,
):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    outcome = bridge.commit_material_intent(_intent(_reserve()))
    assert outcome.status is MaterialOutcomeStatus.COMMITTED
    assert bridge.project_pending(10) is ProjectionStatus.UP_TO_DATE
    context.pause()
    checkpoint = bridge.checkpoint()
    assert len(coordinator.ledger.events) == 2

    empty = bridge.projection.snapshot()
    empty["source_cursor"] = 0
    empty["projection"] = []
    empty["projection_trace_digest"] = canonical_digest([])
    bridge.projection.restore(empty)
    assert bridge.reconcile_committed_outbox() is (
        ProjectionStatus.INCOMPATIBLE
    )
    assert len(coordinator.ledger.events) == 2

    assert bridge.restore_or_rebuild(checkpoint) is (
        ProjectionStatus.UP_TO_DATE
    )
    events = [
        event
        for event in bridge.coordinator.ledger.events
        if event.event_id == outcome.outbox_ids[0]
    ]
    assert len(events) == 1
    assert ledger.version == 2
