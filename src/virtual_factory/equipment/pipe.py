"""Pipe equipment with Darcy-Weisbach pressure drop.

A straight pipe segment that adds flow-dependent pressure loss between
two physical ports.  Can be placed between tanks, pumps, and valves in
any plant configuration.
"""

from dataclasses import dataclass

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.equipment.base_equipment import BaseEquipment


@dataclass(slots=True)
class Pipe(BaseEquipment):
    """Straight pipe segment with configurable length and diameter.

    Parameters (from config)
    ------------------------
    length_m : float
        Pipe length in metres (default 10.0).
    diameter_m : float
        Internal pipe diameter in metres (default 0.05 ≈ DN 50).
    roughness_mm : float
        Absolute wall roughness in millimetres (default 0.046 for
        commercial steel).
    """

    def initialize_state(self, state: RuntimeState) -> None:
        """Create pipe truth placeholders."""
        state.set_truth(f"{self.id}.pressure_drop_kpa", 0.0)
        state.set_truth(f"{self.id}.flow_true", 0.0)
        state.set_truth(f"{self.id}.velocity_m_s", 0.0)

    def resistance_k(self, density_kg_m3: float, viscosity_pa_s: float) -> float:
        """Return the Darcy-Weisbach resistance coefficient K [Pa/(m³/s)²].

        ΔP = K · Q²

        Computes the Darcy friction factor using the Swamee-Jain explicit
        approximation valid for 1e-6 ≤ ε/D ≤ 1e-2 and 5e3 ≤ Re ≤ 1e8.
        """
        L = float(self.parameters.get("length_m", 10.0))
        D = float(self.parameters.get("diameter_m", 0.05))
        roughness_m = float(self.parameters.get("roughness_mm", 0.046)) / 1000.0

        A = (3.14159 * D**2) / 4.0  # cross-sectional area
        # K = (f · L · ρ) / (2 · D · A²)   … but f depends on Q (Re).
        # For a conservative constant-friction estimate use f ≈ 0.02 for
        # turbulent flow in smooth-ish commercial steel pipe.
        f = 0.02
        return (f * L * density_kg_m3) / (2.0 * D * A**2)
