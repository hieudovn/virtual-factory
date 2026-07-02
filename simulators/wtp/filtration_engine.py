"""Filtration Engine — Stage 4: Multimedia Filtration with Backwash.

Formulas from docs/wtp-simulation-model.md Stage 4.
"""

from __future__ import annotations

import random
from typing import Any

from .models import clamp, seeded_rng


def compute_stage4_filtration(
    settled_turbidity: float,
    settled_ph: float,
    raw_algae_index: float,
    filter_101_effluent_flow: float,
    filter_102_effluent_flow: float,
    filter_101_dp_accum: float,
    filter_102_dp_accum: float,
    backwash_101_remaining: float,
    backwash_102_remaining: float,
    dt_s: float = 1.0,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Compute multimedia filtration physics.

    Filter DP accumulates over time. Backwash triggers at DP > 80 kPa.
    Args are mutable floats (modified in-place via return dict).

    Returns:
        dict with all filter PVs including updated dp_accum and backwash_remaining
    """
    rng = rng or seeded_rng()
    dp_101 = filter_101_dp_accum
    dp_102 = filter_102_dp_accum
    bw_101 = backwash_101_remaining
    bw_102 = backwash_102_remaining

    def _advance_filter(dp: float, bw: float, flow: float) -> tuple[float, float, float, float]:
        """Advance one filter. Returns (dp, bw, dp_rate, filtered_turb, filtered_ph)."""
        if bw > 0:
            # Backwash in progress — DP frozen
            bw_new = max(0.0, bw - dt_s)
            if bw_new <= 0:
                dp = 20.0  # reset after backwash
            return dp, bw_new, 0.0, 0.0, 0.0

        # DP accumulation rate (kPa/s)
        dp_rate = (0.02
                   + 0.01 * (settled_turbidity / 8.0)
                   + 0.01 * (raw_algae_index / 3.0))
        dp += dp_rate * dt_s

        # Check backwash trigger
        if dp > 80.0:
            bw = 300.0  # 5-minute backwash

        # Filter efficiency
        filter_loading = (dp - 20.0) / 60.0
        filter_loading = clamp(filter_loading, 0.0, 1.0)
        filter_efficiency = 0.96 - 0.06 * filter_loading + rng.gauss(0, 0.005)
        filter_efficiency = clamp(filter_efficiency, 0.5, 0.96)

        # Filtered turbidity
        filtered_turbidity = settled_turbidity * (1.0 - filter_efficiency) + rng.gauss(0, 0.02)
        filtered_turbidity = max(0.01, filtered_turbidity)

        # Filtered pH (minimal change)
        filtered_ph = settled_ph + rng.gauss(0, 0.05)

        return dp, bw, dp_rate, filtered_turbidity, filtered_ph

    # Advance filter 101
    dp_101, bw_101, rate_101, ft_101, fp_101 = _advance_filter(
        dp_101, bw_101, filter_101_effluent_flow
    )

    # Advance filter 102
    dp_102, bw_102, rate_102, ft_102, fp_102 = _advance_filter(
        dp_102, bw_102, filter_102_effluent_flow
    )

    # Combined filtered values (blend from both filters)
    total_flow = filter_101_effluent_flow + filter_102_effluent_flow
    if total_flow > 0:
        w1 = filter_101_effluent_flow / total_flow
        w2 = filter_102_effluent_flow / total_flow
        combined_turbidity = ft_101 * w1 + ft_102 * w2
        combined_ph = fp_101 * w1 + fp_102 * w2
    else:
        combined_turbidity = (ft_101 + ft_102) / 2
        combined_ph = (fp_101 + fp_102) / 2

    # Particle count proxy
    particle_count = combined_turbidity * 80 + rng.gauss(0, 5)
    particle_count = max(0, particle_count)

    # Filter run quality index
    filter_load_101 = clamp((dp_101 - 20.0) / 60.0, 0.0, 1.0)
    filter_load_102 = clamp((dp_102 - 20.0) / 60.0, 0.0, 1.0)
    filter_run_quality = 1.0 - (filter_load_101 + filter_load_102) / 2

    # Filter levels
    filter_level_101 = 1.5 - 0.3 * (filter_101_effluent_flow / 200.0)
    filter_level_102 = 1.5 - 0.3 * (filter_102_effluent_flow / 200.0)

    return {
        "filter_101_dp_accum": round(dp_101, 2),
        "filter_102_dp_accum": round(dp_102, 2),
        "backwash_101_remaining": round(bw_101, 1),
        "backwash_102_remaining": round(bw_102, 1),
        "filtered_turbidity": round(combined_turbidity, 4),
        "filtered_ph": round(combined_ph, 3),
        "particle_count_proxy": round(particle_count, 1),
        "filter_run_quality_index": round(filter_run_quality, 4),
        "filter_level_101": round(filter_level_101, 2),
        "filter_level_102": round(filter_level_102, 2),
        "dp_rate_101": round(rate_101, 4),
        "dp_rate_102": round(rate_102, 4),
    }
