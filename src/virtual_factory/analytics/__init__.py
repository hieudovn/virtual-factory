"""Analytics Runtime — Integration layer for analytics-first simulation.

Ties together the fault engine, operating state machines, maintenance
event generator, and benchmark manager into a cohesive analytics
simulation runtime.

This module is the primary entry point for analytics benchmark
simulations. It extends the core SimulationEngine with analytics
capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from virtual_factory.benchmark.benchmark_manager import (
    BenchmarkLabels,
    BenchmarkManager,
    BenchmarkMode,
    BenchmarkPackage,
)
from virtual_factory.benchmark.export_utils import BenchmarkExporter
from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import PlantConfig
from virtual_factory.faults.fault_engine import FaultEngine, FaultScheduler
from virtual_factory.faults.fault_loader import build_default_fault_library
from virtual_factory.faults.fault_models import FaultLibrary
from virtual_factory.maintenance.event_generator import EventGenerator
from virtual_factory.operating_states.state_machine import (
    OperatingState,
    OperatingStateMachine,
    StateTransition,
)


@dataclass
class AnalyticsRuntime:
    """Orchestrates analytics-focused simulation runs.

    Extends core simulation with:
    - Fault lifecycle engine
    - Operating state tracking per equipment
    - Maintenance event generation
    - Benchmark label collection
    - Structured dataset export

    Usage::

        runtime = AnalyticsRuntime(plant_config)
        runtime.setup_compressor_states("COMP01")
        runtime.schedule_fault("COMP01", "bearing_wear", 3600.0)
        runtime.run(duration_s=7200, dt_s=1.0)
        runtime.export_benchmark("output/benchmark/")
    """

    plant_config: PlantConfig
    fault_library: FaultLibrary = field(default_factory=build_default_fault_library)
    benchmark_mode: BenchmarkMode = BenchmarkMode.BENCHMARK

    # Engines
    fault_engine: FaultEngine = field(init=False)
    event_generator: EventGenerator = field(init=False)
    benchmark_manager: BenchmarkManager = field(init=False)

    # State machines per equipment
    state_machines: dict[str, OperatingStateMachine] = field(default_factory=dict)

    # Simulation state
    current_time_s: float = field(default=0.0, init=False)
    dt_s: float = field(default=1.0, init=False)

    # Collected data
    telemetry_records: list[dict[str, Any]] = field(default_factory=list)
    fault_timeline_records: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.fault_engine = FaultEngine(library=self.fault_library)
        self.event_generator = EventGenerator()
        self.benchmark_manager = BenchmarkManager(mode=self.benchmark_mode)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def setup_compressor_states(self, equipment_id: str) -> OperatingStateMachine:
        """Configure standard compressor operating state transitions."""
        sm = OperatingStateMachine(equipment_id, initial=OperatingState.STOPPED)

        # Stopped -> Startup (when running=true and flow=0)
        sm.add_transition(StateTransition(
            OperatingState.STOPPED, OperatingState.STARTUP,
            condition=lambda s, t: bool(s.get(f"{equipment_id}.running", False)),
            description="Compressor start command received",
        ))

        # Startup -> Ramp-up (when flow > 10% rated)
        sm.add_transition(StateTransition(
            OperatingState.STARTUP, OperatingState.RAMP_UP,
            condition=lambda s, t: float(s.get(f"{equipment_id}.flow_m3_s", 0.0)) > 0.05,
            description="Flow established, ramping up",
        ))

        # Ramp-up -> Steady Running (when pressure ratio stabilizes)
        sm.add_transition(StateTransition(
            OperatingState.RAMP_UP, OperatingState.STEADY_RUNNING,
            condition=lambda s, t: t > 30.0,  # After 30s in ramp-up
            description="Reached steady running conditions",
        ))

        # Steady Running -> Low Load
        sm.add_transition(StateTransition(
            OperatingState.STEADY_RUNNING, OperatingState.LOW_LOAD,
            condition=lambda s, t: float(s.get(f"{equipment_id}.flow_m3_s", 999)) < 0.5,
            description="Flow dropped below 50% rated",
        ))

        # Low Load -> Steady Running
        sm.add_transition(StateTransition(
            OperatingState.LOW_LOAD, OperatingState.STEADY_RUNNING,
            condition=lambda s, t: float(s.get(f"{equipment_id}.flow_m3_s", 0.0)) >= 0.5,
            description="Flow recovered above 50% rated",
        ))

        # Steady Running -> High Load
        sm.add_transition(StateTransition(
            OperatingState.STEADY_RUNNING, OperatingState.HIGH_LOAD,
            condition=lambda s, t: float(s.get(f"{equipment_id}.flow_m3_s", 0.0)) > 1.5,
            description="Flow above 150% rated",
        ))

        # High Load -> Steady Running
        sm.add_transition(StateTransition(
            OperatingState.HIGH_LOAD, OperatingState.STEADY_RUNNING,
            condition=lambda s, t: float(s.get(f"{equipment_id}.flow_m3_s", 999)) <= 1.5,
            description="Flow returned to normal range",
        ))

        # Any running -> Near Surge (surge margin < 0.1)
        sm.add_transition(StateTransition(
            OperatingState.STEADY_RUNNING, OperatingState.NEAR_SURGE,
            condition=lambda s, t: float(s.get(f"{equipment_id}.surge_margin", 1.0)) < 0.1,
            description="Surge margin below 10%",
        ))
        sm.add_transition(StateTransition(
            OperatingState.HIGH_LOAD, OperatingState.NEAR_SURGE,
            condition=lambda s, t: float(s.get(f"{equipment_id}.surge_margin", 1.0)) < 0.1,
            description="Surge margin below 10%",
        ))

        # Near Surge -> Steady Running (recovery)
        sm.add_transition(StateTransition(
            OperatingState.NEAR_SURGE, OperatingState.STEADY_RUNNING,
            condition=lambda s, t: float(s.get(f"{equipment_id}.surge_margin", 0.0)) >= 0.15,
            description="Surge margin recovered above 15%",
        ))

        # Any running -> Shutdown (running=false)
        for run_state in [OperatingState.STARTUP, OperatingState.RAMP_UP,
                          OperatingState.STEADY_RUNNING, OperatingState.LOW_LOAD,
                          OperatingState.HIGH_LOAD, OperatingState.NEAR_SURGE,
                          OperatingState.RECYCLE_MODE]:
            sm.add_transition(StateTransition(
                run_state, OperatingState.SHUTDOWN,
                condition=lambda s, t: not bool(s.get(f"{equipment_id}.running", True)),
                description="Compressor stop command received",
            ))

        # Shutdown -> Stopped (after cooldown, or immediately)
        sm.add_transition(StateTransition(
            OperatingState.SHUTDOWN, OperatingState.STOPPED,
            condition=lambda s, t: t > 10.0,
            description="Cooldown complete",
        ))

        self.state_machines[equipment_id] = sm
        return sm

    def setup_pump_states(self, equipment_id: str) -> OperatingStateMachine:
        """Configure standard pump operating state transitions."""
        sm = OperatingStateMachine(equipment_id, initial=OperatingState.STOPPED)

        sm.add_transition(StateTransition(
            OperatingState.STOPPED, OperatingState.STARTUP,
            condition=lambda s, t: bool(s.get(f"{equipment_id}.running", False)),
            description="Pump start command received",
        ))

        sm.add_transition(StateTransition(
            OperatingState.STARTUP, OperatingState.STEADY_RUNNING,
            condition=lambda s, t: t > 5.0,
            description="Pump reached steady running",
        ))

        sm.add_transition(StateTransition(
            OperatingState.STEADY_RUNNING, OperatingState.SHUTDOWN,
            condition=lambda s, t: not bool(s.get(f"{equipment_id}.running", True)),
            description="Pump stop command received",
        ))

        sm.add_transition(StateTransition(
            OperatingState.SHUTDOWN, OperatingState.STOPPED,
            condition=lambda s, t: t > 3.0,
            description="Pump fully stopped",
        ))

        self.state_machines[equipment_id] = sm
        return sm

    # ------------------------------------------------------------------
    # Fault scheduling (convenience)
    # ------------------------------------------------------------------

    def schedule_fault(
        self,
        equipment_id: str,
        fault_id: str,
        start_time_s: float,
        initial_severity: float = 0.0,
    ) -> None:
        """Schedule a fault for injection at a future time."""
        self.fault_engine.schedule_fault(FaultScheduler(
            fault_id=fault_id,
            equipment_id=equipment_id,
            start_time_s=start_time_s,
            initial_severity=initial_severity,
        ))

    def inject_fault_now(
        self,
        equipment_id: str,
        fault_id: str,
        initial_severity: float = 0.0,
    ) -> None:
        """Immediately inject a fault."""
        self.fault_engine.inject_fault(
            fault_id, equipment_id, self.current_time_s, initial_severity
        )

    # ------------------------------------------------------------------
    # Step execution
    # ------------------------------------------------------------------

    def step(self, state: RuntimeState) -> dict[str, object]:
        """Advance analytics runtime by one step.

        Call this after the core simulation engine step.
        Returns a diagnostics snapshot.
        """
        # Advance fault engine
        fault_summary = self.fault_engine.step(state, self.current_time_s)

        # Collect truth values for state machine evaluation
        truth_dict = self._build_truth_dict(state)

        # Advance operating state machines
        state_snapshots = {}
        for eq_id, sm in self.state_machines.items():
            sm.step(truth_dict, self.dt_s)
            state_snapshots[eq_id] = sm.snapshot()

        # Generate fault timeline record
        for eq_id in self.state_machines:
            faults = self.fault_engine.get_active_faults(eq_id)
            health = self.fault_engine.get_health_index(eq_id)
            sm = self.state_machines.get(eq_id)

            self.fault_timeline_records.append({
                "timestamp_s": self.current_time_s,
                "equipment_id": eq_id,
                "operating_state": sm.current.value if sm else "unknown",
                "active_faults": ",".join(f.fault_id for f in faults),
                "max_severity": max((f.severity for f in faults), default=0.0),
                "health_index": health,
                "fault_count": len(faults),
            })

        # Record benchmark labels
        for eq_id, sm in self.state_machines.items():
            self.benchmark_manager.record_from_engine(
                timestamp_s=self.current_time_s,
                equipment_id=eq_id,
                state_machine=sm,
                fault_engine=self.fault_engine,
            )

        self.current_time_s += self.dt_s

        return {
            "fault_engine": fault_summary,
            "operating_states": state_snapshots,
        }

    # ------------------------------------------------------------------
    # Run simulation
    # ------------------------------------------------------------------

    def run(
        self,
        duration_s: float,
        dt_s: float = 1.0,
        core_step_fn=None,  # Callable[[], dict] — core engine step
    ) -> None:
        """Run a complete analytics simulation.

        Parameters
        ----------
        duration_s : float
            Total simulation duration in seconds.
        dt_s : float
            Time step in seconds.
        core_step_fn : callable or None
            Function that advances the core simulation engine by one step
            and returns a snapshot containing at least ``telemetry_latest``.
        """
        self.dt_s = dt_s
        self.current_time_s = 0.0
        steps = int(duration_s / dt_s)

        for _ in range(steps):
            if core_step_fn:
                snapshot = core_step_fn()
                # Collect telemetry
                telemetry = snapshot.get("telemetry_latest", [])
                if telemetry:
                    self._collect_telemetry(telemetry)
                # Get runtime state from snapshot
                state = snapshot.get("runtime_state")
            else:
                state = None

            if state is None:
                # Without a core engine, just advance analytics
                state = RuntimeState()

            self.step(state)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_benchmark(self, output_dir: str = "output/benchmark") -> dict[str, str]:
        """Export the complete benchmark package."""
        package = self.benchmark_manager.build_package(
            telemetry_records=self.telemetry_records,
            asset_metadata=self._build_asset_metadata(),
            alarm_records=[],  # Populated by core engine
            maintenance_records=self.event_generator.to_records(),
            fault_timeline_records=self.fault_timeline_records,
        )

        from virtual_factory.benchmark.export_utils import export_benchmark_package
        return export_benchmark_package(package, output_dir)

    def get_benchmark_package(self) -> BenchmarkPackage:
        """Get the current benchmark package without exporting."""
        return self.benchmark_manager.build_package(
            telemetry_records=self.telemetry_records,
            asset_metadata=self._build_asset_metadata(),
            alarm_records=[],
            maintenance_records=self.event_generator.to_records(),
            fault_timeline_records=self.fault_timeline_records,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_truth_dict(self, state: RuntimeState) -> dict[str, Any]:
        """Build a flat dict of truth values for state machine evaluation."""
        result: dict[str, Any] = {}
        for key in state.truth:
            result[key] = state.get_truth(key)
        return result

    def _collect_telemetry(self, frame: list) -> None:
        """Collect telemetry signals as records."""
        for signal in frame:
            self.telemetry_records.append({
                "timestamp_s": getattr(signal, "timestamp_s", self.current_time_s),
                "name": getattr(signal, "name", ""),
                "value": getattr(signal, "value", None),
                "unit": getattr(signal, "unit", ""),
                "category": getattr(signal, "category", ""),
                "quality": getattr(signal, "quality", "GOOD"),
            })

    def _build_asset_metadata(self) -> dict[str, Any]:
        """Build asset metadata from plant config and state machines."""
        return {
            "plant_id": self.plant_config.plant.id,
            "plant_name": self.plant_config.plant.name,
            "equipment": [
                {
                    "id": eq.id,
                    "model_type": eq.model_type,
                    "display_name": eq.display_name,
                }
                for eq in self.plant_config.equipment
            ],
            "operating_states": [
                sm.snapshot()
                for sm in self.state_machines.values()
            ],
            "fault_library_size": len(self.fault_library),
            "fault_categories": self.fault_library.categories(),
        }

    def reset(self) -> None:
        """Reset all analytics state."""
        self.current_time_s = 0.0
        self.fault_engine.reset()
        self.event_generator.reset()
        self.benchmark_manager.reset()
        self.state_machines.clear()
        self.telemetry_records.clear()
        self.fault_timeline_records.clear()
