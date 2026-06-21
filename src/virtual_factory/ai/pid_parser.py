"""P&ID shorthand parser — convert text diagrams into PlantConfig.

Parses a compact notation like:

    T101[10m3,4m] -> P101[centrifugal,0.012m3/s,18m] -> V101[cv=50] -> T102[8m3,1m,out=0.006]
    LT102: T102.level -> LIC102[PID,kp=1,ki=0.1,sp=2.5] -> VA101 -> V101

Equipment chain (->) creates physical connections.
Control chain (:) creates sensor → controller → actuator → valve links.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from virtual_factory.core.schema import (
    ActuatorConfig,
    AlarmConfig,
    ConnectionConfig,
    ControllerConfig,
    EquipmentConfig,
    MediumConfig,
    OutputPolicyConfig,
    PlantConfig,
    PlantMetadata,
    SensorConfig,
    SignalConfig,
    SignalOutputPolicy,
)


def parse_pid_shorthand(text: str, plant_name: str = "Generated Plant") -> PlantConfig:
    """Parse a P&ID shorthand text into a validated PlantConfig."""
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]

    equipment: list[EquipmentConfig] = []
    connections: list[ConnectionConfig] = []
    sensors: list[SensorConfig] = []
    controllers: list[ControllerConfig] = []
    actuators: list[ActuatorConfig] = []
    signals: dict[str, SignalConfig] = {}
    alarms: list[AlarmConfig] = []
    signals_dict: dict[str, SignalConfig] = {}
    conn_counter = 0
    signal_counter = 0

    for line in lines:
        # Control chain: SensorID: source -> ControllerID[params] -> ActuatorID -> TargetID
        if ":" in line and "->" in line:
            _parse_control_chain(line, sensors, controllers, actuators, signals_dict, equipment)
        # Equipment chain: EqID[params] -> EqID[params] -> ...
        elif "->" in line:
            _parse_equipment_chain(line, equipment, connections, conn_counter)
            conn_counter += 1
        # Standalone sensor
        elif any(kw in line.lower() for kw in ["sensor", "transmitter", "tx"]):
            _parse_sensor_line(line, sensors, signals_dict)

    # Build config
    medium = MediumConfig(
        id="water",
        density_kg_m3=997.0,
        viscosity_pa_s=0.00089,
        specific_heat_j_kg_k=4182.0,
    )

    # Determine output policy from existing signals
    output_policy_signals: dict[str, SignalOutputPolicy] = {}
    for name, sig in signals_dict.items():
        output_policy_signals[name] = SignalOutputPolicy(
            publish=sig.category != "internal_truth",
        )

    config = PlantConfig(
        plant=PlantMetadata(
            id=plant_name.lower().replace(" ", "_"),
            name=plant_name,
            type="continuous_process",
        ),
        medium=medium,
        equipment=equipment,
        connections=connections,
        sensors=sensors,
        controllers=controllers,
        actuators=actuators,
        signals=signals_dict,
        alarms=alarms,
        output_policy=OutputPolicyConfig(signals=output_policy_signals),
    )
    return config


def _parse_equipment_chain(line: str, equipment: list, connections: list, conn_counter: int) -> None:
    """Parse T101[params] -> P101[params] -> ..."""
    parts = re.split(r"\s*->\s*", line)
    prev_id = None
    for part in parts:
        part = part.strip()
        eq = _parse_equipment_part(part)
        if eq and not any(e.id == eq.id for e in equipment):
            equipment.append(eq)
        if eq and prev_id:
            conn_counter += 1
            connections.append(ConnectionConfig(
                id=f"C{conn_counter:03d}",
                from_endpoint=f"{prev_id}.outlet",
                to=f"{eq.id}.inlet",
                connection_type="physical",
                medium="water",
            ))
        if eq:
            prev_id = eq.id


def _parse_equipment_part(part: str) -> EquipmentConfig | None:
    """Parse 'T101[10m3,4m]' into EquipmentConfig."""
    m = re.match(r"(\w+)\[([^\]]*)\]", part)
    if not m:
        m = re.match(r"(\w+)", part)
        if m:
            return EquipmentConfig(id=m.group(1), model_type=_infer_type(m.group(1)), parameters={})
        return None
    eid = m.group(1)
    params_str = m.group(2)
    params = {}
    for token in params_str.split(","):
        token = token.strip()
        if not token:
            continue
        if "=" in token:
            k, v = token.split("=", 1)
            params[k.strip()] = _parse_param_value(v.strip())
        elif "m3" in token:
            params["capacity_m3"] = float(token.replace("m3", ""))
        elif "m" in token:
            params["initial_level_m"] = float(token.replace("m", ""))
            params["max_level_m"] = float(token.replace("m", "")) * 1.25
        elif "out=" in token:
            params["outlet_demand_m3_s"] = float(token.replace("out=", ""))
        elif "kW" in token:
            params["rated_power_kw"] = float(token.replace("kW", ""))
        else:
            try:
                params["cv"] = float(token)
            except ValueError:
                params["rated_flow_m3_s"] = float(token)
    return EquipmentConfig(id=eid, model_type=_infer_type(eid), parameters=params)


def _parse_control_chain(line: str, sensors: list, controllers: list, actuators: list,
                         signals: dict, equipment: list) -> None:
    """Parse 'LT102: T102.level -> LIC102[PID,kp=1,ki=0.1] -> VA101 -> V101'"""
    # Split into sensor definition and chain
    sensor_part, chain = line.split(":", 1)
    sensor_part = sensor_part.strip()
    chain = chain.strip()

    # Parse sensor
    m = re.match(r"(\w+)", sensor_part)
    if not m:
        return
    sensor_id = m.group(1)
    sensor_model = "level_transmitter_v1"
    if "FT" in sensor_id or "flow" in sensor_part.lower():
        sensor_model = "flow_transmitter_v1"
    elif "PT" in sensor_id or "press" in sensor_part.lower():
        sensor_model = "pressure_transmitter_v1"

    # Determine measures path
    measures_path = None
    chain_parts = re.split(r"\s*->\s*", chain)
    if chain_parts and "." not in chain_parts[0]:
        # First part is the measured variable if it contains a dot
        pass
    for tok in chain_parts:
        if "." in tok:
            measures_path = tok
            chain_parts.remove(tok)
            break

    if not measures_path:
        # Infer from sensor type
        for eq in equipment:
            if eq.model_type == "tank_v1":
                if sensor_model == "level_transmitter_v1":
                    measures_path = f"{eq.id}.level_true"
                break

    output_signal = f"{sensor_id}_{sensor_id.replace('L','L').replace('F','F').replace('P','P')}"
    output_signal = f"{sensor_id}_VALUE"
    signals[output_signal] = SignalConfig(
        category="industrial_signal", publish=True, unit="m", source=sensor_id,
    )

    sensors.append(SensorConfig(
        id=sensor_id,
        model_type=sensor_model,
        measures=measures_path or "unknown.truth",
        output_signal=output_signal,
        parameters={"sample_time_s": 1.0, "resolution": 0.01, "quality": "GOOD"},
    ))

    # Parse remaining chain: Controller[params] -> Actuator -> Target
    for i, part in enumerate(chain_parts):
        part = part.strip()
        if not part:
            continue
        cm = re.match(r"(\w+)\[([^\]]*)\]", part)
        cm_id = cm.group(1) if cm else part
        cm_params_str = cm.group(2) if cm else ""

        if i == 0:
            # Controller
            params = {}
            if cm_params_str:
                for tok in cm_params_str.split(","):
                    if "=" in tok:
                        k, v = tok.split("=", 1)
                        params[k.strip()] = _parse_param_value(v.strip())
            ctrl_output = f"{cm_id}_OUT"
            signals[ctrl_output] = SignalConfig(
                category="controller_signal", publish=True, unit="percent", source=cm_id,
            )
            controllers.append(ControllerConfig(
                id=cm_id,
                model_type="pid_controller_v1",
                pv_signal=output_signal,
                setpoint=float(params.pop("sp", 2.5)),
                output_signal=ctrl_output,
                scan_time_s=0.5,
                parameters=params,
            ))
        elif i == 1:
            # Actuator
            fb_signal = f"{cm_id}_FEEDBACK"
            signals[fb_signal] = SignalConfig(
                category="actuator_feedback", publish=True, unit="percent", source=cm_id,
            )
            actuators.append(ActuatorConfig(
                id=cm_id,
                model_type="valve_actuator_v1",
                command_signal=ctrl_output,
                feedback_signal=fb_signal,
                actuates=f"{chain_parts[2] if len(chain_parts) > 2 else 'unknown'}.opening_actual",
                parameters={"max_rate": 20.0},
            ))
        # Target (last part) is just a reference, already handled


def _parse_sensor_line(line: str, sensors: list, signals: dict) -> None:
    """Parse standalone sensor line."""
    m = re.match(r"(\w+)", line)
    if not m:
        return
    sid = m.group(1)
    s_model = "level_transmitter_v1"
    if "flow" in line.lower():
        s_model = "flow_transmitter_v1"
    elif "press" in line.lower():
        s_model = "pressure_transmitter_v1"
    sig_name = f"{sid}_VALUE"
    signals[sig_name] = SignalConfig(
        category="industrial_signal", publish=True, unit="raw", source=sid,
    )
    sensors.append(SensorConfig(
        id=sid, model_type=s_model, measures="", output_signal=sig_name,
        parameters={"sample_time_s": 1.0, "quality": "GOOD"},
    ))


def _infer_type(eid: str) -> str:
    """Infer model type from equipment ID prefix."""
    prefix = eid[0].upper()
    if prefix == "T":
        return "tank_v1"
    elif prefix == "P":
        return "centrifugal_pump_v1"
    elif prefix == "V":
        return "control_valve_v1"
    elif prefix == "H":
        return "heat_exchanger_v1"
    elif prefix == "F":
        return "fan_v1"
    elif prefix == "C":
        return "compressor_v1"
    elif prefix == "S":
        return "separator_v1"
    return "pipe_v1"


def _parse_param_value(value: str) -> float | str:
    try:
        return float(value)
    except ValueError:
        return value


def parse_and_save(text: str, output_path: str | Path) -> Path:
    """Parse P&ID shorthand and save to YAML file."""
    config = parse_pid_shorthand(text)
    path = Path(output_path)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config.model_dump(mode="json"), f, default_flow_style=False, allow_unicode=True)
    return path
