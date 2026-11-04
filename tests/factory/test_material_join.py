from decimal import Decimal

import pytest

from virtual_factory.factory.material import (
    CapacityError,
    MaterialFlowLedger,
    RecipeError,
    RequestStatus,
    canonical_request_key,
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
    operation_execution_id=None,
    recipe_revision=None,
    parent_refs=None,
    child_refs=None,
):
    return {
        "contract_version": "vf-material-transaction-v0.1",
        "factory_run_id": "run-1",
        "generation": 1,
        "transaction_id": transaction_id,
        "idempotency_key": idempotency_key,
        "simulation_tick_us": tick_us,
        "ledger_expected_version": ledger_expected_version,
        "transaction_type": transaction_type,
        "operation_execution_id": operation_execution_id,
        "transfer_id": None,
        "recipe_revision": recipe_revision,
        "legs": legs,
        "parent_refs": parent_refs or [],
        "child_refs": child_refs or [],
        "source_kind": "SIMULATED",
        "definition_provenance": "SYNTHETIC_ASSUMPTION",
    }


def _recipe():
    return {
        "recipe_revision": "motor-recipe-v1",
        "inputs": [
            {"material_type": "stator", "unit": "EA", "quantity": "1"},
            {"material_type": "rotor", "unit": "EA", "quantity": "1"},
        ],
        "outputs": [
            {"material_type": "motor", "unit": "EA", "quantity": "1"}
        ],
        "yield_ratio": "1",
    }


def _ledger(directory, **overrides):
    values = {
        "factory_run_id": "run-1",
        "generation": 1,
        "definition_digest": "sha256:definition",
        "config_digest": "sha256:config",
        "model_revision": "model-r1",
        "seed": 7,
        "buffers": {
            "buffer:producer": {"capacity": None},
            "buffer:join": {"capacity": "2", "unit": "EA"},
            "buffer:line": {"capacity": None},
        },
        "recipes": {"motor-recipe-v1": _recipe()},
        "quality_fixture": {
            "stator-1": "ACCEPTED",
            "rotor-1": "ACCEPTED",
            "motor-1": "ACCEPTED",
        },
    }
    values.update(overrides)
    return MaterialFlowLedger(directory, **values)


def _produce(ledger, material_id, material_type, location, tick, version):
    return ledger.apply_transaction(
        _tx(
            f"tx-produce-{material_id}",
            f"key-produce-{material_id}",
            tick,
            version,
            "PRODUCE",
            [
                _leg(
                    material_id,
                    material_type,
                    "1",
                    "EA",
                    to_location=location,
                )
            ],
            child_refs=[material_id],
        ),
        version,
    )


def _transform_tx(tick, version, output_quantity="1"):
    return _tx(
        "tx-join",
        "key-join",
        tick,
        version,
        "TRANSFORM",
        [
            _leg(
                "stator-1",
                "stator",
                "1",
                "EA",
                from_location="buffer:producer",
            ),
            _leg(
                "rotor-1",
                "rotor",
                "1",
                "EA",
                from_location="buffer:producer",
            ),
            _leg(
                "motor-1",
                "motor",
                output_quantity,
                "EA",
                to_location="buffer:join",
            ),
        ],
        operation_execution_id="consumer-op",
        recipe_revision="motor-recipe-v1",
        parent_refs=["stator-1", "rotor-1"],
        child_refs=["motor-1"],
    )


def test_two_parent_join_creates_one_child_with_two_genealogy_edges(tmp_path):
    ledger = _ledger(tmp_path)
    _produce(ledger, "stator-1", "stator", "buffer:producer", 0, 0)
    _produce(ledger, "rotor-1", "rotor", "buffer:producer", 0, 1)

    receipt = ledger.apply_transaction(_transform_tx(1, 2), 2)

    assert receipt.status is RequestStatus.COMMITTED
    assert ledger.version == 3
    assert ledger.get_item("stator-1").quantity == Decimal("0")
    assert ledger.get_item("stator-1").lifecycle.value == "CONSUMED"
    assert ledger.get_item("rotor-1").quantity == Decimal("0")
    assert ledger.get_item("rotor-1").lifecycle.value == "CONSUMED"
    assert ledger.get_item("motor-1").quantity == Decimal("1")
    assert ledger.get_item("motor-1").location == "buffer:join"
    assert ledger.get_item("motor-1").parent_ids == ("stator-1", "rotor-1")

    edges = [
        (edge.parent_material_id, edge.child_material_id)
        for edge in ledger.genealogy
    ]
    assert edges == [
        ("stator-1", "motor-1"),
        ("rotor-1", "motor-1"),
    ]
    transform_events = [
        record
        for record in ledger.outbox
        if record.event_type == "MATERIAL_TRANSFORMED"
    ]
    assert len(transform_events) == 1
    assert transform_events[0].payload["parent_ids"] == ["stator-1", "rotor-1"]
    assert transform_events[0].payload["child_ids"] == ["motor-1"]


def test_missing_parent_does_not_partially_transform(tmp_path):
    ledger = _ledger(tmp_path)
    _produce(ledger, "stator-1", "stator", "buffer:producer", 0, 0)

    receipt = ledger.apply_transaction(_transform_tx(1, 1), 1)

    assert receipt.status is RequestStatus.WAITING_FOR_MATERIAL
    assert ledger.version == 1
    assert ledger.get_item("stator-1").quantity == Decimal("1")
    assert ledger.get_item("rotor-1") is None
    assert ledger.get_item("motor-1") is None
    assert ledger.genealogy == ()
    assert not any(
        record.event_type == "MATERIAL_TRANSFORMED"
        for record in ledger.outbox
    )


def test_quality_blocked_parent_does_not_partially_transform(tmp_path):
    ledger = _ledger(
        tmp_path,
        quality_fixture={
            "stator-1": "ACCEPTED",
            "rotor-1": "HOLD",
            "motor-1": "ACCEPTED",
        },
    )
    _produce(ledger, "stator-1", "stator", "buffer:producer", 0, 0)
    _produce(ledger, "rotor-1", "rotor", "buffer:producer", 0, 1)

    receipt = ledger.apply_transaction(_transform_tx(1, 2), 2)

    assert receipt.status is RequestStatus.WAITING_FOR_QUALITY
    assert ledger.version == 2
    assert ledger.get_item("stator-1").quantity == Decimal("1")
    assert ledger.get_item("rotor-1").quantity == Decimal("1")
    assert ledger.get_item("motor-1") is None
    assert ledger.genealogy == ()
    assert not any(
        record.event_type == "MATERIAL_TRANSFORMED"
        for record in ledger.outbox
    )


def test_child_capacity_rejection_preserves_parents_and_no_edges(tmp_path):
    ledger = _ledger(
        tmp_path,
        buffers={
            "buffer:producer": {"capacity": None},
            "buffer:join": {"capacity": "0", "unit": "EA"},
        },
    )
    _produce(ledger, "stator-1", "stator", "buffer:producer", 0, 0)
    _produce(ledger, "rotor-1", "rotor", "buffer:producer", 0, 1)

    with pytest.raises(CapacityError):
        ledger.apply_transaction(_transform_tx(1, 2), 2)

    assert ledger.version == 2
    assert ledger.get_item("stator-1").quantity == Decimal("1")
    assert ledger.get_item("rotor-1").quantity == Decimal("1")
    assert ledger.get_item("motor-1") is None
    assert ledger.genealogy == ()
    assert not any(
        record.event_type == "MATERIAL_TRANSFORMED"
        for record in ledger.outbox
    )


def test_recipe_conservation_rejects_naive_parent_sum(tmp_path):
    ledger = _ledger(tmp_path)
    _produce(ledger, "stator-1", "stator", "buffer:producer", 0, 0)
    _produce(ledger, "rotor-1", "rotor", "buffer:producer", 0, 1)

    with pytest.raises(RecipeError):
        ledger.apply_transaction(_transform_tx(1, 2, "2"), 2)

    assert ledger.version == 2
    assert ledger.get_item("stator-1").quantity == Decimal("1")
    assert ledger.get_item("rotor-1").quantity == Decimal("1")
    assert ledger.get_item("motor-1") is None
    assert ledger.genealogy == ()


def test_contending_reservations_have_one_deterministic_winner(tmp_path):
    outcomes = []
    for run_name, input_order in (
        ("run-a", ("a", "b")),
        ("run-b", ("b", "a")),
    ):
        ledger = _ledger(
            tmp_path / run_name,
            quality_fixture={"rotor-1": "ACCEPTED"},
        )
        _produce(ledger, "rotor-1", "rotor", "buffer:line", 0, 0)
        requests = {
            "a": _tx(
                "tx-a",
                "key-a",
                1,
                1,
                "RESERVE",
                [
                    _leg(
                        "rotor-1",
                        "rotor",
                        "1",
                        "EA",
                        from_location="buffer:line",
                    )
                ],
                operation_execution_id="consumer-a",
            ),
            "b": _tx(
                "tx-b",
                "key-b",
                1,
                1,
                "RESERVE",
                [
                    _leg(
                        "rotor-1",
                        "rotor",
                        "1",
                        "EA",
                        from_location="buffer:line",
                    )
                ],
                operation_execution_id="consumer-b",
            ),
        }
        ordered = sorted(
            (requests[item] for item in input_order),
            key=canonical_request_key,
        )
        statuses = []
        version = 1
        for request in ordered:
            request = dict(request)
            request["ledger_expected_version"] = version
            receipt = ledger.apply_transaction(request, version)
            statuses.append(receipt.status.value)
            if receipt.status is RequestStatus.COMMITTED:
                version += 1
        outcomes.append(
            (
                tuple(statuses),
                ledger.version,
                "tx-a" in ledger.reservations,
                "tx-b" in ledger.reservations,
                ledger.get_item("rotor-1").quantity,
            )
        )

    assert outcomes[0] == outcomes[1]
    assert outcomes[0][0] == ("COMMITTED", "WAITING_FOR_MATERIAL")
    assert outcomes[0][1] == 2
    assert outcomes[0][2] is True
    assert outcomes[0][3] is False
    assert outcomes[0][4] == Decimal("1")
