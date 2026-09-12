"""VF-vNEXT-G4 — typed boundary port tests.

Proves (Issue #49): stable port identity within owning scope; explicit in/out
direction (no ambiguous inout for baseline); category/type/unit compatibility
fail-closed; duplicate port identity fail-closed; registry lookup fail-closed;
port identity is VF structural identity, not PIM canonical.
"""

from __future__ import annotations

import pytest

from virtual_factory.composition import (
    BoundaryPort,
    PortCategory,
    PortDirection,
    PortError,
    PortRef,
    PortRegistry,
    check_port_compatibility,
)
from virtual_factory.workspace import StructuralPath

_SCOPE = StructuralPath(("W", "AREA", "UNIT"))
_ROOT = StructuralPath(("W",))


def _ref(port_id: str, scope=_SCOPE) -> PortRef:
    return PortRef(scope, port_id)


def _port(ref: PortRef, direction, category, unit=None, descriptor=None) -> BoundaryPort:
    return BoundaryPort(ref, direction, category, unit=unit, descriptor=descriptor)


def test_port_ref_canonical_identity() -> None:
    ref = _ref("flow_out")
    assert ref.as_string() == "W/AREA/UNIT#flow_out"
    # Port identity is VF structural identity; no PIM canonical id exists.
    assert not hasattr(ref, "canonical_signal_id")


def test_port_must_belong_to_a_scope_not_workspace_root() -> None:
    with pytest.raises(PortError):
        PortRef(_ROOT, "p")


def test_port_id_must_be_nonempty_and_no_hash() -> None:
    with pytest.raises(PortError):
        _ref("")
    with pytest.raises(PortError):
        _ref("a#b")


def test_duplicate_port_identity_fails_closed() -> None:
    p = _port(_ref("flow"), PortDirection.OUT, PortCategory.MATERIAL)
    with pytest.raises(PortError):
        PortRegistry([p, p])


def test_registry_missing_port_fails_closed() -> None:
    registry = PortRegistry()
    with pytest.raises(PortError):
        registry.require(_ref("missing"))


def test_out_to_in_is_valid() -> None:
    source = _port(_ref("s"), PortDirection.OUT, PortCategory.MATERIAL)
    target = _port(_ref("t"), PortDirection.IN, PortCategory.MATERIAL)
    check_port_compatibility(source, target)  # no raise


def test_in_to_in_is_invalid() -> None:
    source = _port(_ref("s"), PortDirection.IN, PortCategory.MATERIAL)
    target = _port(_ref("t"), PortDirection.IN, PortCategory.MATERIAL)
    with pytest.raises(PortError):
        check_port_compatibility(source, target)


def test_out_to_out_is_invalid() -> None:
    source = _port(_ref("s"), PortDirection.OUT, PortCategory.MATERIAL)
    target = _port(_ref("t"), PortDirection.OUT, PortCategory.MATERIAL)
    with pytest.raises(PortError):
        check_port_compatibility(source, target)


def test_category_mismatch_fails_closed() -> None:
    source = _port(_ref("s"), PortDirection.OUT, PortCategory.MATERIAL)
    target = _port(_ref("t"), PortDirection.IN, PortCategory.INFORMATION)
    with pytest.raises(PortError):
        check_port_compatibility(source, target)


def test_unit_mismatch_fails_closed() -> None:
    source = _port(_ref("s"), PortDirection.OUT, PortCategory.MATERIAL, unit="m3/s")
    target = _port(_ref("t"), PortDirection.IN, PortCategory.MATERIAL, unit="kg/s")
    with pytest.raises(PortError):
        check_port_compatibility(source, target)


def test_descriptor_mismatch_fails_closed() -> None:
    source = _port(_ref("s"), PortDirection.OUT, PortCategory.INFORMATION, descriptor="flow")
    target = _port(_ref("t"), PortDirection.IN, PortCategory.INFORMATION, descriptor="level")
    with pytest.raises(PortError):
        check_port_compatibility(source, target)


def test_absent_unit_is_allowed_not_fabricated() -> None:
    source = _port(_ref("s"), PortDirection.OUT, PortCategory.COORDINATION)
    target = _port(_ref("t"), PortDirection.IN, PortCategory.COORDINATION)
    check_port_compatibility(source, target)  # absent unit is not fabricated


def test_registry_order_is_deterministic() -> None:
    a = _port(_ref("a"), PortDirection.OUT, PortCategory.MATERIAL)
    b = _port(_ref("b"), PortDirection.IN, PortCategory.MATERIAL)
    r1 = PortRegistry([b, a])
    r2 = PortRegistry([a, b])
    assert [p.ref.as_string() for p in r1.ports] == [
        p.ref.as_string() for p in r2.ports
    ]
