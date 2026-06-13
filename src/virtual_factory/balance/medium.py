"""Process medium definitions."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Medium:
    """Physical medium metadata used by future balance calculations."""

    id: str
    density_kg_m3: float
    viscosity_pa_s: float
    specific_heat_j_kg_k: float
