"""Source-only outbox projection and deterministic ordering oracles."""

from __future__ import annotations

from datetime import datetime, timezone

from virtual_factory.factory import (
    FactoryHeader,
    FactoryRunContext,
    SerialFactoryCoordinator,
    SimTick,
)
from virtual_factory.factory.event_ledger import canonical_digest
from virtual_factory.factory.integration import (
    PROJECTION_MODULE_ID,
    BridgePolicy,
    MaterialBridge,
    MaterialIntent,
    MaterialOutcomeStatus,
    ProjectionStatus,
)
from virtual_factory.factory.material import MaterialFlowLedger

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


def _ledger(tmp_path):
    return MaterialFlowLedger(
        tmp_path,
        factory_run_id=RUN_ID,
        generation=GENERATION,
        definition_digest=DEFINITION_DIGEST,
        config_digest=HEADER.config_digest,
        model_revision=HEADER.model_revision,
        seed=HEADER.seed,
        buffers={"buffer:line": {"capacity": None}},
        quality_fixture={
            "stator-1": "ACCEPTED",
            "stator-2": "ACCEPTED",
        },
        scope_fixture={},
    )


def _bridge(tmp_path):
    ledger = _ledger(tmp_path)
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
    coordinator.initialize()
    context.mark_ready()
    context.start()
    return context, ledger, coordinator, bridge


def _leg(
    material_id,
    quantity="1",
    *,
    material_type="part",
    from_location="buffer:line",
    to_location=None,
):
    return {
        "material_id": material_id,
        "material_type": material_type,
        "quantity": quantity,
        "unit": "EA",
        "from_location": from_location,
        "to_location": to_location,
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


def _intent(transaction, *, origin_module_id="station:op10", local_sequence=0):
    return MaterialIntent(
        run_id=RUN_ID,
        generation=GENERATION,
        tick_us=transaction["simulation_tick_us"],
        origin_module_id=origin_module_id,
        local_sequence=local_sequence,
        transaction_id=transaction["transaction_id"],
        idempotency_key=transaction["idempotency_key"],
        transaction=transaction,
        expected_ledger_version=transaction[
            "ledger_expected_version"
        ],
    )


def _seed(
    bridge,
    *,
    material_id="stator-1",
    tx_id="tx-produce",
    key="key-produce",
):
    produce = _tx(
        tx_id,
        key,
        0,
        bridge.ledger.version,
        "PRODUCE",
        [
            _leg(
                material_id,
                from_location=None,
                to_location="buffer:line",
            )
        ],
        child_refs=[material_id],
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
    material_id="stator-1",
    origin_module_id="station:op10",
    local_sequence=0,
    operation_execution_id="op:1",
):
    return _tx(
        tx_id,
        key,
        tick,
        expected_version,
        "RESERVE",
        [
            _leg(
                material_id,
                from_location="buffer:line",
                to_location=None,
            )
        ],
        operation_execution_id=operation_execution_id,
    )


def test_projection_matches_committed_outbox_and_bridge_policy(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    reserve = bridge.commit_material_intent(
        _intent(_reserve(), origin_module_id="station:op20")
    )
    assert reserve.status is MaterialOutcomeStatus.COMMITTED
    source = ledger.outbox[-1]
    assert reserve.outbox_ids == (source.event_id,)

    assert bridge.reconcile_committed_outbox() is ProjectionStatus.PENDING
    assert bridge.project_pending(10) is ProjectionStatus.UP_TO_DATE
    event = coordinator.ledger.get_event(source.event_id)
    assert event is not None
    assert event.event_id == source.event_id
    assert event.tick.tick_us == 10
    assert event.local_sequence == 1
    assert event.module_id == PROJECTION_MODULE_ID
    assert event.event_type == "MATERIAL_RESERVED"
    assert event.source_kind == "SIMULATED"
    assert (
        event.definition_provenance
        == "SYNTHETIC_ASSUMPTION"
    )
    assert event.definition_digest == DEFINITION_DIGEST
    payload = dict(event.payload)
    assert payload["transaction_id"] == "tx-reserve"
    assert payload["idempotency_key"] == "key-reserve"
    assert payload["ledger_version"] == reserve.receipt.ledger_version
    assert payload["source_outbox_id"] == source.event_id
    assert payload["source_outbox_digest"] == canonical_digest(
        source.to_dict()
    )
    assert payload["source_tick_us"] == 10
    assert payload["source_material_ids"] == ("stator-1",)


def test_propose_is_side_effect_free_and_does_not_commit_material(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    reserve = bridge.commit_material_intent(_intent(_reserve()))
    assert reserve.status is MaterialOutcomeStatus.COMMITTED
    version = ledger.version
    state_digest = ledger.state_digest()
    outbox_count = len(ledger.outbox)
    genealogy = tuple(ledger.genealogy)
    event_count = coordinator.ledger.cursor
    cursor = bridge.projection.source_cursor

    context.advance_to(SimTick(10))
    snapshot = coordinator.read_snapshot()
    proposals = bridge.projection.propose(SimTick(10), snapshot)
    assert len(proposals) == 1
    assert proposals[0].event_id == ledger.outbox[-1].event_id
    assert proposals[0].tick == SimTick(10)

    assert ledger.version == version
    assert ledger.state_digest() == state_digest
    assert len(ledger.outbox) == outbox_count
    assert tuple(ledger.genealogy) == genealogy
    assert coordinator.ledger.cursor == event_count
    assert bridge.projection.source_cursor == cursor


def test_next_event_time_is_earliest_unprojected_within_horizon(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    bridge.commit_material_intent(_intent(_reserve(tick=20)))
    assert bridge.projection.next_event_time(SimTick(9)) is None
    assert bridge.projection.next_event_time(SimTick(19)) is None
    assert bridge.projection.next_event_time(SimTick(20)) == SimTick(20)
    assert bridge.project_pending(20) is ProjectionStatus.UP_TO_DATE
    assert bridge.projection.next_event_time(SimTick(20)) is None


def test_pending_source_is_not_reported_as_pass(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    bridge.commit_material_intent(_intent(_reserve()))
    assert bridge.reconcile_committed_outbox() is ProjectionStatus.PENDING
    assert coordinator.ledger.cursor == 1
    assert bridge.project_pending(10) is ProjectionStatus.UP_TO_DATE
    assert bridge.reconcile_committed_outbox() is ProjectionStatus.UP_TO_DATE
    assert coordinator.ledger.cursor == 2


def test_future_outbox_waits_for_exact_event_time(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    future = bridge.commit_material_intent(
        _intent(_reserve(tick=100))
    )
    assert future.status is MaterialOutcomeStatus.COMMITTED
    assert context.tick_us == 0
    assert bridge.project_pending(50) is ProjectionStatus.PENDING
    assert context.tick_us == 0
    assert coordinator.ledger.get_event(future.outbox_ids[0]) is None
    assert bridge.project_pending(100) is ProjectionStatus.UP_TO_DATE
    assert context.tick_us == 100
    event = coordinator.ledger.get_event(future.outbox_ids[0])
    assert event is not None
    assert event.tick.tick_us == 100


def test_source_older_than_coordinator_clock_requires_recovery(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    reserve = bridge.commit_material_intent(_intent(_reserve(tick=10)))
    assert reserve.status is MaterialOutcomeStatus.COMMITTED
    context.advance_to(SimTick(50))
    assert (
        bridge.reconcile_committed_outbox()
        is ProjectionStatus.RECOVERY_REQUIRED
    )
    assert (
        bridge.project_pending(50)
        is ProjectionStatus.RECOVERY_REQUIRED
    )
    assert coordinator.ledger.get_event(reserve.outbox_ids[0]) is None
    assert "older than the coordinator clock" in bridge.last_error


def test_projection_preserves_source_outbox_order(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    _seed(
        bridge,
        material_id="stator-2",
        tx_id="tx-produce-2",
        key="key-produce-2",
    )
    outcomes = bridge.commit_material_intents(
        [
            _intent(
                _reserve(
                    tx_id="tx-b",
                    key="key-b",
                    expected_version=3,
                    material_id="stator-2",
                    origin_module_id="station:b",
                    operation_execution_id="op:b",
                )
            ),
            _intent(
                _reserve(
                    tx_id="tx-a",
                    key="key-a",
                    expected_version=2,
                    origin_module_id="station:a",
                    operation_execution_id="op:a",
                )
            ),
        ]
    )
    assert [item.status for item in outcomes] == [
        MaterialOutcomeStatus.COMMITTED,
        MaterialOutcomeStatus.COMMITTED,
    ]
    assert bridge.project_pending(10) is ProjectionStatus.UP_TO_DATE
    source_ids = [record.event_id for record in ledger.outbox]
    projected_ids = [
        item["event_id"]
        for item in bridge.projection.projected_items()
    ]
    assert projected_ids == source_ids
    projected_events = [
        event
        for event in coordinator.ledger.events
        if event.module_id == PROJECTION_MODULE_ID
    ]
    assert [event.local_sequence for event in projected_events] == [
        0,
        1,
        2,
        3,
    ]
    assert [event.event_id for event in projected_events] == source_ids
