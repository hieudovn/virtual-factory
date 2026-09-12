"""G6 — Shared hierarchical UI context model (read-only, additive).

Derives a minimal READ-ONLY JSON projection from the accepted G1
Workspace/Scope structural authority for the shared hierarchical UI primitives
(hierarchy navigator + context breadcrumb).

Rules frozen by Issue #51 / ARCH-04:
- hierarchy is derived from G1 structural authority ONLY; no second model;
- canonical full :class:`StructuralPath` is preserved (``path`` fields);
- bare local ids are display labels only, never canonical lookup authority;
- container-only vs executable-capable comes from G1 ``ScopeMode``; capability
  is never inferred from a scope name/archetype;
- no PIM canonical identity fabrication; no run/scenario/provenance guessing;
- no runtime state mutation — every function here is a pure read-only
  projection of an already-constructed Workspace (G1 Workspaces are frozen);
- Inspector (object) context vs Monitoring (scope) context stay distinct: an
  object is appended to the selection ONLY when an object is actually selected
  and resolvable in the selected scope.

This module does NOT implement G7 run-control/replay or any orchestration API.
"""

from __future__ import annotations

from typing import Optional

from virtual_factory.workspace import (
    SimulationObject,
    SimulationScope,
    StructuralPath,
    Workspace,
)


class UiHierarchyError(ValueError):
    """Raised when a UI hierarchy/context projection violates a fail-closed
    structural rule (unknown path, unknown/ambiguous object, foreign workspace).
    """


# ── Read-only projection helpers ─────────────────────────────

def simulation_object_to_dict(obj: SimulationObject) -> dict:
    """Project one Simulation Object (display label only, never canonical)."""
    return {
        "object_id": obj.object_id,
        "object_type": obj.object_type,
        "display_name": obj.display_name,
    }


def simulation_scope_to_dict(scope: SimulationScope) -> dict:
    """Recursively project one Simulation Scope preserving canonical path.

    Deterministic: child order follows the G1 tree order (sorted by scope id),
    never a UI/insertion order.
    """
    return {
        "scope_id": scope.scope_id,
        "path": scope.path.as_string(),
        "mode": scope.mode.value if scope.mode is not None else None,
        "container_only": scope.is_container_only,
        "executable_capable": scope.is_executable_capable,
        "archetype": (
            scope.archetype.value if scope.archetype is not None else None
        ),
        "display_name": scope.display_name or scope.scope_id,
        "objects": [
            simulation_object_to_dict(o)
            for o in scope.objects  # already ordered by object id (G1)
        ],
        "children": [
            simulation_scope_to_dict(child) for child in scope.children
        ],
    }


def workspace_to_dict(workspace: Workspace) -> dict:
    """Project a G1 Workspace (id, path, metadata, recursive scope tree)."""
    return {
        "workspace_id": workspace.workspace_id,
        "path": workspace.path.as_string(),
        "display_name": workspace.display_name,
        "description": workspace.description,
        "scopes": [
            simulation_scope_to_dict(scope)
            for scope in workspace.top_level_scopes  # deterministic G1 order
        ],
    }


# ── Path-qualified selection helpers ─────────────────────────

def parse_path(raw: str) -> StructuralPath:
    """Parse a canonical structural path string (fail closed on empty/garbage)."""
    if not raw or not isinstance(raw, str):
        raise UiHierarchyError("structural path must be a non-empty string")
    try:
        return StructuralPath.from_string(raw)
    except Exception as exc:  # noqa: BLE001 - re-raise as UI contract error
        raise UiHierarchyError(f"invalid structural path {raw!r}: {exc}") from exc


def _resolve_scope(workspace: Workspace, path: StructuralPath) -> SimulationScope:
    if path.workspace_id != workspace.workspace_id:
        raise UiHierarchyError(
            f"path {path.as_string()!r} is outside workspace "
            f"{workspace.workspace_id!r}"
        )
    scope = workspace.find_scope_by_path(path)
    if scope is None:
        raise UiHierarchyError(
            f"unknown structural path {path.as_string()!r} in workspace "
            f"{workspace.workspace_id!r}"
        )
    return scope


# ── Structural context (selection) ───────────────────────────

def structural_context(
    workspace: Workspace,
    *,
    scope_path: Optional[StructuralPath] = None,
    object_id: Optional[str] = None,
) -> dict:
    """Build a read-only UI context for one workspace + optional selection.

    - With no scope_path: workspace-level (monitoring) context.
    - With a scope_path: scope-level (monitoring) context; container-only scopes
      are selectable for context but never imply executability.
    - With an object_id: the object is appended ONLY when it actually resolves
      in the SELECTED scope (Inspector object context). No object is fabricated.
    """
    tree = workspace_to_dict(workspace)

    if scope_path is None:
        if object_id is not None:
            raise UiHierarchyError(
                "an object requires an owning scope selection"
            )
        selection = {
            "kind": "workspace",
            "path": workspace.path.as_string(),
            "workspace_id": workspace.workspace_id,
            "display_name": workspace.display_name or workspace.workspace_id,
        }
    else:
        scope = _resolve_scope(workspace, scope_path)
        selection = {
            "kind": "scope",
            "path": scope.path.as_string(),
            "scope_id": scope.scope_id,
            "mode": scope.mode.value if scope.mode is not None else None,
            "container_only": scope.is_container_only,
            "executable_capable": scope.is_executable_capable,
            "display_name": scope.display_name or scope.scope_id,
        }
        if object_id is not None:
            obj = _find_object_in_scope(scope, object_id)
            selection["kind"] = "object"
            selection["object"] = simulation_object_to_dict(obj)
            selection["object_id"] = obj.object_id

    return {
        "workspace": {
            "workspace_id": workspace.workspace_id,
            "path": workspace.path.as_string(),
            "display_name": workspace.display_name,
        },
        "hierarchy": tree["scopes"],
        "selection": selection,
        "scope_centric": True,
        "executable_controls_implied": False,
    }


def _find_object_in_scope(
    scope: SimulationScope, object_id: str
) -> SimulationObject:
    """Find an object in the SELECTED scope only (owning-scope-qualified).

    Object selection never changes structural ownership and never searches a
    different scope implicitly.
    """
    for obj in scope.objects:
        if obj.object_id == object_id:
            return obj
    raise UiHierarchyError(
        f"object {object_id!r} not present in scope {scope.path.as_string()!r}"
    )


# ── Truthful minimal contexts (continuous) ───────────────────

def root_only_context(
    workspace_id: str,
    *,
    display_name: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Smallest TRUTHFUL context when no authoritative multi-level G1 hierarchy
    is available (e.g. the continuous dashboard): a workspace root with NO
    invented nested scopes.

    Rule: do not invent plant structure. Consumers must not fabricate scope
    levels that G1 authority does not provide.
    """
    if not workspace_id:
        raise UiHierarchyError("workspace_id must be non-empty")
    return {
        "workspace": {
            "workspace_id": workspace_id,
            "path": workspace_id,
            "display_name": display_name or workspace_id,
        },
        "hierarchy": [],
        "selection": {
            "kind": "workspace",
            "path": workspace_id,
            "workspace_id": workspace_id,
            "display_name": display_name or workspace_id,
        },
        "scope_centric": True,
        "executable_controls_implied": False,
        "note": (
            "no authoritative multi-level G1 structure available; "
            "root-only context; no hierarchy invented"
        ),
    }
