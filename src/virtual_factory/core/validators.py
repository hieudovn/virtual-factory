"""Validation for plant and model configuration with structured reports."""

from typing import Any

from virtual_factory.core.schema import INDUSTRIAL_PUBLISH_CATEGORIES, PlantConfig, endpoint_object_id


def validate_required_keys(config: dict[str, Any], required_keys: list[str]) -> list[str]:
    """Return missing top-level keys without enforcing a full schema yet."""
    return [key for key in required_keys if key not in config]


def validate_plant_config_shape(config: dict[str, Any]) -> list[str]:
    """Perform minimal shape checks for early configuration feedback."""
    return validate_required_keys(config, ["plant", "medium", "equipment", "connections", "signals", "output_policy"])


def validate_with_report(config: PlantConfig) -> dict:
    """Validate an already-loaded PlantConfig and return a structured report.

    Returns
    -------
    dict with keys: valid (bool), errors (list), warnings (list),
    graph_checks (dict), policy_checks (dict).
    """
    errors: list[str] = []
    warnings: list[str] = []
    graph_checks: dict[str, Any] = {}
    policy_checks: dict[str, Any] = {}

    # --- Equipment ID uniqueness ---
    ids = [e.id for e in config.equipment]
    sensor_ids = [s.id for s in config.sensors]
    controller_ids = [c.id for c in config.controllers]
    actuator_ids = [a.id for a in config.actuators]
    all_ids = ids + sensor_ids + controller_ids + actuator_ids
    dupes = {i for i in all_ids if all_ids.count(i) > 1}
    if dupes:
        errors.append(f"Duplicate IDs across equipment/sensors/controllers/actuators: {sorted(dupes)}")

    # --- Graph connectivity ---
    connected_ids: set[str] = set()
    for conn in config.connections:
        src = endpoint_object_id(conn.from_endpoint)
        tgt = endpoint_object_id(conn.to)
        connected_ids.add(src)
        connected_ids.add(tgt)
    missing_from_graph = [eid for eid in ids if eid not in connected_ids]
    if missing_from_graph:
        warnings.append(f"Equipment with no connections: {missing_from_graph}")
    graph_checks["equipment_total"] = len(ids)
    graph_checks["equipment_connected"] = len(ids) - len(missing_from_graph)

    # --- Sensor measures: must reference an existing equipment truth path ---
    for sensor in config.sensors:
        if sensor.measures:
            obj_id = endpoint_object_id(sensor.measures)
            if obj_id not in ids:
                warnings.append(f"Sensor '{sensor.id}' measures '{sensor.measures}' but equipment '{obj_id}' not found")

    # --- Controller PV signal must reference a valid signal ---
    for ctrl in config.controllers:
        if ctrl.pv_signal and ctrl.pv_signal not in config.signals:
            errors.append(f"Controller '{ctrl.id}' PV signal '{ctrl.pv_signal}' not defined in signals")
        if ctrl.pv_signal:
            sig = config.signals.get(ctrl.pv_signal)
            if sig and sig.category not in ("industrial_signal", "controller_signal"):
                warnings.append(f"Controller '{ctrl.id}' PV signal '{ctrl.pv_signal}' category should be industrial_signal or controller_signal, got {sig.category}")

    # --- Output policy: no internal_truth in publishable categories ---
    for sig_name, sig_config in config.signals.items():
        if sig_config.category == "internal_truth" and sig_config.publish:
            errors.append(f"Signal '{sig_name}' is internal_truth but marked publish=True")
        if sig_config.category in INDUSTRIAL_PUBLISH_CATEGORIES and "truth" in sig_config.source:
            warnings.append(f"Signal '{sig_name}' category '{sig_config.category}' has suspicious source '{sig_config.source}'")
    policy_checks["signals_total"] = len(config.signals)
    policy_checks["signals_publishable"] = sum(1 for s in config.signals.values() if s.publish)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "graph_checks": graph_checks,
        "policy_checks": policy_checks,
    }

