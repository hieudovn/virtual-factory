"""Generic Workspace runtime registry/selector (VF-vNEXT-G23).

A smallest, domain-agnostic backend/platform selection seam that lets VF expose
and select between accepted independent Workspaces (e.g. ``TIPA`` and
``shwtp``) without UI yet, preserving strict runtime/session isolation.

Frozen semantics:

- Deterministic Workspace enumeration independent of registration order.
- Selecting a Workspace creates/returns a session for THAT Workspace only.
- Workspace identity is authoritative for target selection: unknown/ambiguous
  id fails closed, and a factory returning a session whose ``workspace_id``
  differs from the registered key fails closed.
- The registry never shares state, run_id, clock, scenario, or truth across
  Workspaces; switching never mutates/merges/silently reuses another session.
- The registry is orchestration/platform metadata only — never a domain-truth
  owner and never a cross-workspace ``CompositionGraph``/runtime coupler.
- The architecture is open: any future Workspace can be registered with its own
  session factory; no platform logic assumes exactly two factories.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from virtual_factory.runcontrol.session import RuntimeSession


class WorkspaceRegistryError(ValueError):
    """Raised when a workspace-runtime registry invariant is violated."""


def _require_workspace_id(workspace_id: str) -> str:
    if not isinstance(workspace_id, str) or not workspace_id.strip():
        raise WorkspaceRegistryError("workspace_id must be a non-empty str")
    return workspace_id


@dataclass(frozen=True, slots=True)
class WorkspaceRuntimeInfo:
    """Deterministic orchestration metadata for one registered Workspace."""

    workspace_id: str
    description: str

    def to_dict(self) -> dict:
        return {"workspace_id": self.workspace_id, "description": self.description}


class WorkspaceRuntimeRegistry:
    """Generic registry mapping ``workspace_id`` -> session factory.

    Orchestration/platform metadata only. Domain runtimes remain truth owners;
    each ``select`` returns an independent fresh session for one Workspace.
    """

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], RuntimeSession]] = {}
        self._descriptions: dict[str, str] = {}

    def register(
        self,
        workspace_id: str,
        factory: Callable[[], RuntimeSession],
        *,
        description: str = "",
    ) -> None:
        """Register a session factory for ``workspace_id`` (fail closed)."""
        workspace_id = _require_workspace_id(workspace_id)
        if not callable(factory):
            raise WorkspaceRegistryError(
                f"factory for {workspace_id!r} must be callable"
            )
        if workspace_id in self._factories:
            raise WorkspaceRegistryError(
                f"duplicate registration for workspace {workspace_id!r}"
            )
        if description is None:
            description = ""
        self._factories[workspace_id] = factory
        self._descriptions[workspace_id] = description

    # ── deterministic enumeration ─────────────────────────────

    def workspace_ids(self) -> tuple[str, ...]:
        """Deterministic sorted Workspace ids (independent of registration order)."""
        return tuple(sorted(self._factories))

    def enumerate(self) -> tuple[WorkspaceRuntimeInfo, ...]:
        """Deterministic orchestration metadata for every registered Workspace."""
        return tuple(
            WorkspaceRuntimeInfo(wid, self._descriptions[wid])
            for wid in self.workspace_ids()
        )

    def metadata(self) -> dict:
        """Read-only platform orchestration metadata (no domain truth)."""
        return {
            "workspace_ids": list(self.workspace_ids()),
            "workspaces": [info.to_dict() for info in self.enumerate()],
        }

    # ── selection ─────────────────────────────────────────────

    def has(self, workspace_id: str) -> bool:
        return _require_workspace_id(workspace_id) in self._factories

    def select(self, workspace_id: str) -> RuntimeSession:
        """Create/return a fresh session for ``workspace_id`` only.

        Unknown workspace fails closed. A factory whose returned session does
        not carry the registered ``workspace_id`` also fails closed (identity
        mismatch). Each call returns an independent instance.
        """
        workspace_id = _require_workspace_id(workspace_id)
        factory = self._factories.get(workspace_id)
        if factory is None:
            raise WorkspaceRegistryError(
                f"unknown workspace {workspace_id!r}; registered workspaces: "
                f"{self.workspace_ids()}"
            )
        session = factory()
        if not isinstance(session, RuntimeSession):
            raise WorkspaceRegistryError(
                f"factory for {workspace_id!r} must return RuntimeSession, got "
                f"{type(session).__name__}"
            )
        if session.workspace_id != workspace_id:
            raise WorkspaceRegistryError(
                f"workspace identity mismatch: registered {workspace_id!r}, "
                f"factory returned session for {session.workspace_id!r}"
            )
        return session
