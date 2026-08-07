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
from virtual_factory.assembly.runtime import AssemblyRuntimeState, RuntimeStateError
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
        buf_prim = topology.get_primitive(buffer_id)
        if buf_prim is None or not isinstance(buf_prim, Buffer):
            return HandlerOutcome(
                event_id=event.event_id, success=False,
                error_code="invalid_buffer", state_changes=(), follow_up_events=())
        buf: Buffer = buf_prim
        state.ensure_buffer(buf)

        wip_id_str = event.event_id.replace("-arrive", "")
        wip_id = WipId(wip_id_str)
        ws = state.get_wip(wip_id)
        if ws is None:
            return HandlerOutcome(
                event_id=event.event_id, success=False,
                error_code="unknown_wip", state_changes=(), follow_up_events=())

        # Enqueue (capacity check)
        try:
            state.buffer_enqueue(buffer_id, wip_id, buf.capacity)
        except RuntimeStateError:
            return HandlerOutcome(
                event_id=event.event_id, success=False,
                error_code="buffer_full",
                state_changes=(f"{wip_id}:buffer_full@{buffer_id}",),
                follow_up_events=())

        ws.advance(buffer_id, WipStatus.QUEUED)
        next_id = topology.next_primitive(buffer_id)
        if next_id is None:
            return HandlerOutcome(
                event_id=event.event_id, success=False,
                error_code="no_route", state_changes=(), follow_up_events=())

        # FIFO dequeue — single WIP, immediate forward
        dequeued = state.buffer_dequeue(buffer_id)
        assert dequeued.id == wip_id.id, f"FIFO mismatch: {dequeued.id} != {wip_id.id}"
        ws.advance(next_id, WipStatus.PROCESSING)

        return HandlerOutcome(
            event_id=event.event_id, success=True,
            state_changes=(
                f"{wip_id}:enqueued@{buffer_id}",
                f"{wip_id}:dequeued→processing@{next_id}",
                f"buffer:{buffer_id}:size={state.buffer_size(buffer_id)}",
            ),
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

        # Extract WIP ID: strip known suffixes
        eid = event.event_id
        is_rewrk = "-rewrk-process-start" in eid or "-rewrk-process-complete" in eid
        # Strip rework prefix first, then target-ID-prefixed suffix, then plain suffix
        wip_id_str = eid.replace("-rewrk-process-start", "").replace("-rewrk-process-complete", "")
        import re as _re
        wip_id_str = _re.sub(r'-(AP\d{2}|[a-z]+-\d+)?-?process-start$', '', wip_id_str)
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
        # Derive follow-up event_id from incoming event
        complete_eid = event.event_id.replace("-process-start", "-process-complete")

        return HandlerOutcome(
            event_id=event.event_id, success=True,
            state_changes=(f"{wip_id}:processing@{proc_id}",),
            follow_up_events=(
                _evt(complete_eid,
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
    """Handler for PROCESS_COMPLETE — routes to next primitive based on its type."""

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

        # Extract WIP ID: strip known suffixes
        eid = event.event_id
        import re as _re2
        wip_id_str = _re2.sub(r'-(AP\d{2}|[a-z]+-\d+)?-?process-complete$', '', eid)
        wip_id_str = wip_id_str.replace("-rewrk-process-complete", "")
        is_rewrk = "-rewrk-process-complete" in eid
        wip_id = WipId(wip_id_str)
        ws = state.get_wip(wip_id)
        if ws is None:
            return HandlerOutcome(
                event_id=event.event_id, success=False,
                error_code="unknown_wip",
                state_changes=(), follow_up_events=())

        next_prim = topology.get_primitive(next_id)
        if next_prim is None:
            return HandlerOutcome(
                event_id=event.event_id, success=False,
                error_code="unknown_next", state_changes=(), follow_up_events=())

        if isinstance(next_prim, Processor):
            # Chain to next processor
            ws.advance(next_id, WipStatus.PROCESSING)
            if is_rewrk:
                suffix = "-rewrk-process-start"
            else:
                suffix = f"-{next_id}-process-start"
            return HandlerOutcome(
                event_id=event.event_id, success=True,
                state_changes=(f"{wip_id}:processing→next@{next_id}",),
                follow_up_events=(
                    _evt(f"{wip_id}{suffix}", simulation_time_s=event.simulation_time_s,
                         event_type="PROCESS_START", target_id=next_id,
                         causation_id=event.event_id),
                ),
            )
        else:
            # QualityGate or other — route with QUALITY_CHECK
            ws.advance(next_id, WipStatus.INSPECTING)
            suffix = "-rewrk-quality-check" if is_rewrk else "-quality-check"
            return HandlerOutcome(
                event_id=event.event_id, success=True,
                state_changes=(f"{wip_id}:processing→inspecting@{next_id}",),
                follow_up_events=(
                    _evt(f"{wip_id}{suffix}", simulation_time_s=event.simulation_time_s,
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
    quality_plan: dict[str, list[QualityDisposition]] | None = None,
):
    """Handler for QualityGate.  Consumes next disposition from per-WIP plan.

    ``quality_plan`` maps WipId.id to a list of QualityDisposition values
    consumed in order.  If empty or no entry, defaults to PASS.
    """

    def handler(event: ScheduledEvent) -> HandlerOutcome:
        qg_id = event.target_id or "unknown-qg"

        wip_id_str = event.event_id.replace("-rewrk-quality-check", "").replace("-quality-check", "")
        wip_id = WipId(wip_id_str)
        ws = state.get_wip(wip_id)
        if ws is None:
            return HandlerOutcome(
                event_id=event.event_id, success=False,
                error_code="unknown_wip",
                state_changes=(),
                follow_up_events=(),
            )

        # Consume next disposition from plan
        disposition = QualityDisposition.PASS
        if quality_plan and wip_id.id in quality_plan:
            plan = quality_plan[wip_id.id]
            if plan:
                disposition = plan.pop(0)

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
            # Route toward Sink — Sink owns the final COMPLETED transition
            ws.advance(next_id, WipStatus.INSPECTING)
            return HandlerOutcome(
                event_id=event.event_id, success=True,
                state_changes=(f"{wip_id}:pass→sink@{next_id}",),
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
                    _evt(f"{wip_id}-rewrk-process-start",
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
