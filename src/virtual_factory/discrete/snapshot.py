"""Immutable domain-neutral runtime snapshot.

M2-S01: transport-free — no message_sequence, allowed_actions, nodes, entities.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    """Immutable projection of ``DiscreteRunState`` for inspection.

    Fields are ordered so ``schema_version`` (defaulted) comes last.
    """

    run_id: str
    model_id: str
    model_version: str | None
    scenario_id: str | None
    scenario_version: str | None
    status: str
    simulation_time_s: float
    stop_reason: str | None
    failure_error: str | None
    processed_events: int
    pending_events: int
    last_event_id: str | None
    snapshot_sequence: int
    schema_version: str = "1.0.0"
