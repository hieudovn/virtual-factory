"""Deterministic same-tick contention and replay-identity oracles."""

from __future__ import annotations

from datetime import datetime, timezone

from virtual_factory.factory import (
    FactoryHeader,
    FactoryRunContext,
    SerialFactoryCoordinator,
)
from virtual_factory.factory.event_ledger import canonical_digest
from virtual_factory.factory.integration import (
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
        quality_fixture={"stator-1": "ACCEPTED"},
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


def _leg(material_id):
    return {
        "material_id": material_id,
        "material_type": "part",
        "quantity": "1",
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


def _intent(
    transaction,
    *,
    origin_module_id,
    local_sequence=0,
):
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
    outcome = bridge.commit_material_intent(
        _intent(produce, origin_module_id="station:seed")
    )
    assert outcome.status is MaterialOutcomeStatus.COMMITTED
    assert bridge.project_pending(0) is ProjectionStatus.UP_TO_DATE


def _reserve(name, expected_version, *, origin=None):
    return _tx(
        f"tx-{name}",
        f"key-{name}",
        10,
        expected_version,
        "RESERVE",
        [_leg("stator-1")],
        operation_execution_id=f"op-{name}",
    )


def test_same_tick_contenders_have_one_stable_winner(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    outcomes = bridge.commit_material_intents(
        [
            _intent(
                _reserve("a", 1),
                origin_module_id="station:a",
            ),
            _intent(
                _reserve("b", 2),
                origin_module_id="station:b",
            ),
        ]
    )
    assert [outcome.status for outcome in outcomes] == [
        MaterialOutcomeStatus.COMMITTED,
        MaterialOutcomeStatus.WAITING_FOR_MATERIAL,
    ]
    assert ledger.version == 2
    assert len(ledger.reservations) == 1
    assert "tx-a" in ledger.reservations
    assert "tx-b" not in ledger.reservations
    assert outcomes[0].outbox_ids == (
        ledger.outbox[-1].event_id,
    )
    assert outcomes[1].outbox_ids == ()
    assert len(ledger.outbox) == 2


def test_input_order_does_not_change_same_tick_winner(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    outcomes = bridge.commit_material_intents(
        [
            _intent(
                _reserve("b", 2),
                origin_module_id="station:b",
            ),
            _intent(
                _reserve("a", 1),
                origin_module_id="station:a",
            ),
        ]
    )
    assert [outcome.transaction_id for outcome in outcomes] == [
        "tx-a",
        "tx-b",
    ]
    assert [outcome.status for outcome in outcomes] == [
        MaterialOutcomeStatus.COMMITTED,
        MaterialOutcomeStatus.WAITING_FOR_MATERIAL,
    ]
    assert len(ledger.reservations) == 1
    assert "tx-a" in ledger.reservations


def test_local_sequence_breaks_ties_within_one_origin(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    outcomes = bridge.commit_material_intents(
        [
            _intent(
                _reserve("second", 2),
                origin_module_id="station:a",
                local_sequence=1,
            ),
            _intent(
                _reserve("first", 1),
                origin_module_id="station:a",
                local_sequence=0,
            ),
        ]
    )
    assert [outcome.transaction_id for outcome in outcomes] == [
        "tx-first",
        "tx-second",
    ]
    assert outcomes[0].status is MaterialOutcomeStatus.COMMITTED
    assert (
        outcomes[1].status
        is MaterialOutcomeStatus.WAITING_FOR_MATERIAL
    )


def test_duplicate_outbox_replay_is_projected_exactly_once(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    intent = _intent(
        _reserve("a", 1), origin_module_id="station:a"
    )
    first = bridge.commit_material_intent(intent)
    duplicate = bridge.commit_material_intent(intent)
    assert first.status is MaterialOutcomeStatus.COMMITTED
    assert duplicate.status is MaterialOutcomeStatus.COMMITTED
    assert duplicate.receipt is not None
    assert duplicate.receipt.idempotent_replay is True
    assert duplicate.outbox_ids == first.outbox_ids
    assert len(ledger.outbox) == 2
    assert ledger.version == 2

    assert bridge.project_pending(10) is ProjectionStatus.UP_TO_DATE
    events = [
        event
        for event in coordinator.ledger.events
        if event.event_id == first.outbox_ids[0]
    ]
    assert len(events) == 1
    assert ledger.version == 2
    assert ledger.stock("stator-1") == 1
    assert bridge.reconcile_committed_outbox() is (
        ProjectionStatus.UP_TO_DATE
    )

    after_projection = bridge.commit_material_intent(intent)
    assert after_projection.receipt is not None
    assert after_projection.receipt.idempotent_replay is True
    assert bridge.project_pending(10) is ProjectionStatus.UP_TO_DATE
    events = [
        event
        for event in coordinator.ledger.events
        if event.event_id == first.outbox_ids[0]
    ]
    assert len(events) == 1
    assert ledger.version == 2


def test_two_identical_replays_have_equal_canonical_digests(tmp_path):
    def run(path):
        context, ledger, coordinator, bridge = _bridge(path)
        _seed(bridge)
        outcome = bridge.commit_material_intent(
            _intent(
                _reserve("a", 1), origin_module_id="station:a"
            )
        )
        assert outcome.status is MaterialOutcomeStatus.COMMITTED
        assert bridge.project_pending(10) is ProjectionStatus.UP_TO_DATE
        result = {
            "ledger_state": ledger.state_digest(),
            "ledger_version": ledger.version,
            "outbox": [record.to_dict() for record in ledger.outbox],
            "event_trace": canonical_digest(
                [event.to_dict() for event in coordinator.ledger.events]
            ),
            "projection_trace": canonical_digest(
                list(bridge.projection.projected_items())
            ),
            "event_ids": [
                event.event_id for event in coordinator.ledger.events
            ],
        }
        ledger.close()
        return result

    first = run(tmp_path / "replay-a")
    second = run(tmp_path / "replay-b")
    assert first == second
