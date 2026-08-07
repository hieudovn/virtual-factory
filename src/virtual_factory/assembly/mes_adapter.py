"""MES Simulation Adapter Contract.

M4-S04: Define the boundary between MES/CDM and Virtual Factory.
Input (MES→Simulation) and Output (Simulation→MES) contracts.
No production Odoo integration. Clear adapter boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════
# MES → Simulation input
# ═══════════════════════════════════════

@dataclass
class ProductionOrder:
    """MES Manufacturing Order / Production Order."""
    order_id: str
    product_id: str
    quantity: int
    routing_id: str | None = None
    priority: int = 0
    due_date: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class MaterialRelease:
    """Release WIP/material into simulation."""
    release_id: str
    order_id: str
    wip_id: str | None = None   # assigned by simulation if None
    quantity: int = 1
    source_id: str = ""          # which Source primitive to release into


@dataclass
class OperationCommand:
    """Command to start/control an operation."""
    command_id: str
    command_type: str  # "start", "pause", "resume", "stop"
    target_id: str      # station/processor ID
    wip_id: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityRequirement:
    """Quality/test requirement from MES."""
    requirement_id: str
    order_id: str | None = None
    product_id: str | None = None
    station_id: str | None = None
    test_type: str = "inspection"
    specification: dict[str, Any] = field(default_factory=dict)


@dataclass
class MESInput:
    """Bundle of MES inputs for a simulation run."""
    run_id: str
    production_orders: list[ProductionOrder] = field(default_factory=list)
    material_releases: list[MaterialRelease] = field(default_factory=list)
    operation_commands: list[OperationCommand] = field(default_factory=list)
    quality_requirements: list[QualityRequirement] = field(default_factory=list)
    scenario_parameters: dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════
# Simulation → MES output
# ═══════════════════════════════════════

class MESEventType(str, Enum):
    WIP_CREATED = "wip_created"
    OPERATION_STARTED = "operation_started"
    OPERATION_COMPLETED = "operation_completed"
    QUALITY_RESULT = "quality_result"
    CHECKLIST_RESULT = "checklist_result"
    REWORK = "rework"
    SCRAP = "scrap"
    WIP_COMPLETED = "wip_completed"
    ISSUE_FAULT = "issue_fault"
    RUN_STATUS = "run_status"


@dataclass
class MESEvent:
    """Simulation output event in MES/CDM terms."""
    event_id: str
    event_type: MESEventType
    run_id: str
    simulation_time_s: float
    wip_id: str | None = None
    order_id: str | None = None
    station_id: str | None = None
    disposition: str | None = None
    result: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None


@dataclass
class MESOutput:
    """Bundle of simulation output events for MES consumption."""
    run_id: str
    run_status: str
    events: list[MESEvent] = field(default_factory=list)


# ═══════════════════════════════════════
# Adapter boundary
# ═══════════════════════════════════════

class MESAdapter:
    """Boundary between MES/CDM and Virtual Factory.

    Translates MES inputs into simulation commands and simulation
    events back into MES/CDM events. Does not expose engine/runtime internals.
    """

    def mes_to_simulation(self, mes_input: MESInput) -> dict[str, Any]:
        """Convert MES input to simulation-ready configuration.

        Returns a dict suitable for SimulationDefinition construction.
        This is a contract definition — actual conversion logic
        will be implemented per MES integration scenario.
        """
        return {
            "run_id": mes_input.run_id,
            "orders": [o.order_id for o in mes_input.production_orders],
            "releases": [
                {"wip_id": r.wip_id, "source": r.source_id}
                for r in mes_input.material_releases
            ],
            "quality_count": len(mes_input.quality_requirements),
        }

    def simulation_to_mes(
        self,
        run_id: str,
        run_status: str,
        simulation_events: list[dict[str, Any]],
    ) -> MESOutput:
        """Convert simulation events to MES/CDM output events.

        Accepts generic dict representations of simulation events
        to maintain adapter boundary isolation.
        """
        mes_events: list[MESEvent] = []
        for se in simulation_events:
            event_type_str = se.get("event_type", "")
            mes_type = _map_event_type(event_type_str)
            mes_events.append(MESEvent(
                event_id=se.get("event_id", ""),
                event_type=mes_type,
                run_id=run_id,
                simulation_time_s=se.get("simulation_time_s", 0.0),
                wip_id=se.get("wip_id"),
                station_id=se.get("target_id"),
                disposition=se.get("disposition"),
                result=se.get("result"),
                correlation_id=se.get("correlation_id"),
            ))
        return MESOutput(run_id=run_id, run_status=run_status, events=mes_events)


def _map_event_type(sim_type: str) -> MESEventType:
    mapping = {
        "WIP_CREATED": MESEventType.WIP_CREATED,
        "PROCESS_START": MESEventType.OPERATION_STARTED,
        "PROCESS_COMPLETE": MESEventType.OPERATION_COMPLETED,
        "QUALITY_CHECK": MESEventType.QUALITY_RESULT,
        "WIP_COMPLETED": MESEventType.WIP_COMPLETED,
    }
    for key, val in mapping.items():
        if key in sim_type:
            return val
    return MESEventType.RUN_STATUS
