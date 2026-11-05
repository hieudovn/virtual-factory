from decimal import Decimal

import pytest

from virtual_factory.factory.material import (
    CapacityError,
    MaterialFlowLedger,
    TransferError,
    TransferPolicy,
    TransferState,
    in_transit_location,
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
    transfer_id=None,
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
        "transfer_id": transfer_id,
        "recipe_revision": None,
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
        "buffers": {
            "buffer:sender": {"capacity": None},
            "buffer:receiver": {"capacity": None},
        },
        "quality_fixture": {"mover": "ACCEPTED", "occupied": "ACCEPTED"},
        "transfer_policy": TransferPolicy(default_latency_us=100),
    }
    values.update(overrides)
    return MaterialFlowLedger(tmp_path, **values)


def _produce(ledger, material_id, quantity, location, tick, version):
    return ledger.apply_transaction(
        _tx(
            f"tx-produce-{material_id}",
            f"key-produce-{material_id}",
            tick,
            version,
            "PRODUCE",
            [_leg(material_id, material_id, quantity, "EA", to_location=location)],
            child_refs=[material_id],
        ),
        version,
    )


def test_staged_transfer_latency_receive_and_no_double_arrival(tmp_path):
    ledger = _ledger(tmp_path)
    _produce(ledger, "mover", "2", "buffer:sender", 0, 0)

    ship = _tx(
        "tx-ship-1",
        "key-ship-1",
        10,
        1,
        "SHIP",
        [
            _leg(
                "mover",
                "mover",
                "1",
                "EA",
                from_location="buffer:sender",
                to_location="buffer:receiver",
            )
        ],
        operation_execution_id="sender-op",
        transfer_id="t1",
    )
    ledger.apply_transaction(ship, 1)

    transfer = ledger.transfers["t1"]
    transit_id = transfer.material_id
    assert transfer.state is TransferState.IN_TRANSIT
    assert transfer.ship_tick_us == 10
    assert transfer.delivery_tick_us == 110
    assert ledger.get_item("mover").quantity == Decimal("1")
    assert ledger.get_item(transit_id).location == in_transit_location("t1")

    early = _tx(
        "tx-receive-early",
        "key-receive-early",
        50,
        2,
        "RECEIVE",
        [
            _leg(
                transit_id,
                "mover",
                "1",
                "EA",
                from_location=in_transit_location("t1"),
                to_location="buffer:receiver",
            )
        ],
        operation_execution_id="receiver-op",
        transfer_id="t1",
    )
    with pytest.raises(TransferError):
        ledger.apply_transaction(early, 2)
    assert ledger.transfers["t1"].state is TransferState.IN_TRANSIT
    assert ledger.get_item(transit_id).location == in_transit_location("t1")
    assert ledger.version == 2

    wrong_port = _tx(
        "tx-receive-port",
        "key-receive-port",
        110,
        2,
        "RECEIVE",
        [
            _leg(
                transit_id,
                "mover",
                "1",
                "EA",
                from_location=in_transit_location("t1"),
                to_location="buffer:wrong",
            )
        ],
        operation_execution_id="receiver-op",
        transfer_id="t1",
    )
    with pytest.raises(TransferError):
        ledger.apply_transaction(wrong_port, 2)

    receive = _tx(
        "tx-receive-1",
        "key-receive-1",
        110,
        2,
        "RECEIVE",
        [
            _leg(
                transit_id,
                "mover",
                "1",
                "EA",
                from_location=in_transit_location("t1"),
                to_location="buffer:receiver",
            )
        ],
        operation_execution_id="receiver-op",
        transfer_id="t1",
    )
    ledger.apply_transaction(receive, 2)
    assert ledger.transfers["t1"].state is TransferState.RECEIVED
    assert ledger.transfers["t1"].received_tick_us == 110
    assert ledger.get_item(transit_id).location == "buffer:receiver"
    assert ledger.get_item(transit_id).quantity == Decimal("1")

    duplicate = _tx(
        "tx-receive-2",
        "key-receive-2",
        120,
        3,
        "RECEIVE",
        [
            _leg(
                transit_id,
                "mover",
                "1",
                "EA",
                from_location=in_transit_location("t1"),
                to_location="buffer:receiver",
            )
        ],
        operation_execution_id="receiver-op",
        transfer_id="t1",
    )
    with pytest.raises(TransferError):
        ledger.apply_transaction(duplicate, 3)
    assert ledger.version == 3
    assert ledger.get_item(transit_id).quantity == Decimal("1")
    assert len(ledger.outbox) == 3


def test_wrong_sender_and_missing_ship_are_rejected(tmp_path):
    ledger = _ledger(tmp_path)
    _produce(ledger, "mover", "1", "buffer:sender", 0, 0)

    wrong_sender = _tx(
        "tx-ship-wrong",
        "key-ship-wrong",
        10,
        1,
        "SHIP",
        [
            _leg(
                "mover",
                "mover",
                "1",
                "EA",
                from_location="buffer:other",
                to_location="buffer:receiver",
            )
        ],
        operation_execution_id="sender-op",
        transfer_id="t1",
    )
    with pytest.raises(TransferError):
        ledger.apply_transaction(wrong_sender, 1)

    missing_ship = _tx(
        "tx-receive-missing",
        "key-receive-missing",
        20,
        1,
        "RECEIVE",
        [
            _leg(
                "mover",
                "mover",
                "1",
                "EA",
                from_location=in_transit_location("t1"),
                to_location="buffer:receiver",
            )
        ],
        operation_execution_id="receiver-op",
        transfer_id="t1",
    )
    with pytest.raises(TransferError):
        ledger.apply_transaction(missing_ship, 1)

    assert ledger.version == 1
    assert not ledger.transfers
    assert ledger.get_item("mover").location == "buffer:sender"


def test_destination_capacity_rejection_preserves_both_sides(tmp_path):
    ledger = _ledger(
        tmp_path,
        buffers={
            "buffer:sender": {"capacity": None},
            "buffer:receiver": {"capacity": "1", "unit": "EA"},
        },
    )
    _produce(ledger, "occupied", "1", "buffer:receiver", 0, 0)
    _produce(ledger, "mover", "1", "buffer:sender", 1, 1)

    ship = _tx(
        "tx-ship",
        "key-ship",
        10,
        2,
        "SHIP",
        [
            _leg(
                "mover",
                "mover",
                "1",
                "EA",
                from_location="buffer:sender",
                to_location="buffer:receiver",
            )
        ],
        operation_execution_id="sender-op",
        transfer_id="t1",
    )
    ledger.apply_transaction(ship, 2)
    transit_id = ledger.transfers["t1"].material_id

    receive = _tx(
        "tx-receive",
        "key-receive",
        110,
        3,
        "RECEIVE",
        [
            _leg(
                transit_id,
                "mover",
                "1",
                "EA",
                from_location=in_transit_location("t1"),
                to_location="buffer:receiver",
            )
        ],
        operation_execution_id="receiver-op",
        transfer_id="t1",
    )
    with pytest.raises(CapacityError):
        ledger.apply_transaction(receive, 3)

    assert ledger.version == 3
    assert ledger.transfers["t1"].state is TransferState.IN_TRANSIT
    assert ledger.get_item(transit_id).location == in_transit_location("t1")
    assert ledger.get_item(transit_id).quantity == Decimal("1")
    assert ledger.get_item("occupied").quantity == Decimal("1")
    assert ledger.get_item("mover").quantity == Decimal("0")


def test_return_and_loss_cannot_create_phantom_arrival(tmp_path):
    ledger = _ledger(tmp_path)
    _produce(ledger, "mover", "2", "buffer:sender", 0, 0)

    first_ship = _tx(
        "tx-ship-1",
        "key-ship-1",
        10,
        1,
        "SHIP",
        [
            _leg(
                "mover",
                "mover",
                "1",
                "EA",
                from_location="buffer:sender",
                to_location="buffer:receiver",
            )
        ],
        operation_execution_id="sender-op",
        transfer_id="t1",
    )
    ledger.apply_transaction(first_ship, 1)
    first_transit = ledger.transfers["t1"].material_id

    returned = _tx(
        "tx-return",
        "key-return",
        20,
        2,
        "RETURN",
        [
            _leg(
                first_transit,
                "mover",
                "1",
                "EA",
                from_location=in_transit_location("t1"),
                to_location="buffer:sender",
            )
        ],
        operation_execution_id="sender-op",
        transfer_id="t1",
    )
    ledger.apply_transaction(returned, 2)
    assert ledger.transfers["t1"].state is TransferState.RETURNED
    assert ledger.get_item(first_transit).location == "buffer:sender"
    assert ledger.get_item(first_transit).lifecycle.value == "RETURNED"

    late_receive = _tx(
        "tx-receive-returned",
        "key-receive-returned",
        200,
        3,
        "RECEIVE",
        [
            _leg(
                first_transit,
                "mover",
                "1",
                "EA",
                from_location=in_transit_location("t1"),
                to_location="buffer:receiver",
            )
        ],
        operation_execution_id="receiver-op",
        transfer_id="t1",
    )
    with pytest.raises(TransferError):
        ledger.apply_transaction(late_receive, 3)

    second_ship = _tx(
        "tx-ship-2",
        "key-ship-2",
        30,
        3,
        "SHIP",
        [
            _leg(
                "mover",
                "mover",
                "1",
                "EA",
                from_location="buffer:sender",
                to_location="buffer:receiver",
            )
        ],
        operation_execution_id="sender-op",
        transfer_id="t2",
    )
    ledger.apply_transaction(second_ship, 3)
    second_transit = ledger.transfers["t2"].material_id

    lost = _tx(
        "tx-scrap",
        "key-scrap",
        40,
        4,
        "SCRAP",
        [
            _leg(
                second_transit,
                "mover",
                "1",
                "EA",
                from_location=in_transit_location("t2"),
            )
        ],
        operation_execution_id="sender-op",
        transfer_id="t2",
    )
    ledger.apply_transaction(lost, 4)
    assert ledger.transfers["t2"].state is TransferState.LOST
    assert ledger.get_item(second_transit).lifecycle.value == "SCRAPPED"

    receive_lost = _tx(
        "tx-receive-lost",
        "key-receive-lost",
        200,
        5,
        "RECEIVE",
        [
            _leg(
                second_transit,
                "mover",
                "1",
                "EA",
                from_location=in_transit_location("t2"),
                to_location="buffer:receiver",
            )
        ],
        operation_execution_id="receiver-op",
        transfer_id="t2",
    )
    with pytest.raises(TransferError):
        ledger.apply_transaction(receive_lost, 5)
    assert ledger.version == 5
