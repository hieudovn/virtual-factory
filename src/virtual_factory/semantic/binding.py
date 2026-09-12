"""G9 — Semantic Binding vNext: generic model (PIM read-only reference).

Frozen authority split (Issue #54 / PH00 / ARCH):

- PIM owns canonical semantic identity (``canonical_signal_id``, canonical
  object identity) and the external export artifact pins;
- VF owns runtime/simulation identity (``runtime_signal_id``, ``StructuralPath``,
  simulation object ids);
- a binding is an EXPLICIT local -> canonical relationship, never a rename, and
  never a name-based/heuristic fallback;
- semantic compatibility decision and runtime authorization are SEPARATE fields.

All value objects are immutable; no network, no dynamic ``main/latest`` lookup.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SemanticBindingError(ValueError):
    """Raised when a semantic binding model invariant is violated."""


class BindingMode(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    NONE = "none"


class CompatibilityDecision(str, Enum):
    """Semantic compatibility/review decision (NOT runtime authorization)."""

    COMPATIBLE = "compatible"
    COMPATIBLE_WITH_CONSTRAINTS = "compatible_with_constraints"
    NOT_COMPATIBLE = "not_compatible"


class RuntimeAuthorization(str, Enum):
    """Whether the pinned export may drive VF runtime execution.

    Independent from :class:`CompatibilityDecision`. ``compatible_with_constraints``
    never implies ``AUTHORIZED``.
    """

    NOT_AUTHORIZED = "NOT_AUTHORIZED"
    AUTHORIZED = "AUTHORIZED"


class MappingStatus(str, Enum):
    ACCEPTED = "accepted"
    UNMAPPED = "unmapped"
    REVIEW_REQUIRED = "review_required"


def _non_empty(value: Any, name: str) -> None:
    if value is not None and (not isinstance(value, str) or not value.strip()):
        raise SemanticBindingError(f"{name} must be a non-empty str")


@dataclass(frozen=True, slots=True)
class SemanticSourcePin:
    """Pinned semantic source identity (prevents floating/name-only binding)."""

    producer_id: str | None = None
    artifact_id: str | None = None
    version: str | None = None
    artifact_hash: str | None = None
    semantic_identity_sha: str | None = None
    source_model_version: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "producer_id",
            "artifact_id",
            "version",
            "artifact_hash",
            "semantic_identity_sha",
            "source_model_version",
        ):
            _non_empty(getattr(self, name), name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "producer_id": self.producer_id,
            "artifact_id": self.artifact_id,
            "version": self.version,
            "artifact_hash": self.artifact_hash,
            "semantic_identity_sha": self.semantic_identity_sha,
            "source_model_version": self.source_model_version,
        }


@dataclass(frozen=True, slots=True)
class LocalCanonicalMapping:
    """Explicit relationship between one VF local id and one PIM canonical id.

    ``local_id`` is VF runtime identity and is NEVER replaced by
    ``canonical_id`` (which stays external/read-only). ``explicit=False`` marks a
    name-only/heuristic mapping, which is rejected for required bindings.
    """

    local_id: str
    canonical_id: str | None = None
    status: MappingStatus = MappingStatus.ACCEPTED
    published: bool = False
    canonical_claimed: bool = False
    explicit: bool = True

    def __post_init__(self) -> None:
        _non_empty(self.local_id, "local_id")
        _non_empty(self.canonical_id, "canonical_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "local_id": self.local_id,
            "canonical_id": self.canonical_id,
            "status": self.status.value,
            "published": self.published,
            "canonical_claimed": self.canonical_claimed,
            "explicit": self.explicit,
        }


@dataclass(frozen=True, slots=True)
class SemanticBinding:
    """One pinned semantic contract a VF Workspace may reference/consume."""

    mode: BindingMode = BindingMode.NONE
    source: SemanticSourcePin = field(default_factory=SemanticSourcePin)
    compatibility: CompatibilityDecision = CompatibilityDecision.NOT_COMPATIBLE
    runtime_authorization: RuntimeAuthorization = RuntimeAuthorization.NOT_AUTHORIZED
    mappings: tuple[LocalCanonicalMapping, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "source": self.source.to_dict(),
            "compatibility": self.compatibility.value,
            "runtime_authorization": self.runtime_authorization.value,
            "mappings": [m.to_dict() for m in self.mappings],
        }
