"""Runtime service facade for monitoring API access."""

from dataclasses import asdict
from pathlib import Path

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.schema import ScenarioConfig
from virtual_factory.core.simulation_engine import SimulationEngine
from virtual_factory.scenarios.scenario_loader import load_scenario
from virtual_factory.telemetry.signal_value import SignalValue


class RuntimeService:
    """Owns one simulation engine instance for API monitoring endpoints."""

    def __init__(
        self,
        config_path: str | Path,
        scenario_path: str | Path | None = None,
        dt_s: float = 1.0,
    ) -> None:
        self.config_path = Path(config_path)
        self.scenario_path = Path(scenario_path) if scenario_path else None
        self.config = load_plant_config(self.config_path)
        self.scenario: ScenarioConfig | None = load_scenario(self.scenario_path) if self.scenario_path else None
        self.engine = SimulationEngine(self.config, dt_s=dt_s, scenario=self.scenario)
        self.latest_snapshot: dict[str, object] | None = None

    def step_once(self) -> list[dict]:
        """Run one simulation step and return the latest publishable telemetry."""
        self.latest_snapshot = self.engine.step()
        return self.latest_telemetry()

    def run_steps(self, n: int) -> list[dict]:
        """Run multiple simulation steps and return the latest publishable telemetry."""
        count = max(0, n)
        for _ in range(count):
            self.latest_snapshot = self.engine.step()
        if count == 0 and self.latest_snapshot is None:
            self.latest_snapshot = self.engine.step()
        return self.latest_telemetry()

    def latest_telemetry(self) -> list[dict]:
        """Return the latest publishable telemetry frame as JSON-safe records."""
        if self.latest_snapshot and "telemetry_latest" in self.latest_snapshot:
            return _signals_to_records(self.latest_snapshot["telemetry_latest"])
        if self.engine.assembly is not None:
            return _signals_to_records(self.engine.assembly.telemetry_store.latest())
        return []

    def telemetry_history(self, limit: int = 100) -> list[dict]:
        """Return recent publishable telemetry records from the in-memory store."""
        if self.engine.assembly is None:
            return []
        frames = self.engine.assembly.telemetry_store.all()
        selected_frames = frames[-max(0, limit) :] if limit else []
        records: list[dict] = []
        for frame in selected_frames:
            records.extend(_signals_to_records(frame))
        return records

    def latest_alarms(self) -> list[dict]:
        """Return latest industrial event signals from publishable telemetry."""
        return [record for record in self.latest_telemetry() if record.get("category") == "industrial_event"]

    def status(self) -> dict:
        """Return service and simulation status without exposing internal truth."""
        frame_count = 0
        if self.engine.assembly is not None:
            frame_count = len(self.engine.assembly.telemetry_store.all())
        return {
            "status": "running",
            "plant_id": self.config.plant.id,
            "plant_name": self.config.plant.name,
            "scenario_id": self.scenario.id if self.scenario else None,
            "initialized": self.engine.initialized,
            "time_s": self.engine.time_manager.now(),
            "dt_s": self.engine.dt_s,
            "telemetry_frames": frame_count,
        }


def _signals_to_records(signals: object) -> list[dict]:
    """Convert SignalValue objects to dicts and filter internal truth defensively."""
    if not isinstance(signals, list):
        return []
    records: list[dict] = []
    for signal in signals:
        if not isinstance(signal, SignalValue):
            continue
        if signal.category == "internal_truth":
            continue
        records.append(asdict(signal))
    return records
