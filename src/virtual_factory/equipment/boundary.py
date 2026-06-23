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

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.equipment.base_equipment import BaseEquipment

# Air composition defaults
_AIR_MW = 28.97       # kg/kmol
_AIR_K = 1.4           # cp/cv


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
        """Boundary is passive — no internal dynamics.

        Flow is set externally by connected equipment (e.g. compressor).
        Backpressure may be updated by scenarios.
        """
        # No-op: all state changes are driven by connected equipment or scenarios.

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
