"""Generic Workspace -> hierarchical Simulation Scope -> Simulation Object model.

G1 structural containment foundation. The model is immutable once built and
validated by :func:`virtual_factory.workspace.builder.build_workspace`. It
carries NO domain runtime state, NO provenance, NO semantic binding, and NO
coordinator/ports.

Frozen semantics preserved (ARCH-01/ARCH-06):

- A Workspace is a top-level structural grouping of Scopes.
- A Simulation Scope is a recursive structural subsystem inside a Workspace.
- A Simulation Object is a leaf structural reference/ownership inside a Scope.
- Hierarchy/containment is a tree (exactly one structural parent).
- A Scope is container-only or executable-capable; executability is a
  capability, not implied by archetype/type/name. G1 does NOT implement the
  execution boundary behind an executable-capable scope.
- Archetype is informational classification metadata, NOT engine-selection
  authority and NOT a universal engine-cardinality rule.
- Structural identity stays distinct from PIM canonical identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from virtual_factory.workspace.identity import StructuralPath


class ScopeMode(str, Enum):
    """Whether a Scope may own an execution/runtime boundary (not implemented in G1)."""

    CONTAINER_ONLY = "container_only"
    EXECUTABLE_CAPABLE = "executable_capable"


class Archetype(str, Enum):
    """Informational classification metadata — never engine-selection authority."""

    CONTINUOUS = "continuous"
    BATCH = "batch"
    DISCRETE = "discrete"
    COMPOSED = "composed"  # hybrid / composed


@dataclass(frozen=True, slots=True)
class SimulationObject:
    """Leaf structural reference belonging to exactly one owning Scope.

    ``object_id`` is unique within the owning scope namespace. ``object_type``
    is an optional plain tag (e.g. ``station``, ``tank``, ``pump``); it is a VF
    structural/runtime-local tag, never a PIM canonical id.
    """

    object_id: str
    object_type: str | None = None
    display_name: str | None = None

    @property
    def id(self) -> str:
        return self.object_id


@dataclass(frozen=True, slots=True)
class SimulationScope:
    """One Simulation Scope in the containment tree.

    ``path`` is the deterministic full structural path (workspace + all ancestor
    scope ids + this scope id). ``children`` and ``objects`` are ordered by id
    (deterministic regardless of input iteration order).
    """

    scope_id: str
    path: StructuralPath
    mode: ScopeMode
    archetype: Archetype | None = None  # informational profile metadata
    display_name: str | None = None
    children: tuple[SimulationScope, ...] = ()
    objects: tuple[SimulationObject, ...] = ()

    @property
    def id(self) -> str:
        return self.scope_id

    @property
    def is_container_only(self) -> bool:
        """True when this scope owns no execution boundary (no fake runtime)."""
        return self.mode is ScopeMode.CONTAINER_ONLY

    @property
    def is_executable_capable(self) -> bool:
        """True when this scope MAY own an execution boundary (G1 does not create one)."""
        return self.mode is ScopeMode.EXECUTABLE_CAPABLE

    def require_executable(self) -> None:
        """Fail-closed guard: executable-only assumptions must never target a
        container-only scope.

        G1 has no execution implementation; this guard exists so later gates
        cannot apply executable-only assumptions to a container-only scope.
        """
        from virtual_factory.workspace.builder import StructuralValidationError

        if self.is_container_only:
            raise StructuralValidationError(
                f"executable-only assumption applied to container-only scope "
                f"{self.path.as_string()}"
            )

    def iter_scopes(self):
        """Yield self then all descendant scopes in deterministic pre-order."""
        yield self
        for child in self.children:
            yield from child.iter_scopes()

    def find_scope(self, scope_id: str) -> SimulationScope | None:
        """Return the descendant scope with this id, or None when absent.

        Raises ``StructuralValidationError`` when the bare id is ambiguous
        (duplicate local ids under different parents). The canonical public
        lookup is path-based (:meth:`Workspace.find_scope_by_path`).
        """
        from virtual_factory.workspace.builder import StructuralValidationError

        matches = [s for s in self.iter_scopes() if s.scope_id == scope_id]
        if not matches:
            return None
        if len(matches) > 1:
            raise StructuralValidationError(
                f"ambiguous scope id {scope_id!r}: {len(matches)} matches; "
                f"use a structural path"
            )
        return matches[0]

    def find_object(self, object_id: str) -> SimulationObject | None:
        """Find an object in this scope's subtree by id, or None when absent.

        Raises when the bare object id is ambiguous across the subtree.
        """
        from virtual_factory.workspace.builder import StructuralValidationError

        matches: list[SimulationObject] = []
        for scope in self.iter_scopes():
            for obj in scope.objects:
                if obj.object_id == object_id:
                    matches.append(obj)
        if not matches:
            return None
        if len(matches) > 1:
            raise StructuralValidationError(
                f"ambiguous object id {object_id!r}: {len(matches)} matches; "
                f"use an owning-scope-qualified reference"
            )
        return matches[0]

    def scope_path_by_id(self, scope_id: str) -> StructuralPath | None:
        """Return the structural path of a descendant scope by id, or None.

        Raises when the bare id is ambiguous (duplicate local ids).
        """
        from virtual_factory.workspace.builder import StructuralValidationError

        matches = [s for s in self.iter_scopes() if s.scope_id == scope_id]
        if not matches:
            return None
        if len(matches) > 1:
            raise StructuralValidationError(
                f"ambiguous scope id {scope_id!r}: {len(matches)} matches; "
                f"use a structural path"
            )
        return matches[0].path


@dataclass(frozen=True, slots=True)
class Workspace:
    """Top-level structural grouping: a Workspace contains top-level Scopes.

    A Workspace does NOT contain Simulation Objects directly (ARCH-01: objects
    belong to Scopes). ``top_level_scopes`` is ordered by scope id.
    """

    workspace_id: str
    path: StructuralPath
    display_name: str | None = None
    description: str | None = None
    top_level_scopes: tuple[SimulationScope, ...] = ()

    @property
    def id(self) -> str:
        return self.workspace_id

    @property
    def scopes(self) -> tuple[SimulationScope, ...]:
        """Alias for the top-level scopes."""
        return self.top_level_scopes

    def find_scope(self, scope_id: str) -> SimulationScope | None:
        """Find a scope anywhere in this workspace by id, or None when absent.

        Raises ``StructuralValidationError`` when the bare id is ambiguous
        (duplicate local ids under different parents). Path-based lookup
        (:meth:`find_scope_by_path`) is the canonical public API.
        """
        from virtual_factory.workspace.builder import StructuralValidationError

        matches: list[SimulationScope] = []
        for scope in self.top_level_scopes:
            matches.extend(s for s in scope.iter_scopes() if s.scope_id == scope_id)
        if not matches:
            return None
        if len(matches) > 1:
            raise StructuralValidationError(
                f"ambiguous scope id {scope_id!r}: {len(matches)} matches; "
                f"use a structural path"
            )
        return matches[0]

    def find_scope_by_path(self, path: StructuralPath) -> SimulationScope | None:
        """Resolve a structural path to a scope in this workspace.

        Fail-closed via :meth:`resolve_scope`; this returns None when absent.
        """
        if path.workspace_id != self.workspace_id:
            return None
        scope_ids = path.scope_ids
        current: SimulationScope | None = None
        children = self.top_level_scopes
        for scope_id in scope_ids:
            found = next((s for s in children if s.scope_id == scope_id), None)
            if found is None:
                return None
            current = found
            children = found.children
        return current

    def resolve_scope(self, path: StructuralPath) -> SimulationScope:
        """Resolve a scope by structural path; raise when it does not exist."""
        from virtual_factory.workspace.builder import StructuralValidationError

        scope = self.find_scope_by_path(path)
        if scope is None:
            raise StructuralValidationError(
                f"unknown structural path {path.as_string()!r} in workspace "
                f"{self.workspace_id!r}"
            )
        return scope

    def resolve_object(self, ref) -> SimulationObject:
        """Resolve an object reference to its owning scope and return the object.

        Fail-closed: raises when the owning scope or object does not exist.
        """
        from virtual_factory.workspace.builder import StructuralValidationError

        scope = self.find_scope_by_path(ref.owning_scope_path)
        if scope is None:
            raise StructuralValidationError(
                f"object {ref.canonical!r} attached to nonexistent scope "
                f"{ref.owning_scope_path.as_string()!r}"
            )
        for obj in scope.objects:
            if obj.object_id == ref.object_id:
                return obj
        raise StructuralValidationError(
            f"object {ref.object_id!r} not found in scope "
            f"{scope.path.as_string()!r}"
        )
