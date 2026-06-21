"""Mass balance evaluation for continuous-process simulation.

Computes mass-in, mass-out, delta-stored, residual, and a pass/fail
indicator for each simulation step.  Results are written to
``RuntimeState.diagnostics["mass_balance"]`` and never leak into
industrial telemetry.

The evaluator is **stateful**: it keeps a copy of the previous step's
total system volume between calls.  On the very first call it snapshots
the current volume and reports a ``null`` (empty) result — subsequent
calls compute the true delta.
"""

from dataclasses import dataclass, field

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import PlantConfig, endpoint_object_id

# Default tolerance for residual percentage — anything below this is
# considered perfectly balanced.
_DEFAULT_TOLERANCE_PCT = 0.1


@dataclass(slots=True)
class MassBalance:
    """Mass balance evaluator for a tank-pump-valve-tank path.

    Stores ``_prev_system_volume_m3`` between calls so the volume delta
    is computed correctly even though ``update_continuous_process`` has
    already overwritten the runtime state by the time ``evaluate()`` runs.
    """

    plant_config: PlantConfig
    tolerance_pct: float = _DEFAULT_TOLERANCE_PCT
    _prev_system_volume_m3: float | None = None

    def evaluate(self, state: RuntimeState, dt_s: float) -> dict[str, float | bool | str | None]:
        """Run mass balance and return a diagnostics-safe result dict."""
        density = float(self.plant_config.medium.density_kg_m3)

        src_id = self._infer_source_tank()
        dst_id = self._infer_destination_tank()

        # ── current (post-dynamics) volumes ──
        src_vol_m3 = float(state.get_truth(f"{src_id}.volume_true", 0.0))
        dst_vol_m3 = float(state.get_truth(f"{dst_id}.volume_true", 0.0))
        system_vol_m3 = src_vol_m3 + dst_vol_m3

        # ── flows (prefer streams, fall back to truth) ──
        flow_in_m3s = self._read_flow(state, dst_id, "inflow")
        flow_out_m3s = self._read_flow(state, dst_id, "outflow")

        mass_in_kg = flow_in_m3s * dt_s * density
        mass_out_kg = flow_out_m3s * dt_s * density

        # ── delta stored (requires a prior snapshot) ──
        if self._prev_system_volume_m3 is None:
            # First call: snapshot and return a null result.
            self._prev_system_volume_m3 = system_vol_m3
            return {
                "mass_in_kg": round(mass_in_kg, 9),
                "mass_out_kg": round(mass_out_kg, 9),
                "mass_stored_before_kg": None,
                "mass_stored_after_kg": round(system_vol_m3 * density, 9),
                "mass_stored_delta_kg": None,
                "residual_kg": None,
                "residual_pct": None,
                "balanced": True,
                "message": "Initial snapshot — balance will start next step",
            }

        mass_stored_before = self._prev_system_volume_m3 * density
        mass_stored_after = system_vol_m3 * density
        mass_stored_delta = mass_stored_after - mass_stored_before

        # ── residual ──
        # Conservation: mass leaving the system + change in stored mass = 0
        #   → residual = mass_out_kg + mass_stored_delta
        residual_kg = mass_out_kg + mass_stored_delta

        max_throughput = max(abs(mass_out_kg), abs(mass_stored_delta), 1e-12)
        residual_pct = (residual_kg / max_throughput) * 100.0
        balanced = abs(residual_pct) <= self.tolerance_pct

        # Save for next step
        self._prev_system_volume_m3 = system_vol_m3

        return {
            "mass_in_kg": round(mass_in_kg, 9),
            "mass_out_kg": round(mass_out_kg, 9),
            "mass_stored_before_kg": round(mass_stored_before, 9),
            "mass_stored_after_kg": round(mass_stored_after, 9),
            "mass_stored_delta_kg": round(mass_stored_delta, 9),
            "residual_kg": round(residual_kg, 12),
            "residual_pct": round(residual_pct, 6),
            "balanced": balanced,
            "message": (
                "Mass balanced" if balanced else
                f"Mass imbalance: {residual_kg:.4e} kg ({residual_pct:.4f}%)"
            ),
        }

    # ------------------------------------------------------------------
    # Helpers — re-use the same inference logic as process_dynamics
    # ------------------------------------------------------------------

    def _infer_source_tank(self) -> str | None:
        return self._find_tank("source")

    def _infer_destination_tank(self) -> str | None:
        return self._find_tank("destination")

    def _find_tank(self, role: str) -> str | None:
        tanks = [
            eq.id for eq in self.plant_config.equipment
            if eq.model_type in ("tank_v1",)
        ]
        if len(tanks) >= 2:
            return tanks[0] if role == "source" else tanks[-1]
        return tanks[0] if tanks else None

    def _tank_outlet_demand(self, tank_id: str) -> float:
        for eq in self.plant_config.equipment:
            if eq.id == tank_id:
                if "outlet_demand_m3_s" in eq.parameters:
                    return float(eq.parameters["outlet_demand_m3_s"])
                if "outlet_demand_m3h" in eq.parameters:
                    return float(eq.parameters["outlet_demand_m3h"]) / 3600.0
                return 0.006
        return 0.0

    def _read_flow(self, state: RuntimeState, tank_id: str | None, direction: str) -> float:
        """Read flow from a stream or fall back to truth values."""
        # Try stream first for the last connection into/out of the tank
        if tank_id:
            for conn_id, stream in state.streams.items():
                if direction == "inflow":
                    # Connection C003 goes to T102.inlet → target is tank
                    for conn in self.plant_config.connections:
                        if conn.id == conn_id and endpoint_object_id(conn.to) == tank_id:
                            return stream.flow_rate_m3_s
                else:
                    # Connection from tank → first hop
                    for conn in self.plant_config.connections:
                        if conn.id == conn_id and endpoint_object_id(conn.from_endpoint) == tank_id:
                            return stream.flow_rate_m3_s

        # Fall back to truth
        flow = float(state.get_truth(f"{tank_id}.{direction}_true", 0.0)) if tank_id else 0.0
        if flow == 0.0 and direction == "inflow":
            flow = float(state.get_truth("V101.outlet.flow_true", 0.0))
        if flow == 0.0 and direction == "outflow" and tank_id:
            flow = self._tank_outlet_demand(tank_id)
        return flow
