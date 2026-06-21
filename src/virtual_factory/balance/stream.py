"""Material stream between physical equipment ports.

A ``Stream`` travels along a physical connection and carries flow-rate,
medium, and optional thermal data so downstream code (balance checks,
graph-based solvers) can work with richer objects instead of raw floats.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class Stream:
    """Material stream on a physical connection.

    Attributes
    ----------
    medium_id : str
        Identifier of the flowing medium (e.g. ``"water"``).
    flow_rate_m3_s : float
        Volumetric flow rate in m³/s.
    density_kg_m3 : float
        Density of the medium at current conditions.
    temperature_c : float | None
        Optional temperature in degrees Celsius.
    """

    medium_id: str
    flow_rate_m3_s: float = 0.0
    density_kg_m3: float = 1000.0
    temperature_c: float | None = None

    @property
    def mass_flow_kg_s(self) -> float:
        """Mass flow rate in kg/s."""
        return self.flow_rate_m3_s * self.density_kg_m3
