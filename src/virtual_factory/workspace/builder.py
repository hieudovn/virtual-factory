"""Fail-closed Workspace/Scope structural building and validation.

Builds an immutable :class:`~virtual_factory.workspace.model.Workspace` from flat
scope specifications and enforces the G1 containment/identity invariants:

- workspace id valid;
- scope id valid and unique WITHIN ITS STRUCTURAL PARENT NAMESPACE (NOT global
  across the Workspace); the full ``StructuralPath`` is the authoritative
  unambiguous scope identity. Repeated local scope ids along an ancestor chain
  (e.g. ``W/Area-A/Line-1/Area-A``) are VALID because their full structural
  paths differ;
- parent references are path-qualified (``StructuralPath``) — resolution never
  depends on a globally-unique bare scope id;
- every declared parent path exists (missing/invalid parent is an error); a
  parent cycle is structurally unrepresentable because each scope path is its
  parent path plus one segment (parent depth strictly decreases to the
  canonical top-level), so containment is a tree by construction;
- container-only vs executable-capable is explicit; executable-only assumptions
  are never applied to a container-only scope (guarded at the model);
- objects belong to declared scopes; an object attached to a nonexistent scope
  is rejected at resolution time (fail-closed);
- completeness: every validated declaration materializes exactly once (C02);
- the resulting tree is deterministic independent of input iteration order
  (children and objects are ordered by id).

G1 does NOT implement runtime orchestration, provenance-v2, semantic binding,
coordinator/ports, or any execution boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

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

    ``parent_path`` is the full ``StructuralPath`` of the parent scope, or None
    for a top-level scope directly under the Workspace. It is path-qualified
    (never a bare id), so duplicate local scope ids under different parents
    remain valid and resolve independently by their full path.
    """

    scope_id: str
    mode: ScopeMode
    parent_path: StructuralPath | None = None
    archetype: Archetype | None = None
    display_name: str | None = None
    objects: tuple[ObjectSpec, ...] = ()


def _workspace_root(workspace_id: str) -> StructuralPath:
    if not workspace_id:
        raise StructuralValidationError("workspace id must not be empty")
    return StructuralPath.workspace_root(workspace_id)


def _scope_path(spec: ScopeSpec, workspace_root: StructuralPath) -> StructuralPath:
    """The full structural path of a declared scope."""
    if spec.parent_path is None:
        return workspace_root.child(spec.scope_id)
    return spec.parent_path.child(spec.scope_id)


def _compute_paths(
    specs: Sequence[ScopeSpec], workspace_root: StructuralPath
) -> dict[StructuralPath, ScopeSpec]:
    """Compute each scope's full path and validate id/path/object basics.

    Returns a deterministic-by-construction map ``path -> spec``. Duplicate scope
    ids are only rejected when they collide in the SAME parent namespace (same
    parent path + same scope id -> same full path).
    """
    path_to_spec: dict[StructuralPath, ScopeSpec] = {}
    for spec in specs:
        if not spec.scope_id:
            raise StructuralValidationError("scope id must not be empty")
        if spec.parent_path is not None and (
            spec.parent_path.workspace_id != workspace_root.workspace_id
        ):
            raise StructuralValidationError(
                f"scope {spec.scope_id!r} parent path "
                f"{spec.parent_path.as_string()!r} is not inside workspace "
                f"{workspace_root.workspace_id!r}"
            )
        if spec.parent_path == workspace_root:
            raise StructuralValidationError(
                f"scope {spec.scope_id!r} uses workspace root "
                f"{workspace_root.as_string()!r} as parent_path; a top-level "
                f"scope must use parent_path=None (canonical representation)"
            )

        path = _scope_path(spec, workspace_root)
        if path in path_to_spec:
            raise StructuralValidationError(
                f"duplicate scope id {spec.scope_id!r} within the same parent "
                f"namespace (path {path.as_string()!r})"
            )
        path_to_spec[path] = spec

        # object ids unique within owning scope + non-empty
        obj_ids = [o.object_id for o in spec.objects]
        if len(obj_ids) != len(set(obj_ids)):
            raise StructuralValidationError(
                f"scope {spec.scope_id!r} has duplicate object ids"
            )
        for obj in spec.objects:
            if not obj.object_id:
                raise StructuralValidationError("object id must not be empty")
    return path_to_spec


def _validate_parents(
    path_to_spec: dict[StructuralPath, ScopeSpec],
) -> None:
    """Every non-root parent path must reference a declared scope path.

    A top-level scope uses ``parent_path=None`` (the canonical representation);
    ``parent_path == workspace_root`` is rejected earlier in ``_compute_paths``.
    """
    for path, spec in path_to_spec.items():
        if spec.parent_path is None:
            continue
        if spec.parent_path not in path_to_spec:
            raise StructuralValidationError(
                f"scope {spec.scope_id!r} has missing/invalid parent path "
                f"{spec.parent_path.as_string()!r}"
            )


def _build_scope(
    path: StructuralPath,
    spec: ScopeSpec,
    path_to_spec: dict[StructuralPath, ScopeSpec],
    children_by_parent: dict[StructuralPath | None, list[StructuralPath]],
) -> SimulationScope:
    """Recursively build an immutable scope subtree (children sorted by path)."""
    child_paths = sorted(
        children_by_parent.get(path, ()), key=lambda p: p.as_string()
    )
    children = tuple(
        _build_scope(cp, path_to_spec[cp], path_to_spec, children_by_parent)
        for cp in child_paths
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


def _scope_count(scopes: tuple[SimulationScope, ...]) -> int:
    """Total number of scope nodes under the given roots (recursive)."""
    total = 0
    for scope in scopes:
        total += 1 + _scope_count(scope.children)
    return total


def _check_completeness(
    path_to_spec: dict[StructuralPath, ScopeSpec],
    top_scopes: tuple[SimulationScope, ...],
) -> None:
    """Every validated ScopeSpec must materialize exactly once in the tree.

    Fail-closed: if the number of scope nodes in the built tree differs from the
    number of validated declarations (or any declared path is missing), the build
    must fail rather than silently drop a declaration.
    """
    built_paths = set()

    def collect(scopes: tuple[SimulationScope, ...]) -> None:
        for scope in scopes:
            built_paths.add(scope.path)
            collect(scope.children)

    collect(top_scopes)
    declared = set(path_to_spec)
    if len(built_paths) != len(declared):
        missing = sorted(p.as_string() for p in declared - built_paths)
        extra = sorted(p.as_string() for p in built_paths - declared)
        raise StructuralValidationError(
            f"internal completeness error: {len(declared)} scope declarations "
            f"materialized {len(built_paths)} nodes (missing={missing}, "
            f"extra={extra})"
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
    :class:`~virtual_factory.workspace.identity.StructuralIdentityError` from the
    path segment validation) on any invalid layout, including a completeness
    check that every validated declaration materializes exactly once. The result
    is deterministic regardless of ``scope_specs`` iteration order.
    """
    specs = list(scope_specs)
    workspace_root = _workspace_root(workspace_id)

    path_to_spec = _compute_paths(specs, workspace_root)
    _validate_parents(path_to_spec)

    children_by_parent: dict[StructuralPath | None, list[StructuralPath]] = {}
    for path, spec in path_to_spec.items():
        children_by_parent.setdefault(spec.parent_path, []).append(path)

    top_paths = sorted(
        children_by_parent.get(None, ()), key=lambda p: p.as_string()
    )
    top_scopes = tuple(
        _build_scope(tp, path_to_spec[tp], path_to_spec, children_by_parent)
        for tp in top_paths
    )
    _check_completeness(path_to_spec, top_scopes)
    return Workspace(
        workspace_id=workspace_id,
        path=workspace_root,
        display_name=display_name,
        description=description,
        top_level_scopes=top_scopes,
    )
