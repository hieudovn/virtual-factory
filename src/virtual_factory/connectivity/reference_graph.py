"""Generic Reference Connectivity Graph foundation (G12A).

A dependency-light, immutable, deterministic representation of externally
sourced semantic/topology facts — the ``ReferenceConnectivityGraph`` layer of
the frozen architecture:

    PIM -> ReferenceConnectivityGraph -> explicit later projection/mapping
        -> VF Boundary Contracts/Ports -> G4 CompositionGraph -> Coordinator/Runtime

G12A implements ONLY the ReferenceConnectivityGraph layer. It is intentionally
separate from, and must not be coupled to:

- G1 containment (``virtual_factory.workspace``) — no containment parentage, no
  edge inferred from shared ancestry;
- G4 composition (``virtual_factory.composition``) — no ``BoundaryPort`` /
  ``PortDirection`` / ``PortCategory`` / ``PortRegistry`` / coordinator / runtime
  semantics, and G4 semantics are unchanged;
- any SH-WTP / plant-specific vocabulary — no hard-coded ids, relation names,
  relation-class enum, or evidence vocabulary.

Frozen semantics:

- Endpoints are generic immutable external semantic node references
  (authority + external/canonical entity id + optional entity kind). They do NOT
  require ``StructuralPath`` and never rename an external id into a VF local id.
- Edges are immutable, provenance-rich, inert reference facts with an explicit
  ``runtime_effect = "none"`` marker (enforced, not defaulted to anything else).
- The graph supports fan-out, fan-in, many-to-many, cycles, and endpoints that
  are not VF Scopes.
- Fail closed on: empty endpoint identity, empty relation type, duplicate edge
  id, and duplicate exact logical relation under the frozen deterministic
  identity rule ``(source, target, relation_type)``.
- Deterministic enumeration/serialization independent of input declaration
  order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

# Canonical string separator for endpoint identity. Neither authority nor
# entity_id may contain it (fail closed), mirroring the G4 PortRef '#' rule so
# the reversible endpoint string form is unambiguous and deterministic.
_ENDPOINT_SEPARATOR = "::"

# Frozen inert marker. In G12A every reference edge is inert; any other value
# is rejected at construction (a stronger type-level invariant than a default).
NO_RUNTIME_EFFECT = "none"

SCHEMA = "vf.vnext.g12a.reference_connectivity_graph.v1"


class ReferenceGraphError(ValueError):
    """Raised when a reference-connectivity invariant is violated."""


def _require_nonempty(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ReferenceGraphError(f"{name} must be a non-empty str")


def _require_no_separator(value: str, name: str) -> None:
    if _ENDPOINT_SEPARATOR in value:
        raise ReferenceGraphError(
            f"{name} must not contain {_ENDPOINT_SEPARATOR!r}"
        )


@dataclass(frozen=True, slots=True)
class ReferenceEndpoint:
    """Generic immutable external semantic node reference.

    ``authority`` is the source/authority identity (e.g. a repository or system
    that owns the entity). ``entity_id`` is the external/canonical entity id.
    ``entity_kind`` is optional descriptive metadata (e.g. ``Unit``, ``Signal``,
    ``ProcessConnection``) — never a VF runtime type and never used to infer
    semantics.
    """

    authority: str
    entity_id: str
    entity_kind: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty(self.authority, "authority")
        _require_nonempty(self.entity_id, "entity_id")
        _require_no_separator(self.authority, "authority")
        _require_no_separator(self.entity_id, "entity_id")
        if self.entity_kind is not None:
            _require_nonempty(self.entity_kind, "entity_kind")
            _require_no_separator(self.entity_kind, "entity_kind")

    @property
    def key(self) -> tuple[str, str]:
        """Deterministic identity tuple (authority, entity_id)."""
        return (self.authority, self.entity_id)

    def as_string(self) -> str:
        """Deterministic canonical string form ``authority::entity_id``."""
        return f"{self.authority}{_ENDPOINT_SEPARATOR}{self.entity_id}"

    def __str__(self) -> str:
        return self.as_string()


@dataclass(frozen=True, slots=True)
class ReferenceEdge:
    """One immutable, inert, provenance-rich reference relation fact.

    ``relation_type`` is a free-form, non-empty semantic relation type string.
    It is NOT restricted to a universal enum (no taxonomy is chosen here) and
    NOT classified by this layer.
    """

    edge_id: str
    source: ReferenceEndpoint
    target: ReferenceEndpoint
    relation_type: str
    evidence_ref: str
    confidence: str | None = None
    status: str | None = None
    gaps: tuple[str, ...] = ()
    runtime_effect: str = NO_RUNTIME_EFFECT

    def __post_init__(self) -> None:
        _require_nonempty(self.edge_id, "edge_id")
        if not isinstance(self.source, ReferenceEndpoint):
            raise ReferenceGraphError(
                f"edge source must be ReferenceEndpoint, "
                f"got {type(self.source).__name__}"
            )
        if not isinstance(self.target, ReferenceEndpoint):
            raise ReferenceGraphError(
                f"edge target must be ReferenceEndpoint, "
                f"got {type(self.target).__name__}"
            )
        _require_nonempty(self.relation_type, "relation_type")
        _require_nonempty(self.evidence_ref, "evidence_ref")
        for name in ("confidence", "status"):
            value = getattr(self, name)
            if value is not None:
                _require_nonempty(value, name)
        for gap in self.gaps:
            _require_nonempty(gap, "gap")
        if self.runtime_effect != NO_RUNTIME_EFFECT:
            raise ReferenceGraphError(
                f"G12A reference edges must be inert: runtime_effect must be "
                f"{NO_RUNTIME_EFFECT!r}, got {self.runtime_effect!r}"
            )

    @property
    def logical_key(self) -> tuple[tuple[str, str], tuple[str, str], str]:
        """Frozen duplicate-logical-relation identity rule.

        Two edges are the same exact logical relation when they share
        (source, target, relation_type), independent of edge id or evidence.
        """
        return (self.source.key, self.target.key, self.relation_type)

    @property
    def sort_key(self) -> tuple[str, str, str, str]:
        """Deterministic canonical sort key independent of declaration order."""
        return (
            self.source.as_string(),
            self.target.as_string(),
            self.relation_type,
            self.edge_id,
        )


class ReferenceConnectivityGraph:
    """Immutable, deterministic graph of inert reference relation facts.

    Built fail-closed from any iteration order of edges. Enumerates nodes and
    edges in a deterministic canonical order.
    """

    __slots__ = ("_edges",)

    def __init__(self, edges: Iterable[ReferenceEdge] = ()) -> None:
        by_edge_id: dict[str, ReferenceEdge] = {}
        logical: dict[tuple, ReferenceEdge] = {}
        for edge in edges:
            if not isinstance(edge, ReferenceEdge):
                raise ReferenceGraphError(
                    f"edges must be ReferenceEdge, got {type(edge).__name__}"
                )
            if edge.edge_id in by_edge_id:
                raise ReferenceGraphError(f"duplicate edge id {edge.edge_id!r}")
            if edge.logical_key in logical:
                raise ReferenceGraphError(
                    f"duplicate exact logical relation "
                    f"{edge.source.as_string()!r} --{edge.relation_type}--> "
                    f"{edge.target.as_string()!r}"
                )
            by_edge_id[edge.edge_id] = edge
            logical[edge.logical_key] = edge
        self._edges = tuple(sorted(by_edge_id.values(), key=lambda e: e.sort_key))

    @property
    def edges(self) -> tuple[ReferenceEdge, ...]:
        """Edges in deterministic canonical order (not declaration order)."""
        return self._edges

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    @property
    def runtime_effect(self) -> str:
        """Every G12A edge is inert; this is the graph-wide marker."""
        return NO_RUNTIME_EFFECT

    def nodes(self) -> tuple[ReferenceEndpoint, ...]:
        """All distinct endpoints, deterministic order."""
        seen: dict[tuple[str, str], ReferenceEndpoint] = {}
        for edge in self._edges:
            for endpoint in (edge.source, edge.target):
                seen.setdefault(endpoint.key, endpoint)
        return tuple(
            sorted(seen.values(), key=lambda e: e.as_string())
        )

    def outbound(self, endpoint: ReferenceEndpoint) -> tuple[ReferenceEdge, ...]:
        """Deterministic fan-out edges leaving ``endpoint``."""
        return tuple(e for e in self._edges if e.source == endpoint)

    def inbound(self, endpoint: ReferenceEndpoint) -> tuple[ReferenceEdge, ...]:
        """Deterministic fan-in edges entering ``endpoint``."""
        return tuple(e for e in self._edges if e.target == endpoint)

    def has_edge(
        self,
        source: ReferenceEndpoint,
        target: ReferenceEndpoint,
        relation_type: str,
    ) -> bool:
        return (source.key, target.key, relation_type) in {
            e.logical_key for e in self._edges
        }

    def _endpoint_dict(self, endpoint: ReferenceEndpoint) -> dict:
        return {
            "authority": endpoint.authority,
            "entity_id": endpoint.entity_id,
            "entity_kind": endpoint.entity_kind,
        }

    def serialize(self) -> dict:
        """Deterministic machine-readable inspection of the graph."""
        edges = [
            {
                "edge_id": e.edge_id,
                "source": self._endpoint_dict(e.source),
                "target": self._endpoint_dict(e.target),
                "relation_type": e.relation_type,
                "evidence_ref": e.evidence_ref,
                "confidence": e.confidence,
                "status": e.status,
                "gaps": tuple(sorted(e.gaps)),
                "runtime_effect": e.runtime_effect,
            }
            for e in self._edges
        ]
        return {
            "schema": SCHEMA,
            "edge_count": self.edge_count,
            "runtime_effect": self.runtime_effect,
            "endpoints": [self._endpoint_dict(n) for n in self.nodes()],
            "edges": edges,
        }
