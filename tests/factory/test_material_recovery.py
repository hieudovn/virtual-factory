import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from virtual_factory.factory.material import (
    CorruptJournalError,
    MaterialFlowLedger,
    TransferPolicy,
    TransferState,
    in_transit_location,
)

ROOT = Path(__file__).resolve().parents[2]


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
        "transfer_id": transfer_id,
        "recipe_revision": recipe_revision,
        "legs": legs,
        "parent_refs": parent_refs or [],
        "child_refs": child_refs or [],
        "source_kind": "SIMULATED",
        "definition_provenance": "SYNTHETIC_ASSUMPTION",
    }


def _config():
    return {
        "factory_run_id": "run-1",
        "generation": 1,
        "definition_digest": "sha256:definition",
        "config_digest": "sha256:config",
        "model_revision": "model-r1",
        "seed": 7,
        "buffers": {
            "buffer:producer": {"capacity": None},
            "buffer:join": {"capacity": "2", "unit": "EA"},
            "buffer:sender": {"capacity": None},
            "buffer:receiver": {"capacity": None},
        },
        "recipes": {
            "motor-recipe-v1": {
                "recipe_revision": "motor-recipe-v1",
                "inputs": [
                    {
                        "material_type": "stator",
                        "unit": "EA",
                        "quantity": "1",
                    },
                    {
                        "material_type": "rotor",
                        "unit": "EA",
                        "quantity": "1",
                    },
                ],
                "outputs": [
                    {
                        "material_type": "motor",
                        "unit": "EA",
                        "quantity": "1",
                    }
                ],
                "yield_ratio": "1",
            }
        },
        "quality_fixture": {
            "stator-1": "ACCEPTED",
            "rotor-1": "ACCEPTED",
            "motor-1": "ACCEPTED",
            "mover": "ACCEPTED",
        },
        "transfer_policy": TransferPolicy(default_latency_us=100),
    }


def _open(directory):
    return MaterialFlowLedger(directory, **_config())


def _produce(
    ledger, material_id, material_type, location, tick, version, quantity="1"
):
    tx = _tx(
        f"tx-produce-{material_id}",
        f"key-produce-{material_id}",
        tick,
        version,
        "PRODUCE",
        [
            _leg(
                material_id,
                material_type,
                quantity,
                "EA",
                to_location=location,
            )
        ],
        child_refs=[material_id],
    )
    return tx, ledger.apply_transaction(tx, version)


def _reserve(ledger, material_id, material_type, tick, version, operation_id):
    tx = _tx(
        f"tx-reserve-{material_id}",
        f"key-reserve-{material_id}",
        tick,
        version,
        "RESERVE",
        [
            _leg(
                material_id,
                material_type,
                "1",
                "EA",
                from_location="buffer:producer",
            )
        ],
        operation_execution_id=operation_id,
    )
    return tx, ledger.apply_transaction(tx, version)


def _join_tx(version):
    return _tx(
        "tx-join",
        "key-join",
        2,
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
            _leg("motor-1", "motor", "1", "EA", to_location="buffer:join"),
        ],
        operation_execution_id="consumer-op",
        recipe_revision="motor-recipe-v1",
        parent_refs=["stator-1", "rotor-1"],
        child_refs=["motor-1"],
    )


def _ship_tx(version):
    return _tx(
        "tx-ship",
        "key-ship",
        10,
        version,
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


def _run_child(directory, transaction, expected_version, stage, tx_type):
    code = (
        "from virtual_factory.factory.material import MaterialFlowLedger, "
        "TransferPolicy\n"
        f"ledger = MaterialFlowLedger({str(directory)!r}, "
        "factory_run_id='run-1', generation=1, "
        "definition_digest='sha256:definition', "
        "config_digest='sha256:config', model_revision='model-r1', seed=7, "
        "buffers={'buffer:producer': {'capacity': None}, "
        "'buffer:join': {'capacity': '2', 'unit': 'EA'}, "
        "'buffer:sender': {'capacity': None}, "
        "'buffer:receiver': {'capacity': None}}, "
        "recipes={'motor-recipe-v1': {'recipe_revision': 'motor-recipe-v1', "
        "'inputs': [{'material_type': 'stator', 'unit': 'EA', "
        "'quantity': '1'}, {'material_type': 'rotor', 'unit': 'EA', "
        "'quantity': '1'}], 'outputs': [{'material_type': 'motor', "
        "'unit': 'EA', 'quantity': '1'}], 'yield_ratio': '1'}}, "
        "quality_fixture={'stator-1': 'ACCEPTED', 'rotor-1': 'ACCEPTED', "
        "'motor-1': 'ACCEPTED', 'mover': 'ACCEPTED'}, "
        "transfer_policy=TransferPolicy(default_latency_us=100))\n"
        f"ledger.apply_transaction({transaction!r}, {expected_version})\n"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["VF_MATERIAL_CRASH_STAGE"] = stage
    env["VF_MATERIAL_CRASH_TYPE"] = tx_type
    return subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_reopen_preserves_reservation_then_join_state(tmp_path):
    directory = tmp_path / "journal"
    ledger = _open(directory)
    _produce(ledger, "stator-1", "stator", "buffer:producer", 0, 0)
    _produce(ledger, "rotor-1", "rotor", "buffer:producer", 0, 1)
    _reserve(ledger, "stator-1", "stator", 1, 2, "consumer-op")
    _reserve(ledger, "rotor-1", "rotor", 1, 3, "consumer-op")
    digest_before = ledger.state_digest()

    reopened = _open(directory)
    assert reopened.state_digest() == digest_before
    assert reopened.version == 4
    assert reopened.reservations["tx-reserve-stator-1"].state.value == "ACTIVE"
    assert reopened.reservations["tx-reserve-rotor-1"].state.value == "ACTIVE"

    join = _join_tx(4)
    reopened.apply_transaction(join, 4)
    digest_after = reopened.state_digest()

    recovered = _open(directory)
    assert recovered.state_digest() == digest_after
    assert recovered.version == 5
    assert recovered.get_item("motor-1").quantity == Decimal("1")
    assert len(recovered.genealogy) == 2
    assert [
        edge.parent_material_id for edge in recovered.genealogy
    ] == ["stator-1", "rotor-1"]


def test_precommit_crash_leaves_no_state_and_retry_commits(tmp_path):
    directory = tmp_path / "journal"
    _open(directory)
    tx = _tx(
        "tx-produce",
        "key-produce",
        0,
        0,
        "PRODUCE",
        [_leg("mover", "mover", "1", "EA", to_location="buffer:sender")],
        child_refs=["mover"],
    )
    result = _run_child(directory, tx, 0, "precommit", "PRODUCE")
    assert result.returncode == 23

    recovered = _open(directory)
    assert recovered.version == 0
    assert recovered.items == {}
    assert recovered.outbox == ()

    recovered.apply_transaction(tx, 0)
    assert recovered.version == 1
    assert recovered.get_item("mover").quantity == Decimal("1")


def test_postdurable_crash_replays_original_receipt_without_duplicates(tmp_path):
    directory = tmp_path / "journal"
    _open(directory)
    tx = _tx(
        "tx-produce",
        "key-produce",
        0,
        0,
        "PRODUCE",
        [_leg("mover", "mover", "1", "EA", to_location="buffer:sender")],
        child_refs=["mover"],
    )
    result = _run_child(directory, tx, 0, "postdurable", "PRODUCE")
    assert result.returncode == 23

    recovered = _open(directory)
    assert recovered.version == 1
    assert recovered.get_item("mover").quantity == Decimal("1")
    assert len(recovered.outbox) == 1

    replay = recovered.apply_transaction(tx, 0)
    assert replay.idempotent_replay is True
    assert recovered.version == 1
    assert len(recovered.outbox) == 1
    assert recovered.get_item("mover").quantity == Decimal("1")


def test_transfer_crash_after_durable_is_recovered_and_replayable(tmp_path):
    directory = tmp_path / "journal"
    ledger = _open(directory)
    _produce(
        ledger, "mover", "mover", "buffer:sender", 0, 0, quantity="2"
    )
    ledger = _open(directory)
    tx = _ship_tx(1)
    result = _run_child(directory, tx, 1, "transfer-postdurable", "SHIP")
    assert result.returncode == 23

    recovered = _open(directory)
    assert recovered.version == 2
    transfer = recovered.transfers["t1"]
    assert transfer.state is TransferState.IN_TRANSIT
    assert recovered.get_item(transfer.material_id).quantity == Decimal("1")
    assert recovered.get_item(transfer.material_id).location == (
        in_transit_location("t1")
    )

    replay = recovered.apply_transaction(tx, 1)
    assert replay.idempotent_replay is True
    assert recovered.version == 2

    receive = _tx(
        "tx-receive",
        "key-receive",
        110,
        2,
        "RECEIVE",
        [
            _leg(
                transfer.material_id,
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
    recovered.apply_transaction(receive, 2)
    assert recovered.transfers["t1"].state is TransferState.RECEIVED
    assert recovered.get_item(transfer.material_id).location == "buffer:receiver"


def test_join_crash_after_durable_has_no_phantom_child_or_edges(tmp_path):
    directory = tmp_path / "journal"
    ledger = _open(directory)
    _produce(ledger, "stator-1", "stator", "buffer:producer", 0, 0)
    _produce(ledger, "rotor-1", "rotor", "buffer:producer", 0, 1)
    tx = _join_tx(2)
    result = _run_child(directory, tx, 2, "join-postdurable", "TRANSFORM")
    assert result.returncode == 23

    recovered = _open(directory)
    assert recovered.version == 3
    assert recovered.get_item("motor-1").quantity == Decimal("1")
    assert len(recovered.genealogy) == 2
    transform_events = [
        record
        for record in recovered.outbox
        if record.event_type == "MATERIAL_TRANSFORMED"
    ]
    assert len(transform_events) == 1
    assert recovered.get_item("stator-1").quantity == Decimal("0")
    assert recovered.get_item("rotor-1").quantity == Decimal("0")

    replay = recovered.apply_transaction(tx, 2)
    assert replay.idempotent_replay is True
    assert recovered.version == 3
    assert len(recovered.genealogy) == 2
    assert len(
        [
            record
            for record in recovered.outbox
            if record.event_type == "MATERIAL_TRANSFORMED"
        ]
    ) == 1


def test_torn_final_record_is_ignored_without_phantom_state(tmp_path):
    directory = tmp_path / "journal"
    ledger = _open(directory)
    _produce(ledger, "m-1", "part", "buffer:producer", 0, 0)
    second_tx = _tx(
        "tx-produce-m-2",
        "key-produce-m-2",
        1,
        1,
        "PRODUCE",
        [_leg("m-2", "part", "1", "EA", to_location="buffer:producer")],
        child_refs=["m-2"],
    )
    ledger.apply_transaction(second_tx, 1)
    data = ledger.journal_path.read_bytes()
    ledger.journal_path.write_bytes(data[:-5])

    recovered = _open(directory)
    assert recovered.version == 1
    assert set(recovered.items) == {"m-1"}
    assert len(recovered.outbox) == 1
    assert recovered.get_item("m-2") is None

    recovered.apply_transaction(second_tx, 1)
    assert recovered.version == 2
    assert set(recovered.items) == {"m-1", "m-2"}


def test_corrupt_committed_record_fails_closed(tmp_path):
    directory = tmp_path / "journal"
    ledger = _open(directory)
    _produce(ledger, "m-1", "part", "buffer:producer", 0, 0)
    data = bytearray(ledger.journal_path.read_bytes())
    data[-1] ^= 0xFF
    ledger.journal_path.write_bytes(bytes(data))

    with pytest.raises(CorruptJournalError):
        _open(directory)
