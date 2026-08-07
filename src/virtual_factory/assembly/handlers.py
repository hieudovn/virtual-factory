"""Assembly domain handlers for the vertical flow.

M3-S02: Source, Buffer, Processor, QualityGate, Sink handlers.
Use real M2 HandlerOutcome, ScheduledEvent, state_changes, follow_up_events.
"""

from __future__ import annotations

from virtual_factory.assembly.primitives import (
    Buffer,
    Processor,
    QualityGate,
)
from virtual_factory.assembly.quality import QualityDisposition
from virtual_factory.assembly.runtime import AssemblyRuntimeState
from virtual_factory.assembly.topology import AssemblyTopology
from virtual_factory.assembly.wip import WipId, WipState, WipStatus
from virtual_factory.discrete.dispatcher import HandlerOutcome
from virtual_factory.discrete.events import ScheduledEvent


def _evt(event_id: str, simulation_time_s: float = 0.0, event_type: str = "",
        target_id: str = "", causation_id: str | None = None) -> ScheduledEvent:
    return ScheduledEvent(
        event_id=event_id, simulation_time_s=simulation_time_s, event_type=event_type,
        target_id=target_id, causation_id=causation_id,
    )


# ═══════════════════════════════════════════════════
# Source handler  — WIP_CREATED
# ═══════════════════════════════════════════════════

def make_source_handler(
    state: AssemblyRuntimeState,
    topology: AssemblyTopology,
    wip_counter: list[int] | None = None,
):
    """Handler for Source primitive.  Creates WIP and routes to next primitive."""

    def handler(event: ScheduledEvent) -> HandlerOutcome:
        source_id = event.target_id or "unknown-source"
        next_id = topology.next_primitive(source_id)
        if next_id is None:
            return HandlerOutcome(
                event_id=event.event_id, success=False,
                error_code="no_route",
                state_changes=(),
                follow_up_events=(),
            )

        seq = (wip_counter[0] + 1) if wip_counter else 1
        if wip_counter:
            wip_counter[0] = seq
        wip_id = WipId(f"wip-{seq:04d}")

        ws = WipState(wip_id=wip_id, location=source_id, status=WipStatus.CREATED)
        state.add_wip(ws)
        ws.advance(next_id, WipStatus.QUEUED)

        return HandlerOutcome(
            event_id=event.event_id, success=True,
            state_changes=(f"{wip_id}:created→queued@{next_id}",),
            follow_up_events=(
                _evt(f"{wip_id}-arrive", simulation_time_s=event.simulation_time_s,
                     event_type="WIP_QUEUED", target_id=next_id, causation_id=event.event_id),
            ),
        )

    return handler


# ═══════════════════════════════════════════════════
# Buffer handler  — WIP_QUEUED
# ═══════════════════════════════════════════════════

def make_buffer_handler(
    state: AssemblyRuntimeState,
    topology: AssemblyTopology,
):
    """Handler for Buffer primitive.  Records occupancy, routes to next primitive."""

    def handler(event: ScheduledEvent) -> HandlerOutcome:
        buffer_id = event.target_id or "unknown-buffer"
        wip_id_str = event.event_id.replace("-arrive", "")
        wip_id = WipId(wip_id_str)
        ws = state.get_wip(wip_id)
        if ws is None:
            return HandlerOutcome(
                event_id=event.event_id, success=False,
                error_code="unknown_wip", state_changes=(), follow_up_events=())

        next_id = topology.next_primitive(buffer_id)
        if next_id is None:
            return HandlerOutcome(
                event_id=event.event_id, success=False,
                error_code="no_route", state_changes=(), follow_up_events=())

        ws.advance(buffer_id, WipStatus.QUEUED)
        ws.advance(next_id, WipStatus.PROCESSING)

        return HandlerOutcome(
            event_id=event.event_id, success=True,
            state_changes=(f"{wip_id}:queued→processing@{next_id}",),
            follow_up_events=(
                _evt(f"{wip_id}-process-start", simulation_time_s=event.simulation_time_s,
                     event_type="PROCESS_START", target_id=next_id,
                     causation_id=event.event_id),
            ),
        )

    return handler


# ═══════════════════════════════════════════════════
# Processor handler  — PROCESS_START
# ═══════════════════════════════════════════════════

def make_processor_handler(
    state: AssemblyRuntimeState,
    topology: AssemblyTopology,
):
    """Handler for Processor primitive.  Schedules PROCESS_COMPLETE after delay."""

    def handler(event: ScheduledEvent) -> HandlerOutcome:
        proc_id = event.target_id or "unknown-processor"
        proc_prim = topology.get_primitive(proc_id)
        if proc_prim is None or not isinstance(proc_prim, Processor):
            return HandlerOutcome(
                event_id=event.event_id, success=False,
                error_code="invalid_processor",
                state_changes=(),
                follow_up_events=(),
            )
        proc: Processor = proc_prim

        wip_id_str = event.event_id.replace("-process-start", "")
        wip_id = WipId(wip_id_str)
        ws = state.get_wip(wip_id)
        if ws is None:
            return HandlerOutcome(
                event_id=event.event_id, success=False,
                error_code="unknown_wip",
                state_changes=(),
                follow_up_events=(),
            )

        ws.advance(proc_id, WipStatus.PROCESSING)
        completion_time = event.simulation_time_s + proc.processing_time_s

        return HandlerOutcome(
            event_id=event.event_id, success=True,
            state_changes=(f"{wip_id}:processing@{proc_id}",),
            follow_up_events=(
                _evt(f"{wip_id}-process-complete",
                     simulation_time_s=completion_time,
                     event_type="PROCESS_COMPLETE", target_id=proc_id,
                     causation_id=event.event_id),
            ),
        )

    return handler


# ═══════════════════════════════════════════════════
# Process-complete handler  — PROCESS_COMPLETE
# ═══════════════════════════════════════════════════

def make_process_complete_handler(
    state: AssemblyRuntimeState,
    topology: AssemblyTopology,
):
    """Handler for PROCESS_COMPLETE — routes to next primitive (QualityGate)."""

    def handler(event: ScheduledEvent) -> HandlerOutcome:
        proc_id = event.target_id or "unknown-processor"
        next_id = topology.next_primitive(proc_id)
        if next_id is None:
            return HandlerOutcome(
                event_id=event.event_id, success=False,
                error_code="no_route",
                state_changes=(),
                follow_up_events=(),
            )

        wip_id_str = event.event_id.replace("-process-complete", "")
        wip_id = WipId(wip_id_str)
        ws = state.get_wip(wip_id)
        if ws is None:
            return HandlerOutcome(
                event_id=event.event_id, success=False,
                error_code="unknown_wip",
                state_changes=(),
                follow_up_events=(),
            )

        ws.advance(next_id, WipStatus.INSPECTING)

        return HandlerOutcome(
            event_id=event.event_id, success=True,
            state_changes=(f"{wip_id}:processing→inspecting@{next_id}",),
            follow_up_events=(
                _evt(f"{wip_id}-quality-check",
                     simulation_time_s=event.simulation_time_s,
                     event_type="QUALITY_CHECK", target_id=next_id,
                     causation_id=event.event_id),
            ),
        )

    return handler


# ═══════════════════════════════════════════════════
# QualityGate handler  — QUALITY_CHECK
# ═══════════════════════════════════════════════════

def make_quality_gate_handler(
    state: AssemblyRuntimeState,
    topology: AssemblyTopology,
    disposition_map: dict[str, QualityDisposition] | None = None,
):
    """Handler for QualityGate.  Uses pre-configured disposition per WIP.

    ``disposition_map`` maps WipId.id to the expected QualityDisposition.
    If not provided or no entry, defaults to PASS.
    """

    def handler(event: ScheduledEvent) -> HandlerOutcome:
        qg_id = event.target_id or "unknown-qg"

        wip_id_str = event.event_id.replace("-quality-check", "")
        wip_id = WipId(wip_id_str)
        ws = state.get_wip(wip_id)
        if ws is None:
            return HandlerOutcome(
                event_id=event.event_id, success=False,
                error_code="unknown_wip",
                state_changes=(),
                follow_up_events=(),
            )

        disposition = QualityDisposition.PASS
        if disposition_map and wip_id.id in disposition_map:
            disposition = disposition_map[wip_id.id]

        ws.advance(qg_id, WipStatus.INSPECTING)

        # Route based on disposition
        next_id = topology.next_primitive(qg_id, disposition.value)
        if next_id is None:
            return HandlerOutcome(
                event_id=event.event_id, success=False,
                error_code="no_route_for_disposition",
                state_changes=(f"{wip_id}:disposition={disposition.value}",),
                follow_up_events=(),
            )

        if disposition == QualityDisposition.PASS:
            ws.advance(next_id, WipStatus.COMPLETED)
            return HandlerOutcome(
                event_id=event.event_id, success=True,
                state_changes=(f"{wip_id}:pass→completed@{next_id}",),
                follow_up_events=(
                    _evt(f"{wip_id}-sink", simulation_time_s=event.simulation_time_s,
                         event_type="WIP_COMPLETED", target_id=next_id,
                         causation_id=event.event_id),
                ),
            )
        else:  # REWORK
            ws.advance(next_id, WipStatus.REWORK)
            return HandlerOutcome(
                event_id=event.event_id, success=True,
                state_changes=(f"{wip_id}:rework→processing@{next_id}",),
                follow_up_events=(
                    _evt(f"{wip_id}-process-start",
                         simulation_time_s=event.simulation_time_s,
                         event_type="PROCESS_START", target_id=next_id,
                         causation_id=event.event_id),
                ),
            )

    return handler


# ═══════════════════════════════════════════════════
# Sink handler  — WIP_COMPLETED
# ═══════════════════════════════════════════════════

def make_sink_handler(
    state: AssemblyRuntimeState,
):
    """Handler for Sink.  Terminal — marks WIP as COMPLETED."""

    def handler(event: ScheduledEvent) -> HandlerOutcome:
        wip_id_str = event.event_id.replace("-sink", "")
        wip_id = WipId(wip_id_str)
        ws = state.get_wip(wip_id)
        if ws is None:
            return HandlerOutcome(
                event_id=event.event_id, success=False,
                error_code="unknown_wip",
                state_changes=(),
                follow_up_events=(),
            )

        sink_id = event.target_id or "sink"
        ws.advance(sink_id, WipStatus.COMPLETED)

        return HandlerOutcome(
            event_id=event.event_id, success=True,
            state_changes=(f"{wip_id}:completed@{sink_id}",),
            follow_up_events=(),
        )

    return handler
