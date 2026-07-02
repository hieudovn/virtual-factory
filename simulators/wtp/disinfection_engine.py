"""Disinfection Engine — Stage 5: Chlorine Disinfection Chemistry.

Formulas from docs/wtp-simulation-model.md Stage 5.
"""

from __future__ import annotations

import random
from typing import Any

from .models import clamp, seeded_rng


def compute_stage5_disinfection(
    chlorine_dose_rate: float,
    raw_ammonia: float,
    raw_algae_index: float,
    contact_time: float,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Compute chlorine disinfection chemistry.

    Chlorine reacts with NH3 to form chloramines (combined chlorine).
    Free chlorine = total chlorine - combined chlorine.

    Args:
        chlorine_dose_rate: Chlorine dose rate (mg/L, from MV2 * 0.375)
        raw_ammonia: Raw water ammonia (mg/L, DV5)
        raw_algae_index: Algae index (DV6)
        contact_time: Contact time (min)
        rng: Random number generator

    Returns:
        dict with free_chlorine, total_chlorine, orp, ct_value, disinfection_ok
    """
    rng = rng or seeded_rng()

    # Chlorine demand from NH3 and organic matter
    cl_demand_nh3 = raw_ammonia * 5.0  # each mg NH3 consumes ~5 mg Cl
    cl_demand_org = raw_algae_index * 0.3  # organic matter demand

    # Total chlorine in system
    total_chlorine = chlorine_dose_rate + rng.gauss(0, 0.05)
    total_chlorine = max(0.0, total_chlorine)

    # Combined chlorine = chloramines
    combined_cl = min(cl_demand_nh3 + cl_demand_org, total_chlorine)

    # Free chlorine residual
    free_chlorine = max(0.0, total_chlorine - combined_cl) + rng.gauss(0, 0.02)
    free_chlorine = max(0.0, free_chlorine)

    # CT value (mg·min/L) — disinfection dose
    ct_value = free_chlorine * contact_time

    # ORP (Oxidation-Reduction Potential)
    orp = 450.0 + 250.0 * (free_chlorine / max(0.8, free_chlorine)) + rng.gauss(0, 5)
    if free_chlorine < 0.01:
        orp = 200.0 + rng.gauss(0, 10)

    # Disinfection OK check
    disinfection_ok = free_chlorine >= 0.5 and ct_value >= 15.0

    return {
        "free_chlorine": round(free_chlorine, 4),
        "total_chlorine": round(total_chlorine, 4),
        "combined_chlorine": round(combined_cl, 4),
        "orp": round(orp, 1),
        "ct_value": round(ct_value, 2),
        "disinfection_ok": bool(disinfection_ok),
        "cl_demand_nh3": round(cl_demand_nh3, 2),
        "cl_demand_org": round(cl_demand_org, 2),
    }
