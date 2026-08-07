"""Assembly snapshot projection — UI/transport-friendly detached read model.

M4-S01: Projects DiscreteRunService + AssemblyRuntimeState + AssemblyTopology
into a serializable, immutable projection without exposing mutable internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from virtual_factory.assembly.primitives import (
    AssemblyPrimitive, Buffer, PrimitiveType, Processor, QualityGate,
)
from virtual_factory.assembly.runtime import AssemblyRuntimeState
from virtual_factory.assembly.topology import AssemblyTopology
from virtual_factory.assembly.wip import WipId, WipState, WipStatus
from virtual_factory.discrete.run_service import DiscreteRunService
from virtual_factory.discrete.snapshot import RuntimeSnapshot
from virtual_factory.discrete.trace import EventTraceEntry


# ═══════════════════════════════════════════════════
# Projection data classes
# ═══════════════════════════════════════════════════

@dataclass
class RunInfo:
    status: str
    simulation_time_s: float
    pending_events: int
    processed_events: int
    run_id: str
    model_id: str


@dataclass
class PrimitiveView:
    primitive_id: str
    primitive_type: str
    label: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class EdgeView:
    from_id: str
    to_id: str
    disposition: str | None = None


@dataclass
class WipView:
    wip_id: str
    location: str
    status: str
    flow_id: str
    step_count: int
    is_terminal: bool


@dataclass
class BufferView:
    buffer_id: str
    capacity: int
    occupancy: int
    wip_ids: list[str] = field(default_factory=list)


@dataclass
class EventView:
    event_id: str
    event_type: str
    target_id: str
    simulation_time_s: float
    wip_id: str | None
    state_changes: tuple[str, ...]
    result: str
    error_code: str | None


@dataclass
class IssueMarker:
    marker_type: str    # "fault", "quality_failure", "blocked", "rework", "line_in", "line_out"
    target_id: str
    simulation_time_s: float
    label: str
    severity: str = "info"
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class AssemblyProjection:
    """Detached, serializable projection of assembly simulation state."""

    run: RunInfo
    primitives: list[PrimitiveView]
    edges: list[EdgeView]
    wips: list[WipView]
    buffers: list[BufferView]
    recent_events: list[EventView]
    issues: list[IssueMarker] = field(default_factory=list)


# ═══════════════════════════════════════════════════
# Projection builder
# ═══════════════════════════════════════════════════

def project_assembly(
    service: DiscreteRunService,
    runtime_state: AssemblyRuntimeState,
    topology: AssemblyTopology,
) -> AssemblyProjection:
    """Build a detached projection from live runtime components.

    The returned projection is fully detached — mutations to the
    projection have no effect on the runtime.
    """
    snap = service.snapshot
    if snap is None:
        raise ValueError("No run available — call create_run first")

    # --- Run ---
    run = RunInfo(
        status=snap.status,
        simulation_time_s=snap.simulation_time_s,
        pending_events=snap.pending_events,
        processed_events=snap.processed_events,
        run_id=snap.run_id,
        model_id=snap.model_id,
    )

    # --- Primitives ---
    primitives = [
        _project_primitive(p)
        for p in topology.primitives.values()
    ]

    # --- Edges ---
    edges = [
        EdgeView(from_id=k[0], to_id=v, disposition=k[1])
        for k, v in topology.edges.items()
    ]

    # --- WIPs ---
    wips = [
        _project_wip(ws)
        for ws in runtime_state.all_wips()
    ]

    # --- Buffers ---
    buffers = [
        BufferView(
            buffer_id=pid,
            capacity=_get_buffer_capacity(topology, pid),
            occupancy=runtime_state.buffer_size(pid),
            wip_ids=[],  # WIP IDs in buffer not directly exposed in current runtime
        )
        for pid in _collect_buffer_ids(topology)
    ]

    # --- Recent events ---
    recent_events = [
        _project_event(e)
        for e in snap.recent_events
    ]

    # --- Issues ---
    issues = _collect_issues(snap.recent_events)

    return AssemblyProjection(
        run=run,
        primitives=primitives,
        edges=edges,
        wips=wips,
        buffers=buffers,
        recent_events=recent_events,
        issues=issues,
    )


# ═══════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════

def _project_primitive(p: AssemblyPrimitive) -> PrimitiveView:
    props: dict[str, Any] = {}
    if isinstance(p, Processor):
        props["processing_time_s"] = p.processing_time_s
    elif isinstance(p, Buffer):
        props["capacity"] = p.capacity
    return PrimitiveView(
        primitive_id=p.primitive_id,
        primitive_type=p.primitive_type.value,
        label=p.label,
        properties=props,
    )


def _project_wip(ws: WipState) -> WipView:
    return WipView(
        wip_id=str(ws.wip_id),
        location=ws.location,
        status=ws.status.value,
        flow_id="base",  # current runtime doesn't expose flow_id on WipState
        step_count=ws.step_count,
        is_terminal=ws.status in (WipStatus.COMPLETED, WipStatus.SCRAPPED),
    )


def _project_event(e: EventTraceEntry) -> EventView:
    wip_id = None
    if e.correlation_id:
        wip_id = e.correlation_id
    return EventView(
        event_id=e.event_id,
        event_type=e.event_type,
        target_id=e.target_id,
        simulation_time_s=e.simulation_time_s,
        wip_id=wip_id,
        state_changes=e.state_changes,
        result=e.result,
        error_code=e.error_code,
    )


def _collect_issues(events: tuple[EventTraceEntry, ...]) -> list[IssueMarker]:
    issues: list[IssueMarker] = []
    for e in events:
        if e.result == "failed":
            issues.append(IssueMarker(
                marker_type="fault",
                target_id=e.target_id,
                simulation_time_s=e.simulation_time_s,
                label=f"{e.event_type} failed: {e.error_code or 'unknown'}",
                severity="error",
            ))
        for sc in e.state_changes:
            if "rework" in sc.lower():
                issues.append(IssueMarker(
                    marker_type="rework",
                    target_id=e.target_id,
                    simulation_time_s=e.simulation_time_s,
                    label=sc,
                    severity="warning",
                ))
            if "buffer_full" in sc.lower():
                issues.append(IssueMarker(
                    marker_type="blocked",
                    target_id=e.target_id,
                    simulation_time_s=e.simulation_time_s,
                    label=sc,
                    severity="error",
                ))
    return issues


def _collect_buffer_ids(topology: AssemblyTopology) -> list[str]:
    return [
        pid for pid, p in topology.primitives.items()
        if p.primitive_type == PrimitiveType.BUFFER
    ]


def _get_buffer_capacity(topology: AssemblyTopology, buffer_id: str) -> int:
    p = topology.get_primitive(buffer_id)
    if isinstance(p, Buffer):
        return p.capacity
    return 0
