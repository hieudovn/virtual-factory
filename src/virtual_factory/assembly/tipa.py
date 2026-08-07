"""TIPA topology configuration and handler wiring.

M3-S03: TIPA-specific assembly model built on M3-S02 vertical runtime.
2 SSO2 sources → shared buffer → AP01-AP06 → final quality → Sink/rework.
"""

from __future__ import annotations

from virtual_factory.assembly.handlers import (
    make_source_handler,
    make_buffer_handler,
    make_processor_handler,
    make_process_complete_handler,
    make_quality_gate_handler,
    make_sink_handler,
)
from virtual_factory.assembly.primitives import (
    Source, Buffer, Processor, QualityGate, Sink,
)
from virtual_factory.assembly.quality import QualityDisposition
from virtual_factory.assembly.runtime import AssemblyRuntimeState
from virtual_factory.assembly.topology import AssemblyTopology
from virtual_factory.discrete.handler_registry import HandlerRegistry


def build_tipa_topology() -> AssemblyTopology:
    """Build the TIPA assembly topology.

    Flow:
      sso2-1 ──┐
               ├→ shared-buffer → AP01 → AP02 → AP03 → AP04 → AP05 → AP06
      sso2-2 ──┘                                              ↓
                                                        final-quality
                                                       ├── PASS → finished-sink
                                                       └── REWORK → AP04
    """
    topo = AssemblyTopology()

    # Sources: 2 SSO2 material entry points
    topo.add_primitive(Source(primitive_id="sso2-1", label="SSO2 Source 1"))
    topo.add_primitive(Source(primitive_id="sso2-2", label="SSO2 Source 2"))

    # Shared buffer
    topo.add_primitive(Buffer(primitive_id="shared-buffer", capacity=50, label="Shared Input Buffer"))

    # Assembly stations AP01-AP06
    for ap_id in ["AP01", "AP02", "AP03", "AP04", "AP05", "AP06"]:
        topo.add_primitive(Processor(primitive_id=ap_id, processing_time_s=1.0,
                                     label=f"Assembly Point {ap_id}"))

    # Final quality gate
    topo.add_primitive(QualityGate(primitive_id="final-quality", label="Final Quality Inspection"))

    # Sinks
    topo.add_primitive(Sink(primitive_id="finished-sink", label="Finished Goods"))

    # --- Edges ---
    # SSO2 sources → shared buffer
    topo.add_edge("sso2-1", "shared-buffer")
    topo.add_edge("sso2-2", "shared-buffer")

    # Shared buffer → AP01
    topo.add_edge("shared-buffer", "AP01")

    # AP01 → AP02 → AP03 → AP04 → AP05 → AP06
    topo.add_edge("AP01", "AP02")
    topo.add_edge("AP02", "AP03")
    topo.add_edge("AP03", "AP04")
    topo.add_edge("AP04", "AP05")
    topo.add_edge("AP05", "AP06")

    # AP06 → final quality
    topo.add_edge("AP06", "final-quality")

    # Quality → finished sink (PASS) or rework to AP04 (REWORK)
    topo.add_edge("final-quality", "finished-sink", QualityDisposition.PASS.value)
    topo.add_edge("final-quality", "AP04", QualityDisposition.REWORK.value)

    return topo


def build_tipa_handler_registry(
    quality_plan: dict[str, list[QualityDisposition]] | None = None,
) -> tuple[HandlerRegistry, AssemblyRuntimeState, list[int]]:
    """Build HandlerRegistry for TIPA flow with shared runtime state.

    Returns (registry, runtime_state, wip_counter).
    """
    topo = build_tipa_topology()
    state = AssemblyRuntimeState()
    wip_counter = [0]

    reg = HandlerRegistry()
    reg.register("WIP_CREATED", make_source_handler(state, topo, wip_counter))
    reg.register("WIP_QUEUED", make_buffer_handler(state, topo))
    reg.register("PROCESS_START", make_processor_handler(state, topo))
    reg.register("PROCESS_COMPLETE", make_process_complete_handler(state, topo))
    reg.register("QUALITY_CHECK", make_quality_gate_handler(state, topo, quality_plan))
    reg.register("WIP_COMPLETED", make_sink_handler(state))

    return reg, state, wip_counter
