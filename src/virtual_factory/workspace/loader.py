"""Workspace manifest loading seam (generic, structural only).

Loads a YAML workspace manifest under ``configs/workspaces/`` (PH00 B9), parses
and validates its structure, and builds an immutable Workspace tree. No runtime
engine, no semantic binding, no coordinator/ports, no provenance-v2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from virtual_factory.workspace.builder import StructuralValidationError
from virtual_factory.workspace.config import WorkspaceConfig, WorkspaceManifestFile
from virtual_factory.workspace.model import Workspace


class WorkspaceManifestError(ValueError):
    """Raised when a workspace manifest cannot be parsed or validated."""


def load_yaml_mapping(path: str | Path) -> dict[str, Any]:
    """Load a YAML file into a top-level mapping."""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise WorkspaceManifestError(
            f"expected mapping at top level of {config_path}"
        )
    return data


def load_workspace_config(path: str | Path) -> WorkspaceConfig:
    """Parse and structurally validate a workspace manifest into a config."""
    manifest = WorkspaceManifestFile.model_validate(load_yaml_mapping(path))
    return manifest.workspace


def load_workspace_manifest(path: str | Path) -> Workspace:
    """Load a workspace manifest file and build the validated Workspace tree."""
    try:
        config = load_workspace_config(path)
        return config.to_workspace()
    except (StructuralValidationError, ValueError) as exc:
        if isinstance(exc, StructuralValidationError):
            raise
        raise WorkspaceManifestError(str(exc)) from exc
