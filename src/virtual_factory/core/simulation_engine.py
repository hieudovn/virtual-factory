"""Simulation engine skeleton.

The engine will execute plant configurations loaded from YAML/JSON. It must not
hard-code a specific plant, including the first continuous-process MVP.
"""

from dataclasses import dataclass, field

from virtual_factory.core.time_manager import TimeManager
from virtual_factory.core.runtime_factory import RuntimeAssembly, build_runtime
from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import PlantConfig
from virtual_factory.equipment.process_dynamics import update_continuous_process
from virtual_factory.telemetry.telemetry_frame import build_publishable_frame


@dataclass(slots=True)
class SimulationEngine:
    """Coordinates time, plant graph, models, and telemetry policies."""

    plant_config: PlantConfig
    dt_s: float = 1.0
    assembly: RuntimeAssembly | None = None
    initialized: bool = False
    state: RuntimeState = field(default_factory=RuntimeState)
    time_manager: TimeManager = field(init=False)

    def __post_init__(self) -> None:
        self.time_manager = TimeManager(step_s=self.dt_s)

    def initialize(self) -> None:
        """Build runtime objects and initialize equipment truth state."""
        self.assembly = build_runtime(self.plant_config)
        self.state = self.assembly.state
        for equipment in self.assembly.equipment.values():
            equipment.initialize_state(self.state)
        self.initialized = True

    def step(self) -> dict[str, object]:
        """Advance one tick and return a state snapshot.

        Current MVP timing samples sensors for controller input, applies
        controller and actuator outputs, updates process dynamics, then samples
        sensors again so snapshots reflect the new physical state. Future
        versions should make sampling and scan phases explicit.
        """
        if not self.initialized:
            self.initialize()
        assert self.assembly is not None
        timestamp_s = self.time_manager.now()

        for sensor in self.assembly.sensors.values():
            sensor.sample(
                self.state,
                timestamp_s=timestamp_s,
                signal_config=self.plant_config.signals.get(sensor.output_signal),
            )
        for controller in self.assembly.controllers.values():
            controller.execute(
                self.state,
                timestamp_s=timestamp_s,
                signal_config=self.plant_config.signals.get(controller.output_signal),
            )
        for actuator in self.assembly.actuators.values():
            feedback_config = (
                self.plant_config.signals.get(actuator.feedback_signal)
                if actuator.feedback_signal
                else None
            )
            actuator.update(self.state, timestamp_s=timestamp_s, feedback_signal_config=feedback_config)
        update_continuous_process(self.plant_config, self.state, self.dt_s)
        for sensor in self.assembly.sensors.values():
            sensor.sample(
                self.state,
                timestamp_s=timestamp_s,
                signal_config=self.plant_config.signals.get(sensor.output_signal),
            )
        telemetry_frame = build_publishable_frame(
            self.plant_config,
            self.state,
            self.assembly.output_policy,
            timestamp_s,
        )
        self.assembly.telemetry_store.append_frame(telemetry_frame)
        self.time_manager.advance()

        snapshot = self.state.snapshot()
        snapshot["telemetry_latest"] = telemetry_frame
        return snapshot
