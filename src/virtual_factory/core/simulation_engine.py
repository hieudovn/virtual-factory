"""Simulation engine skeleton.

The engine will execute plant configurations loaded from YAML/JSON. It must not
hard-code a specific plant, including the first continuous-process MVP.
"""

from dataclasses import dataclass, field

from virtual_factory.core.exceptions import OutputPolicyViolation
from virtual_factory.core.runtime_factory import RuntimeAssembly, build_runtime
from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import PlantConfig, ScenarioConfig, INDUSTRIAL_PUBLISH_CATEGORIES
from virtual_factory.core.time_manager import TimeManager
from virtual_factory.equipment.process_dynamics import update_continuous_process
from virtual_factory.scenarios.scenario_manager import ScenarioManager
from virtual_factory.balance.basic_balance import MassBalance
from virtual_factory.balance.energy_balance import EnergyBalance
from virtual_factory.telemetry.telemetry_frame import build_publishable_frame


@dataclass
class SimulationEngine:
    """Coordinates time, plant graph, models, and telemetry policies."""

    plant_config: PlantConfig
    dt_s: float = 1.0
    scenario: ScenarioConfig | None = None
    assembly: RuntimeAssembly | None = None
    initialized: bool = False
    state: RuntimeState = field(default_factory=RuntimeState)
    time_manager: TimeManager = field(init=False, default=None)
    scenario_manager: ScenarioManager = field(init=False, default=None)
    mass_balance: MassBalance = field(init=False, default=None)
    energy_balance: EnergyBalance = field(init=False, default=None)

    def __post_init__(self) -> None:
        self.time_manager = TimeManager(step_s=self.dt_s)
        self.scenario_manager = ScenarioManager(self.scenario)
        self.mass_balance = MassBalance(self.plant_config)
        self.energy_balance = EnergyBalance(self.plant_config)

    def _check_output_policy(self) -> None:
        """Check all signals against output policy before running a step.

        Raises ``OutputPolicyViolation`` if any signal would leak
        internal truth through the industrial publish path.
        """
        if self.assembly is None:
            return
        for sig_name, sig_config in self.plant_config.signals.items():
            # Rule 1: internal_truth must never be publishable
            if sig_config.category == "internal_truth" and sig_config.publish:
                raise OutputPolicyViolation(
                    f"Signal '{sig_name}' has category 'internal_truth' "
                    f"but publish=True"
                )
            # Rule 2: publishable signal's source must not look like a truth path
            if sig_config.publish and sig_config.source:
                if "truth" in sig_config.source.lower() or sig_config.source.endswith("_true"):
                    raise OutputPolicyViolation(
                        f"Signal '{sig_name}' publish=True with source "
                        f"'{sig_config.source}' looks like internal truth"
                    )

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
        self._check_output_policy()
        assert self.assembly is not None
        timestamp_s = self.time_manager.now()
        fired_actions = self.scenario_manager.apply_due_actions(self.state, self.plant_config, timestamp_s)
        if fired_actions:
            self.state.diagnostics["scenario_actions_fired_last_step"] = len(fired_actions)

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
        # Plugin: call process_step on every equipment object so that
        # models with custom dynamics (heat exchanger, fan, compressor,
        # separator, …) can advance their physics without modifying
        # process_dynamics.py.
        for equipment in self.assembly.equipment.values():
            equipment.process_step(self.state, self.dt_s)
        self.state.diagnostics["mass_balance"] = self.mass_balance.evaluate(self.state, self.dt_s)
        self.state.diagnostics["energy_balance"] = self.energy_balance.evaluate(self.state, self.dt_s)
        # Combined balance summary
        mb = self.state.diagnostics.get("mass_balance", {})
        eb = self.state.diagnostics.get("energy_balance", {})
        self.state.diagnostics["balance_summary"] = {
            "mass_balanced": mb.get("balanced"),
            "energy_balanced": eb.get("balanced"),
            "mass_residual_pct": mb.get("residual_pct"),
            "energy_residual_pct": eb.get("residual_pct"),
            "step_time_s": timestamp_s,
        }
        for sensor in self.assembly.sensors.values():
            sensor.sample(
                self.state,
                timestamp_s=timestamp_s,
                signal_config=self.plant_config.signals.get(sensor.output_signal),
            )
        self.assembly.alarm_manager.evaluate(self.state, self.plant_config, timestamp_s)
        telemetry_frame = build_publishable_frame(
            self.plant_config,
            self.state,
            self.assembly.output_policy,
            timestamp_s,
        )
        # Append equipment truth values as calculated signals so the
        # dashboard can display tank levels, volumes, etc. even when
        # no dedicated sensor is configured for that equipment.
        _append_equipment_truth(telemetry_frame, self.state, self.assembly, timestamp_s)
        self.assembly.telemetry_store.append_frame(telemetry_frame)
        self.time_manager.advance()

        snapshot = self.state.snapshot()
        snapshot["telemetry_latest"] = telemetry_frame
        return snapshot


def _append_equipment_truth(
    frame: list,
    state,
    assembly,
    timestamp_s: float,
) -> None:
    """Append equipment truth values (level, volume, etc.) to the frame.

    These are labelled ``calculated`` so they pass the output policy
    and appear in the dashboard telemetry table and asset inspector.
    """
    from virtual_factory.telemetry.signal_value import SignalValue

    # Common physical parameters to expose per equipment
    TRUTH_PARAMS = ["level_true", "volume_true", "outflow_true", "inflow_true",
                    "pressure_rise_pa", "discharge_pressure_kpa",
                    "heat_transfer_kw", "power_consumed_kw"]

    for eq_id, _eq in assembly.equipment.items():
        for param in TRUTH_PARAMS:
            key = f"{eq_id}.{param}"
            val = state.get_truth(key)
            if val is not None:
                # Derive a friendly unit
                unit = ""
                if "level" in param:
                    unit = "m"
                elif "volume" in param:
                    unit = "m3"
                elif "flow" in param or "outflow" in param or "inflow" in param:
                    unit = "m3/s"
                elif "pressure" in param or "pressure_rise" in param:
                    unit = "kPa" if "kpa" in param else "Pa"
                elif "power" in param:
                    unit = "kW"
                elif "heat" in param:
                    unit = "kW"

                frame.append(SignalValue(
                    name=key,
                    value=float(val) if isinstance(val, (int, float)) else val,
                    unit=unit,
                    category="calculated",
                    quality="GOOD",
                    timestamp_s=timestamp_s,
                    source=f"{eq_id}.truth",
                ))
