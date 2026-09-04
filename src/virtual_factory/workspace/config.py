"""Generic Workspace manifest configuration models (PH00 B9 seam).

Loads and validates the *structure* of a workspace manifest. G1 deliberately
implements NO semantic binding, NO runtime engine creation, NO coordinator/ports
and NO provenance-v2. The schema is generic — it is not SH-WTP- or TIPA-name
specific (workspace names are data, never platform behavior).

Frozen workspace location convention (PH00 B9): manifests live under
``configs/workspaces/``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from virtual_factory.workspace.builder import ObjectSpec, ScopeSpec, build_workspace
from virtual_factory.workspace.model import Archetype, ScopeMode, Workspace


class ObjectConfig(BaseModel):
    """One leaf Simulation Object declared inside an owning scope."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    object_type: str | None = None
    display_name: str | None = None


class ScopeConfig(BaseModel):
    """One Simulation Scope declaration (recursive via ``children``)."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    mode: ScopeMode
    archetype: Archetype | None = None
    display_name: str | None = None
    children: list["ScopeConfig"] = Field(default_factory=list)
    objects: list[ObjectConfig] = Field(default_factory=list)

    def to_specs(self, parent_scope_id: str | None) -> list[ScopeSpec]:
        """Flatten this nested scope into one ScopeSpec per scope."""
        specs = [
            ScopeSpec(
                scope_id=self.id,
                mode=self.mode,
                parent_scope_id=parent_scope_id,
                archetype=self.archetype,
                display_name=self.display_name,
                objects=tuple(
                    ObjectSpec(
                        object_id=o.id,
                        object_type=o.object_type,
                        display_name=o.display_name,
                    )
                    for o in self.objects
                ),
            )
        ]
        for child in self.children:
            specs.extend(child.to_specs(parent_scope_id=self.id))
        return specs


class WorkspaceConfig(BaseModel):
    """A generic workspace manifest (structure only)."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    name: str | None = None
    description: str | None = None
    scopes: list[ScopeConfig] = Field(default_factory=list)

    def to_specs(self) -> list[ScopeSpec]:
        """Flatten the nested manifest into flat ScopeSpec declarations."""
        specs: list[ScopeSpec] = []
        for scope in self.scopes:
            specs.extend(scope.to_specs(parent_scope_id=None))
        return specs

    def to_workspace(self) -> Workspace:
        """Validate and build the immutable Workspace structural tree."""
        return build_workspace(
            workspace_id=self.id,
            scope_specs=self.to_specs(),
            display_name=self.name,
            description=self.description,
        )


class WorkspaceManifestFile(BaseModel):
    """Top-level YAML envelope: ``workspace: <WorkspaceConfig>``."""

    model_config = ConfigDict(extra="allow")

    workspace: WorkspaceConfig

    @model_validator(mode="before")
    @classmethod
    def _accept_bare_mapping(cls, value: Any) -> Any:
        # Tolerate a manifest that is already the workspace mapping itself.
        if isinstance(value, dict) and "workspace" not in value:
            return {"workspace": value}
        return value
