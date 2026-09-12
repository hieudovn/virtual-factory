"""G7-B — hierarchical target resolution (read-only, G1 authority).

Resolves a path-qualified target against a G1 Workspace and produces the
deterministic set of descendant EXECUTABLE scopes that may actually run:

- workspace target        -> every executable scope in the workspace tree;
- container target        -> every executable descendant of that container;
- executable scope target -> that scope only.

Rules (Issue #52):
- canonical G1 ``StructuralPath`` is the only lookup authority;
- unknown/foreign paths fail closed;
- container-only scopes are orchestration targets ONLY and are never returned
  as executable participants;
- the resulting scope set is deterministic (sorted by canonical path).
"""

from __future__ import annotations

from dataclasses import dataclass

from virtual_factory.workspace import (
    SimulationScope,
    StructuralPath,
    Workspace,
)


class TargetResolutionError(ValueError):
    """Raised when a run target cannot be resolved honestly."""


@dataclass(frozen=True, slots=True)
class TargetResolution:
    workspace_id: str
    target_path: StructuralPath
    target_kind: str  # "workspace" | "container" | "executable"
    effective_scope_paths: tuple[StructuralPath, ...]

    @property
    def effective_scope_strings(self) -> tuple[str, ...]:
        return tuple(p.as_string() for p in self.effective_scope_paths)


def _collect_executable(
    scope: SimulationScope, out: list[StructuralPath]
) -> None:
    """Collect executable scope paths in this scope's subtree (recursive).

    Container-only nodes are skipped — they never become participants.
    """
    if scope.is_executable_capable:
        out.append(scope.path)
    for child in scope.children:
        _collect_executable(child, out)


def resolve_target(
    workspace: Workspace, target_path: StructuralPath
) -> TargetResolution:
    """Resolve a path-qualified run target to its effective executable scopes."""
    if not isinstance(target_path, StructuralPath):
        raise TargetResolutionError(
            f"target_path must be a StructuralPath, got {type(target_path).__name__}"
        )
    if target_path.workspace_id != workspace.workspace_id:
        raise TargetResolutionError(
            f"target path {target_path.as_string()!r} is outside workspace "
            f"{workspace.workspace_id!r}"
        )

    if target_path.is_workspace_root:
        effective: list[StructuralPath] = []
        for top in workspace.top_level_scopes:
            _collect_executable(top, effective)
        return TargetResolution(
            workspace_id=workspace.workspace_id,
            target_path=target_path,
            target_kind="workspace",
            effective_scope_paths=tuple(sorted(effective, key=lambda p: p.as_string())),
        )

    scope = workspace.find_scope_by_path(target_path)
    if scope is None:
        raise TargetResolutionError(
            f"unknown structural path {target_path.as_string()!r} in workspace "
            f"{workspace.workspace_id!r}"
        )

    if scope.is_executable_capable:
        return TargetResolution(
            workspace_id=workspace.workspace_id,
            target_path=target_path,
            target_kind="executable",
            effective_scope_paths=(scope.path,),
        )

    # container-only: orchestration target -> descendant executable scopes only.
    effective = []
    for child in scope.children:
        _collect_executable(child, effective)
    return TargetResolution(
        workspace_id=workspace.workspace_id,
        target_path=target_path,
        target_kind="container",
        effective_scope_paths=tuple(sorted(effective, key=lambda p: p.as_string())),
    )
