"""G9 — deterministic pinned binding artifact loader (repo-native, offline).

Loads a pinned semantic binding description (YAML/JSON-shaped) WITHOUT any
network access and WITHOUT a mutable ``main/latest`` lookup. The caller supplies
the exact artifact path; content is expected to be deterministic (pinned).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from virtual_factory.semantic.binding import (
    BindingMode,
    CompatibilityDecision,
    LocalCanonicalMapping,
    MappingStatus,
    RuntimeAuthorization,
    SemanticBinding,
    SemanticBindingError,
    SemanticSourcePin,
)


def binding_from_dict(data: dict[str, Any]) -> SemanticBinding:
    """Build a SemanticBinding from a plain dict (deterministic, keyed fields)."""
    if not isinstance(data, dict):
        raise SemanticBindingError("binding artifact must be a mapping")

    source_data = data.get("source") or {}
    if not isinstance(source_data, dict):
        raise SemanticBindingError("binding source must be a mapping")

    source = SemanticSourcePin(
        producer_id=source_data.get("producer_id"),
        artifact_id=source_data.get("artifact_id"),
        version=source_data.get("version"),
        artifact_hash=source_data.get("artifact_hash"),
        semantic_identity_sha=source_data.get("semantic_identity_sha"),
        source_model_version=source_data.get("source_model_version"),
    )

    mappings: list[LocalCanonicalMapping] = []
    for entry in data.get("mappings", []) or []:
        if not isinstance(entry, dict):
            raise SemanticBindingError("mapping entry must be a mapping")
        mappings.append(
            LocalCanonicalMapping(
                local_id=entry["local_id"],
                canonical_id=entry.get("canonical_id"),
                status=MappingStatus(entry.get("status", "accepted")),
                published=bool(entry.get("published", False)),
                canonical_claimed=bool(entry.get("canonical_claimed", False)),
                explicit=bool(entry.get("explicit", True)),
            )
        )

    return SemanticBinding(
        mode=BindingMode(data.get("mode", "none")),
        source=source,
        compatibility=CompatibilityDecision(
            data.get("compatibility", "not_compatible")
        ),
        runtime_authorization=RuntimeAuthorization(
            data.get("runtime_authorization", "NOT_AUTHORIZED")
        ),
        mappings=tuple(mappings),
    )


def load_binding_artifact(path: str | Path) -> SemanticBinding:
    """Load a pinned binding artifact from a repo-native file path.

    Deterministic and offline: no network, no dynamic main/latest resolution.
    """
    text = Path(path).read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except Exception as exc:  # noqa: BLE001 - fail closed, surface the parse error
        raise SemanticBindingError(f"cannot parse binding artifact {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SemanticBindingError(f"binding artifact {path} is not a mapping")
    return binding_from_dict(data)
