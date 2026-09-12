"""Immutable structural identity value objects for the Workspace/Scope foundation.

G1 scope: structural identity and containment ONLY. No runtime orchestration,
provenance, semantic binding, coordinator, ports, or domain state.

The three distinct identities from PH00 B2 remain separate:

- ``workspace_id`` / structural scope path = VF structural identity (this module);
- ``canonical_signal_id`` / PIM canonical identity = owned by PIM (never here);
- ``outputs.namespace`` = protocol/path-safe output namespace (never here).

Structural identity NEVER silently equals or replaces a PIM canonical id.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PATH_SEPARATOR = "/"
# Id segments must be path-safe and deterministic; letters/digits and . _ -
_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class StructuralIdentityError(ValueError):
    """Raised when a structural id or structural path is invalid."""


def _validate_segment(segment: str, role: str) -> None:
    """Validate one path segment (workspace id or scope id)."""
    if not segment:
        raise StructuralIdentityError(f"{role} must not be empty")
    if _PATH_SEPARATOR in segment:
        raise StructuralIdentityError(
            f"{role} {segment!r} must not contain {_PATH_SEPARATOR!r}"
        )
    if not _SEGMENT_RE.fullmatch(segment):
        raise StructuralIdentityError(
            f"{role} {segment!r} is invalid; allowed: letters, digits, '.', '_', '-'"
        )


@dataclass(frozen=True, slots=True)
class StructuralPath:
    """Deterministic structural identity path ``workspace/scope/.../scope``.

    ``segments[0]`` is the workspace id; ``segments[1:]`` are scope ids down the
    containment chain. A path with a single segment addresses the workspace
    itself. Immutable and value-style.
    """

    segments: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.segments:
            raise StructuralIdentityError("structural path must not be empty")
        for index, segment in enumerate(self.segments):
            _validate_segment(
                segment, "workspace id" if index == 0 else "scope id"
            )

    @property
    def workspace_id(self) -> str:
        """Workspace id (first segment)."""
        return self.segments[0]

    @property
    def scope_ids(self) -> tuple[str, ...]:
        """Scope ids along the containment chain (excludes workspace id)."""
        return self.segments[1:]

    @property
    def depth(self) -> int:
        """Number of segments (1 == the workspace root itself)."""
        return len(self.segments)

    @property
    def is_workspace_root(self) -> bool:
        return len(self.segments) == 1

    @property
    def parent(self) -> StructuralPath | None:
        """Parent structural path, or None when already at the workspace root."""
        if self.is_workspace_root:
            return None
        return StructuralPath(self.segments[:-1])

    def child(self, scope_id: str) -> StructuralPath:
        """Return the structural path of a child scope under this path."""
        _validate_segment(scope_id, "scope id")
        return StructuralPath(self.segments + (scope_id,))

    def as_string(self) -> str:
        """Deterministic canonical string form."""
        return _PATH_SEPARATOR.join(self.segments)

    def __str__(self) -> str:
        return self.as_string()

    @classmethod
    def workspace_root(cls, workspace_id: str) -> StructuralPath:
        """Structural path for a workspace root."""
        return cls((workspace_id,))

    @classmethod
    def from_string(cls, raw: str) -> StructuralPath:
        """Parse a canonical structural path string."""
        if not raw:
            raise StructuralIdentityError("structural path must not be empty")
        return cls(tuple(raw.split(_PATH_SEPARATOR)))


@dataclass(frozen=True, slots=True)
class SimulationObjectRef:
    """Deterministic reference to a leaf Simulation Object.

    Includes the full owning structural Scope path (so a bare object id is never
    ambiguous) plus the object id unique within that owning scope namespace.
    """

    owning_scope_path: StructuralPath
    object_id: str

    def __post_init__(self) -> None:
        if self.owning_scope_path.is_workspace_root:
            raise StructuralIdentityError(
                "SimulationObjectRef requires a Scope owning path, "
                "not a workspace root path"
            )
        _validate_segment(self.object_id, "object id")

    @property
    def canonical(self) -> str:
        """Deterministic canonical string: ``<scope path>/<object id>``."""
        return f"{self.owning_scope_path.as_string()}{_PATH_SEPARATOR}{self.object_id}"

    def __str__(self) -> str:
        return self.canonical

    @classmethod
    def from_string(cls, raw: str) -> SimulationObjectRef:
        """Parse ``workspace/scope/.../object`` into a ref.

        The final segment is the object id; the prefix is the owning scope path.
        """
        if not raw:
            raise StructuralIdentityError("object ref must not be empty")
        parts = raw.split(_PATH_SEPARATOR)
        if len(parts) < 2:
            raise StructuralIdentityError(
                "object ref must include at least workspace/scope/object"
            )
        scope_path = StructuralPath(tuple(parts[:-1]))
        return cls(owning_scope_path=scope_path, object_id=parts[-1])
