"""SimulationDefinition I/O — YAML loader.

M4-S02: Load SimulationDefinition from YAML with validation.
"""

from __future__ import annotations

import yaml

from virtual_factory.assembly.definition import (
    SimulationDefinition, PrimitiveDef, EdgeDef, ValidationError,
)


def load_definition_from_yaml(path: str) -> SimulationDefinition:
    """Load a SimulationDefinition from a YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return _parse_definition(data)


def load_definition_from_dict(data: dict) -> SimulationDefinition:
    """Load a SimulationDefinition from a dictionary."""
    return _parse_definition(data)


def _parse_definition(data: dict) -> SimulationDefinition:
    model = data.get("model", data)
    prims_data = data.get("primitives", [])
    edges_data = data.get("edges", [])

    primitives = [
        PrimitiveDef(
            id=p["id"],
            type=p["type"],
            label=p.get("label", ""),
            capacity=p.get("capacity"),
            processing_time_s=p.get("processing_time_s", 1.0),
        )
        for p in prims_data
    ]

    edges = [
        EdgeDef(
            from_id=e["from"],
            to=e["to"],
            disposition=e.get("disposition"),
        )
        for e in edges_data
    ]

    return SimulationDefinition(
        model_id=model.get("id", "unknown"),
        model_name=model.get("name", ""),
        primitives=primitives,
        edges=edges,
    )
