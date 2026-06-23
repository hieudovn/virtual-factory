"""Fault Lifecycle Engine.

Orchestrates fault injection, progression, symptom propagation, alarm
triggering, maintenance actions, and recovery for the simulation runtime.
"""

from dataclasses import dataclass, field

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.faults.fault_models import (
    FaultConfig,
    FaultInstance,
    FaultLibrary,
    FaultSymptom,
    MaintenanceAction,
)


@dataclass
class FaultScheduler:
    """Planned fault injection with start time and configuration."""

    fault_id: str
    equipment_id: str
    start_time_s: float
    initial_severity: float = 0.0

    def __post_init__(self) -> None:
        if self.initial_severity < 0.0 or self.initial_severity > 1.0:
            raise ValueError(f"initial_severity must be in [0, 1], got {self.initial_severity}")


@dataclass
class FaultEngine:
    """Manages active faults, their progression, and symptom propagation.

    The engine is driven by schedule (FaultScheduler entries) and can
    also accept runtime fault injection via ``inject_fault()``.

    Usage::

        engine = FaultEngine(fault_library)
        engine.schedule(FaultScheduler("bearing_wear", "COMP01", 100.0))
        # Each simulation step:
        engine.step(state, current_time_s)
        # Symptoms are written to state.truth as additive effects
    """

    library: FaultLibrary
    active_faults: dict[str, FaultInstance] = field(default_factory=dict)
    schedule: list[FaultScheduler] = field(default_factory=list)
    event_log: list[dict] = field(default_factory=list)

    # Internal tracking
    _applied_indices: set[int] = field(default_factory=set)
    _fault_counter: dict[str, int] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Fault injection
    # ------------------------------------------------------------------

    def schedule_fault(self, item: FaultScheduler) -> None:
        """Add a fault to the injection schedule."""
        self.schedule.append(item)

    def inject_fault(
        self,
        fault_id: str,
        equipment_id: str,
        current_time_s: float,
        initial_severity: float = 0.0,
    ) -> FaultInstance | None:
        """Immediately inject a fault (runtime injection, bypasses schedule)."""
        config = self.library.get(fault_id)
        if config is None:
            raise ValueError(f"Unknown fault: {fault_id}")

        instance = FaultInstance(
            fault_config=config,
            equipment_id=equipment_id,
            start_time_s=current_time_s,
            initial_severity=initial_severity,
        )
        key = self._instance_key(fault_id, equipment_id)
        self.active_faults[key] = instance

        self._fault_counter[fault_id] = self._fault_counter.get(fault_id, 0) + 1
        self._log_event("fault_injected", current_time_s, {
            "fault_id": fault_id,
            "equipment_id": equipment_id,
            "initial_severity": initial_severity,
        })
        return instance

    # ------------------------------------------------------------------
    # Step execution
    # ------------------------------------------------------------------

    def step(self, state: RuntimeState, current_time_s: float) -> dict[str, object]:
        """Advance all active faults and propagate symptoms.

        Returns a summary dict of active fault states for diagnostics.
        """
        # Process scheduled injections
        self._apply_due_injections(current_time_s)

        # Clear previous symptom accumulations
        self._clear_symptoms(state)

        # Advance each active fault
        summary: dict[str, object] = {"active_count": 0, "faults": []}

        completed_keys: list[str] = []
        for key, instance in self.active_faults.items():
            instance.advance(1.0)  # default dt=1s; engine step aligns

            if not instance.active and instance.severity <= 0.01:
                completed_keys.append(key)
                continue

            self._propagate_symptoms(instance, state, current_time_s)
            summary["active_count"] = int(summary["active_count"]) + 1  # type: ignore[operator]
            fault_summary = {
                "fault_id": instance.fault_id,
                "equipment_id": instance.equipment_id,
                "severity": round(instance.severity, 4),
                "severity_label": instance.severity_label.value,
                "detected": instance.detected,
            }
            if isinstance(summary["faults"], list):
                summary["faults"].append(fault_summary)  # type: ignore[attr-defined]

        # Clean up completed faults
        for key in completed_keys:
            del self.active_faults[key]

        # Write fault diagnostics to state
        state.diagnostics["fault_engine"] = summary
        return summary

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def apply_maintenance(
        self,
        fault_id: str,
        equipment_id: str,
        action: MaintenanceAction,
        current_time_s: float,
    ) -> bool:
        """Apply a maintenance action to an active fault."""
        key = self._instance_key(fault_id, equipment_id)
        instance = self.active_faults.get(key)
        if instance is None:
            return False

        instance.start_recovery(action)
        self._log_event("maintenance_applied", current_time_s, {
            "fault_id": fault_id,
            "equipment_id": equipment_id,
            "action_id": action.action_id,
            "action_type": action.action_type,
        })
        return True

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_active_faults(self, equipment_id: str | None = None) -> list[FaultInstance]:
        """Get all active faults, optionally filtered by equipment."""
        if equipment_id:
            return [
                inst for inst in self.active_faults.values()
                if inst.equipment_id == equipment_id
            ]
        return list(self.active_faults.values())

    def get_severity(self, fault_id: str, equipment_id: str) -> float:
        """Get current severity of a specific fault on equipment."""
        key = self._instance_key(fault_id, equipment_id)
        instance = self.active_faults.get(key)
        return instance.severity if instance else 0.0

    def get_health_index(self, equipment_id: str) -> float:
        """Compute a simple health index for equipment (1.0 = healthy, 0.0 = failed).

        Health = 1.0 - max(severity of active faults on this equipment).
        """
        faults = self.get_active_faults(equipment_id)
        if not faults:
            return 1.0
        max_severity = max(f.severity for f in faults)
        return round(1.0 - max_severity, 4)

    def reset(self) -> None:
        """Clear all active faults and schedules."""
        self.active_faults.clear()
        self.schedule.clear()
        self.event_log.clear()
        self._applied_indices.clear()
        self._fault_counter.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _instance_key(self, fault_id: str, equipment_id: str) -> str:
        return f"{equipment_id}:{fault_id}"

    def _apply_due_injections(self, current_time_s: float) -> None:
        for i, item in enumerate(self.schedule):
            if i in self._applied_indices:
                continue
            if current_time_s >= item.start_time_s:
                self.inject_fault(item.fault_id, item.equipment_id, current_time_s, item.initial_severity)
                self._applied_indices.add(i)

    def _propagate_symptoms(
        self, instance: FaultInstance, state: RuntimeState, current_time_s: float
    ) -> None:
        """Write symptom effects to runtime state truth variables."""
        for symptom in instance.fault_config.symptoms:
            effect = instance.get_symptom_value(symptom, current_time_s)
            if effect == 0.0:
                continue

            var = symptom.variable
            current_val = float(state.get_truth(var, 0.0))

            if symptom.effect_type == "additive":
                state.set_truth(var, current_val + effect)
            elif symptom.effect_type == "multiplicative":
                state.set_truth(var, current_val * (1.0 + effect))
            elif symptom.effect_type == "replacement":
                state.set_truth(var, effect)

    def _clear_symptoms(self, state: RuntimeState) -> None:
        """Reset symptom-affected variables to base values before re-computing.

        This is intentionally minimal — a full implementation would snapshot
        base values at fault injection time. For now, symptom effects are
        additive and cumulative across steps.
        """

    def _log_event(self, event_type: str, timestamp_s: float, data: dict) -> None:
        self.event_log.append({
            "type": event_type,
            "timestamp_s": timestamp_s,
            **data,
        })
