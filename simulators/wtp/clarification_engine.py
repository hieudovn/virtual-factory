"""Clarification Engine — Stage 3: Coagulation / Flocculation / Sedimentation.

Formulas from docs/wtp-simulation-model.md Stage 3.
This is the most important stage — determines ~80% of water quality.
"""

from __future__ import annotations

import math
import random
from typing import Any

from .models import clamp, seeded_rng


def compute_stage3_clarification(
    raw_turbidity: float,
    raw_ph: float,
    coag_dose_rate: float,
    ph_pump_flow: float,
    mixer_speed: float,
    flocculator_speed: float,
    raw_algae_index: float = 0.0,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Compute coagulation/flocculation/sedimentation physics.

    Args:
        raw_turbidity: Raw water turbidity (NTU)
        raw_ph: Raw water pH
        coag_dose_rate: Coagulant dose rate (mg/L)
        ph_pump_flow: pH correction pump flow (L/min)
        mixer_speed: Flash mixer speed (RPM)
        flocculator_speed: Flocculator speed (RPM)
        raw_algae_index: Algae index (affects coagulation)
        rng: Random number generator

    Returns:
        dict with settled_turbidity, settled_ph, floc_size_index,
        clarifier_efficiency_index, streaming_current
    """
    rng = rng or seeded_rng()

    # Normalize inputs
    coag_dose_norm = coag_dose_rate / 25.0  # 25 mg/L = optimal
    mixing_norm = mixer_speed / 300.0       # 300 RPM = optimal
    floc_norm = flocculator_speed / 40.0    # 40 RPM = optimal

    # Coagulation efficiency (Jar Test model)
    efficiency_max = 0.85  # max 85% turbidity removal
    turb_factor = min(1.0, 50.0 / max(raw_turbidity, 1.0))  # harder when very turbid
    efficiency = (efficiency_max * coag_dose_norm * mixing_norm * floc_norm * turb_factor)
    efficiency = clamp(efficiency, 0.0, efficiency_max)

    # Settled turbidity
    settled_turbidity = raw_turbidity * (1.0 - efficiency) + rng.gauss(0, 0.3)
    settled_turbidity = max(0.1, settled_turbidity)

    # Settled pH
    settled_ph = (raw_ph
                  - 0.15 * coag_dose_norm          # coagulant lowers pH
                  + 0.05 * (ph_pump_flow / 5.0)    # pH corrector raises pH
                  + rng.gauss(0, 0.02))

    # Floc size index
    floc_size_index = 3.5 * coag_dose_norm * floc_norm + rng.gauss(0, 0.1)
    floc_size_index = max(0.5, floc_size_index)

    # Clarifier efficiency index (1.0 = optimal, < 0.7 = problem)
    clarifier_efficiency = efficiency / efficiency_max if efficiency_max > 0 else 0.0

    # Streaming current (mV)
    streaming_current = -5.0 + 0.3 * (coag_dose_rate - 25.0) + rng.gauss(0, 0.2)

    return {
        "settled_turbidity": round(settled_turbidity, 2),
        "settled_ph": round(settled_ph, 3),
        "floc_size_index": round(floc_size_index, 2),
        "clarifier_efficiency_index": round(clarifier_efficiency, 4),
        "streaming_current": round(streaming_current, 2),
        "_efficiency": efficiency,
    }
