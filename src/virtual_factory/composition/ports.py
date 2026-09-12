"""Typed cross-scope boundary ports (G4).

A boundary port is a VF structural/runtime boundary identity — NOT a PIM
canonical identity. It declares exactly one exchange endpoint owned by exactly
one structural scope.

Frozen semantics:

- direction is explicit ``in``/``out`` (no ambiguous ``inout`` for the G4
  baseline);
- category is one of the frozen cross-scope flows (material / utility /
  information / coordination);
- optional ``unit``/``descriptor`` are plain compatibility tags — they are NEVER
  PIM semantic authority;
- output may fan out deterministically; baseline input has at most one producer
  (implicit many-to-one merge is rejected by the coordinator);
- a port belongs to a Scope (never the Workspace root directly).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from virtual_factory.workspace.identity import StructuralPath


class PortError(ValueError):
    """Raised when a boundary-port invariant is violated."""


class PortDirection(str, Enum):
    """Direction of a boundary exchange endpoint."""

    IN = "in"
    OUT = "out"


class PortCategory(str, Enum):
    """Frozen cross-scope flow categories."""

    MATERIAL = "material"          # physical flow
    UTILITY = "utility"            # energy flow
    INFORMATION = "information"    # observation flow
    COORDINATION = "coordination"  # event flow


def _require_nonempty(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise PortError(f"{name} must be a non-empty str")


@dataclass(frozen=True, slots=True)
class PortRef:
    """Deterministic boundary endpoint identity: ``owner scope + port id``.

    The port id is unique within its owning scope namespace; the full ref is
    authoritative. It is VF structural/runtime boundary identity, never a PIM
    canonical id.
    """

    owner_scope: StructuralPath
    port_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.owner_scope, StructuralPath):
            raise PortError(
                f"owner_scope must be StructuralPath, "
                f"got {type(self.owner_scope).__name__}"
            )
        if self.owner_scope.is_workspace_root:
            raise PortError(
                f"port {self.port_id!r} must belong to a Scope, not the "
                f"Workspace root {self.owner_scope.as_string()!r}"
            )
        _require_nonempty(self.port_id, "port_id")
        if "#" in self.port_id:
            raise PortError("port_id must not contain '#'")

    def as_string(self) -> str:
        """Deterministic canonical boundary-endpoint string."""
        return f"{self.owner_scope.as_string()}#{self.port_id}"

    def __str__(self) -> str:
        return self.as_string()


@dataclass(frozen=True, slots=True)
class BoundaryPort:
    """A typed directional exchange endpoint owned by one structural scope."""

    ref: PortRef
    direction: PortDirection
    category: PortCategory
    unit: str | None = None
    descriptor: str | None = None  # optional plain type/schema tag (NOT PIM)

    def __post_init__(self) -> None:
        if not isinstance(self.ref, PortRef):
            raise PortError(f"ref must be PortRef, got {type(self.ref).__name__}")
        if not isinstance(self.direction, PortDirection):
            raise PortError(
                f"direction must be PortDirection, "
                f"got {type(self.direction).__name__}"
            )
        if not isinstance(self.category, PortCategory):
            raise PortError(
                f"category must be PortCategory, "
                f"got {type(self.category).__name__}"
            )
        for name in ("unit", "descriptor"):
            value = getattr(self, name)
            if value is not None:
                _require_nonempty(value, name)


class PortRegistry:
    """Immutable registry of declared boundary ports (fail-closed on duplicate
    port identity). Deterministic regardless of input iteration order."""

    def __init__(self, ports: Iterable[BoundaryPort] = ()) -> None:
        self._by_ref: dict[str, BoundaryPort] = {}
        for port in ports:
            if not isinstance(port, BoundaryPort):
                raise PortError(
                    f"registry entries must be BoundaryPort, "
                    f"got {type(port).__name__}"
                )
            key = port.ref.as_string()
            if key in self._by_ref:
                raise PortError(
                    f"duplicate port identity {key!r} within the registry"
                )
            self._by_ref[key] = port

    def get(self, ref: PortRef) -> BoundaryPort | None:
        return self._by_ref.get(ref.as_string())

    def require(self, ref: PortRef) -> BoundaryPort:
        port = self.get(ref)
        if port is None:
            raise PortError(
                f"unknown boundary port {ref.as_string()!r}"
            )
        return port

    @property
    def ports(self) -> tuple[BoundaryPort, ...]:
        return tuple(sorted(self._by_ref.values(), key=lambda p: p.ref.as_string()))

    def __len__(self) -> int:
        return len(self._by_ref)


def check_port_compatibility(source: BoundaryPort, target: BoundaryPort) -> None:
    """Fail-closed compatibility rules for one declared source -> target edge.

    - source direction must be ``out``; target direction must be ``in``;
    - categories must match;
    - when both endpoints declare a unit it must match (absent unit is allowed,
      never fabricated);
    - when both endpoints declare a descriptor it must match.
    """
    if source.direction is not PortDirection.OUT:
        raise PortError(
            f"source port {source.ref.as_string()!r} must be direction 'out', "
            f"got {source.direction.value!r}"
        )
    if target.direction is not PortDirection.IN:
        raise PortError(
            f"target port {target.ref.as_string()!r} must be direction 'in', "
            f"got {target.direction.value!r}"
        )
    if source.category is not target.category:
        raise PortError(
            f"port category mismatch: {source.ref.as_string()!r} is "
            f"{source.category.value!r}, {target.ref.as_string()!r} is "
            f"{target.category.value!r}"
        )
    if (
        source.unit is not None
        and target.unit is not None
        and source.unit != target.unit
    ):
        raise PortError(
            f"port unit mismatch: {source.ref.as_string()!r} unit "
            f"{source.unit!r} vs {target.ref.as_string()!r} unit {target.unit!r}"
        )
    if (
        source.descriptor is not None
        and target.descriptor is not None
        and source.descriptor != target.descriptor
    ):
        raise PortError(
            f"port descriptor mismatch: {source.ref.as_string()!r} "
            f"{source.descriptor!r} vs {target.ref.as_string()!r} "
            f"{target.descriptor!r}"
        )
