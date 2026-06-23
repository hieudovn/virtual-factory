"""Boundary Equipment — inlet/outlet boundary conditions.

A boundary equipment acts as a gas source (provides pressure, temperature,
composition, available flow) or gas sink (accepts flow with backpressure).

It is intentionally simple: it does NOT contain internal dynamics. Its
purpose is to provide well-defined inlet/outlet conditions that other
equipment models read through the graph via connections and ports.

Parameters (from config)
------------------------
boundary_type : str
    ``source`` — provides gas at controlled conditions.
    ``sink``   — receives gas, applies backpressure.
pressure_kpa : float
    Source supply pressure or sink backpressure (kPa).
temperature_c : float
    Source temperature (°C).
available_flow_m3_s : float
    Maximum available flow from this source (m³/s).  0 = unlimited.
composition : dict
    Gas composition (mole fractions).  Default: air (N₂ 0.79, O₂ 0.21).

Truth variables
---------------
{id}.pressure_kpa          — current pressure
{id}.temperature_c          — current temperature
{id}.flow_m3_s              — current flow (positive = leaving source / entering sink)
{id}.available_flow_m3_s   — remaining available flow (source only)
{id}.molecular_weight_kg_kmol — gas molecular weight
{id}.specific_heat_ratio    — cp/cv
"""

from dataclasses import dataclass
import math
import random

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.equipment.base_equipment import BaseEquipment

# Air composition defaults
_AIR_MW = 28.97       # kg/kmol
_AIR_K = 1.4           # cp/cv
_SECONDS_PER_HOUR = 3600.0


@dataclass(slots=True)
class BoundaryEquipment(BaseEquipment):
    """Inlet or outlet boundary for gas process equipment."""

    def initialize_state(self, state: RuntimeState) -> None:
        """Set up boundary condition truth variables."""
        bid = self.id
        btype = str(self.parameters.get("boundary_type", "source"))

        p = float(self.parameters.get("pressure_kpa", 101.325))
        t = float(self.parameters.get("temperature_c", 25.0))
        avail = float(self.parameters.get("available_flow_m3_s", 0.0))

        state.set_truth(f"{bid}.pressure_kpa", p)
        state.set_truth(f"{bid}.temperature_c", t)
        state.set_truth(f"{bid}.flow_m3_s", 0.0)

        if btype == "source":
            state.set_truth(f"{bid}.available_flow_m3_s", avail)
        else:
            state.set_truth(f"{bid}.backpressure_kpa", p)

        # Gas properties (from composition or defaults)
        comp = self.parameters.get("composition", {})
        mw = self._compute_molecular_weight(comp)
        k = self._compute_specific_heat_ratio(comp)
        state.set_truth(f"{bid}.molecular_weight_kg_kmol", mw)
        state.set_truth(f"{bid}.specific_heat_ratio", k)

    def process_step(self, state: RuntimeState, dt_s: float) -> None:
        """Evaluate demand profile for sink boundaries.

        For sink boundaries with a ``demand_profile`` parameter, updates
        ``backpressure_kpa`` each tick based on the profile. Source
        boundaries remain passive.
        """
        btype = str(self.parameters.get("boundary_type", "source"))
        if btype != "sink":
            return

        profile = self.parameters.get("demand_profile")
        if not profile or not isinstance(profile, dict):
            return

        ptype = profile.get("type", "constant")
        if ptype == "constant":
            return  # no change needed

        # Get current simulation time from operating hours or truth
        bid = self.id
        base_bp = float(self.parameters.get("pressure_kpa", 101.325))
        base_flow = float(profile.get("base_flow_m3_s", 1.0))
        fluct_pct = float(profile.get("fluctuation_pct", 0.0))

        # Track elapsed time via a truth variable
        elapsed = float(state.get_truth(f"{bid}._elapsed_s", 0.0)) + dt_s
        state.set_truth(f"{bid}._elapsed_s", elapsed)

        factor = 1.0

        if ptype == "step":
            schedule = profile.get("schedule", [])
            for entry in schedule:
                t_s = float(entry.get("at_s", 0))
                f = float(entry.get("factor", 1.0))
                if elapsed >= t_s:
                    factor = f

        elif ptype == "daily_shift":
            schedule = profile.get("schedule", [])
            sim_hour = (elapsed / _SECONDS_PER_HOUR) % 24.0
            # Find the two surrounding schedule points and interpolate
            if schedule:
                sorted_sched = sorted(schedule, key=lambda e: e.get("hour", 0))
                # Wrap-around: find current segment
                prev = sorted_sched[-1]
                for entry in sorted_sched:
                    h = float(entry.get("hour", 0))
                    f = float(entry.get("factor", 1.0))
                    if sim_hour < h:
                        # Interpolate between prev and entry
                        prev_h = float(prev.get("hour", 0))
                        prev_f = float(prev.get("factor", 1.0))
                        if prev_h > h:  # wrap around midnight
                            prev_h -= 24.0
                        seg_len = h - prev_h
                        if seg_len > 0:
                            t = (sim_hour - prev_h) / seg_len
                            factor = prev_f + (f - prev_f) * t
                        else:
                            factor = f
                        break
                    prev = entry
                else:
                    factor = float(sorted_sched[-1].get("factor", 1.0))

        elif ptype == "random":
            factor = 1.0 + random.gauss(0, fluct_pct / 100.0)

        # Apply factor to backpressure
        new_bp = base_bp * factor
        state.set_truth(f"{bid}.backpressure_kpa", round(new_bp, 2))

    # ------------------------------------------------------------------
    # Composition helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_molecular_weight(composition: dict[str, float]) -> float:
        """Compute mixture molecular weight from mole fractions."""
        if not composition:
            return _AIR_MW

        # Common gas MW (kg/kmol)
        MW = {
            "N2": 28.013, "O2": 31.999, "CH4": 16.043, "C2H6": 30.070,
            "C3H8": 44.096, "CO2": 44.010, "H2": 2.016, "H2O": 18.015,
            "H2S": 34.082, "CO": 28.010, "Ar": 39.948,
        }
        mw = sum(MW.get(gas.upper(), _AIR_MW) * frac for gas, frac in composition.items())
        total = sum(composition.values())
        return mw / total if total > 0 else _AIR_MW

    @staticmethod
    def _compute_specific_heat_ratio(composition: dict[str, float]) -> float:
        """Compute mixture cp/cv from mole fractions."""
        if not composition:
            return _AIR_K

        # cp/cv at ~300K
        K = {
            "N2": 1.40, "O2": 1.40, "CH4": 1.31, "C2H6": 1.20,
            "C3H8": 1.13, "CO2": 1.29, "H2": 1.41, "H2O": 1.33,
            "H2S": 1.32, "CO": 1.40, "Ar": 1.67,
        }
        total = sum(composition.values())
        if total <= 0:
            return _AIR_K
        k = sum(K.get(gas.upper(), _AIR_K) * frac for gas, frac in composition.items()) / total
        return round(k, 3)
