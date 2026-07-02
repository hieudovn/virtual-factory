"""Scenario Manager — loads, applies, and transitions between 8 WTP scenarios."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import yaml

from .actuator_engine import ActuatorEngine
from .disturbance_engine import DisturbanceEngine


SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"


class ScenarioOverride:
    """Override for a single signal's behavior or setpoint."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.signal_id: str = data.get("signal_id", "")
        self.sp: float | None = data.get("sp")
        self.baseline: float | None = data.get("baseline")
        self.amplitude: float | None = data.get("amplitude")
        self.bounds_min: float | None = data.get("bounds_min")
        self.bounds_max: float | None = data.get("bounds_max")
        self.override_dv: bool = data.get("override", False)


class Scenario:
    """One operational scenario with MV/DV overrides."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.scenario_id: str = data.get("scenario_id", "unknown")
        self.name: str = data.get("name", "Unknown")
        self.description: str = data.get("description", "")
        raw_mv = data.get("mv_overrides", {})
        raw_dv = data.get("dv_overrides", {})
        self.mv_overrides: dict[str, dict] = raw_mv
        self.dv_overrides: dict[str, dict] = raw_dv


class ScenarioTransition:
    """Tracks a smooth transition between scenarios."""

    def __init__(self, from_scenario: str, to_scenario: str, duration_s: float) -> None:
        self.from_scenario = from_scenario
        self.to_scenario = to_scenario
        self.duration_s = duration_s
        self.elapsed_s = 0.0
        self.mv_start: dict[str, float] = {}
        self.mv_target: dict[str, float] = {}
        self.dv_start: dict[str, dict] = {}
        self.dv_target: dict[str, dict] = {}

    @property
    def is_complete(self) -> bool:
        return self.elapsed_s >= self.duration_s

    @property
    def progress(self) -> float:
        return min(1.0, self.elapsed_s / max(self.duration_s, 0.1))


class ScenarioManager:
    """Manages 8 operational scenarios with smooth transitions."""

    def __init__(
        self,
        scenarios_dir: str | Path | None = None,
        default_scenario: str = "normal_operation",
        transition_s: float = 30.0,
    ) -> None:
        self.scenarios_dir = Path(scenarios_dir) if scenarios_dir else SCENARIOS_DIR
        self.default_scenario_id = default_scenario
        self.transition_s = transition_s
        self.scenarios: dict[str, Scenario] = {}
        self.current_scenario_id: str = default_scenario
        self.transition: ScenarioTransition | None = None

    def load_all(self) -> None:
        """Load all scenario YAML files from the scenarios directory."""
        if not self.scenarios_dir.exists():
            raise FileNotFoundError(f"Scenarios directory not found: {self.scenarios_dir}")

        for yaml_file in sorted(self.scenarios_dir.glob("*.yaml")):
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data and "scenario_id" in data:
                scenario = Scenario(data)
                self.scenarios[scenario.scenario_id] = scenario

    def load_scenario(self, scenario_id: str) -> Scenario | None:
        """Load a single scenario file by ID."""
        yaml_path = self.scenarios_dir / f"{scenario_id}.yaml"
        if not yaml_path.exists():
            return None
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data and data.get("scenario_id") == scenario_id:
            return Scenario(data)
        return None

    def switch_scenario(
        self,
        scenario_id: str,
        actuator_engine: ActuatorEngine | None = None,
        disturbance_engine: DisturbanceEngine | None = None,
    ) -> dict[str, Any]:
        """Initiate smooth transition to a new scenario."""
        if scenario_id not in self.scenarios:
            scenario = self.load_scenario(scenario_id)
            if scenario is None:
                return {"status": "error", "message": f"Scenario '{scenario_id}' not found"}
            self.scenarios[scenario_id] = scenario

        scenario = self.scenarios[scenario_id]
        old_id = self.current_scenario_id

        # Create transition
        transition = ScenarioTransition(old_id, scenario_id, self.transition_s)

        # Capture MV targets
        for sid, override in scenario.mv_overrides.items():
            if actuator_engine and sid in actuator_engine.actuators:
                act = actuator_engine.actuators[sid]
                transition.mv_start[sid] = act.value
                transition.mv_target[sid] = override.get("sp", act.setpoint)

        # Capture DV targets
        for sid, override in scenario.dv_overrides.items():
            if disturbance_engine and sid in disturbance_engine.configs:
                cfg = disturbance_engine.configs[sid]
                transition.dv_start[sid] = {
                    "baseline": cfg.baseline,
                    "amplitude": cfg.amplitude,
                    "bounds_min": cfg.bounds_min,
                    "bounds_max": cfg.bounds_max,
                }
                transition.dv_target[sid] = {
                    "baseline": override.get("baseline", cfg.baseline),
                    "amplitude": override.get("amplitude", cfg.amplitude),
                    "bounds_min": override.get("bounds_min", cfg.bounds_min),
                    "bounds_max": override.get("bounds_max", cfg.bounds_max),
                }

        self.transition = transition
        self.current_scenario_id = scenario_id

        return {
            "status": "transitioning",
            "from_scenario": old_id,
            "to_scenario": scenario_id,
            "transition_duration_s": self.transition_s,
            "message": f"Smoothly transitioning to {scenario_id} over {self.transition_s} seconds",
        }

    def step(
        self,
        dt_s: float,
        actuator_engine: ActuatorEngine | None = None,
        disturbance_engine: DisturbanceEngine | None = None,
    ) -> bool:
        """Advance transition if active. Returns True if transition is complete."""
        if self.transition is None or self.transition.is_complete:
            return True

        self.transition.elapsed_s += dt_s
        progress = self.transition.progress

        # Apply interpolated MV setpoints
        for sid, target_sp in self.transition.mv_target.items():
            if actuator_engine and sid in actuator_engine.actuators:
                start_sp = self.transition.mv_start.get(sid, target_sp)
                interpolated = start_sp + (target_sp - start_sp) * progress
                actuator_engine.actuators[sid].set(interpolated)

        # Apply interpolated DV parameters
        for sid, target in self.transition.dv_target.items():
            if disturbance_engine and sid in disturbance_engine.configs:
                start = self.transition.dv_start.get(sid, target)
                cfg = disturbance_engine.configs[sid]
                for key in ("baseline", "amplitude", "bounds_min", "bounds_max"):
                    if key in target:
                        s_val = start.get(key, getattr(cfg, key, 0.0))
                        t_val = target.get(key, getattr(cfg, key, 0.0))
                        interpolated = s_val + (t_val - s_val) * progress
                        setattr(cfg, key, interpolated)

        if self.transition.is_complete:
            self.transition = None
            return True

        return False

    def get_current(self) -> str:
        return self.current_scenario_id

    def list_scenarios(self) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for sid, scenario in self.scenarios.items():
            result.append({
                "scenario_id": sid,
                "name": scenario.name,
                "description": scenario.description,
            })
        return result

    def load_scenario_by_name(self, name: str) -> None:
        """Load a scenario by its file stem name."""
        scenario = self.load_scenario(name)
        if scenario:
            self.scenarios[name] = scenario
