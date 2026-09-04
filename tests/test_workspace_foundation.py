"""VF-vNEXT-G1 — Workspace/Scope structural foundation: unit tests.

Covers the structural model, identity/path determinism, tree building,
resolution, and container-only vs executable-capable semantics.
"""

from __future__ import annotations

import pytest

from virtual_factory.workspace import (
    Archetype,
    ObjectSpec,
    ScopeMode,
    ScopeSpec,
    SimulationObjectRef,
    StructuralIdentityError,
    StructuralPath,
    StructuralValidationError,
    Workspace,
    build_workspace,
)


def _default_tree() -> Workspace:
    specs = [
        ScopeSpec(
            scope_id="ASSY",
            mode=ScopeMode.CONTAINER_ONLY,
            archetype=Archetype.DISCRETE,
        ),
        ScopeSpec(
            scope_id="ASSY-SL01",
            mode=ScopeMode.EXECUTABLE_CAPABLE,
            parent_path=StructuralPath(("TIPA", "ASSY")),
            archetype=Archetype.DISCRETE,
            objects=(
                ObjectSpec(object_id="AP04", object_type="station"),
                ObjectSpec(object_id="AP06", object_type="station"),
            ),
        ),
        ScopeSpec(
            scope_id="ASSY-SL02",
            mode=ScopeMode.EXECUTABLE_CAPABLE,
            parent_path=StructuralPath(("TIPA", "ASSY")),
            archetype=Archetype.DISCRETE,
        ),
    ]
    return build_workspace("TIPA", specs, display_name="TIPA ASSY")


def test_structural_path_roundtrip() -> None:
    path = StructuralPath(("TIPA", "ASSY", "ASSY-SL01"))
    assert path.workspace_id == "TIPA"
    assert path.scope_ids == ("ASSY", "ASSY-SL01")
    assert path.depth == 3
    assert path.is_workspace_root is False
    assert path.parent == StructuralPath(("TIPA", "ASSY"))
    assert StructuralPath.from_string(path.as_string()) == path
    assert str(path) == "TIPA/ASSY/ASSY-SL01"


def test_workspace_root_path() -> None:
    root = StructuralPath.workspace_root("TIPA")
    assert root.is_workspace_root is True
    assert root.parent is None
    assert root.scope_ids == ()


def test_structural_path_rejects_empty_and_separator() -> None:
    with pytest.raises(StructuralIdentityError):
        StructuralPath(())
    with pytest.raises(StructuralIdentityError):
        StructuralPath(("TIPA/ASSY",))


def test_structural_path_rejects_bad_segment() -> None:
    with pytest.raises(StructuralIdentityError):
        StructuralPath(("has space",))


def test_object_ref_roundtrip() -> None:
    ref = SimulationObjectRef(
        owning_scope_path=StructuralPath(("TIPA", "ASSY", "ASSY-SL01")),
        object_id="AP04",
    )
    assert ref.canonical == "TIPA/ASSY/ASSY-SL01/AP04"
    assert SimulationObjectRef.from_string(ref.canonical) == ref
    assert str(ref) == ref.canonical


def test_object_ref_requires_scope_path() -> None:
    with pytest.raises(StructuralIdentityError):
        SimulationObjectRef(
            owning_scope_path=StructuralPath(("TIPA",)),
            object_id="AP04",
        )


def test_build_workspace_tree_and_paths() -> None:
    ws = _default_tree()
    assert ws.workspace_id == "TIPA"
    assert ws.path == StructuralPath(("TIPA",))
    assert [s.scope_id for s in ws.top_level_scopes] == ["ASSY"]

    assy = ws.find_scope("ASSY")
    assert assy is not None
    assert assy.is_container_only
    assert not assy.is_executable_capable
    assert assy.path == StructuralPath(("TIPA", "ASSY"))

    sl1 = ws.find_scope("ASSY-SL01")
    assert sl1 is not None
    assert sl1.is_executable_capable
    assert not sl1.is_container_only
    assert sl1.path == StructuralPath(("TIPA", "ASSY", "ASSY-SL01"))


def test_find_scope_by_path_and_resolve() -> None:
    ws = _default_tree()
    scope = ws.resolve_scope(StructuralPath(("TIPA", "ASSY", "ASSY-SL02")))
    assert scope.scope_id == "ASSY-SL02"
    with pytest.raises(StructuralValidationError):
        ws.resolve_scope(StructuralPath(("TIPA", "ASSY", "ASSY-SL99")))


def test_container_scope_guards_executable_assumption() -> None:
    ws = _default_tree()
    assy = ws.find_scope("ASSY")
    assert assy is not None
    with pytest.raises(StructuralValidationError):
        assy.require_executable()
    sl1 = ws.find_scope("ASSY-SL01")
    assert sl1 is not None
    sl1.require_executable()  # no error


def test_build_is_deterministic_regardless_of_input_order() -> None:
    def make_specs(reversed_order: bool) -> list[ScopeSpec]:
        specs = [
            ScopeSpec("C", mode=ScopeMode.CONTAINER_ONLY),
            ScopeSpec("A", mode=ScopeMode.CONTAINER_ONLY),
            ScopeSpec("B", mode=ScopeMode.CONTAINER_ONLY),
        ]
        return list(reversed(specs)) if reversed_order else specs

    ws_a = build_workspace("W", make_specs(False))
    ws_b = build_workspace("W", make_specs(True))
    assert [s.scope_id for s in ws_a.top_level_scopes] == ["A", "B", "C"]
    assert [s.scope_id for s in ws_b.top_level_scopes] == ["A", "B", "C"]
    assert ws_a == ws_b


def test_archetype_is_informational_metadata() -> None:
    ws = build_workspace(
        "W",
        [ScopeSpec("U", mode=ScopeMode.EXECUTABLE_CAPABLE, archetype=Archetype.CONTINUOUS)],
    )
    unit = ws.find_scope("U")
    assert unit is not None
    assert unit.archetype == Archetype.CONTINUOUS


def test_object_resolution_and_not_found() -> None:
    ws = _default_tree()
    ref = SimulationObjectRef(
        owning_scope_path=StructuralPath(("TIPA", "ASSY", "ASSY-SL01")),
        object_id="AP04",
    )
    obj = ws.resolve_object(ref)
    assert obj.object_id == "AP04"
    assert obj.object_type == "station"

    # object attached to a scope that does not exist -> fail closed
    with pytest.raises(StructuralValidationError):
        ws.resolve_object(
            SimulationObjectRef(
                owning_scope_path=StructuralPath(("TIPA", "ASSY", "ASSY-SL99")),
                object_id="AP04",
            )
        )

    # object id not present in an existing scope -> fail closed
    with pytest.raises(StructuralValidationError):
        ws.resolve_object(
            SimulationObjectRef(
                owning_scope_path=StructuralPath(("TIPA", "ASSY", "ASSY-SL02")),
                object_id="AP04",
            )
        )


def test_scope_find_helpers_deterministic() -> None:
    ws = _default_tree()
    sl1 = ws.find_scope("ASSY-SL01")
    assert sl1 is not None
    assert sl1.find_object("AP06") is not None
    assert sl1.find_object("NOPE") is None
    assert sl1.scope_path_by_id("ASSY-SL01") == sl1.path
    assert ws.find_scope("NOPE") is None


def test_duplicate_local_scope_ids_under_different_parents_are_valid() -> None:
    """C01-1: local scope ids are unique per parent, not globally.

    Two different parents may each have a child named ``Utilities``; the full
    StructuralPath is the unambiguous identity.
    """
    specs = [
        ScopeSpec("Line-A", mode=ScopeMode.CONTAINER_ONLY),
        ScopeSpec("Line-B", mode=ScopeMode.CONTAINER_ONLY),
        ScopeSpec(
            "Utilities",
            mode=ScopeMode.EXECUTABLE_CAPABLE,
            parent_path=StructuralPath(("W", "Line-A")),
        ),
        ScopeSpec(
            "Utilities",
            mode=ScopeMode.EXECUTABLE_CAPABLE,
            parent_path=StructuralPath(("W", "Line-B")),
        ),
    ]
    ws = build_workspace("W", specs)

    # Path-based resolution is deterministic and unambiguous.
    util_a = ws.resolve_scope(StructuralPath(("W", "Line-A", "Utilities")))
    util_b = ws.resolve_scope(StructuralPath(("W", "Line-B", "Utilities")))
    assert util_a.scope_id == "Utilities"
    assert util_b.scope_id == "Utilities"
    assert util_a is not util_b
    assert util_a.path == StructuralPath(("W", "Line-A", "Utilities"))
    assert util_b.path == StructuralPath(("W", "Line-B", "Utilities"))


def test_bare_id_lookup_raises_on_ambiguity() -> None:
    """C01-1: a bare-id convenience lookup must not silently return first match."""
    specs = [
        ScopeSpec("Line-A", mode=ScopeMode.CONTAINER_ONLY),
        ScopeSpec("Line-B", mode=ScopeMode.CONTAINER_ONLY),
        ScopeSpec(
            "Utilities",
            mode=ScopeMode.EXECUTABLE_CAPABLE,
            parent_path=StructuralPath(("W", "Line-A")),
        ),
        ScopeSpec(
            "Utilities",
            mode=ScopeMode.EXECUTABLE_CAPABLE,
            parent_path=StructuralPath(("W", "Line-B")),
        ),
    ]
    ws = build_workspace("W", specs)
    with pytest.raises(StructuralValidationError):
        ws.find_scope("Utilities")

    # Within a single parent subtree the id is unique, so a bare-id lookup is OK.
    line_a = ws.find_scope("Line-A")
    assert line_a is not None
    util = line_a.find_scope("Utilities")
    assert util is not None
    assert util.path == StructuralPath(("W", "Line-A", "Utilities"))


def test_subtree_bare_lookup_within_single_parent_is_ok() -> None:
    """A bare-id lookup is fine when the id is unique within the searched scope."""
    specs = [
        ScopeSpec("Line-A", mode=ScopeMode.CONTAINER_ONLY),
        ScopeSpec(
            "Utilities",
            mode=ScopeMode.EXECUTABLE_CAPABLE,
            parent_path=StructuralPath(("W", "Line-A")),
        ),
    ]
    ws = build_workspace("W", specs)
    line_a = ws.find_scope("Line-A")
    assert line_a is not None
    util = line_a.find_scope("Utilities")
    assert util is not None
    assert util.path == StructuralPath(("W", "Line-A", "Utilities"))


def _count_tree_scopes(top_scopes) -> int:
    """Recursively count scope nodes under the given top-level scopes."""
    total = 0
    for scope in top_scopes:
        total += 1 + _count_tree_scopes(scope.children)
    return total


def test_declaration_count_matches_tree_count_completeness() -> None:
    """C02-1: every validated declaration materializes exactly once in the tree.

    A nested tree (top-level, deep children, and duplicate local ids under
    different parents) must build with node count == declaration count, and each
    declared structural path must be present exactly once.
    """
    specs = [
        ScopeSpec("Line-A", mode=ScopeMode.CONTAINER_ONLY),
        ScopeSpec("Line-B", mode=ScopeMode.CONTAINER_ONLY),
        ScopeSpec("Utilities", mode=ScopeMode.EXECUTABLE_CAPABLE,
                  parent_path=StructuralPath(("W", "Line-A"))),
        ScopeSpec("Utilities", mode=ScopeMode.EXECUTABLE_CAPABLE,
                  parent_path=StructuralPath(("W", "Line-B"))),
        ScopeSpec("Area", mode=ScopeMode.CONTAINER_ONLY),
        ScopeSpec("Unit", mode=ScopeMode.EXECUTABLE_CAPABLE,
                  parent_path=StructuralPath(("W", "Area"))),
        ScopeSpec("Cell", mode=ScopeMode.EXECUTABLE_CAPABLE,
                  parent_path=StructuralPath(("W", "Area", "Unit"))),
    ]
    ws = build_workspace("W", specs)

    # every declaration materializes exactly once
    assert _count_tree_scopes(ws.top_level_scopes) == len(specs)

    # each declared structural path resolves to exactly one scope
    for spec in specs:
        path = (
            StructuralPath(("W",))
            .child(spec.scope_id)
            if spec.parent_path is None
            else spec.parent_path.child(spec.scope_id)
        )
        resolved = ws.resolve_scope(path)
        assert resolved.scope_id == spec.scope_id
        assert resolved.path == path

    # top-level scopes are exactly the parent_path=None declarations
    assert [s.scope_id for s in ws.top_level_scopes] == ["Area", "Line-A", "Line-B"]

