"""Generic VF_SCENARIO_ASSUMED_TOPOLOGY overlay (VF-vNEXT-G18).

A dependency-light, immutable, deterministic, INERT set of scenario/design-stage
topology assumptions that VF may carry WITHOUT modifying or impersonating the
authoritative reference topology (G12A :class:`ReferenceConnectivityGraph`,
backed by PIM).

Frozen architecture position:

    PIM  -> ReferenceConnectivityGraph (authoritative, evidence-gated)
    VF scenario/design -> ScenarioTopologyOverlay (assumed, synthetic, reversible)
    both -> explicit later projection/mapping -> Boundary Contracts/Ports
        -> G4 CompositionGraph -> Coordinator/Runtime

This module implements ONLY the overlay layer. It is intentionally separate
from, and must not be coupled to, G1 containment, G4 composition, run-control,
or any plant-specific vocabulary.

Frozen semantics:

- Every assumed edge carries an EXPLICIT identity (``assumption_id``) and
  ``version``.
- ``source_kind`` is frozen to ``vf_scenario_assumption``; it can never be PIM,
  site, or source-mapped provenance.
- ``status`` is frozen to ``assumed/synthetic``; an edge can never be marked
  DocumentConfirmed / SourceMapped / site-verified / calibrated.
- Every assumption is reversible and replaceable via immutable
  ``remove`` / ``replace`` operations (the original overlay is never mutated).
- No back-propagation into PIM/KG: this module never writes authoritative data.
- Authoritative graph and overlay remain distinguishable by distinct schema and
  provenance fields.
- Fail closed on malformed/ambiguous overlay: empty identity, duplicate
  ``assumption_id``, and duplicate exact logical assumption
  ``(source, target, relation_type)``.
- Deterministic enumeration/serialization independent of input declaration order.
- The overlay is an UNORDERED SET of edges: enumeration order is identity-only
  and NEVER implies execution order.
- No coupling-policy semantics: coupling policy remains G14B orchestration
  policy and is not represented here.
- No runtime/site authorization is implied or broadened.
"""

from __future__ import annotations

from dataclasses import dataclass, field

ASSUMED_TOPOLOGY_SCHEMA = "vf.vnext.g18.scenario_assumed_topology_overlay.v1"
ASSUMED_SOURCE_KIND = "vf_scenario_assumption"
ASSUMED_STATUS = "assumed/synthetic"
OVERLAY_RUNTIME_AUTHORIZATION = "NOT_AUTHORIZED"
OVERLAY_SITE_AUTHORIZED_EXECUTION = "NOT_AUTHORIZED"


class ScenarioTopologyOverlayError(ValueError):
    """Raised when a scenario-topology-overlay invariant is violated."""


def _require_nonempty(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ScenarioTopologyOverlayError(f"{name} must be a non-empty str")


@dataclass(frozen=True, slots=True)
class AssumedTopologyEdge:
    """One immutable, reversible, provenance-bearing topology assumption.

    ``source`` and ``target`` are VF-LOCAL topology identities (e.g. G1
    ``StructuralPath`` strings such as ``shwtp/line1/l1_t108``). They are never
    PIM canonical ids and never renamed into PIM identity here.

    ``relation_type`` is a free-form descriptive label (e.g.
    ``ASSUMED_FLOWS_TO``). It is NOT a PIM relation id and NOT a runtime
    classification.
    """

    assumption_id: str
    version: str
    source: str
    target: str
    relation_type: str
    rationale: str
    source_kind: str = ASSUMED_SOURCE_KIND
    status: str = ASSUMED_STATUS
    replaces_assumption_id: str | None = None
    reversible: bool = True

    def __post_init__(self) -> None:
        _require_nonempty(self.assumption_id, "assumption_id")
        _require_nonempty(self.version, "version")
        _require_nonempty(self.source, "source")
        _require_nonempty(self.target, "target")
        _require_nonempty(self.relation_type, "relation_type")
        _require_nonempty(self.rationale, "rationale")
        if self.source_kind != ASSUMED_SOURCE_KIND:
            raise ScenarioTopologyOverlayError(
                f"source_kind must be {ASSUMED_SOURCE_KIND!r}; got "
                f"{self.source_kind!r}. Assumed topology can never impersonate "
                f"PIM/site/source-mapped provenance."
            )
        if self.status != ASSUMED_STATUS:
            raise ScenarioTopologyOverlayError(
                f"status must be {ASSUMED_STATUS!r}; got {self.status!r}. "
                f"Assumed topology can never be marked DocumentConfirmed / "
                f"SourceMapped / site-verified."
            )
        if self.replaces_assumption_id is not None:
            _require_nonempty(self.replaces_assumption_id, "replaces_assumption_id")
        if self.reversible is not True:
            raise ScenarioTopologyOverlayError(
                "an assumed topology edge must be reversible (reversible=True)"
            )

    @property
    def logical_key(self) -> tuple[str, str, str]:
        """Frozen duplicate-logical-assumption identity rule.

        Two assumptions are the same exact logical assumption when they share
        (source, target, relation_type), independent of assumption_id/version.
        """
        return (self.source, self.target, self.relation_type)

    @property
    def sort_key(self) -> tuple[str, str, str, str]:
        """Deterministic canonical sort key independent of declaration order."""
        return (self.source, self.target, self.relation_type, self.assumption_id)

    def to_dict(self) -> dict:
        return {
            "assumption_id": self.assumption_id,
            "version": self.version,
            "source": self.source,
            "target": self.target,
            "relation_type": self.relation_type,
            "rationale": self.rationale,
            "source_kind": self.source_kind,
            "status": self.status,
            "replaces_assumption_id": self.replaces_assumption_id,
            "reversible": self.reversible,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AssumedTopologyEdge":
        if not isinstance(data, dict):
            raise ScenarioTopologyOverlayError("assumed edge must be a dict")
        # Provenance and reversibility fields are REQUIRED on reconstruction:
        # omitting them must fail closed (never silently default to assumed).
        for required in ("source_kind", "status", "reversible"):
            if required not in data:
                raise ScenarioTopologyOverlayError(
                    f"assumed edge missing required field {required!r}"
                )
        return cls(
            assumption_id=data.get("assumption_id", ""),
            version=data.get("version", ""),
            source=data.get("source", ""),
            target=data.get("target", ""),
            relation_type=data.get("relation_type", ""),
            rationale=data.get("rationale", ""),
            source_kind=data["source_kind"],
            status=data["status"],
            replaces_assumption_id=data.get("replaces_assumption_id"),
            reversible=data["reversible"],
        )


@dataclass(frozen=True, slots=True)
class ScenarioTopologyOverlay:
    """Immutable, deterministic, inert set of topology assumptions.

    Built fail-closed from any iteration order of edges. Edges are enumerated in
    a deterministic identity order that NEVER represents execution order.
    """

    overlay_id: str
    version: str
    domain: str
    edges: tuple[AssumedTopologyEdge, ...] = field(default=())

    def __post_init__(self) -> None:
        _require_nonempty(self.overlay_id, "overlay_id")
        _require_nonempty(self.version, "version")
        _require_nonempty(self.domain, "domain")

        ordered: list[AssumedTopologyEdge] = []
        by_id: dict[str, AssumedTopologyEdge] = {}
        logical: dict[tuple[str, str, str], AssumedTopologyEdge] = {}
        for edge in self.edges:
            if not isinstance(edge, AssumedTopologyEdge):
                raise ScenarioTopologyOverlayError(
                    f"edges must be AssumedTopologyEdge, got {type(edge).__name__}"
                )
            if edge.assumption_id in by_id:
                raise ScenarioTopologyOverlayError(
                    f"duplicate assumption id {edge.assumption_id!r}"
                )
            if edge.logical_key in logical:
                raise ScenarioTopologyOverlayError(
                    f"ambiguous overlay: duplicate exact logical assumption "
                    f"{edge.source!r} --{edge.relation_type}--> {edge.target!r}"
                )
            by_id[edge.assumption_id] = edge
            logical[edge.logical_key] = edge
            ordered.append(edge)
        ordered.sort(key=lambda e: e.sort_key)
        object.__setattr__(self, "edges", tuple(ordered))

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    @property
    def assumption_ids(self) -> tuple[str, ...]:
        """Assumption ids in deterministic order."""
        return tuple(e.assumption_id for e in self.edges)

    def edge_by_id(self, assumption_id: str) -> AssumedTopologyEdge:
        for edge in self.edges:
            if edge.assumption_id == assumption_id:
                return edge
        raise ScenarioTopologyOverlayError(
            f"unknown assumption id {assumption_id!r}"
        )

    def remove(self, assumption_id: str) -> "ScenarioTopologyOverlay":
        """Return a NEW overlay without ``assumption_id`` (reversible).

        The original overlay is immutable and never mutated.
        """
        remaining = tuple(
            e for e in self.edges if e.assumption_id != assumption_id
        )
        if len(remaining) == len(self.edges):
            raise ScenarioTopologyOverlayError(
                f"cannot remove unknown assumption id {assumption_id!r}"
            )
        return ScenarioTopologyOverlay(
            overlay_id=self.overlay_id,
            version=self.version,
            domain=self.domain,
            edges=remaining,
        )

    def replace(self, new_edge: AssumedTopologyEdge) -> "ScenarioTopologyOverlay":
        """Return a NEW overlay with ``new_edge`` replacing the assumption it
        declares it replaces (via ``replaces_assumption_id``) or, if that is
        absent, its exact logical assumption. Reversible and non-mutating.
        """
        if not isinstance(new_edge, AssumedTopologyEdge):
            raise ScenarioTopologyOverlayError(
                f"new_edge must be AssumedTopologyEdge, got {type(new_edge).__name__}"
            )
        replaced_id = new_edge.replaces_assumption_id
        remaining: list[AssumedTopologyEdge] = []
        if replaced_id is not None:
            found = False
            for edge in self.edges:
                if edge.assumption_id == replaced_id:
                    found = True
                    continue
                remaining.append(edge)
            if not found:
                raise ScenarioTopologyOverlayError(
                    f"replaces_assumption_id {replaced_id!r} not found in overlay"
                )
        else:
            for edge in self.edges:
                if edge.logical_key == new_edge.logical_key:
                    continue
                remaining.append(edge)
        return ScenarioTopologyOverlay(
            overlay_id=self.overlay_id,
            version=self.version,
            domain=self.domain,
            edges=tuple(remaining) + (new_edge,),
        )

    def authorization(self) -> dict:
        """Frozen no-runtime/site-authorization marker (never broadened)."""
        return {
            "runtime": OVERLAY_RUNTIME_AUTHORIZATION,
            "site_execution": OVERLAY_SITE_AUTHORIZED_EXECUTION,
        }

    def serialize(self) -> dict:
        """Deterministic machine-readable inspection of the overlay."""
        return {
            "schema": ASSUMED_TOPOLOGY_SCHEMA,
            "overlay_id": self.overlay_id,
            "version": self.version,
            "domain": self.domain,
            "edge_count": self.edge_count,
            "authorization": self.authorization(),
            "edges": [e.to_dict() for e in self.edges],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScenarioTopologyOverlay":
        if not isinstance(data, dict):
            raise ScenarioTopologyOverlayError("overlay must be a dict")
        if data.get("schema") != ASSUMED_TOPOLOGY_SCHEMA:
            raise ScenarioTopologyOverlayError(
                f"overlay schema must be {ASSUMED_TOPOLOGY_SCHEMA!r}; got "
                f"{data.get('schema')!r}"
            )
        edges = [
            AssumedTopologyEdge.from_dict(e) for e in data.get("edges", [])
        ]
        return cls(
            overlay_id=data.get("overlay_id", ""),
            version=data.get("version", ""),
            domain=data.get("domain", ""),
            edges=tuple(edges),
        )
