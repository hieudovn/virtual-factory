"""VF-vNEXT-G4 — immutable staged boundary transfer tests.

Proves (Issue #49): payload is detached/immutable (no live runtime reference);
no callable/runtime object in payload; consumer cannot mutate producer state;
workspace identity fail-closed; deterministic serialization; no PIM canonical.
"""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from virtual_factory.composition import (
    BoundaryTransfer,
    PortRef,
    TransferError,
)
from virtual_factory.workspace import StructuralPath

_A = StructuralPath(("W", "AREA", "A"))
_B = StructuralPath(("W", "AREA", "B"))


def _transfer(**overrides) -> BoundaryTransfer:
    kwargs = dict(
        transfer_id="t1",
        source=PortRef(_A, "out"),
        target=PortRef(_B, "in"),
        binding_id="e1",
        window_id="w1",
        simulation_time_s=1.0,
        workspace_id="W",
        payload={"value": 42, "nested": {"x": 1}},
    )
    kwargs.update(overrides)
    return BoundaryTransfer(**kwargs)


def test_payload_is_detached_from_producer_mutation() -> None:
    source_payload = {"value": 1}
    transfer = _transfer(payload=source_payload)
    source_payload["value"] = 999  # mutate the producer's dict after staging
    assert transfer.payload["value"] == 1  # transfer is detached


def test_payload_is_immutable() -> None:
    transfer = _transfer(payload={"nested": {"x": 1}})
    with pytest.raises(TypeError):
        transfer.payload["nested"]["x"] = 99  # type: ignore[index]
    with pytest.raises(TypeError):
        transfer.payload["value"] = 99  # type: ignore[index]


def test_transfer_fields_are_frozen() -> None:
    transfer = _transfer()
    with pytest.raises(FrozenInstanceError):
        transfer.transfer_id = "other"  # type: ignore[misc]


def test_payload_rejects_callables() -> None:
    with pytest.raises(TransferError):
        _transfer(payload={"fn": lambda: 1})


def test_payload_rejects_runtime_objects() -> None:
    class RuntimeThing:
        pass

    with pytest.raises(TransferError):
        _transfer(payload={"obj": RuntimeThing()})


def test_workspace_identity_fail_closed() -> None:
    with pytest.raises(TransferError):
        _transfer(workspace_id="OTHER")


def test_serialization_is_deterministic_and_plain() -> None:
    transfer = _transfer()
    d1 = transfer.to_dict()
    d2 = transfer.to_dict()
    assert d1 == d2
    assert d1["payload"] == {"value": 42, "nested": {"x": 1}}
    json.dumps(d1)  # plain JSON-compatible data


def test_no_pim_canonical_identity_fabricated() -> None:
    d = _transfer().to_dict()
    assert "canonical_signal_id" not in d
    assert "canonical_object_id" not in d
