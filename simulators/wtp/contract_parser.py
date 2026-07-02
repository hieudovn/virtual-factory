"""Contract parser for the WTP Simulator.

Reads the PlantOS Integration Contract (wtp-demo-01.contract.yaml)
and extracts all 92 signal definitions, behaviors, scenarios, and OPC UA bindings.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def parse_contract(contract_path: str | Path) -> dict[str, Any]:
    """Parse the PlantOS Integration Contract YAML and return structured data.

    Returns:
        dict with keys: plant, areas, assets, signals, behaviors, scenarios, opcua_bindings
    """
    path = Path(contract_path)
    if not path.exists():
        raise FileNotFoundError(f"Contract file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    result: dict[str, Any] = {}
    result["plant"] = data.get("plant", {})
    result["areas"] = data.get("areas", [])
    result["assets"] = data.get("assets", [])
    result["signals"] = data.get("signals", [])

    # Extract behaviors from simulation.behaviors
    sim = data.get("simulation", {})
    result["behaviors"] = sim.get("behaviors", {})

    # Extract scenarios from extensions.monitoring.scenarios
    extensions = data.get("extensions", {})
    monitoring = extensions.get("monitoring", {})
    result["scenarios"] = monitoring.get("scenarios", [])

    # OPC UA bindings
    result["opcua_bindings"] = data.get("opcua_bindings", [])

    return result


def get_signal_by_id(signals: list[dict], signal_id: str) -> dict | None:
    """Find a signal definition by its signal_id."""
    for s in signals:
        if s.get("signal_id") == signal_id:
            return s
    return None
