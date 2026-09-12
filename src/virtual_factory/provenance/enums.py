"""Simulation truth-label enums for VF provenance.

These are the frozen simulation-truth vocabulary (PH00 §10 / B6). VF-generated
outputs are ALWAYS ``origin_kind = simulation``; ``data_status`` is ``synthetic``
or ``simulated_ground_truth``; ``fidelity`` uses the frozen profile vocabulary.

These values must never be confused with real plant measurement/ground truth.
"""

from __future__ import annotations

from enum import Enum


class OriginKind(str, Enum):
    """Where the output originates. VF-generated outputs are always simulation."""

    SIMULATION = "simulation"


class DataStatus(str, Enum):
    """How VF-generated output relates to real plant data."""

    SYNTHETIC = "synthetic"
    SIMULATED_GROUND_TRUTH = "simulated_ground_truth"


class Fidelity(str, Enum):
    """Frozen fidelity-profile vocabulary (PH00 §09)."""

    LOGICAL_ONLY = "logical_only"
    SYNTHETIC_REFERENCE = "synthetic_reference"
    FIRST_ORDER = "first_order"
