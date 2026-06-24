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
from virtual_factory.telemetry.telemetry_frame import build_publishable_frame


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
        self.dt_s = dt_s
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_topic_prefix = mqtt_topic_prefix
        self.mqtt_client_id = mqtt_client_id
        self.mqtt_connect_retries = mqtt_connect_retries
        self.mqtt_connect_delay = mqtt_connect_delay
        self.opcua_endpoint = opcua_endpoint
        self._init_engine()

    def _init_engine(self) -> None:
        self.config = load_plant_config(self.config_path)
        self.scenario: ScenarioConfig | None = load_scenario(self.scenario_path) if self.scenario_path else None
        self.engine = SimulationEngine(self.config, dt_s=self.dt_s, scenario=self.scenario)
        self.latest_snapshot = None
        self.is_running = False
        self.loop_task = None
        self.mqtt_gateway = (
            MqttGateway(
                host=self.mqtt_host,
                port=self.mqtt_port,
                topic_prefix=self.mqtt_topic_prefix,
                client_id=self.mqtt_client_id,
            )
            if self.mqtt_host
            else None
        )
        self.opcua_gateway = (
            OpcUaGateway(endpoint=self.opcua_endpoint) if self.opcua_endpoint else None
        )
        self.mqtt_connected = False

    def reset(self) -> None:
        """Reinitialize the simulation engine to its initial state."""
        if self.is_running:
            self.is_running = False
            if self.loop_task is not None and not self.loop_task.done():
                self.loop_task.cancel()
            self.loop_task = None
        self._init_engine()
        # Build initial telemetry frame at t=0 without stepping / process dynamics
        self.engine.initialize()
        assert self.engine.assembly is not None
        state = self.engine.assembly.state
        ts = 0.0
        for sensor in self.engine.assembly.sensors.values():
            sensor.sample(
                state,
                timestamp_s=ts,
                signal_config=self.config.signals.get(sensor.output_signal),
            )
        for controller in self.engine.assembly.controllers.values():
            controller.execute(
                state,
                timestamp_s=ts,
                signal_config=self.config.signals.get(controller.output_signal),
            )
        for actuator in self.engine.assembly.actuators.values():
            feedback_cfg = (
                self.config.signals.get(actuator.feedback_signal)
                if actuator.feedback_signal
                else None
            )
            actuator.update(state, timestamp_s=ts, feedback_signal_config=feedback_cfg)
        self.engine.assembly.alarm_manager.evaluate(state, self.config, ts)
        telemetry_frame = build_publishable_frame(
            self.config,
            state,
            self.engine.assembly.output_policy,
            timestamp_s=ts,
        )
        self.engine.assembly.telemetry_store.append_frame(telemetry_frame)
        self.latest_snapshot = {"telemetry_latest": telemetry_frame}
        self.state = state

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

    def plant_graph(self) -> dict:
        """Return the plant graph structure for the visual editor.

        Layout rules:
        - Equipment placed in flow order (left to right)
        - Sensors grouped near the equipment they measure
        - Measurement edges drawn between sensor and measured equipment
        """
        if not self.engine.initialized:
            self.engine.initialize()
        if self.engine.assembly is None:
            return {"nodes": [], "edges": []}
        graph = self.engine.assembly.graph

        positions: dict[str, dict] = {}
        equipment_nodes = [n for n in graph.nodes.values() if n.category == "equipment"]
        sensor_nodes = [n for n in graph.nodes.values() if n.category == "sensors"]
        ctrl_nodes = [n for n in graph.nodes.values() if n.category == "controllers"]
        act_nodes = [n for n in graph.nodes.values() if n.category == "actuators"]

        # --- Equipment: flow order (source -> main -> sink) ---
        eq_by_id = {n.id: n for n in equipment_nodes}
        eq_ids = list(eq_by_id.keys())
        ordered_ids = []
        remaining = set(eq_ids)

        for eid in list(remaining):
            node = eq_by_id[eid]
            params = node.config.get("parameters", {})
            if params.get("boundary_type") == "source":
                ordered_ids.append(eid)
                remaining.discard(eid)

        for eid in list(remaining):
            node = eq_by_id[eid]
            params = node.config.get("parameters", {})
            if params.get("source_equipment_id"):
                ordered_ids.append(eid)
                remaining.discard(eid)

        for eid in list(remaining):
            ordered_ids.append(eid)

        num_eq = len(ordered_ids)
        eq_spacing = max(250, 900 // max(num_eq, 1))
        for i, eid in enumerate(ordered_ids):
            positions[eid] = {"x": 60 + i * eq_spacing, "y": 60}

        # --- Sensors: group by measured equipment ---
        # Build a map: equipment_id -> list of sensor nodes
        sensor_by_eq: dict[str, list] = {}
        for sn in sensor_nodes:
            measures = sn.config.get("measures", "")
            eq_id = measures.split(".")[0] if "." in measures else ""
            sensor_by_eq.setdefault(eq_id, []).append(sn)

        # Place sensors in columns near their measured equipment
        for eq_id, sensors in sensor_by_eq.items():
            eq_pos = positions.get(eq_id, {"x": 300, "y": 120})
            base_x = eq_pos["x"] - 40

            # Categorize sensors by their measure suffix
            pressure_sensors = []
            temp_sensors = []
            flow_sensors = []
            vib_sensors = []
            current_sensors = []
            speed_sensors = []
            other_sensors = []

            for sn in sensors:
                measures = sn.config.get("measures", "")
                suffix = measures.split(".")[-1] if "." in measures else measures
                if "pressure" in suffix or "filter_dp" in suffix:
                    pressure_sensors.append(sn)
                elif "temp" in suffix:
                    temp_sensors.append(sn)
                elif "flow" in suffix:
                    flow_sensors.append(sn)
                elif "vib" in suffix or "displacement" in suffix:
                    vib_sensors.append(sn)
                elif "current" in suffix:
                    current_sensors.append(sn)
                elif "speed" in suffix or "rpm" in suffix:
                    speed_sensors.append(sn)
                else:
                    other_sensors.append(sn)

            # Layout in rows by category
            col_w = 140
            row_h = 55

            # Pressure sensors — left column
            for j, sn in enumerate(pressure_sensors):
                positions[sn.id] = {"x": base_x - col_w, "y": 40 + j * row_h}

            # Temperature sensors — right column
            for j, sn in enumerate(temp_sensors):
                positions[sn.id] = {"x": base_x + col_w + 80, "y": 40 + j * row_h}

            # Flow sensors — below equipment
            for j, sn in enumerate(flow_sensors):
                positions[sn.id] = {"x": base_x + j * col_w, "y": 180}

            # Vibration sensors — below flow
            for j, sn in enumerate(vib_sensors):
                positions[sn.id] = {"x": base_x + j * col_w, "y": 250}

            # Current/speed — below vibration
            misc = current_sensors + speed_sensors + other_sensors
            for j, sn in enumerate(misc):
                positions[sn.id] = {"x": base_x + j * col_w, "y": 320}

        # --- Controllers & actuators (if any) ---
        for i, cid in enumerate([n.id for n in ctrl_nodes]):
            positions[cid] = {"x": 320 + i * 140, "y": 420}
        for i, aid in enumerate([n.id for n in act_nodes]):
            positions[aid] = {"x": 460 + i * 140, "y": 490}

        nodes = []
        for node in graph.nodes.values():
            cfg = node.config
            nodes.append({
                "id": node.id,
                "category": node.category,
                "display_name": cfg.get("display_name", node.id),
                "model_type": cfg.get("model_type", ""),
                "position": positions.get(node.id, {"x": 100, "y": 100}),
            })

        edges = []
        for edge in graph.edges:
            edges.append({
                "source": edge.source,
                "target": edge.target,
                "category": edge.category,
            })

        return {"nodes": nodes, "edges": edges}

    def model_types(self) -> list[dict]:
        """Return available model types for the asset palette."""
        from virtual_factory.core.model_registry import ModelRegistry
        registry = ModelRegistry.from_directory()
        result = []
        for model_id, meta in registry.metadata.items():
            result.append({
                "id": model_id,
                "category": meta.get("category", "unknown"),
                "display_name": meta.get("display_name", model_id),
                "description": meta.get("description", ""),
                "icon": meta.get("ui", {}).get("icon", "circle"),
            })
        return result

    def update_pid(self, controller_id: str, params: dict) -> dict:
        """Update PID controller parameters at runtime."""
        if self.engine.assembly is None:
            self.engine.initialize()
        if self.engine.assembly is None:
            return {"status": "error", "message": "Engine not initialized"}
        ctrl = self.engine.assembly.controllers.get(controller_id)
        if ctrl is None:
            return {"status": "error", "message": f"Controller {controller_id} not found"}
        if "kp" in params:
            ctrl.parameters["kp"] = float(params["kp"])
        if "ki" in params:
            ctrl.parameters["ki"] = float(params["ki"])
        if "kd" in params:
            ctrl.parameters["kd"] = float(params["kd"])
        if "setpoint" in params:
            ctrl.setpoint = float(params["setpoint"])
        return {"status": "ok", "controller_id": controller_id, "parameters": {
            "kp": ctrl.parameters.get("kp"),
            "ki": ctrl.parameters.get("ki"),
            "kd": ctrl.parameters.get("kd"),
            "setpoint": getattr(ctrl, "setpoint", None),
        }}

    def inject_fault(self, fault_type: str | None, value: object) -> dict:
        """Inject a fault into the running simulation."""
        if self.engine.assembly is None:
            self.engine.initialize()
        if self.engine.assembly is None:
            return {"status": "error", "message": "Engine not initialized"}
        state = self.engine.assembly.state
        if fault_type == "valve_stuck":
            if value is not None:
                state.diagnostics["fault.valve_stuck.VA101"] = float(value)
                state.diagnostics["fault.valve_stuck.V101"] = float(value)
            else:
                state.diagnostics.pop("fault.valve_stuck.VA101", None)
                state.diagnostics.pop("fault.valve_stuck.V101", None)
        elif fault_type == "pump_degradation":
            if value is not None:
                state.diagnostics["fault.pump_degradation.P101"] = float(value)
            else:
                state.diagnostics.pop("fault.pump_degradation.P101", None)
        elif fault_type == "sensor_bias":
            if value is not None:
                state.diagnostics["sensor_bias.LT102"] = float(value)
            else:
                state.diagnostics.pop("sensor_bias.LT102", None)
        else:
            return {"status": "error", "message": f"Unknown fault type: {fault_type}"}
        return {"status": "ok", "fault_type": fault_type, "value": value}

    def opcua_status(self) -> dict:
        """Return OPC UA gateway status."""
        if self.opcua_gateway is None:
            return {"enabled": False, "endpoint": None}
        return {
            "enabled": self.opcua_gateway.enabled,
            "endpoint": self.opcua_gateway.endpoint,
            "started": self.opcua_gateway._started,
        }

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

    async def reload_config(self, config_path: str) -> dict:
        """Stop the loop, reload the simulation with a new plant config, and reset."""
        await self.stop_loop()
        self.config_path = Path(config_path)
        self._init_engine()
        self.reset()
        return self.status()

    def current_config_info(self) -> dict:
        """Return info about the currently loaded config."""
        import os
        configs_dir = Path("configs/plants")
        available = []
        if configs_dir.exists():
            for f in sorted(configs_dir.glob("*.yaml")):
                available.append({
                    "path": str(f),
                    "name": f.stem,
                })
        return {
            "current": str(self.config_path),
            "plant_id": self.config.plant.id,
            "plant_name": self.config.plant.name,
            "available": available,
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
