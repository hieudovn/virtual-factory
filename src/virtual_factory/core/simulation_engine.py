"""Simulation engine skeleton.

The engine will execute plant configurations loaded from YAML/JSON. It must not
hard-code a specific plant, including the first continuous-process MVP.
"""

from dataclasses import dataclass, field

from virtual_factory.core.runtime_factory import RuntimeAssembly, build_runtime
from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import PlantConfig


@dataclass(slots=True)
class SimulationEngine:
    """Coordinates time, plant graph, models, and telemetry policies."""

    plant_config: PlantConfig
    assembly: RuntimeAssembly | None = None
    initialized: bool = False
    state: RuntimeState = field(default_factory=RuntimeState)

    def initialize(self) -> None:
        """Build runtime objects and initialize equipment truth state."""
        self.assembly = build_runtime(self.plant_config)
        self.state = self.assembly.state
        for equipment in self.assembly.equipment.values():
            equipment.initialize_state(self.state)
        self.initialized = True

    def step(self) -> dict[str, dict[str, object]]:
        """Advance signal flow by one tick and return a state snapshot."""
        if not self.initialized:
            self.initialize()
        assert self.assembly is not None

        for sensor in self.assembly.sensors.values():
            sensor.sample(self.state)
        for controller in self.assembly.controllers.values():
            controller.execute(self.state)
        for actuator in self.assembly.actuators.values():
            actuator.update(self.state)

        return self.state.snapshot()
