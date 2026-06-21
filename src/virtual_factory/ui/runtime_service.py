"""Runtime service facade for monitoring API access."""

import asyncio
from dataclasses import asdict
from pathlib import Path

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.schema import ScenarioConfig
from virtual_factory.core.simulation_engine import SimulationEngine
from virtual_factory.protocols.mqtt_gateway import MqttGateway
from virtual_factory.protocols.opcua_gateway import OpcUaGateway
from virtual_factory.scenarios.scenario_loader import load_scenario
from virtual_factory.telemetry.signal_value import SignalValue


class RuntimeService:
    """Owns one simulation engine instance for API monitoring endpoints."""

    def __init__(
        self,
        config_path: str | Path,
        scenario_path: str | Path | None = None,
        dt_s: float = 1.0,
        mqtt_host: str | None = None,
        mqtt_port: int = 1883,
        mqtt_topic_prefix: str = "virtual-factory/demo/continuous_mvp_01",
        mqtt_client_id: str | None = None,
        mqtt_connect_retries: int = 20,
        mqtt_connect_delay: float = 1.0,
        opcua_endpoint: str | None = None,
    ) -> None:
        self.config_path = Path(config_path)
        self.scenario_path = Path(scenario_path) if scenario_path else None
        self.config = load_plant_config(self.config_path)
        self.scenario: ScenarioConfig | None = load_scenario(self.scenario_path) if self.scenario_path else None
        self.engine = SimulationEngine(self.config, dt_s=dt_s, scenario=self.scenario)
        self.latest_snapshot: dict[str, object] | None = None
        self.mqtt_gateway = (
            MqttGateway(
                host=mqtt_host,
                port=mqtt_port,
                topic_prefix=mqtt_topic_prefix,
                client_id=mqtt_client_id,
            )
            if mqtt_host
            else None
        )
        self.opcua_gateway = (
            OpcUaGateway(endpoint=opcua_endpoint) if opcua_endpoint else None
        )
        self.mqtt_connect_retries = mqtt_connect_retries
        self.mqtt_connect_delay = mqtt_connect_delay
        self.mqtt_connected = False
        self.is_running = False
        self.loop_task: asyncio.Task | None = None

    def connect_mqtt(self) -> None:
        """Connect the optional MQTT gateway."""
        if self.mqtt_gateway is None or self.mqtt_connected:
            return
        self.mqtt_gateway.connect(retries=self.mqtt_connect_retries, delay_s=self.mqtt_connect_delay)
        self.mqtt_connected = True

    def disconnect_mqtt(self) -> None:
        """Disconnect the optional MQTT gateway."""
        if self.mqtt_gateway is None:
            return
        self.mqtt_gateway.disconnect()
        self.mqtt_connected = False

    def publish_latest_frame(self) -> None:
        """Publish the latest publishable telemetry frame through MQTT and OPC UA."""
        frame = self._latest_frame_values()
        if not frame:
            return
        if self.mqtt_gateway is not None:
            if not self.mqtt_connected:
                self.connect_mqtt()
            self.mqtt_gateway.publish_frame(frame)
        if self.opcua_gateway is not None:
            self.opcua_gateway.publish_frame(frame)

    def step_once(self) -> list[dict]:
        """Run one simulation step, optionally publish it, and return telemetry."""
        self.latest_snapshot = self.engine.step()
        self.publish_latest_frame()
        return self.latest_telemetry()

    def run_steps(self, n: int) -> list[dict]:
        """Run multiple simulation steps and return the latest publishable telemetry."""
        count = max(0, n)
        for _ in range(count):
            self.step_once()
        if count == 0 and self.latest_snapshot is None:
            self.step_once()
        return self.latest_telemetry()

    def start_loop(self) -> None:
        """Start the background simulation loop in the current event loop."""
        if self.loop_task is not None and not self.loop_task.done():
            self.is_running = True
            return
        self.connect_mqtt()
        self.is_running = True
        self.loop_task = asyncio.create_task(self._run_loop())

    async def stop_loop(self) -> None:
        """Stop the background simulation loop."""
        self.is_running = False
        if self.loop_task is not None and not self.loop_task.done():
            self.loop_task.cancel()
            try:
                await self.loop_task
            except asyncio.CancelledError:
                pass
        self.loop_task = None

    async def _run_loop(self) -> None:
        while self.is_running:
            self.step_once()
            await asyncio.sleep(max(self.engine.dt_s, 0.0))

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
            "status": "running" if self.is_running else "stopped",
            "running": self.is_running,
            "plant_id": self.config.plant.id,
            "plant_name": self.config.plant.name,
            "scenario_id": self.scenario.id if self.scenario else None,
            "initialized": self.engine.initialized,
            "time_s": self.engine.time_manager.now(),
            "dt_s": self.engine.dt_s,
            "telemetry_frames": frame_count,
            "mqtt_enabled": self.mqtt_gateway is not None,
            "mqtt_connected": self.mqtt_connected,
        }

    def _latest_frame_values(self) -> list[SignalValue]:
        if self.latest_snapshot and "telemetry_latest" in self.latest_snapshot:
            frame = self.latest_snapshot["telemetry_latest"]
            if isinstance(frame, list):
                return [
                    signal
                    for signal in frame
                    if isinstance(signal, SignalValue) and signal.category != "internal_truth"
                ]
        if self.engine.assembly is not None:
            return [
                signal
                for signal in self.engine.assembly.telemetry_store.latest()
                if signal.category != "internal_truth"
            ]
        return []


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
