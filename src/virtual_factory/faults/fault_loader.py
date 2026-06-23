"""Fault library YAML loader and configuration helpers."""

from pathlib import Path
from typing import Any

import yaml

from virtual_factory.faults.fault_models import (
    FaultConfig,
    FaultLibrary,
    FaultSymptom,
    MaintenanceAction,
    RecoveryProfile,
)


def load_fault_library(path: str | Path) -> FaultLibrary:
    """Load a fault library from a YAML file.

    The YAML file should have a top-level ``faults`` key containing
    a list of fault definitions.

    Example YAML structure::

        faults:
          - fault_id: bearing_wear
            category: compressor
            display_name: Bearing Wear
            severity_curve: exponential
            growth_rate: 0.0005
            symptoms:
              - variable: "{id}.vibration_de_mm_s"
                effect_type: additive
                magnitude: 8.0
            maintenance_actions:
              - action_id: bearing_replace
                action_type: replace
                duration_s: 28800
                recovery:
                  method: instant
                  residual_severity: 0.0
    """
    with open(path, "r") as f:
        data = yaml.safe_load(f)

    if not data or "faults" not in data:
        raise ValueError(f"No 'faults' key found in {path}")

    faults: list[FaultConfig] = []
    for item in data["faults"]:
        faults.append(_parse_fault(item))

    return FaultLibrary(faults)


def load_fault_libraries(paths: list[str | Path]) -> FaultLibrary:
    """Load and merge multiple fault library YAML files."""
    library = FaultLibrary()
    for path in paths:
        lib = load_fault_library(path)
        for fault in lib.list_all():
            library.register(fault)
    return library


def _parse_fault(item: dict[str, Any]) -> FaultConfig:
    """Parse a single fault definition dict into a FaultConfig."""
    symptoms = []
    for s in item.get("symptoms", []):
        symptoms.append(FaultSymptom(
            variable=s["variable"],
            effect_type=s.get("effect_type", "additive"),
            magnitude=float(s.get("magnitude", 1.0)),
            noise_std=float(s.get("noise_std", 0.0)),
            delay_s=float(s.get("delay_s", 0.0)),
        ))

    actions = []
    for a in item.get("maintenance_actions", []):
        recovery_raw = a.get("recovery", {})
        recovery = RecoveryProfile(
            method=recovery_raw.get("method", "instant"),
            duration_s=float(recovery_raw.get("duration_s", 0.0)),
            residual_severity=float(recovery_raw.get("residual_severity", 0.0)),
        )
        actions.append(MaintenanceAction(
            action_id=a["action_id"],
            action_type=a.get("action_type", "repair"),
            duration_s=float(a.get("duration_s", 3600.0)),
            recovery=recovery,
            description=a.get("description", ""),
        ))

    return FaultConfig(
        fault_id=item["fault_id"],
        category=item.get("category", "generic"),
        display_name=item.get("display_name", item["fault_id"]),
        severity_curve=item.get("severity_curve", "linear"),
        growth_rate=float(item.get("growth_rate", 0.001)),
        symptoms=symptoms,
        alarm_delay_s=float(item.get("alarm_delay_s", 0.0)),
        maintenance_actions=actions,
        description=item.get("description", ""),
        tags=item.get("tags", []),
    )


def build_default_fault_library() -> FaultLibrary:
    """Build the default fault library from bundled YAML files."""
    config_dir = Path(__file__).parent.parent.parent.parent / "configs" / "faults"
    paths = list(config_dir.glob("*.yaml"))
    if not paths:
        return FaultLibrary()
    return load_fault_libraries(paths)
