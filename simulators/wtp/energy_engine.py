"""Energy Engine — Stage 8: Pump power curves, total power, specific energy.

Formulas from docs/wtp-simulation-model.md Stage 7 (pump power) + Stage 8 (energy KPIs).
"""

from __future__ import annotations

import random
from typing import Any

from .models import clamp, seeded_rng


def compute_energy(
    rwp101_flow: float,
    rwp102_flow: float,
    hsp101_flow: float,
    hsp102_flow: float,
    manifold_pressure: float,
    outlet_pressure: float,
    total_flow_outlet: float,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Compute pump power curves and total energy.

    Args:
        rwp101_flow: RWP-101 actual flow (m³/h)
        rwp102_flow: RWP-102 actual flow (m³/h)
        hsp101_flow: HSP-101 actual flow (m³/h)
        hsp102_flow: HSP-102 actual flow (m³/h)
        manifold_pressure: Raw water manifold pressure (kPa)
        outlet_pressure: Outlet discharge pressure (kPa)
        total_flow_outlet: Total outlet flow (m³/h)
        rng: Random number generator

    Returns:
        dict with individual motor powers, total_power, specific_energy consumption
    """
    rng = rng or seeded_rng()

    # RWP motor power (kW)
    rwp101_power = 45.0 * (rwp101_flow / max(450.0, rwp101_flow)) * (manifold_pressure / 250.0)
    rwp101_power += rng.gauss(0, 1)
    rwp101_power = max(0, rwp101_power)

    rwp102_power = 45.0 * (rwp102_flow / max(450.0, rwp102_flow)) * (manifold_pressure / 250.0)
    rwp102_power += rng.gauss(0, 1)
    rwp102_power = max(0, rwp102_power)

    # HSP motor power (kW)
    hsp101_power = 110.0 * (hsp101_flow / max(320.0, hsp101_flow)) * (outlet_pressure / 380.0)
    hsp101_power += rng.gauss(0, 1)
    hsp101_power = max(0, hsp101_power)

    hsp102_power = 110.0 * (hsp102_flow / max(320.0, hsp102_flow)) * (outlet_pressure / 380.0)
    hsp102_power += rng.gauss(0, 1)
    hsp102_power = max(0, hsp102_power)

    # Auxiliary load
    aux_power = 50.0

    # Total active power
    total_power = rwp101_power + rwp102_power + hsp101_power + hsp102_power + aux_power

    # Specific energy consumption (kWh/m³)
    spec_energy = total_power / max(0.1, total_flow_outlet)

    return {
        "rwp101_power": round(rwp101_power, 2),
        "rwp102_power": round(rwp102_power, 2),
        "hsp101_power": round(hsp101_power, 2),
        "hsp102_power": round(hsp102_power, 2),
        "total_active_power": round(total_power, 2),
        "specific_energy_consumption": round(spec_energy, 4),
        "aux_power": aux_power,
    }
