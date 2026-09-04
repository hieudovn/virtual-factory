"""Fail-closed Workspace/Scope structural building and validation.

Builds an immutable :class:`~virtual_factory.workspace.model.Workspace` from flat
scope specifications and enforces the G1 containment/identity invariants:

- workspace id valid;
- scope id valid and unique within its structural parent namespace;
- every declared parent scope exists (missing/invalid parent is an error);
- no containment cycle (parent references are followed upward);
- container-only vs executable-capable is explicit; executable-only assumptions
  are never applied to a container-only scope (guarded at the model);
- objects belong to declared scopes; an object attached to a nonexistent scope
  is rejected at resolution time (fail-closed);
- the resulting tree is deterministic independent of input iteration order
  (children and objects are ordered by id).

G1 does NOT implement runtime orchestration, provenance-v2, semantic binding,
coordinator/ports, or any execution boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from virtual_factory.workspace.identity import StructuralIdentityError
from virtual_factory.workspace.identity import StructuralPath
from virtual_factory.workspace.model import (
    Archetype,
    ScopeMode,
    SimulationObject,
    SimulationScope,
    Workspace,
)


class StructuralValidationError(ValueError):
    """Raised when a structural layout violates a fail-closed invariant."""


@dataclass(frozen=True, slots=True)
class ObjectSpec:
    """Declaration of one Simulation Object inside an owning scope."""

    object_id: str
    object_type: str | None = None
    display_name: str | None = None


@dataclass(frozen=True, slots=True)
class ScopeSpec:
    """Declaration of one Simulation Scope.

    ``parent_scope_id`` is None for a top-level scope under the Workspace.
    """

    scope_id: str
    mode: ScopeMode
    parent_scope_id: str | None = None
    archetype: Archetype | None = None
    display_name: str | None = None
    objects: tuple[ObjectSpec, ...] = ()


def _validate_ids(specs: Sequence[ScopeSpec], workspace_id: str) -> None:
    """Fail-closed id validation (unique within parent, valid, parent exists)."""
    if not workspace_id:
        raise StructuralValidationError("workspace id must not be empty")

    # all declared scope ids (for parent-existence check)
    all_ids = {spec.scope_id for spec in specs}
    if len(all_ids) != len(specs):
        seen: set[str] = set()
        dupes = sorted(
            {s.scope_id for s in specs if s.scope_id in seen or seen.add(s.scope_id)}
        )
        raise StructuralValidationError(
            f"duplicate scope id within workspace {workspace_id!r}: {dupes}"
        )

    for spec in specs:
        if not spec.scope_id:
            raise StructuralValidationError("scope id must not be empty")
        if spec.parent_scope_id is not None:
            if spec.parent_scope_id not in all_ids:
                raise StructuralValidationError(
                    f"scope {spec.scope_id!r} has missing/invalid parent "
                    f"{spec.parent_scope_id!r}"
                )
        # object ids unique within owning scope + non-empty
        obj_ids = [o.object_id for o in spec.objects]
        if len(obj_ids) != len(set(obj_ids)):
            raise StructuralValidationError(
                f"scope {spec.scope_id!r} has duplicate object ids"
            )
        for obj in spec.objects:
            if not obj.object_id:
                raise StructuralValidationError("object id must not be empty")


def _detect_cycles(specs: Sequence[ScopeSpec]) -> None:
    """Detect containment cycles by walking parent references upward.

    A containment tree has exactly one structural parent per child, so a cycle
    (A inside B inside A) is invalid and must fail closed.
    """
    by_id = {spec.scope_id: spec for spec in specs}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(scope_id: str) -> None:
        if scope_id in visiting:
            raise StructuralValidationError(
                f"containment cycle detected involving scope {scope_id!r}"
            )
        if scope_id in visited:
            return
        visiting.add(scope_id)
        parent = by_id[scope_id].parent_scope_id
        if parent is not None:
            visit(parent)
        visiting.discard(scope_id)
        visited.add(scope_id)

    for spec in specs:
        visit(spec.scope_id)


def _build_scope(
    spec: ScopeSpec,
    path: StructuralPath,
    children_by_parent: dict[str | None, list[ScopeSpec]],
    spec_by_id: dict[str, ScopeSpec],
) -> SimulationScope:
    """Recursively build an immutable scope subtree (children sorted by id)."""
    child_specs = children_by_parent.get(spec.scope_id, [])
    child_specs_sorted = sorted(child_specs, key=lambda s: s.scope_id)
    children = tuple(
        _build_scope(child, path.child(child.scope_id), children_by_parent, spec_by_id)
        for child in child_specs_sorted
    )
    objects = tuple(
        SimulationObject(
            object_id=o.object_id,
            object_type=o.object_type,
            display_name=o.display_name,
        )
        for o in sorted(spec.objects, key=lambda x: x.object_id)
    )
    return SimulationScope(
        scope_id=spec.scope_id,
        path=path,
        mode=spec.mode,
        archetype=spec.archetype,
        display_name=spec.display_name,
        children=children,
        objects=objects,
    )


def build_workspace(
    workspace_id: str,
    scope_specs: Iterable[ScopeSpec],
    *,
    display_name: str | None = None,
    description: str | None = None,
) -> Workspace:
    """Validate and build an immutable Workspace tree from flat scope specs.

    Fail-closed: raises :class:`StructuralValidationError` (or
    :class:`StructuralIdentityError`) on any invalid layout. The result is
    deterministic regardless of ``scope_specs`` iteration order.
    """
    specs = list(scope_specs)
    if not workspace_id:
        raise StructuralValidationError("workspace id must not be empty")

    _validate_ids(specs, workspace_id)
    _detect_cycles(specs)

    children_by_parent: dict[str | None, list[ScopeSpec]] = {}
    for spec in specs:
        children_by_parent.setdefault(spec.parent_scope_id, []).append(spec)

    workspace_path = StructuralPath.workspace_root(workspace_id)
    top_specs = sorted(
        children_by_parent.get(None, []), key=lambda s: s.scope_id
    )
    top_scopes = tuple(
        _build_scope(
            spec,
            workspace_path.child(spec.scope_id),
            children_by_parent,
            {s.scope_id: s for s in specs},
        )
        for spec in top_specs
    )
    return Workspace(
        workspace_id=workspace_id,
        path=workspace_path,
        display_name=display_name,
        description=description,
        top_level_scopes=top_scopes,
    )
