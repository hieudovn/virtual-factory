"""Energy balance evaluation for thermal simulation steps.

Computes thermal energy in/out, delta-stored, residual, and a pass/fail
indicator for each step.  Results are written to
``RuntimeState.diagnostics["energy_balance"]`` and never leak into
industrial telemetry.

The evaluator is **stateful**: it keeps a copy of the previous step's
total system thermal energy between calls.  On the very first call it
snapshots the current energy and returns a ``null`` result — subsequent
calls compute the true delta.
"""

from dataclasses import dataclass, field

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import PlantConfig, endpoint_object_id

_DEFAULT_TOLERANCE_PCT = 0.1
_DEFAULT_SPECIFIC_HEAT = 4182.0  # J/(kg·K) — water


@dataclass(slots=True)
class EnergyBalance:
    """Thermal energy balance evaluator.

    Tracks total system energy (sensible heat in tanks + heat exchanger)
    between simulation steps and reports the residual.
    """

    plant_config: PlantConfig
    tolerance_pct: float = _DEFAULT_TOLERANCE_PCT
    _prev_energy_j: float | None = None

    def evaluate(self, state: RuntimeState, dt_s: float) -> dict[str, float | bool | str | None]:
        """Run energy balance and return a diagnostics-safe result dict."""
        density = float(self.plant_config.medium.density_kg_m3)
        cp = float(getattr(self.plant_config.medium, "specific_heat_j_kg_k", _DEFAULT_SPECIFIC_HEAT))

        total_energy_j = 0.0
        heat_added_j = 0.0
        heat_removed_j = 0.0
        details: dict[str, float] = {}

        # --- Sum thermal energy in all tanks ---
        for equip in self.plant_config.equipment:
            if equip.model_type not in ("tank_v1",):
                continue
            eid = equip.id
            volume = float(state.get_truth(f"{eid}.volume_true", 0.0))
            mass = volume * density
            # Use a reference temp of 20 °C as baseline
            temp_c = float(equip.parameters.get("initial_temp_c", 20.0))
            energy_j = mass * cp * (temp_c - 20.0)
            total_energy_j += energy_j
            details[f"{eid}.energy_j"] = energy_j

        # --- Sum thermal energy in heat exchangers ---
        for equip in self.plant_config.equipment:
            if equip.model_type not in ("heat_exchanger_v1",):
                continue
            eid = equip.id
            # Heat transfer from the process dynamics
            q_kw = float(state.get_truth(f"{eid}.heat_transfer_kw", 0.0))
            heat_added_j += q_kw * 1000.0 * dt_s
            details[f"{eid}.heat_transfer_j"] = q_kw * 1000.0 * dt_s

        # --- Energy removed via outlet demands ---
        for equip in self.plant_config.equipment:
            if equip.model_type not in ("tank_v1",):
                continue
            outflow = float(state.get_truth(f"{equip.id}.outflow_true", 0.0))
            if outflow > 0:
                mass_out = outflow * density * dt_s
                temp_c = float(equip.parameters.get("initial_temp_c", 20.0))
                heat_removed_j += mass_out * cp * (temp_c - 20.0)
                details[f"{equip.id}.outflow_energy_j"] = mass_out * cp * (temp_c - 20.0)

        # --- Delta from previous step ---
        if self._prev_energy_j is not None:
            delta_energy_j = total_energy_j - self._prev_energy_j
            net_energy_j = heat_added_j - heat_removed_j
            residual_j = delta_energy_j - net_energy_j
            abs_max = max(abs(delta_energy_j), abs(net_energy_j), 1.0)
            residual_pct = (abs(residual_j) / abs_max) * 100.0
            balanced = residual_pct <= self.tolerance_pct
        else:
            delta_energy_j = 0.0
            residual_j = 0.0
            residual_pct = 0.0
            balanced = True  # first call — nothing to compare

        self._prev_energy_j = total_energy_j

        return {
            "total_energy_j": total_energy_j,
            "heat_added_j": heat_added_j,
            "heat_removed_j": heat_removed_j,
            "delta_energy_j": delta_energy_j,
            "residual_j": residual_j,
            "residual_pct": round(residual_pct, 4),
            "balanced": balanced,
            "details": details,
        }
