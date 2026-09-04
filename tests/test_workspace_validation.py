"""VF-vNEXT-G1 — Workspace/Scope structural foundation: fail-closed validation tests.

Negative tests for the fail-closed containment/identity invariants:

- missing/invalid parent (path-qualified);
- duplicate child identity within the SAME structural parent namespace;
- containment self-nesting (a scope nesting inside itself via its parent path);
- object attached to a nonexistent Scope;
- executable-only assumptions applied to a container-only Scope;
- invalid structural path/reference.

C01-1: scope ids are unique per structural parent namespace (NOT globally);
the full StructuralPath is the unambiguous identity. Positive duplicate-local-id
coverage lives in test_workspace_foundation.py.
"""

from __future__ import annotations

import pytest

from virtual_factory.workspace import (
    Archetype,
    ObjectSpec,
    ScopeMode,
    ScopeSpec,
    StructuralIdentityError,
    StructuralPath,
    StructuralValidationError,
    build_workspace,
)


def test_missing_parent_fails_closed() -> None:
    specs = [
        ScopeSpec(
            scope_id="CHILD",
            mode=ScopeMode.EXECUTABLE_CAPABLE,
            parent_path=StructuralPath(("W", "MISSING")),
        )
    ]
    with pytest.raises(StructuralValidationError):
        build_workspace("W", specs)


def test_parent_outside_workspace_fails_closed() -> None:
    specs = [
        ScopeSpec(
            scope_id="CHILD",
            mode=ScopeMode.EXECUTABLE_CAPABLE,
            parent_path=StructuralPath(("OTHER-WS", "SCOPE")),
        )
    ]
    with pytest.raises(StructuralValidationError):
        build_workspace("W", specs)


def test_workspace_root_parent_fails_closed() -> None:
    """C02-1: top-level scopes MUST use parent_path=None (canonical).

    ``parent_path == workspace_root`` is invalid and fails closed, so a declared
    scope can never silently disappear from the built tree.
    """
    specs = [
        ScopeSpec(
            "A",
            mode=ScopeMode.CONTAINER_ONLY,
            parent_path=StructuralPath(("W",)),
        )
    ]
    with pytest.raises(StructuralValidationError):
        build_workspace("W", specs)


def test_duplicate_child_id_same_parent_fails_closed() -> None:
    # Same parent namespace + same scope id -> same structural path -> rejected.
    specs = [
        ScopeSpec("P", mode=ScopeMode.CONTAINER_ONLY),
        ScopeSpec(
            "X",
            mode=ScopeMode.EXECUTABLE_CAPABLE,
            parent_path=StructuralPath(("W", "P")),
        ),
        ScopeSpec(
            "X",
            mode=ScopeMode.EXECUTABLE_CAPABLE,
            parent_path=StructuralPath(("W", "P")),
        ),
    ]
    with pytest.raises(StructuralValidationError):
        build_workspace("W", specs)


def test_containment_self_nesting_fails_closed() -> None:
    # A scope whose parent path already contains its own id nests inside itself.
    # (With path-qualified parents the parent depth strictly decreases, so
    # multi-node cycles are unrepresentable; self-nesting is the cycle case.)
    specs = [
        ScopeSpec("A", mode=ScopeMode.CONTAINER_ONLY),  # path W/A
        ScopeSpec(
            "A",
            mode=ScopeMode.CONTAINER_ONLY,
            parent_path=StructuralPath(("W", "A")),  # path W/A/A -> nests "A" in "A"
        ),
    ]
    with pytest.raises(StructuralValidationError):
        build_workspace("W", specs)


def test_executable_assumption_on_container_only_fails_closed() -> None:
    specs = [
        ScopeSpec("ASSY", mode=ScopeMode.CONTAINER_ONLY),
        ScopeSpec(
            "ASSY-SL01",
            mode=ScopeMode.EXECUTABLE_CAPABLE,
            parent_path=StructuralPath(("TIPA", "ASSY")),
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
    with pytest.raises(StructuralValidationError):
        build_workspace("", [ScopeSpec("U", mode=ScopeMode.CONTAINER_ONLY)])
    with pytest.raises(StructuralValidationError):
        build_workspace("W", [ScopeSpec("", mode=ScopeMode.CONTAINER_ONLY)])
    with pytest.raises(StructuralIdentityError):
        build_workspace(
            "W",
            [ScopeSpec("has space", mode=ScopeMode.CONTAINER_ONLY)],
        )
