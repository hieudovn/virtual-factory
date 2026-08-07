"""Visualization foundation — scene model, layout, scene builder.

M4-S03: Framework-independent 2D scene representation.
Nodes, edges, WIP tokens, event markers, overlays.
Separate layout from topology.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from virtual_factory.assembly.projection import (
    AssemblyProjection,
)


# ═══════════════════════════════════════
# Layout definition
# ═══════════════════════════════════════

@dataclass
class NodeLayout:
    node_id: str
    x: float
    y: float
    width: float = 120
    height: float = 60


@dataclass
class EdgeRoute:
    edge_id: str
    path: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class LayoutDefinition:
    canvas_width: float = 1200
    canvas_height: float = 800
    nodes: list[NodeLayout] = field(default_factory=list)
    edges: list[EdgeRoute] = field(default_factory=list)

    def get_node(self, node_id: str) -> NodeLayout | None:
        for n in self.nodes:
            if n.node_id == node_id:
                return n
        return None


# ═══════════════════════════════════════
# Scene model
# ═══════════════════════════════════════

@dataclass
class NodeView:
    node_id: str
    primitive_id: str
    node_type: str
    label: str
    x: float
    y: float
    width: float
    height: float
    status: str = "idle"  # idle, active, waiting, blocked, error, completed


@dataclass
class EdgeView:
    edge_id: str
    from_node: str
    to_node: str
    disposition: str | None = None
    highlight: bool = False
    path: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class WipTokenView:
    wip_id: str
    current_node: str | None
    status: str
    flow_id: str = "base"
    display_type: str = "generic"  # material, semi-finished, finished, generic


@dataclass
class EventMarkerView:
    event_type: str
    target_node: str | None
    simulation_time_s: float
    severity: str = "info"  # info, warning, error
    label: str = ""
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulationScene:
    """Detached 2D scene representation of simulation state."""

    canvas_width: float
    canvas_height: float
    nodes: list[NodeView]
    edges: list[EdgeView]
    wips: list[WipTokenView]
    markers: list[EventMarkerView]
    run_status: str
    simulation_time_s: float


# ═══════════════════════════════════════
# Scene builder
# ═══════════════════════════════════════

def build_scene(
    projection: AssemblyProjection,
    layout: LayoutDefinition,
) -> SimulationScene:
    """Build a SimulationScene from projection + layout.

    Uses projection.edges (not AssemblyTopology) for the edge list.
    """

    nodes = _build_nodes(projection, layout)
    edges = _build_edges(projection, layout)
    wips = _build_wips(projection, layout)
    markers = _build_markers(projection)

    return SimulationScene(
        canvas_width=layout.canvas_width,
        canvas_height=layout.canvas_height,
        nodes=nodes,
        edges=edges,
        wips=wips,
        markers=markers,
        run_status=projection.run.status,
        simulation_time_s=projection.run.simulation_time_s,
    )


def _build_nodes(proj: AssemblyProjection, layout: LayoutDefinition) -> list[NodeView]:
    nodes: list[NodeView] = []
    for pv in proj.primitives:
        nl = layout.get_node(pv.primitive_id)
        if nl is None:
            continue
        # Determine runtime status
        status = "idle"
        for w in proj.wips:
            if w.location == pv.primitive_id:
                if w.status in ("processing", "inspecting"):
                    status = "active"
                elif w.status == "queued":
                    status = "waiting"
                elif w.is_terminal:
                    status = "completed"
                break
        nodes.append(NodeView(
            node_id=nl.node_id,
            primitive_id=pv.primitive_id,
            node_type=pv.primitive_type,
            label=pv.label or pv.primitive_id,
            x=nl.x, y=nl.y, width=nl.width, height=nl.height,
            status=status,
        ))
    return nodes


def _build_edges(proj: AssemblyProjection,
                 layout: LayoutDefinition) -> list[EdgeView]:
    edges: list[EdgeView] = []
    active_wip_locations = {w.location for w in proj.wips}
    for ev in proj.edges:
        edge_id = f"{ev.from_id}->{ev.to_id}"
        if ev.disposition:
            edge_id += f":{ev.disposition}"
        highlight = ev.from_id in active_wip_locations
        route = layout.edges
        path: list[tuple[float, float]] = []
        for er in route:
            if er.edge_id == edge_id:
                path = er.path
                break
        edges.append(EdgeView(
            edge_id=edge_id,
            from_node=ev.from_id,
            to_node=ev.to_id,
            disposition=ev.disposition,
            highlight=highlight,
            path=path,
        ))
    return edges


def _build_wips(proj: AssemblyProjection, layout: LayoutDefinition) -> list[WipTokenView]:
    wips: list[WipTokenView] = []
    for w in proj.wips:
        display_type = "generic"
        if w.is_terminal:
            display_type = "finished"
        elif w.step_count > 0:
            display_type = "semi-finished"
        elif w.status == "created":
            display_type = "material"
        wips.append(WipTokenView(
            wip_id=w.wip_id,
            current_node=w.location if w.location else None,
            status=w.status,
            flow_id=w.flow_id,
            display_type=display_type,
        ))
    return wips


def _build_markers(proj: AssemblyProjection) -> list[EventMarkerView]:
    markers: list[EventMarkerView] = []
    for ev in proj.recent_events[-10:]:  # last 10 events
        severity = "info"
        if ev.result == "failed":
            severity = "error"
        elif ev.error_code:
            severity = "warning"
        markers.append(EventMarkerView(
            event_type=ev.event_type,
            target_node=ev.target_id,
            simulation_time_s=ev.simulation_time_s,
            severity=severity,
            label=f"{ev.event_type} @ {ev.target_id}",
        ))
    for iss in proj.issues:
        markers.append(EventMarkerView(
            event_type=iss.marker_type,
            target_node=iss.target_id,
            simulation_time_s=iss.simulation_time_s,
            severity=iss.severity,
            label=iss.label,
        ))
    return markers
