"""Frozen identity, policy and material-outcome contract oracles."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from virtual_factory.factory import (
    FactoryHeader,
    FactoryRunContext,
    SerialFactoryCoordinator,
    SimTick,
)
from virtual_factory.factory.integration import (
    BridgeContractError,
    BridgeIdentityError,
    BridgePolicy,
    MaterialBridge,
    MaterialIntent,
    MaterialOutcomeStatus,
    ProjectionStatus,
)
from virtual_factory.factory.material import (
    MaterialFlowLedger,
    QualityStatus,
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


def _ledger(tmp_path, **overrides):
    values = {
        "factory_run_id": RUN_ID,
        "generation": GENERATION,
        "definition_digest": DEFINITION_DIGEST,
        "config_digest": HEADER.config_digest,
        "model_revision": HEADER.model_revision,
        "seed": HEADER.seed,
        "buffers": {"buffer:line": {"capacity": None}},
        "quality_fixture": {
            "stator-1": "ACCEPTED",
            "stator-2": "ACCEPTED",
            "hold-part": "HOLD",
        },
        "scope_fixture": {},
    }
    values.update(overrides)
    return MaterialFlowLedger(tmp_path, **values)


def _context(*, generation=GENERATION, run_id=RUN_ID):
    context = FactoryRunContext(
        run_id, HEADER, generation=generation
    )
    context.validate()
    context.initialize()
    return context


def _bridge(tmp_path, *, horizon_us=None):
    ledger = _ledger(tmp_path)
    context = _context()
    coordinator = SerialFactoryCoordinator(context)
    bridge = MaterialBridge(
        context,
        ledger,
        coordinator,
        definition_digest=DEFINITION_DIGEST,
        policy=BridgePolicy(),
        horizon_us=horizon_us,
    )
    coordinator.initialize()
    context.mark_ready()
    context.start()
    return context, ledger, coordinator, bridge


def _leg(
    material_id,
    quantity="1",
    unit="EA",
    *,
    material_type="part",
    from_location="buffer:line",
    to_location=None,
):
    return {
        "material_id": material_id,
        "material_type": material_type,
        "quantity": quantity,
        "unit": unit,
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
    run_id=RUN_ID,
    generation=GENERATION,
    operation_execution_id=None,
    child_refs=None,
    source_kind="SIMULATED",
    definition_provenance="SYNTHETIC_ASSUMPTION",
):
    return {
        "contract_version": "vf-material-transaction-v0.1",
        "factory_run_id": run_id,
        "generation": generation,
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
        "source_kind": source_kind,
        "definition_provenance": definition_provenance,
    }


def _intent(
    transaction,
    *,
    origin_module_id="station:op10",
    local_sequence=0,
    expected_version=None,
):
    return MaterialIntent(
        run_id=transaction["factory_run_id"],
        generation=transaction["generation"],
        tick_us=transaction["simulation_tick_us"],
        origin_module_id=origin_module_id,
        local_sequence=local_sequence,
        transaction_id=transaction["transaction_id"],
        idempotency_key=transaction["idempotency_key"],
        transaction=transaction,
        expected_ledger_version=(
            transaction["ledger_expected_version"]
            if expected_version is None
            else expected_version
        ),
    )


def _produce(
    material_id,
    *,
    tx_id="tx-produce",
    key="key-produce",
    tick=0,
    **overrides,
):
    return _tx(
        tx_id,
        key,
        tick,
        0,
        "PRODUCE",
        [
            _leg(
                material_id,
                from_location=None,
                to_location="buffer:line",
            )
        ],
        child_refs=[material_id],
        **overrides,
    )


def _reserve(
    material_id,
    *,
    tx_id="tx-reserve",
    key="key-reserve",
    tick=10,
    expected_version=1,
    quantity="1",
    origin_module_id="station:op10",
    operation_execution_id="op:1",
    **overrides,
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
                quantity=quantity,
                from_location="buffer:line",
                to_location=None,
            )
        ],
        operation_execution_id=operation_execution_id,
        **overrides,
    )


def _seed(bridge, material_id="stator-1", *, tx_id="tx-produce", key="key-produce"):
    outcome = bridge.commit_material_intent(
        _intent(_produce(material_id, tx_id=tx_id, key=key))
    )
    assert outcome.status is MaterialOutcomeStatus.COMMITTED
    assert bridge.project_pending(0) is ProjectionStatus.UP_TO_DATE
    return outcome


def _snapshot(context, ledger, coordinator):
    return (
        context.tick_us,
        context.generation,
        ledger.version,
        ledger.state_digest(),
        len(ledger.outbox),
        tuple(ledger.genealogy),
        coordinator.trace_digest(),
    )


def test_generation_zero_is_not_a_bridge_generation(tmp_path):
    with pytest.raises(BridgeContractError):
        MaterialIntent(
            run_id=RUN_ID,
            generation=0,
            tick_us=0,
            origin_module_id="station:op10",
            local_sequence=0,
            transaction_id="tx",
            idempotency_key="key",
            transaction=_produce("stator-1"),
            expected_ledger_version=0,
        )

    ledger = _ledger(tmp_path / "ledger")
    context = _context(generation=0)
    coordinator = SerialFactoryCoordinator(context)
    with pytest.raises(BridgeIdentityError):
        MaterialBridge(
            context,
            ledger,
            coordinator,
            definition_digest=DEFINITION_DIGEST,
        )


def test_generation_and_run_mismatch_reject_before_mutation(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    before = _snapshot(context, ledger, coordinator)

    foreign_run = _intent(
        _reserve("stator-1", run_id="other-run", expected_version=1)
    )
    outcome = bridge.commit_material_intent(foreign_run)
    assert outcome.status is MaterialOutcomeStatus.REJECTED_CONTRACT
    assert _snapshot(context, ledger, coordinator) == before

    foreign_generation = _intent(
        _reserve("stator-1", generation=2, expected_version=1)
    )
    outcome = bridge.commit_material_intent(foreign_generation)
    assert outcome.status is MaterialOutcomeStatus.REJECTED_CONTRACT
    assert _snapshot(context, ledger, coordinator) == before


def test_past_clock_rejects_without_journal_or_event_mutation(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    context.advance_to(SimTick(20))
    before = _snapshot(context, ledger, coordinator)
    outcome = bridge.commit_material_intent(
        _intent(_reserve("stator-1", tick=10, expected_version=1))
    )
    assert outcome.status is MaterialOutcomeStatus.REJECTED_CONTRACT
    assert "older" in outcome.causal_reason
    assert _snapshot(context, ledger, coordinator) == before


def test_future_intent_is_allowed_but_known_horizon_is_enforced(tmp_path):
    context, ledger, coordinator, bridge = _bridge(
        tmp_path, horizon_us=100
    )
    _seed(bridge)
    future = bridge.commit_material_intent(
        _intent(_reserve("stator-1", tick=50, expected_version=1))
    )
    assert future.status is MaterialOutcomeStatus.COMMITTED
    assert context.tick_us == 0
    assert future.receipt is not None
    assert future.receipt.tick_us == 50

    before = _snapshot(context, ledger, coordinator)
    beyond = bridge.commit_material_intent(
        _intent(_reserve("stator-1", tick=150, expected_version=2))
    )
    assert beyond.status is MaterialOutcomeStatus.REJECTED_CONTRACT
    assert "horizon" in beyond.causal_reason
    assert _snapshot(context, ledger, coordinator) == before


def test_stale_expected_version_is_rejected_without_implicit_retry(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    before = _snapshot(context, ledger, coordinator)

    stale = bridge.commit_material_intent(
        _intent(_reserve("stator-1", expected_version=0))
    )
    assert stale.status is MaterialOutcomeStatus.REJECTED_VERSION
    assert _snapshot(context, ledger, coordinator) == before

    accepted = bridge.commit_material_intent(
        _intent(_reserve("stator-1", expected_version=1))
    )
    assert accepted.status is MaterialOutcomeStatus.COMMITTED
    assert ledger.version == 2


def test_waiting_for_material_creates_no_outbox_genealogy_or_child(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    before = _snapshot(context, ledger, coordinator)
    outcome = bridge.commit_material_intent(
        _intent(
            _reserve(
                "stator-1",
                quantity="2",
                expected_version=1,
            )
        )
    )
    assert outcome.status is MaterialOutcomeStatus.WAITING_FOR_MATERIAL
    assert outcome.outbox_ids == ()
    assert _snapshot(context, ledger, coordinator) == before
    assert bridge.reconcile_committed_outbox() is ProjectionStatus.UP_TO_DATE


def test_waiting_for_quality_creates_no_outbox_or_genealogy(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    produced = bridge.commit_material_intent(
        _intent(_produce("hold-part"))
    )
    assert produced.status is MaterialOutcomeStatus.COMMITTED
    assert bridge.project_pending(0) is ProjectionStatus.UP_TO_DATE
    before = _snapshot(context, ledger, coordinator)
    outcome = bridge.commit_material_intent(
        _intent(_reserve("hold-part", expected_version=1))
    )
    assert outcome.status is MaterialOutcomeStatus.WAITING_FOR_QUALITY
    assert outcome.outbox_ids == ()
    assert _snapshot(context, ledger, coordinator) == before


def test_duplicate_exact_intent_reuses_receipt_and_outbox_ids(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    intent = _intent(_reserve("stator-1", expected_version=1))
    first = bridge.commit_material_intent(intent)
    assert first.status is MaterialOutcomeStatus.COMMITTED
    assert first.receipt is not None
    assert first.receipt.idempotent_replay is False
    version = ledger.version
    outbox_count = len(ledger.outbox)

    second = bridge.commit_material_intent(intent)
    assert second.status is MaterialOutcomeStatus.COMMITTED
    assert second.receipt is not None
    assert second.receipt.idempotent_replay is True
    assert second.outbox_ids == first.outbox_ids
    assert len(second.outbox_ids) == 1
    assert ledger.version == version
    assert len(ledger.outbox) == outbox_count


def test_same_idempotency_key_different_payload_fails_hard(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    first = bridge.commit_material_intent(
        _intent(_reserve("stator-1", expected_version=1))
    )
    assert first.status is MaterialOutcomeStatus.COMMITTED
    before = _snapshot(context, ledger, coordinator)

    conflicting = bridge.commit_material_intent(
        _intent(
            _reserve(
                "stator-1",
                quantity="0.5",
                expected_version=2,
            )
        )
    )
    assert conflicting.status is MaterialOutcomeStatus.FAILED_TERMINAL
    assert _snapshot(context, ledger, coordinator) == before


def test_invalid_schema_and_policy_are_rejected_without_mutation(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    before = _snapshot(context, ledger, coordinator)

    bad_quantity = _reserve("stator-1", expected_version=1)
    bad_quantity["legs"][0]["quantity"] = "01"
    outcome = bridge.commit_material_intent(_intent(bad_quantity))
    assert outcome.status is MaterialOutcomeStatus.REJECTED_CONTRACT
    assert _snapshot(context, ledger, coordinator) == before

    bad_policy = _reserve(
        "stator-1",
        tx_id="tx-policy",
        key="key-policy",
        expected_version=1,
    )
    bad_policy["definition_provenance"] = "PDF_EXPLICIT"
    outcome = bridge.commit_material_intent(_intent(bad_policy))
    assert outcome.status is MaterialOutcomeStatus.REJECTED_CONTRACT
    assert "policy" in outcome.causal_reason
    assert _snapshot(context, ledger, coordinator) == before


def test_identity_retains_workspace_and_definition_digests_separately(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    assert bridge.identity.workspace_digest == HEADER.workspace_digest
    assert bridge.identity.definition_digest == DEFINITION_DIGEST
    assert (
        bridge.identity.workspace_digest
        != bridge.identity.definition_digest
    )
    assert bridge.identity.config_digest == HEADER.config_digest
    assert bridge.identity.model_revision == HEADER.model_revision
    assert bridge.identity.seed == HEADER.seed
    assert bridge.identity.epoch_utc == HEADER.epoch_utc
    assert bridge.identity.run_id == RUN_ID
    assert bridge.identity.generation == GENERATION


def test_ledger_header_identity_mismatch_fails_closed(tmp_path):
    ledger = _ledger(tmp_path, config_digest="sha256:other-config")
    context = _context()
    coordinator = SerialFactoryCoordinator(context)
    with pytest.raises(BridgeIdentityError):
        MaterialBridge(
            context,
            ledger,
            coordinator,
            definition_digest=DEFINITION_DIGEST,
        )


def test_reset_while_attached_fails_closed_and_requires_new_ledger(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    before = _snapshot(context, ledger, coordinator)
    context.reset()
    assert context.generation == GENERATION + 1
    assert bridge.reconcile_committed_outbox() is ProjectionStatus.INCOMPATIBLE
    outcome = bridge.commit_material_intent(
        _intent(_reserve("stator-1", tick=0, expected_version=1))
    )
    assert outcome.status is MaterialOutcomeStatus.REJECTED_CONTRACT
    assert (
        ledger.version,
        ledger.state_digest(),
        len(ledger.outbox),
        coordinator.trace_digest(),
    ) == (
        before[2],
        before[3],
        before[4],
        before[6],
    )


def test_explicit_fresh_generation_two_ledger_and_bridge_are_valid(tmp_path):
    context, ledger, coordinator, bridge = _bridge(tmp_path)
    _seed(bridge)
    context.reset()
    assert context.generation == GENERATION + 1
    ledger.close()

    fresh = _ledger(tmp_path / "generation-2", generation=2)
    fresh_context = _context(generation=2)
    fresh_coordinator = SerialFactoryCoordinator(fresh_context)
    fresh_bridge = MaterialBridge(
        fresh_context,
        fresh,
        fresh_coordinator,
        definition_digest=DEFINITION_DIGEST,
    )
    fresh_coordinator.initialize()
    fresh_context.mark_ready()
    fresh_context.start()
    outcome = fresh_bridge.commit_material_intent(
        _intent(
            _produce(
                "stator-2",
                tx_id="tx-g2",
                key="key-g2",
                generation=2,
            )
        )
    )
    assert outcome.status is MaterialOutcomeStatus.COMMITTED
    assert fresh_bridge.identity.generation == 2
    assert fresh.version == 1
    assert fresh_bridge.project_pending(0) is ProjectionStatus.UP_TO_DATE
