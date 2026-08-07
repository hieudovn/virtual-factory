"""Assembly topology — explicit connectivity between primitives.

M3-S02: Deterministic adjacency map. No routing DSL, no expression language.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from virtual_factory.assembly.primitives import AssemblyPrimitive
from virtual_factory.assembly.quality import QualityDisposition


class TopologyError(ValueError):
    """Raised when a topology invariant is violated."""


@dataclass
class AssemblyTopology:
    """Explicit directed connectivity between assembly primitives.

    Edges map (from_primitive_id, disposition_or_NONE) → to_primitive_id.
    A disposition of ``None`` represents the default/only edge from a primitive
    that has no branching (e.g. Source, Buffer, Processor, Sink).
    """

    primitives: dict[str, AssemblyPrimitive] = field(default_factory=dict)
    edges: dict[tuple[str, str | None], str] = field(default_factory=dict)

    def add_primitive(self, p: AssemblyPrimitive) -> None:
        if p.primitive_id in self.primitives:
            raise TopologyError(f"Duplicate primitive: {p.primitive_id}")
        self.primitives[p.primitive_id] = p

    def add_edge(
        self,
        from_id: str,
        to_id: str,
        disposition: str | None = None,
    ) -> None:
        """Add a directed edge.  ``disposition`` is None for unconditional edges,
        or a QualityDisposition value for branching edges (e.g. from QualityGate).
        """
        if from_id not in self.primitives:
            raise TopologyError(f"Unknown from primitive: {from_id}")
        if to_id not in self.primitives:
            raise TopologyError(f"Unknown to primitive: {to_id}")
        key = (from_id, disposition)
        if key in self.edges:
            raise TopologyError(f"Duplicate edge: {from_id} -> {to_id} ({disposition})")
        self.edges[key] = to_id

    def next_primitive(
        self, from_id: str, disposition: str | None = None
    ) -> str | None:
        """Return the next primitive ID, or None if no edge exists."""
        return self.edges.get((from_id, disposition))

    def get_primitive(self, primitive_id: str) -> AssemblyPrimitive | None:
        return self.primitives.get(primitive_id)
