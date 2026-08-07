"""SimulationDefinition — declarative configuration for assembly simulation.

M4-S02: YAML-serializable definition with validation.
Primitives, edges, metadata. Load → validate → instantiate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from virtual_factory.assembly.primitives import (
    AssemblyPrimitive, Buffer, PrimitiveType, Processor,
    QualityGate, Router, Sink, Source,
)
from virtual_factory.assembly.topology import AssemblyTopology


# ═══════════════════════════════════════
# Definition data classes
# ═══════════════════════════════════════

@dataclass
class PrimitiveDef:
    id: str
    type: str
    label: str = ""
    capacity: int | None = None       # Buffer
    processing_time_s: float = 1.0     # Processor


@dataclass
class EdgeDef:
    from_id: str   # field name in YAML: "from"
    to: str
    disposition: str | None = None


@dataclass
class SimulationDefinition:
    model_id: str
    model_name: str = ""
    primitives: list[PrimitiveDef] = field(default_factory=list)
    edges: list[EdgeDef] = field(default_factory=list)


# ═══════════════════════════════════════
# Validation
# ═══════════════════════════════════════

class ValidationError(ValueError):
    """Raised when a SimulationDefinition fails validation."""


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def raise_if_invalid(self) -> None:
        if not self.valid:
            raise ValidationError("\n".join(self.errors))


def validate_definition(defn: SimulationDefinition) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if not defn.model_id or not defn.model_id.strip():
        errors.append("model_id is required")

    # Primitive IDs
    seen_ids: set[str] = set()
    for i, p in enumerate(defn.primitives):
        if not p.id or not p.id.strip():
            errors.append(f"primitives[{i}]: id is required")
            continue
        if p.id in seen_ids:
            errors.append(f"primitives[{i}]: duplicate id '{p.id}'")
        seen_ids.add(p.id)

        if p.type not in {t.value for t in PrimitiveType}:
            errors.append(f"primitives[{i}] '{p.id}': unknown type '{p.type}'")

        if p.type == "buffer":
            if p.capacity is None or p.capacity <= 0:
                errors.append(f"primitives[{i}] '{p.id}': buffer capacity must be > 0")
        if p.type == "processor":
            if p.processing_time_s < 0 or math.isnan(p.processing_time_s) or math.isinf(p.processing_time_s):
                errors.append(f"primitives[{i}] '{p.id}': invalid processing_time_s")

    # Edge validation
    for i, e in enumerate(defn.edges):
        if e.from_id not in seen_ids:
            errors.append(f"edges[{i}]: from '{e.from_id}' not found in primitives")
        if e.to not in seen_ids:
            errors.append(f"edges[{i}]: to '{e.to}' not found in primitives")
        if e.disposition and e.disposition not in ("pass", "fail", "rework", "scrap"):
            errors.append(f"edges[{i}]: invalid disposition '{e.disposition}'")

    # QualityGate must have at least a PASS route
    for p in defn.primitives:
        if p.type == "quality_gate":
            pass_edges = [e for e in defn.edges if e.from_id == p.id and e.disposition == "pass"]
            if not pass_edges:
                errors.append(f"quality_gate '{p.id}': missing PASS route")

    # Source must have outgoing edge
    for p in defn.primitives:
        if p.type == "source":
            out_edges = [e for e in defn.edges if e.from_id == p.id]
            if not out_edges:
                errors.append(f"source '{p.id}': no outgoing edge")

    # Reachability: every primitive must be reachable from at least one source
    reachable = _compute_reachable(defn)
    for p in defn.primitives:
        if p.id not in reachable:
            warnings.append(f"primitive '{p.id}': unreachable from any source")
        # Non-sink without outgoing edge = dead end
        if p.type not in ("sink",) and not any(e.from_id == p.id for e in defn.edges):
            errors.append(f"primitive '{p.id}': non-terminal dead end (no outgoing edge)")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


# ═══════════════════════════════════════
# Topology builder
# ═══════════════════════════════════════

def build_topology_from_definition(defn: SimulationDefinition) -> AssemblyTopology:
    """Instantiate an AssemblyTopology from a validated definition."""
    result = validate_definition(defn)
    result.raise_if_invalid()

    topo = AssemblyTopology()
    for pdef in defn.primitives:
        prim = _instantiate_primitive(pdef)
        topo.add_primitive(prim)

    for edef in defn.edges:
        topo.add_edge(edef.from_id, edef.to, edef.disposition)

    return topo


def _compute_reachable(defn: SimulationDefinition) -> set[str]:
    """BFS from all sources to find reachable primitives."""
    adjacency: dict[str, list[str]] = {p.id: [] for p in defn.primitives}
    for e in defn.edges:
        adjacency.setdefault(e.from_id, []).append(e.to)

    sources = [p.id for p in defn.primitives if p.type == "source"]
    reachable: set[str] = set(sources)
    queue = list(sources)
    while queue:
        current = queue.pop(0)
        for neighbor in adjacency.get(current, []):
            if neighbor not in reachable:
                reachable.add(neighbor)
                queue.append(neighbor)
    return reachable


def _instantiate_primitive(pdef: PrimitiveDef) -> AssemblyPrimitive:
    pt = PrimitiveType(pdef.type)
    if pt == PrimitiveType.SOURCE:
        return Source(primitive_id=pdef.id, label=pdef.label)
    elif pt == PrimitiveType.BUFFER:
        return Buffer(primitive_id=pdef.id, label=pdef.label,
                      capacity=pdef.capacity or 256)
    elif pt == PrimitiveType.PROCESSOR:
        return Processor(primitive_id=pdef.id, label=pdef.label,
                         processing_time_s=pdef.processing_time_s)
    elif pt == PrimitiveType.QUALITY_GATE:
        return QualityGate(primitive_id=pdef.id, label=pdef.label)
    elif pt == PrimitiveType.ROUTER:
        return Router(primitive_id=pdef.id, label=pdef.label)
    elif pt == PrimitiveType.SINK:
        return Sink(primitive_id=pdef.id, label=pdef.label)
    raise ValidationError(f"Unknown primitive type: {pdef.type}")
