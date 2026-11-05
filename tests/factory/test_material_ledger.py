from decimal import Decimal

import pytest

from virtual_factory.factory.material import (
    CapacityError,
    DuplicateMaterialError,
    IdempotencyConflictError,
    MaterialFlowLedger,
    MaterialValidationError,
    QualityStatus,
    ReservationState,
    TransactionReceipt,
    VersionConflictError,
)


def _leg(material_id, material_type, quantity, unit, from_location=None, to_location=None):
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
    ledger_expected_version,
    transaction_type,
    legs,
    *,
    factory_run_id="run-1",
    generation=1,
    operation_execution_id=None,
    transfer_id=None,
    recipe_revision=None,
    parent_refs=None,
    child_refs=None,
):
    return {
        "contract_version": "vf-material-transaction-v0.1",
        "factory_run_id": factory_run_id,
        "generation": generation,
        "transaction_id": transaction_id,
        "idempotency_key": idempotency_key,
        "simulation_tick_us": tick_us,
        "ledger_expected_version": ledger_expected_version,
        "transaction_type": transaction_type,
        "operation_execution_id": operation_execution_id,
        "transfer_id": transfer_id,
        "recipe_revision": recipe_revision,
        "legs": legs,
        "parent_refs": parent_refs or [],
        "child_refs": child_refs or [],
        "source_kind": "SIMULATED",
        "definition_provenance": "SYNTHETIC_ASSUMPTION",
    }


def _ledger(tmp_path, **overrides):
    values = {
        "factory_run_id": "run-1",
        "generation": 1,
        "definition_digest": "sha256:definition",
        "config_digest": "sha256:config",
        "model_revision": "model-r1",
        "seed": 7,
        "buffers": {"buffer:line": {"capacity": None}},
        "quality_fixture": {},
        "scope_fixture": {},
    }
    values.update(overrides)
    return MaterialFlowLedger(tmp_path, **values)


def test_produce_unit_and_lot_accounting_with_canonical_decimal(tmp_path):
    ledger = _ledger(
        tmp_path,
        scope_fixture={"resin-lot": "LOT"},
        quality_fixture={"stator-1": "ACCEPTED", "resin-lot": "ACCEPTED"},
    )
    unit_tx = _tx(
        "tx-unit",
        "key-unit",
        0,
        0,
        "PRODUCE",
        [_leg("stator-1", "stator", "1", "EA", to_location="buffer:line")],
        child_refs=["stator-1"],
    )
    lot_tx = _tx(
        "tx-lot",
        "key-lot",
        1,
        1,
        "PRODUCE",
        [_leg("resin-lot", "resin", "5.250", "KG", to_location="buffer:line")],
        child_refs=["resin-lot"],
    )

    first = ledger.apply_transaction(unit_tx, 0)
    second = ledger.apply_transaction(lot_tx, 1)

    assert isinstance(first, TransactionReceipt)
    assert first.status.value == "COMMITTED"
    assert second.status.value == "COMMITTED"
    assert ledger.version == 2
    assert ledger.stock("stator-1") == Decimal("1")
    assert ledger.stock("resin-lot") == Decimal("5.250")
    assert ledger.get_item("stator-1").scope.value == "UNIT"
    assert ledger.get_item("resin-lot").scope.value == "LOT"
    assert ledger.get_item("resin-lot").unit.value == "KG"
    assert len(ledger.outbox) == 2


@pytest.mark.parametrize(
    ("quantity", "unit"),
    [
        ("1.0", "EA"),
        ("0", "EA"),
        ("01", "EA"),
        ("1e2", "EA"),
        ("-1", "EA"),
        ("NaN", "EA"),
        ("1.25", "KG"),
        ("1.0000", "KG"),
        ("01.000", "KG"),
        ("1E+3", "KG"),
        ("0.000", "KG"),
    ],
)
def test_quantity_semantics_reject_noncanonical_or_bad_precision(
    tmp_path, quantity, unit
):
    ledger = _ledger(tmp_path)
    tx = _tx(
        f"tx-bad-{quantity}-{unit}",
        f"key-bad-{quantity}-{unit}",
        0,
        0,
        "PRODUCE",
        [_leg("material-1", "raw", quantity, unit, to_location="buffer:line")],
        child_refs=["material-1"],
    )
    with pytest.raises(MaterialValidationError):
        ledger.apply_transaction(tx, 0)
    assert ledger.version == 0
    assert not ledger.items


def test_produce_respects_buffer_capacity_and_zero_capacity(tmp_path):
    ledger = _ledger(
        tmp_path,
        buffers={
            "buffer:small": {"capacity": "2", "unit": "EA"},
            "buffer:zero": {"capacity": "0", "unit": "EA"},
        },
    )
    first = _tx(
        "tx-1",
        "key-1",
        0,
        0,
        "PRODUCE",
        [_leg("m-1", "part", "1", "EA", to_location="buffer:small")],
    )
    second = _tx(
        "tx-2",
        "key-2",
        1,
        1,
        "PRODUCE",
        [_leg("m-2", "part", "1", "EA", to_location="buffer:small")],
    )
    overflow = _tx(
        "tx-3",
        "key-3",
        2,
        2,
        "PRODUCE",
        [_leg("m-3", "part", "1", "EA", to_location="buffer:small")],
    )
    zero_capacity = _tx(
        "tx-4",
        "key-4",
        2,
        2,
        "PRODUCE",
        [_leg("m-4", "part", "1", "EA", to_location="buffer:zero")],
    )

    ledger.apply_transaction(first, 0)
    ledger.apply_transaction(second, 1)
    with pytest.raises(CapacityError):
        ledger.apply_transaction(overflow, 2)
    with pytest.raises(CapacityError):
        ledger.apply_transaction(zero_capacity, 2)

    assert ledger.version == 2
    assert set(ledger.items) == {"m-1", "m-2"}


def test_quality_eligibility_reservation_and_consumption(tmp_path):
    ledger = _ledger(
        tmp_path,
        quality_fixture={
            "stator-1": QualityStatus.ACCEPTED.value,
            "rotor-1": QualityStatus.HOLD.value,
        },
    )
    ledger.apply_transaction(
        _tx(
            "tx-produce-1",
            "key-produce-1",
            0,
            0,
            "PRODUCE",
            [
                _leg("stator-1", "stator", "1", "EA", to_location="buffer:line"),
                _leg("rotor-1", "rotor", "1", "EA", to_location="buffer:line"),
            ],
            child_refs=["stator-1", "rotor-1"],
        ),
        0,
    )
    accepted = _tx(
        "tx-reserve-1",
        "key-reserve-1",
        1,
        1,
        "RESERVE",
        [_leg("stator-1", "stator", "1", "EA", from_location="buffer:line")],
        operation_execution_id="op-1",
    )
    hold = _tx(
        "tx-reserve-2",
        "key-reserve-2",
        1,
        2,
        "RESERVE",
        [_leg("rotor-1", "rotor", "1", "EA", from_location="buffer:line")],
        operation_execution_id="op-2",
    )
    hold_consume = _tx(
        "tx-consume-hold",
        "key-consume-hold",
        1,
        2,
        "CONSUME",
        [_leg("rotor-1", "rotor", "1", "EA", from_location="buffer:line")],
        operation_execution_id="op-2",
    )

    assert ledger.apply_transaction(accepted, 1).status.value == "COMMITTED"
    waiting_quality = ledger.apply_transaction(hold, 2)
    waiting_consume = ledger.apply_transaction(hold_consume, 2)

    assert waiting_quality.status.value == "WAITING_FOR_QUALITY"
    assert waiting_consume.status.value == "WAITING_FOR_QUALITY"
    assert ledger.version == 2
    assert ledger.reservations["tx-reserve-1"].state is ReservationState.ACTIVE
    assert ledger.get_item("rotor-1").quantity == Decimal("1")

    consume = _tx(
        "tx-consume-1",
        "key-consume-1",
        2,
        2,
        "CONSUME",
        [_leg("stator-1", "stator", "1", "EA", from_location="buffer:line")],
        operation_execution_id="op-1",
    )
    assert ledger.apply_transaction(consume, 2).status.value == "COMMITTED"
    assert ledger.get_item("stator-1").quantity == Decimal("0")
    assert ledger.get_item("stator-1").lifecycle.value == "CONSUMED"
    assert ledger.reservations["tx-reserve-1"].state is ReservationState.CONSUMED


def test_no_negative_inventory_double_reservation_and_release(tmp_path):
    ledger = _ledger(
        tmp_path,
        quality_fixture={"resin-lot": "ACCEPTED"},
        scope_fixture={"resin-lot": "LOT"},
    )
    ledger.apply_transaction(
        _tx(
            "tx-produce",
            "key-produce",
            0,
            0,
            "PRODUCE",
            [_leg("resin-lot", "resin", "5.000", "KG", to_location="buffer:line")],
            child_refs=["resin-lot"],
        ),
        0,
    )
    reserve_one = _tx(
        "tx-reserve-1",
        "key-reserve-1",
        1,
        1,
        "RESERVE",
        [_leg("resin-lot", "resin", "3.000", "KG", from_location="buffer:line")],
        operation_execution_id="op-1",
    )
    reserve_two = _tx(
        "tx-reserve-2",
        "key-reserve-2",
        1,
        2,
        "RESERVE",
        [_leg("resin-lot", "resin", "3.000", "KG", from_location="buffer:line")],
        operation_execution_id="op-2",
    )
    overflow = _tx(
        "tx-reserve-3",
        "key-reserve-3",
        1,
        2,
        "RESERVE",
        [_leg("resin-lot", "resin", "9.000", "KG", from_location="buffer:line")],
        operation_execution_id="op-3",
    )

    ledger.apply_transaction(reserve_one, 1)
    assert ledger.apply_transaction(reserve_two, 2).status.value == "WAITING_FOR_MATERIAL"
    assert ledger.apply_transaction(overflow, 2).status.value == "WAITING_FOR_MATERIAL"
    assert ledger.version == 2
    assert ledger.get_item("resin-lot").quantity == Decimal("5.000")

    release = _tx(
        "tx-release",
        "key-release",
        2,
        2,
        "RELEASE_RESERVATION",
        [_leg("resin-lot", "resin", "3.000", "KG", from_location="buffer:line")],
        operation_execution_id="op-1",
    )
    ledger.apply_transaction(release, 2)
    assert ledger.reservations["tx-reserve-1"].state is ReservationState.RELEASED
    reserve_after_release = _tx(
        "tx-reserve-4",
        "key-reserve-4",
        3,
        3,
        "RESERVE",
        [_leg("resin-lot", "resin", "3.000", "KG", from_location="buffer:line")],
        operation_execution_id="op-2",
    )
    assert (
        ledger.apply_transaction(reserve_after_release, 3).status.value
        == "COMMITTED"
    )
    assert ledger.version == 4


def test_version_conflict_idempotent_replay_and_hard_conflicts(tmp_path):
    ledger = _ledger(tmp_path)
    produce = _tx(
        "tx-produce",
        "key-produce",
        0,
        0,
        "PRODUCE",
        [_leg("m-1", "part", "1", "EA", to_location="buffer:line")],
        child_refs=["m-1"],
    )
    first = ledger.apply_transaction(produce, 0)
    duplicate = ledger.apply_transaction(produce, 0)

    assert first.status.value == "COMMITTED"
    assert duplicate.idempotent_replay is True
    assert duplicate.ledger_version == first.ledger_version
    assert ledger.version == 1
    assert len(ledger.outbox) == 1
    assert len(ledger.items) == 1

    same_key = _tx(
        "tx-different-id",
        "key-produce",
        1,
        1,
        "PRODUCE",
        [_leg("m-2", "part", "1", "EA", to_location="buffer:line")],
    )
    with pytest.raises(IdempotencyConflictError):
        ledger.apply_transaction(same_key, 1)

    same_transaction = _tx(
        "tx-produce",
        "key-other",
        1,
        1,
        "PRODUCE",
        [_leg("m-2", "part", "1", "EA", to_location="buffer:line")],
    )
    with pytest.raises(IdempotencyConflictError):
        ledger.apply_transaction(same_transaction, 1)

    stale = _tx(
        "tx-stale",
        "key-stale",
        1,
        0,
        "PRODUCE",
        [_leg("m-2", "part", "1", "EA", to_location="buffer:line")],
    )
    with pytest.raises(VersionConflictError):
        ledger.apply_transaction(stale, 0)

    mismatched = _tx(
        "tx-mismatch",
        "key-mismatch",
        1,
        0,
        "PRODUCE",
        [_leg("m-2", "part", "1", "EA", to_location="buffer:line")],
    )
    with pytest.raises(MaterialValidationError):
        ledger.apply_transaction(mismatched, 1)

    assert ledger.version == 1
    assert set(ledger.items) == {"m-1"}


def test_no_phantom_production_and_reference_checks(tmp_path):
    ledger = _ledger(tmp_path)
    with pytest.raises(MaterialValidationError):
        ledger.apply_transaction(
            _tx(
                "tx-from",
                "key-from",
                0,
                0,
                "PRODUCE",
                [
                    _leg(
                        "m-1",
                        "part",
                        "1",
                        "EA",
                        from_location="buffer:line",
                        to_location="buffer:line",
                    )
                ],
            ),
            0,
        )
    with pytest.raises(MaterialValidationError):
        ledger.apply_transaction(
            _tx(
                "tx-refs",
                "key-refs",
                0,
                0,
                "PRODUCE",
                [_leg("m-1", "part", "1", "EA", to_location="buffer:line")],
                child_refs=["other-material"],
            ),
            0,
        )
    ledger.apply_transaction(
        _tx(
            "tx-produce",
            "key-produce",
            0,
            0,
            "PRODUCE",
            [_leg("m-1", "part", "1", "EA", to_location="buffer:line")],
            child_refs=["m-1"],
        ),
        0,
    )
    with pytest.raises(DuplicateMaterialError):
        ledger.apply_transaction(
            _tx(
                "tx-duplicate",
                "key-duplicate",
                1,
                1,
                "PRODUCE",
                [_leg("m-1", "part", "1", "EA", to_location="buffer:line")],
            ),
            1,
        )
    assert ledger.version == 1
