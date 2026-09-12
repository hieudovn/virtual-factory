"""Generic cross-scope composition graph (G4).

A dependency-light directed graph over G1 structural identities that is SEPARATE
from the containment tree. Containment remains a tree; composition/connectivity
is this graph.

Frozen semantics:

- endpoints resolve through authoritative G1 ``StructuralPath``/port refs;
- directed declared bindings (edges) with stable edge identity;
- cycles are allowed — the graph is NOT required to be a DAG and acyclicity is
  never used as a correctness shortcut;
- deterministic enumeration independent of input declaration order;
- dangling endpoint refs and duplicate edge identity / duplicate logical binding
  fail closed;
- no cross-workspace binding in the G4 baseline (fail closed); no
  workspace/domain-name hard-coding.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from virtual_factory.composition.ports import (
    BoundaryPort,
    PortError,
    PortRef,
    PortRegistry,
)
from virtual_factory.workspace.identity import StructuralPath


class CompositionError(ValueError):
    """Raised when a composition-graph invariant is violated."""


@dataclass(frozen=True, slots=True)
class CompositionBinding:
    """One directed declared binding (edge) between two boundary endpoints."""

    edge_id: str
    source: PortRef
    target: PortRef

    def __post_init__(self) -> None:
        if not isinstance(self.edge_id, str) or not self.edge_id.strip():
            raise CompositionError("edge_id must be a non-empty str")
        if not isinstance(self.source, PortRef):
            raise CompositionError(
                f"binding source must be PortRef, got {type(self.source).__name__}"
            )
        if not isinstance(self.target, PortRef):
            raise CompositionError(
                f"binding target must be PortRef, got {type(self.target).__name__}"
            )

    @property
    def key(self) -> tuple[str, str, str]:
        """Deterministic sort key independent of declaration order."""
        return (self.source.as_string(), self.target.as_string(), self.edge_id)

    def as_tuple(self) -> tuple[str, str, str]:
        return (
            self.source.as_string(),
            self.target.as_string(),
            self.edge_id,
        )


class CompositionGraph:
    """Directed composition graph over declared boundary ports.

    Built fail-closed and deterministically from any iteration order of
    bindings and ports.
    """

    def __init__(
        self,
        workspace_id: str,
        bindings: Iterable[CompositionBinding] = (),
        ports: Iterable[BoundaryPort] = (),
    ) -> None:
        if not isinstance(workspace_id, str) or not workspace_id.strip():
            raise CompositionError("workspace_id must be a non-empty str")
        self._workspace_id = workspace_id
        self._registry = PortRegistry(ports)

        by_edge_id: dict[str, CompositionBinding] = {}
        by_logical: dict[tuple[str, str], CompositionBinding] = {}
        for binding in bindings:
            if not isinstance(binding, CompositionBinding):
                raise CompositionError(
                    f"bindings must be CompositionBinding, "
                    f"got {type(binding).__name__}"
                )
            self._check_endpoint(binding.source)
            self._check_endpoint(binding.target)
            if binding.edge_id in by_edge_id:
                raise CompositionError(
                    f"duplicate edge id {binding.edge_id!r}"
                )
            logical = (binding.source.as_string(), binding.target.as_string())
            if logical in by_logical:
                raise CompositionError(
                    f"duplicate logical binding {logical[0]!r} -> {logical[1]!r}"
                )
            by_edge_id[binding.edge_id] = binding
            by_logical[logical] = binding

        self._bindings = tuple(
            sorted(by_edge_id.values(), key=lambda b: b.key)
        )
        # Baseline input has at most one producer (declared, not just emitted):
        # a target input may not receive from >1 distinct source port.
        sources_by_target: dict[str, set[str]] = {}
        for binding in self._bindings:
            sources_by_target.setdefault(
                binding.target.as_string(), set()
            ).add(binding.source.as_string())
        for target, sources in sorted(sources_by_target.items()):
            if len(sources) > 1:
                raise CompositionError(
                    f"implicit multi-producer input at {target!r}: "
                    f"{sorted(sources)}"
                )

    def _check_endpoint(self, ref: PortRef) -> None:
        """Dangling and cross-workspace endpoint refs fail closed."""
        if ref.owner_scope.workspace_id != self._workspace_id:
            raise CompositionError(
                f"binding endpoint {ref.as_string()!r} is outside workspace "
                f"{self._workspace_id!r}; cross-workspace binding is not "
                f"supported in G4"
            )
        if self._registry.get(ref) is None:
            raise CompositionError(
                f"dangling endpoint {ref.as_string()!r}: no such declared "
                f"boundary port"
            )

    @property
    def workspace_id(self) -> str:
        return self._workspace_id

    @property
    def bindings(self) -> tuple[CompositionBinding, ...]:
        """Bindings in deterministic canonical order (not declaration order)."""
        return self._bindings

    @property
    def edges(self) -> tuple[CompositionBinding, ...]:
        return self._bindings

    @property
    def registry(self) -> PortRegistry:
        return self._registry

    def nodes(self) -> tuple[PortRef, ...]:
        """All endpoint nodes involved in bindings, deterministic order."""
        seen: set[str] = set()
        nodes: list[PortRef] = []
        for binding in self._bindings:
            for ref in (binding.source, binding.target):
                key = ref.as_string()
                if key not in seen:
                    seen.add(key)
                    nodes.append(ref)
        return tuple(sorted(nodes, key=lambda r: r.as_string()))

    def has_binding(self, source: PortRef, target: PortRef) -> bool:
        return (source.as_string(), target.as_string()) in {
            (b.source.as_string(), b.target.as_string()) for b in self._bindings
        }

    def outbound(self, source: PortRef) -> tuple[CompositionBinding, ...]:
        """Deterministic fan-out edges leaving ``source``."""
        return tuple(
            b for b in self._bindings if b.source == source
        )

    def inbound(self, target: PortRef) -> tuple[CompositionBinding, ...]:
        return tuple(
            b for b in self._bindings if b.target == target
        )
