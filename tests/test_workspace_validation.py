"""VF-vNEXT-G1 — Workspace/Scope structural foundation: fail-closed validation tests.

Negative tests for the fail-closed containment/identity invariants:

- missing/invalid parent;
- duplicate child identity within the relevant namespace;
- containment cycle;
- object attached to a nonexistent Scope;
- executable-only assumptions applied to a container-only Scope;
- invalid structural path/reference.
"""

from __future__ import annotations

import pytest

from virtual_factory.workspace import (
    Archetype,
    ScopeMode,
    ScopeSpec,
    StructuralValidationError,
    build_workspace,
)


def test_missing_parent_fails_closed() -> None:
    specs = [
        ScopeSpec(
            scope_id="CHILD",
            mode=ScopeMode.EXECUTABLE_CAPABLE,
            parent_scope_id="MISSING",
        )
    ]
    with pytest.raises(StructuralValidationError):
        build_workspace("W", specs)


def test_invalid_parent_self_reference_fails_closed() -> None:
    # A scope may not be its own parent (cycle of length one).
    specs = [
        ScopeSpec(
            scope_id="A",
            mode=ScopeMode.CONTAINER_ONLY,
            parent_scope_id="A",
        )
    ]
    with pytest.raises(StructuralValidationError):
        build_workspace("W", specs)


def test_duplicate_scope_id_fails_closed() -> None:
    specs = [
        ScopeSpec("U", mode=ScopeMode.CONTAINER_ONLY),
        ScopeSpec("U", mode=ScopeMode.CONTAINER_ONLY),
    ]
    with pytest.raises(StructuralValidationError):
        build_workspace("W", specs)


def test_duplicate_scope_id_anywhere_fails_closed() -> None:
    # Scope ids are globally unique within a workspace (stronger invariant,
    # chosen over per-parent-only uniqueness): this keeps structural paths and
    # cycle detection deterministic and matches the canonical ASSY evidence
    # (globally canonical scope ids). Duplicates under any parent are rejected.
    specs = [
        ScopeSpec("P1", mode=ScopeMode.CONTAINER_ONLY),
        ScopeSpec("P2", mode=ScopeMode.CONTAINER_ONLY),
        ScopeSpec("X", mode=ScopeMode.EXECUTABLE_CAPABLE, parent_scope_id="P1"),
        ScopeSpec("X", mode=ScopeMode.EXECUTABLE_CAPABLE, parent_scope_id="P2"),
    ]
    with pytest.raises(StructuralValidationError):
        build_workspace("W", specs)

    # Duplicate within the SAME parent namespace is also rejected.
    specs_bad = [
        ScopeSpec("P", mode=ScopeMode.CONTAINER_ONLY),
        ScopeSpec("X", mode=ScopeMode.EXECUTABLE_CAPABLE, parent_scope_id="P"),
        ScopeSpec("X", mode=ScopeMode.EXECUTABLE_CAPABLE, parent_scope_id="P"),
    ]
    with pytest.raises(StructuralValidationError):
        build_workspace("W", specs_bad)


def test_containment_cycle_fails_closed() -> None:
    # A -> B -> A forms a containment cycle.
    specs = [
        ScopeSpec("A", mode=ScopeMode.CONTAINER_ONLY, parent_scope_id="B"),
        ScopeSpec("B", mode=ScopeMode.CONTAINER_ONLY, parent_scope_id="A"),
    ]
    with pytest.raises(StructuralValidationError):
        build_workspace("W", specs)


def test_three_node_cycle_fails_closed() -> None:
    specs = [
        ScopeSpec("A", mode=ScopeMode.CONTAINER_ONLY, parent_scope_id="C"),
        ScopeSpec("B", mode=ScopeMode.CONTAINER_ONLY, parent_scope_id="A"),
        ScopeSpec("C", mode=ScopeMode.CONTAINER_ONLY, parent_scope_id="B"),
    ]
    with pytest.raises(StructuralValidationError):
        build_workspace("W", specs)


def test_executable_assumption_on_container_only_fails_closed() -> None:
    specs = [
        ScopeSpec("ASSY", mode=ScopeMode.CONTAINER_ONLY),
        ScopeSpec(
            "ASSY-SL01",
            mode=ScopeMode.EXECUTABLE_CAPABLE,
            parent_scope_id="ASSY",
        ),
    ]
    ws = build_workspace("TIPA", specs)
    assy = ws.find_scope("ASSY")
    assert assy is not None
    # executable-only assumption applied to container-only scope -> error
    with pytest.raises(StructuralValidationError):
        assy.require_executable()
    # executable-capable scope permits the guard
    sl1 = ws.find_scope("ASSY-SL01")
    assert sl1 is not None
    sl1.require_executable()


def test_duplicate_object_ids_within_scope_fails_closed() -> None:
    from virtual_factory.workspace import ObjectSpec

    specs = [
        ScopeSpec(
            "U",
            mode=ScopeMode.EXECUTABLE_CAPABLE,
            archetype=Archetype.CONTINUOUS,
            objects=(
                ObjectSpec("TK-101"),
                ObjectSpec("TK-101"),
            ),
        )
    ]
    with pytest.raises(StructuralValidationError):
        build_workspace("W", specs)


def test_empty_workspace_id_and_scope_id_fail_closed() -> None:
    from virtual_factory.workspace.identity import StructuralIdentityError

    with pytest.raises(StructuralValidationError):
        build_workspace("", [ScopeSpec("U", mode=ScopeMode.CONTAINER_ONLY)])
    with pytest.raises(StructuralValidationError):
        build_workspace("W", [ScopeSpec("", mode=ScopeMode.CONTAINER_ONLY)])
    with pytest.raises(StructuralIdentityError):
        build_workspace(
            "W",
            [ScopeSpec("has space", mode=ScopeMode.CONTAINER_ONLY)],
        )
