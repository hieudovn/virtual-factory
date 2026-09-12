"""Workspace / Simulation Scope structural foundation (G1).

A small, dependency-light structural foundation representing
``Workspace -> hierarchical Simulation Scope -> Simulation Object``.

Public API:

- identity: :class:`StructuralPath`, :class:`SimulationObjectRef`
- model: :class:`Workspace`, :class:`SimulationScope`, :class:`SimulationObject`,
  :class:`ScopeMode`, :class:`Archetype`
- builder: :func:`build_workspace`, :class:`ScopeSpec`, :class:`ObjectSpec`
- config/loader: :class:`WorkspaceConfig`, :func:`load_workspace_manifest`

G1 does NOT implement runtime orchestration, provenance-v2, semantic binding,
coordinator/ports, or any execution boundary.
"""

from __future__ import annotations

from virtual_factory.workspace.identity import (
    SimulationObjectRef,
    StructuralIdentityError,
    StructuralPath,
)
from virtual_factory.workspace.model import (
    Archetype,
    ScopeMode,
    SimulationObject,
    SimulationScope,
    Workspace,
)
from virtual_factory.workspace.builder import (
    ObjectSpec,
    ScopeSpec,
    StructuralValidationError,
    build_workspace,
)
from virtual_factory.workspace.config import (
    ObjectConfig,
    ScopeConfig,
    WorkspaceConfig,
    WorkspaceManifestFile,
)
from virtual_factory.workspace.loader import (
    WorkspaceManifestError,
    load_workspace_config,
    load_workspace_manifest,
)

__all__ = [
    "SimulationObjectRef",
    "StructuralIdentityError",
    "StructuralPath",
    "Archetype",
    "ScopeMode",
    "SimulationObject",
    "SimulationScope",
    "Workspace",
    "ObjectSpec",
    "ScopeSpec",
    "StructuralValidationError",
    "build_workspace",
    "ObjectConfig",
    "ScopeConfig",
    "WorkspaceConfig",
    "WorkspaceManifestFile",
    "WorkspaceManifestError",
    "load_workspace_config",
    "load_workspace_manifest",
]
