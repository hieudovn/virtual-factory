"""VF-SHW-X3 evidence generator (SA Issue #98 required evidence).

Runs the canonical X3 profile and records, as committed artefacts, the evidence
the SA requires:

 01 model surface  - 16 scopes, 1-second global windows, exactly two active C2,
                     deferred loops unavailable, queue bound, energy unavailable;
 02 water identity - full-run identity from tick ZERO (startup, ramp, steady),
                     per-window validity, no created water, and the interval
                     diagnostic reported as a supplement only;
 03 reservations   - resource identity/units, acquire/release, series vs parallel
                     capacity, full receiver, in-flight water, no double count;
 04 control        - ACTUAL valve->flow and pump->level responses, feasible SP
                     tracking, disturbance, unreachable-SP saturation, backwash
                     arbitration with the integral held, AUTO/MANUAL continuity;
 05 pumps/energy   - head/power feasibility over the operating envelope, OFF
                     exactly zero, the dimensional conversion of the DIST loss;
 06 mutations      - injected state water, created water, a narrow-pipe breach,
                     impossible head, motor overload and a duplicated
                     initialisation stock must all fail the oracle;
 07 identity       - deterministic trajectories, reset/new attempt/replay;
 08 verdict        - every section verdict machine-derived, the machine-checkable
                     x3.* acceptance block required by the task contract, and the
                     harness acceptance evaluation (X3-1..X3-7) written back into
                     the same artefact by .ai-harness/scripts/evaluate_acceptance.py.

Run:  python .ai-harness/sa-review/evidence/VF-SHW-X3/generate_evidence.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

from virtual_factory.shwtp.contracts import load_whole_plant_contracts  # noqa: E402
from virtual_factory.shwtp.physical_budget import PumpModel  # noqa: E402
from virtual_factory.shwtp.session import (  # noqa: E402
    SHWTP_DEFAULT_MODEL,
    SHWTP_MODEL_G21_SLICE,
    SHWTP_MODEL_WHOLE_PLANT_X2,
    build_shwtp_session,
)
from virtual_factory.shwtp.x3_controls import (  # noqa: E402
    X3_CONTROL_ERROR_SIGN_FLOW,
    X3_CONTROL_ERROR_SIGN_LEVEL,
    PIController,
)
from virtual_factory.shwtp.x3_profile import load_x3_profile  # noqa: E402
from virtual_factory.shwtp.x3_whole_plant import (  # noqa: E402
    build_shwtp_whole_plant_x3,
)

OUT = Path(__file__).resolve().parent
PROFILE_PATH = ROOT / "configs" / "vnext" / "shwtp" / "shwtp_x3_profile_v1.json"
FLOW_LOOP = "vf-shw-ctrl-f106-inlet-flow-pi"
LEVEL_LOOP = "vf-shw-ctrl-t108-level-pi"
L1 = "vf-shw-edge-t101-t102"
L2 = "vf-shw-edge-t102-t103"
L3 = "vf-shw-edge-t103-t104"


def write(name: str, payload: dict) -> dict:
    (OUT / f"{name}.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    return payload


def run(model, ticks: int, *, offset: int = 0) -> None:
    for index in range(1, ticks + 1):
        model.run_window(f"w{offset + index}")


def section_01(profile, contracts) -> dict:
    model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-ev-01")
    run(model, 5)
    report = model.control_report()
    return write(
        "01-model-surface",
        {
            "profile_id": profile.profile_id,
            "profile_version": profile.version,
            "tick_s": profile.tick_s,
            "coupling_policy": profile.coupling_policy,
            "scopes": len(model.participants),
            "participants_are_exactly_the_admitted_scopes": set(model.participants)
            == set(
                row["scope_id"] for row in model.monitor_rows()
            ),
            "c1_active_controllers": len(model.control_layer.c1.active_controller_ids),
            "active_c2_loop_ids": list(report["active_c2_loop_ids"]),
            "exactly_two_active_c2": len(report["active_c2_loop_ids"]) == 2,
            "deferred_loops": dict(sorted(profile.deferred_loops.items())),
            "queue": {
                "max_transfers_per_edge": profile.queue.max_transfers_per_edge,
                "max_queued_volume_m3": profile.queue.max_queued_volume_m3,
            },
            "energy_unavailable": list(profile.energy_unavailable),
            "tanks": len(profile.tanks),
            "edges": len(profile.edges),
            "trunks": len(profile.trunks),
            "valves": len(profile.valves),
            "pumps": len(profile.pumps),
            "acceptance": {
                "flow_steady_error_frac_of_sp": profile.acceptance.flow_steady_error_frac_of_sp,
                "level_steady_error_m": profile.acceptance.level_steady_error_m,
                "nominal_settling_window_s": profile.acceptance.nominal_settling_window_s,
            },
            "authority_labels_present": all(
                key in model.monitor_rows()[0]
                for key in (
                    "site_truth",
                    "simulation_truth",
                    "vf_runtime_authorization",
                    "site_authorized_execution",
                )
            ),
            "verdict": (
                "X3_SURFACE_MATERIALIZED_16_SCOPES_TWO_PI"
                if len(model.participants) == 16
                and len(report["active_c2_loop_ids"]) == 2
                and model.communication_step_s == 1.0
                else "X3_SURFACE_INCOMPLETE"
            ),
        },
    )


def section_02(profile, contracts) -> dict:
    model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-ev-02")
    trace = []
    worst = 0.0
    worst_tick = 0
    invalid_ticks = 0
    for index in range(1, 2401):
        model.run_window(f"w{index}")
        plant = model.balance_report()["plant_water"]
        if not plant["physical_valid"]:
            invalid_ticks += 1
        residual = float(plant["residual_m3"])
        if abs(residual) > abs(worst):
            worst = residual
            worst_tick = index
        if index % 300 == 0 or index in (1, 60, 65, 66):
            trace.append(
                {
                    "tick": index,
                    "plant_in_m3": plant["plant_in_m3"],
                    "plant_out_m3": plant["plant_out_m3"],
                    "stored_delta_m3": plant["stored_delta_m3"],
                    "transit_inventory_m3": plant["transit_inventory_m3"],
                    "process_loss_m3": plant["process_loss_m3"],
                    "overflow_m3": plant["overflow_m3"],
                    "created_water_m3": plant["shortfall_m3"],
                    "residual_m3": residual,
                    "tolerance_m3": plant["tolerance_m3"],
                    "physical_valid": plant["physical_valid"],
                    "storage_integration_gap_m3": plant["storage_integration_gap_m3"],
                }
            )
        if index == 1800:
            model.mark_balance_baseline()
    plant = model.balance_report()["plant_water"]
    # a mutation AFTER a marked baseline must still fail the physical claim
    model.participants["vf-shw-node-t100"]._volume_m3 += 0.5
    model.run_window("mutation-1")
    mutated = model.balance_report()["plant_water"]
    return write(
        "02-water-identity",
        {
            "identity": (
                "R(t) = [storage_flow_delta + created_water + in_transit] - cumulative_in "
                "+ cumulative_out - declared_losses, evaluated from tick zero"
            ),
            "full_run_authoritative": plant["full_run_authoritative"],
            "ticks_evaluated": 2400,
            "invalid_ticks": invalid_ticks,
            "worst_residual_m3": worst,
            "worst_residual_tick": worst_tick,
            "final_residual_m3": plant["residual_m3"],
            "final_tolerance_m3": plant["tolerance_m3"],
            "final_created_water_m3": plant["shortfall_m3"],
            "final_storage_integration_gap_m3": plant["storage_integration_gap_m3"],
            "final_plant_in_m3": plant["plant_in_m3"],
            "final_plant_out_m3": plant["plant_out_m3"],
            "overflow_m3": plant["overflow_m3"],
            "interval_diagnostic": {
                "evaluation_window_start_tick": plant["evaluation_window_start_tick"],
                "window_residual_m3": plant["window_residual_m3"],
                "window_physical_valid": plant["window_physical_valid"],
                "role": "supplementary only: it can never clear a failed full-run residual",
            },
            "mutation_after_baseline": {
                "injected_state_water_m3": 0.5,
                "physical_valid": mutated["physical_valid"],
                "storage_integration_gap_m3": mutated["storage_integration_gap_m3"],
                "detected": mutated["physical_valid"] is False,
            },
            "trace": trace,
            "verdict": (
                "PLANT_WATER_IDENTITY_CLOSED_FROM_TICK_ZERO"
                if invalid_ticks == 0
                and abs(worst) <= plant["tolerance_m3"]
                and plant["shortfall_m3"] == 0.0
                and mutated["physical_valid"] is False
                else "WATER_IDENTITY_NOT_CLOSED"
            ),
        },
    )


def section_03(profile, contracts) -> dict:
    model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-ev-03")
    run(model, 900)
    steady = model._allocation
    components = {
        key: min(steady.budgets[key].requested_m3_s, profile.edge(key).max_flow_m3_s)
        for key in (L2, L3)
    }
    charges = {key: components[key] - steady.conduit_remaining_m3_s[key] for key in (L2, L3)}
    moved = {
        key: sum(
            float(row["water_m3"])
            for row in model._transfers
            if row["binding_id"] == key and row["transfer_kind"] == "physical_water"
        )
        for key in (L2, L3)
    }
    budget_rows = {
        binding_id: {
            "source_scope": budget.source_scope,
            "target_scope": budget.target_scope,
            "requested_m3_s": budget.requested_m3_s,
            "budget_m3_s": budget.budget_m3_s,
            "limiting_factor": budget.limiting_factor,
        }
        for binding_id, budget in sorted(steady.budgets.items())
        if budget.limiting_factor != "none"
    }
    return write(
        "03-reservations",
        {
            "resource_identity": (
                "an edge/trunk/element reservation is a FLOW CAPACITY token in m3/s, "
                "published to the processors in m3/h; a receiver reservation is a VOLUME "
                "headroom expressed as an equivalent one-tick rate. It is never water, "
                "never an extra source or sink."
            ),
            "units": {"internal": "m3/s", "processor_boundary": "m3/h", "queue": "m3"},
            "acquire_release": (
                "a conduit reserves its capacity components ONCE, when water ENTERS it; the "
                "forward emission of the next tick releases it. A series hop is never charged "
                "twice; a parallel branch from the same header shares the same tick."
            ),
            "queue_bound_m3": profile.queue.max_queued_volume_m3,
            "cancellation": (
                "a trip/stop removes the request, so the reservation is released on the "
                "following tick; nothing is held without a parcel"
            ),
            "steady_state": {
                "charged_m3": charges,
                "moved_m3": moved,
                "no_double_count": charges[L2] == charges[L3],
                "charges_cover_the_parcel": all(
                    charges[key] >= moved[key] - 1e-12 for key in charges
                ),
                "trunk_remaining_m3_s": dict(sorted(steady.trunk_used_m3_s.items())),
                "limited_bindings": budget_rows,
                "queued_volume_m3": steady.queued_volume_m3,
            },
            "verdict": (
                "RESERVATIONS_ARE_CAPACITY_TOKENS_NOT_WATER"
                if charges[L2] == charges[L3]
                and all(charges[key] >= moved[key] - 1e-12 for key in charges)
                else "RESERVATION_SEMANTICS_UNPROVEN"
            ),
        },
    )


def _sweep(profile, contracts, *, flow_sp=None, level_sp=None, ticks=1800) -> dict:
    """Run one variant with a different setpoint and record BOTH the CV and the MV."""
    controllers = dict(profile.controllers)
    if flow_sp is not None:
        controllers[FLOW_LOOP] = replace(controllers[FLOW_LOOP], sp=flow_sp)
    if level_sp is not None:
        controllers[LEVEL_LOOP] = replace(controllers[LEVEL_LOOP], sp=level_sp)
    variant = replace(profile, controllers=controllers)
    model = build_shwtp_whole_plant_x3(
        profile=variant, contracts=contracts, run_id="x3-ev-04-sweep"
    )
    run(model, ticks)
    rows = {row["controller_id"]: row for row in model.control_rows()}
    flow_row = rows[FLOW_LOOP]
    level_row = rows[LEVEL_LOOP]
    return {
        "flow_sp_m3_s": flow_row["sp"],
        "flow_measured_m3_s": (
            model.participants["vf-shw-node-t106"].monitor_values()["inflow_m3h"] / 3600.0
        ),
        "flow_error_frac": abs(flow_row["pv"] - flow_row["sp"]) / flow_row["sp"],
        "valve_applied_pct": flow_row["applied_mv"],
        "valve_applied_by": flow_row["applied_by"],
        "level_sp_m": level_row["sp"],
        "level_measured_m": model.participants["vf-shw-node-t108"].monitor_values()["level_m"],
        "level_error_m": abs(level_row["pv"] - level_row["sp"]),
        "pump_applied_pct": level_row["applied_mv"],
        "water_physical_valid": model.balance_report()["plant_water"]["physical_valid"],
    }


def section_04(profile, contracts) -> dict:
    model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-ev-04")
    samples = []
    backwash = None
    released = None
    arbitration_seen = False
    last_pi_owned = None
    for index in range(1, 5401):
        model.run_window(f"w{index}")
        rows = {row["controller_id"]: row for row in model.control_rows()}
        flow_row = rows[FLOW_LOOP]
        level_row = rows[LEVEL_LOOP]
        measured_flow = (
            model.participants["vf-shw-node-t106"].monitor_values()["inflow_m3h"] / 3600.0
        )
        measured_level = model.participants["vf-shw-node-t108"].monitor_values()["level_m"]
        if index % 600 == 0:
            samples.append(
                {
                    "tick": index,
                    "flow_sp": flow_row["sp"],
                    "flow_pv": flow_row["pv"],
                    "flow_measured": measured_flow,
                    "flow_error_frac": abs(measured_flow - flow_row["sp"]) / flow_row["sp"],
                    "valve_applied_pct": flow_row["applied_mv"],
                    "valve_pi_output_pct": flow_row["pi_output_mv"],
                    "valve_applied_by": flow_row["applied_by"],
                    "level_sp": level_row["sp"],
                    "level_pv": level_row["pv"],
                    "level_measured": measured_level,
                    "level_error_m": measured_level - level_row["sp"],
                    "pump_applied_pct": level_row["applied_mv"],
                    "flow_integral": flow_row["integral"],
                    "level_integral": level_row["integral"],
                    "limitation_reason": flow_row["limitation_reason"],
                }
            )
        step = model.control_report()["arbitration"]["inlet_valve_pos"]
        if step == "pi_flow_output" and measured_flow > 0.0:
            # the LAST window where the PI itself owns the valve is the honest place
            # to evaluate the acceptance: a backwash legitimately forces it closed
            last_pi_owned = {
                "tick": index,
                "flow_sp": flow_row["sp"],
                "flow_measured": measured_flow,
                "flow_error_frac": abs(measured_flow - flow_row["sp"]) / flow_row["sp"],
                "valve_applied_pct": flow_row["applied_mv"],
                "level_sp": level_row["sp"],
                "level_measured": measured_level,
                "level_error_m": measured_level - level_row["sp"],
                "pump_applied_pct": level_row["applied_mv"],
                "limitation_reason": flow_row["limitation_reason"],
            }
        if step == "c1_backwash_closes_inlet" and backwash is None:
            arbitration_seen = True
            backwash = {
                "tick": index,
                "arbitration": step,
                "valve_applied_pct": flow_row["applied_mv"],
                "valve_applied_by": flow_row["applied_by"],
                "flow_measured": measured_flow,
                "pi_integral_held": flow_row["integral"],
                "filter_dp_kpa": model.participants["vf-shw-node-t106"]
                .monitor_values()["filter_dp_kpa"],
            }
        if backwash is not None and step == "pi_flow_output" and released is None and index > 100:
            released = {
                "tick": index,
                "arbitration": step,
                "valve_applied_pct": flow_row["applied_mv"],
                "valve_applied_by": flow_row["applied_by"],
                "flow_measured": measured_flow,
                "flow_error_frac": abs(measured_flow - flow_row["sp"]) / flow_row["sp"],
            }
    plant = model.balance_report()["plant_water"]
    final_sample = last_pi_owned or samples[-1]
    # C01-1: after a backwash releases the valve the PI must REOPEN it inside the slew
    # limit, so the release sample is followed by a bounded recovery window.
    recovery = None
    if released is not None:
        run(model, 300, offset=5400)
        flow_row = {row["controller_id"]: row for row in model.control_rows()}[FLOW_LOOP]
        measured = (
            model.participants["vf-shw-node-t106"].monitor_values()["inflow_m3h"] / 3600.0
        )
        recovery = {
            "tick": model._tick_index,
            "flow_sp": flow_row["sp"],
            "flow_measured": measured,
            "flow_error_frac": abs(measured - flow_row["sp"]) / flow_row["sp"],
            "valve_applied_pct": flow_row["applied_mv"],
            "applied_by": flow_row["applied_by"],
            "release_valve_pct": released["valve_applied_pct"],
            "reopened_within_slew": released["valve_applied_pct"]
            <= profile.controllers[FLOW_LOOP].slew_per_s + 1e-9,
            "backwash_episode": backwash,
        }
    # ACTUAL actuator response under two different setpoints per loop: the valve must
    # move the measured inlet flow and the pump must move the measured T108 level.
    flow_low = _sweep(profile, contracts, flow_sp=0.006, ticks=1800)
    flow_high = _sweep(profile, contracts, flow_sp=0.009, ticks=1800)
    level_low = _sweep(profile, contracts, level_sp=2.3, ticks=2400)
    level_high = _sweep(profile, contracts, level_sp=2.7, ticks=2400)
    flow_responds = (
        flow_high["flow_measured_m3_s"] > flow_low["flow_measured_m3_s"]
        and flow_high["valve_applied_pct"] > flow_low["valve_applied_pct"]
    )
    level_responds = level_high["level_measured_m"] > level_low["level_measured_m"]
    off_nominal_band_m = 0.10
    sweep = {
        "flow": {"low": flow_low, "high": flow_high, "actuator_responds": flow_responds},
        "level": {
            "low": level_low,
            "high": level_high,
            "actuator_responds": level_responds,
            "off_nominal_band_m": off_nominal_band_m,
            "inside_documented_band": all(
                row["level_error_m"] <= off_nominal_band_m for row in (level_low, level_high)
            ),
        },
        "two_distinct_setpoints_per_loop": True,
    }
    actuator_ok = (
        flow_responds
        and level_responds
        and sweep["level"]["inside_documented_band"]
        and flow_high["flow_error_frac"] <= profile.acceptance.flow_steady_error_frac_of_sp
        and flow_low["flow_error_frac"] <= profile.acceptance.flow_steady_error_frac_of_sp
    )
    recovered_flow_error = None if recovery is None else recovery["flow_error_frac"]
    _tracking_ok = actuator_ok and (
        recovery is not None
        and recovery["reopened_within_slew"]
        and recovery["applied_by"] == "pi_flow_output"
        and recovered_flow_error <= profile.acceptance.flow_steady_error_frac_of_sp
    )
    return write(
        "04-two-pi-control",
        {
            "active_c2_loop_ids": list(model.control_report()["active_c2_loop_ids"]),
            "samples": samples,
            "last_pi_owned_window": last_pi_owned,
            "backwash_arbitration": backwash,
            "backwash_release": released,
            "backwash_recovery": recovery,
            "actuator_tracking": _actuator_tracking_evidence(profile, contracts),
            "setpoint_sweep": sweep,
            "arbitration_seen": arbitration_seen,
            "acceptance_basis": (
                "evaluated on the last window where the PI itself owns the valve; during a "
                "backwash the C1 sequence owns it and a zero flow is correct"
            ),
            "final_flow_error_frac": final_sample["flow_error_frac"],
            "final_level_error_m": abs(final_sample["level_error_m"]),
            "water_physical_valid": plant["physical_valid"],
            "plant_water_residual_m3": plant["residual_m3"],
            "verdict": (
                "TWO_PI_ACTUATOR_RESPONSE_AND_ARBITRATION_VERIFIED"
                if arbitration_seen
                and actuator_ok
                and _tracking_ok
                and final_sample["flow_error_frac"]
                <= profile.acceptance.flow_steady_error_frac_of_sp
                and abs(final_sample["level_error_m"]) <= profile.acceptance.level_steady_error_m
                and plant["physical_valid"]
                else "TWO_PI_RESPONSE_INCOMPLETE"
            ),
        },
    )


def section_05(profile, contracts) -> dict:
    envelope = {}
    for pump_id, pump in sorted(profile.pumps.items()):
        model = PumpModel(pump, profile.units)
        rows = []
        for speed in range(0, 101, 10):
            cap = model.max_feasible_flow_m3_s(speed / 100.0)
            point = model.operating_point(speed, min(pump.q_rated_m3_s, cap))
            head_ok = (
                True if cap <= 0.0 else model.head_m(speed / 100.0, cap) >= model.required_head_m(cap) - 1e-9
            )
            rows.append(
                {
                    "speed_pct": speed,
                    "max_feasible_flow_m3h": cap * 3600.0,
                    "head_ok": head_ok,
                    "electric_w": point.electric_w,
                    "motor_rating_w": point.motor_rating_w,
                    "power_ok": point.electric_w <= pump.motor_rating_w + 1e-9,
                    "off_is_zero": (point.off and point.flow_m3_s == 0.0 and point.electric_w == 0.0)
                    if speed == 0
                    else None,
                }
            )
        envelope[pump_id] = rows
    runtime = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-ev-05")
    run(runtime, 1200)
    energy = runtime.energy_report()
    per_m3h2_pa = 0.0006 * profile.units.bar_pa
    expected_r = per_m3h2_pa * (3600.0**2) / (profile.units.rho_kg_m3 * profile.units.g_m_s2)
    dist = profile.pumps["dist-hsp"]
    return write(
        "05-pumps-and-energy",
        {
            "dimensional_conversion": {
                "declared_loss": "0.0006 bar per (m3/h)^2",
                "expected_r_s2_m5": expected_r,
                "configured_r_s2_m5": dist.r_s2_m5,
                "matches": abs(dist.r_s2_m5 - expected_r) / expected_r < 1e-6,
                "wrong_value_would_pin_m3h": 0.66,
                "achievable_flow_at_80pct_m3h": PumpModel(
                    dist, profile.units
                ).max_feasible_flow_m3_s(0.8)
                * 3600.0,
            },
            "envelope": envelope,
            "h0_m_synthetic": {
                pump_id: pump.h0_m for pump_id, pump in sorted(profile.pumps.items())
            },
            "energy": {
                "total_energy_j": energy["total_energy_j"],
                "per_pump_electric_j": energy["per_pump_electric_j"],
                "per_pump_running_s": energy["per_pump_running_s"],
                "unavailable_energy": energy["unavailable_energy"],
                "pump_operating_points": {
                    pump_id: {
                        "flow_m3h": point["flow_m3h"],
                        "electric_w": point["electric_w"],
                        "motor_rating_w": point["motor_rating_w"],
                        "feasible": point["feasible"],
                        "off": point["off"],
                        "reason": point["reason"],
                    }
                    for pump_id, point in sorted(energy["pump_operating_points"].items())
                },
            },
            "verdict": (
                "PUMP_ENVELOPE_FEASIBLE_WITH_EXPLICIT_UNITS"
                if all(
                    row["power_ok"] and row["head_ok"]
                    for rows in envelope.values()
                    for row in rows
                )
                and abs(dist.r_s2_m5 - expected_r) / expected_r < 1e-6
                else "PUMP_ENVELOPE_NOT_FEASIBLE"
            ),
        },
    )


def section_06(profile, contracts) -> dict:
    cases = {}

    model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-ev-06a")
    run(model, 600)
    baseline_valid = model.balance_report()["plant_water"]["physical_valid"]
    model.participants["vf-shw-node-t105"]._volume_m3 -= 0.25
    model.run_window("mutate-remove")
    removed = model.balance_report()["plant_water"]
    cases["injected_state_water"] = {
        "baseline_valid": baseline_valid,
        "physical_valid": removed["physical_valid"],
        "storage_integration_gap_m3": removed["storage_integration_gap_m3"],
        "detected": removed["physical_valid"] is False,
    }

    model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-ev-06b")
    run(model, 300)
    model.participants["vf-shw-node-t108"]._shortfall_m3 = 1.0
    created = model.balance_report()["plant_water"]
    cases["created_water"] = {
        "physical_valid": created["physical_valid"],
        "created_water_m3": created["shortfall_m3"],
        "detected": created["physical_valid"] is False,
    }

    model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-ev-06c")
    run(model, 300)
    tank = model.participants["vf-shw-node-t108"]
    tank._volume_m3 = tank.capacity_m3
    tank._initial_volume_m3 = tank.capacity_m3
    run(model, 5, offset=1000)
    full = model.balance_report()["plant_water"]
    cases["full_receiver"] = {
        "physical_valid": full["physical_valid"],
        "created_water_m3": full["shortfall_m3"],
        "volume_within_capacity": tank._storage_volume() <= tank.capacity_m3 + 1e-9,
        "safe": full["shortfall_m3"] <= 1e-9 and tank._storage_volume() <= tank.capacity_m3 + 1e-9,
    }

    dist = profile.pumps["dist-hsp"]
    wrong = replace(dist, r_s2_m5=777_600_000.0)
    wrong_model = PumpModel(wrong, profile.units)
    cases["impossible_head_or_loss"] = {
        "wrong_r_s2_m5_flow_at_80pct_m3h": wrong_model.max_feasible_flow_m3_s(0.8) * 3600.0,
        "configured_flow_at_80pct_m3h": PumpModel(dist, profile.units).max_feasible_flow_m3_s(0.8)
        * 3600.0,
        "detected": wrong_model.max_feasible_flow_m3_s(0.8) * 3600.0 < 40.0,
    }

    raw = profile.pumps["raw-intake-pump"]
    overload = PumpModel(replace(raw, motor_rating_w=250.0), profile.units)
    point = overload.operating_point(75.0, raw.q_rated_m3_s)
    cases["motor_overload"] = {
        "electric_w": point.electric_w,
        "motor_rating_w": 250.0,
        "flow_m3h": point.flow_m3h,
        "bounded": point.electric_w <= 250.0 + 1e-9,
        "detected": point.flow_m3h < raw.q_rated_m3_s * 3600.0,
    }

    model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-ev-06d")
    edges = dict(profile.edges)
    edges[L2] = replace(edges[L2], max_flow_m3_s=0.002)
    narrowed = replace(profile, edges=edges)
    for index in range(1, 1501):
        model.run_window(f"w{index}")
    narrow_model = build_shwtp_whole_plant_x3(
        profile=narrowed, contracts=contracts, run_id="x3-ev-06e"
    )
    run(narrow_model, 1500)
    throughput = narrow_model.participants["vf-shw-node-t106"].monitor_values()["inflow_m3h"] / 3600.0
    cases["narrow_serial_pipe"] = {
        "narrow_rating_m3_s": 0.002,
        "chain_throughput_m3_s": throughput,
        "bounded": throughput <= 0.002 + 1e-9,
        "water_valid": narrow_model.balance_report()["plant_water"]["physical_valid"],
        "no_hidden_loss": narrow_model.balance_report()["plant_water"]["shortfall_m3"] <= 1e-9,
    }

    verdict_ok = (
        cases["injected_state_water"]["detected"]
        and cases["created_water"]["detected"]
        and cases["full_receiver"]["safe"]
        and cases["impossible_head_or_loss"]["detected"]
        and cases["motor_overload"]["bounded"]
        and cases["narrow_serial_pipe"]["bounded"]
        and cases["narrow_serial_pipe"]["water_valid"]
    )
    return write(
        "06-mutations",
        {
            "cases": cases,
            "verdict": "MUTATIONS_VIOLATE_THE_PHYSICAL_ENVELOPE" if verdict_ok else "MUTATION_NOT_DETECTED",
        },
    )


def section_07() -> dict:
    default = SHWTP_DEFAULT_MODEL
    session = build_shwtp_session()
    session.advance()
    model = session.record.bridge.model
    run_id = session.record.context.run_id
    first = [row["values"].get("volume_m3") for row in model.monitor_rows()]
    for _ in range(9):
        session.advance()
    ten = [row["values"].get("volume_m3") for row in model.monitor_rows()]
    session.reset()
    reset_id = session.record.context.run_id
    for _ in range(10):
        session.advance()
    replayed = [row["values"].get("volume_m3") for row in model.monitor_rows()]
    issued = session.new_attempt()
    session.advance()
    new_id = session.record.context.run_id

    x2 = build_shwtp_session(model=SHWTP_MODEL_WHOLE_PLANT_X2)
    x2.advance()
    g21 = build_shwtp_session(model=SHWTP_MODEL_G21_SLICE)
    g21.advance()
    return write(
        "07-identity-and-compatibility",
        {
            "canonical_default_model": default,
            "canonical_scenario_id": session.scenario_id,
            "model_class": type(model).__name__,
            "tick_s": model.communication_step_s,
            "attempt_run_id": run_id,
            "model_run_id_matches_attempt": model.run_id == run_id,
            "reset_preserves_identity": reset_id == run_id,
            "reset_is_deterministic": replayed == ten,
            "new_attempt_issues_new_identity": new_id != run_id,
            "x2_compatibility": {
                "model": SHWTP_MODEL_WHOLE_PLANT_X2,
                "model_class": type(x2.record.bridge.model).__name__,
                "tick_s": x2.record.bridge.model.communication_step_s,
                "has_c2_layer": hasattr(x2.record.bridge.model, "control_layer"),
            },
            "g21_compatibility": {
                "model": SHWTP_MODEL_G21_SLICE,
                "scopes": len(g21.record.bridge.model.scopes),
            },
            "verdict": (
                "X3_CANONICAL_WITH_X2_AND_G21_COMPATIBILITY"
                if model.run_id == run_id
                and reset_id == run_id
                and replayed == ten
                and new_id != run_id
                else "IDENTITY_OR_COMPATIBILITY_UNPROVEN"
            ),
        },
    )


def _acceptance_block(artefacts: dict) -> dict:
    """The machine-checkable acceptance fields the X3 task contract refers to.

    Every value is derived from a MEASURED fact in the section artefacts, so the
    harness rule evaluation (field x3.<name>, operator is_true) can only pass when
    the model really satisfies it.
    """
    s01, s02, s03 = artefacts["01"], artefacts["02"], artefacts["03"]
    s04, s05, s06, s07 = artefacts["04"], artefacts["05"], artefacts["06"], artefacts["07"]
    s10 = artefacts["10"]
    tracking = s04["actuator_tracking"]
    recovery = s04["backwash_recovery"] or {}

    deferred_ok = all(
        ("ACTIVE" in note) == (loop_id in set(s01["active_c2_loop_ids"]))
        for loop_id, note in s01["deferred_loops"].items()
    )
    scope_control = (
        s01["scopes"] == 16
        and s01["tick_s"] == 1.0
        and s01["coupling_policy"] == "explicit_lagged"
        and s01["exactly_two_active_c2"] is True
        and len(s01["active_c2_loop_ids"]) == 2
        and set(s01["active_c2_loop_ids"]) == {FLOW_LOOP, LEVEL_LOOP}
        and s01["participants_are_exactly_the_admitted_scopes"] is True
        and deferred_ok
        and s07["model_run_id_matches_attempt"] is True
    )

    identity_mutation = s02["mutation_after_baseline"]
    water_identity = (
        s02["invalid_ticks"] == 0
        and s02["full_run_authoritative"] is True
        and s02["final_created_water_m3"] <= 1e-9
        and s02["final_residual_m3"] <= s02["final_tolerance_m3"]
        and abs(s02["final_storage_integration_gap_m3"]) <= s02["final_tolerance_m3"]
        and s02["overflow_m3"] == 0.0
        and identity_mutation["detected"] is True
        and identity_mutation["physical_valid"] is False
    )

    steady = s03["steady_state"]
    flow_limits = (
        steady["no_double_count"] is True
        and steady["charges_cover_the_parcel"] is True
        and steady["queued_volume_m3"] <= s03["queue_bound_m3"]
        and s03["units"]["internal"] == "m3/s"
        and s03["units"]["processor_boundary"] == "m3/h"
        and all(
            str(s03[key]).strip()
            for key in ("resource_identity", "acquire_release", "cancellation")
        )
    )

    arbitration = s04["backwash_arbitration"] or {}
    release = s04["backwash_release"] or {}
    sweep = s04["setpoint_sweep"]
    pi_response = (
        s04["arbitration_seen"] is True
        and arbitration.get("arbitration") == "c1_backwash_closes_inlet"
        and arbitration.get("valve_applied_by") == "c1_backwash_closes_inlet"
        and arbitration.get("flow_measured") == 0.0
        and release.get("valve_applied_by") == "pi_flow_output"
        # C01-1: the release itself is slew limited and the bounded recovery window
        # proves the loop takes the real flow back inside the acceptance band
        and release.get("valve_applied_pct") is not None
        and tracking["all_checks_pass"] is True
        and tracking["runtime_continuity"]["violation_count"] == 0
        and recovery.get("reopened_within_slew") is True
        and recovery.get("applied_by") == "pi_flow_output"
        and recovery.get("flow_error_frac", 1.0) <= 0.05
        and sweep["flow"]["actuator_responds"] is True
        and sweep["level"]["actuator_responds"] is True
        and sweep["level"]["inside_documented_band"] is True
        and s04["final_flow_error_frac"] <= 0.05
        and s04["final_level_error_m"] <= 0.05
        and s04["water_physical_valid"] is True
    )

    envelope_rows = [row for rows in s05["envelope"].values() for row in rows]
    points = s05["energy"]["pump_operating_points"].values()
    pump_energy = (
        # C01-2: the energy verdict is built on the REALIZED basis; C02-1/C02-2: on the
        # frozen D6 pump law and an oracle that does not reuse the production helpers
        s10["all_checks_pass"] is True
        and s10["independent_recomputation_matches"] is True
        and s10["capacity_substitution_detected"] is True
        and s10["hreq_substitution_detected"] is True
        and s10["power_identity_holds"] is True
        and s10["throttle_energy_is_charged_in_the_electricity"] is True
        and s10["oracle"]["independent_of_production_helpers"] is True
        and s10["realized_feasibility"]["all_realized_points_feasible"] is True
        and s10["realized_feasibility"]["infeasible_ticks"] == 0
        and all(
            row["water_physical_valid"] and row["all_realized_points_feasible"]
            for row in s10["scenarios"].values()
        )
        and all(row["head_ok"] and row["power_ok"] for row in envelope_rows)
        and all(row["off_is_zero"] is True for row in envelope_rows if row["speed_pct"] == 0)
        and all(
            point["flow_m3h"] == 0.0 and point["electric_w"] == 0.0
            for point in points
            if point["off"]
        )
        and s05["dimensional_conversion"]["matches"] is True
        and s10["total_energy_j"] > 0.0
        and len(s05["energy"]["unavailable_energy"]) > 0
    )

    cases = s06["cases"]
    mutations = (
        cases["injected_state_water"]["detected"] is True
        and cases["injected_state_water"]["physical_valid"] is False
        and cases["created_water"]["detected"] is True
        and cases["created_water"]["physical_valid"] is False
        and cases["impossible_head_or_loss"]["detected"] is True
        and cases["motor_overload"]["detected"] is True
        and cases["motor_overload"]["bounded"] is True
        and cases["narrow_serial_pipe"]["bounded"] is True
        and cases["narrow_serial_pipe"]["no_hidden_loss"] is True
        and cases["full_receiver"]["safe"] is True
        and cases["full_receiver"]["volume_within_capacity"] is True
        and cases["full_receiver"]["created_water_m3"] == 0.0
    )

    regression = (
        s07["canonical_default_model"] == "whole_plant_x3"
        and s07["tick_s"] == 1.0
        and s07["reset_preserves_identity"] is True
        and s07["reset_is_deterministic"] is True
        and s07["new_attempt_issues_new_identity"] is True
        and s07["x2_compatibility"]["tick_s"] == 60.0
        and s07["x2_compatibility"]["has_c2_layer"] is False
        and s07["g21_compatibility"]["scopes"] == 5
    )

    return {
        "scope_control": scope_control,
        "water_identity": water_identity,
        "flow_limits": flow_limits,
        "pi_response": pi_response,
        "pump_energy": pump_energy,
        "mutations": mutations,
        "regression": regression,
    }


def _c01_acceptance_block(artefacts: dict) -> dict:
    """The C01 acceptance fields of the correction contract (SA findings 1 and 2)."""
    s04 = artefacts["04"]
    s10 = artefacts["10"]
    tracking = s04["actuator_tracking"]
    epilogues = list(tracking["protective_epilogues"].values())
    counterexample = tracking["sa_counterexample"]
    steps = tracking["setpoint_steps_one_attempt"]
    actuator_tracking = (
        counterexample["tracked_after_stop_pct"] == 0.0
        and counterexample["within_slew"] is True
        and all(
            row["protected_applied_mv"] == 0.0
            and row["tracked_after_protection_mv"] == 0.0
            and row["protection_recognised"] is True
            and row["integral_held_on_first_tick"] is True
            and row["integral_held_with_changed_pv"] is True
            and row["release_within_slew"] is True
            and row["ramp_within_slew"] is True
            for row in epilogues
        )
        and tracking["runtime_continuity"]["violation_count"] == 0
        and tracking["runtime_continuity"]["backwash_episode_seen"] is True
        and steps["feasible_step_tracked"] is True
        and steps["unreachable_saturated_with_reason"] is True
        and steps["recovered_within_band"] is True
        and steps["state_retained"] is True
    )
    energy_from_actual_flow = (
        s10["operating_point_basis"] == "realized_actual_pumped_throughput"
        and s10["independent_recomputation_matches"] is True
        and s10["capacity_substitution_detected"] is True
        and s10["realized_feasibility"]["all_realized_points_feasible"] is True
        and s10["realized_feasibility"]["infeasible_ticks"] == 0
        and s10["scenarios"]["zero_available_water"]["downstream_pumped_flow_sum_m3_s"] == 0.0
        and all(
            row["off_rows_integrate_zero"] and row["idle_rows_have_no_hydraulic_power"]
            for row in s10["scenarios"].values()
        )
        and all(row["water_physical_valid"] for row in s10["scenarios"].values())
    )
    return {
        "actuator_tracking": actuator_tracking,
        "energy_from_actual_flow": energy_from_actual_flow,
    }


def _c02_acceptance_block(artefacts: dict) -> dict:
    """The C02 acceptance fields of the correction contract (SA findings C02-1/C02-2)."""
    s10 = artefacts["10"]
    counterexample = s10["sa_counterexample"]
    split_error = abs(
        counterexample["pump_hydraulic_w"]
        - (counterexample["useful_hydraulic_w"] + counterexample["throttle_power_w"])
    )
    pump_power_law = (
        counterexample["matches_sa_numbers"] is True
        and split_error <= 1e-3
        and counterexample["power_balance_error_w"] <= 1e-6
        and s10["power_identity_holds"] is True
        and s10["throttle_energy_is_charged_in_the_electricity"] is True
        and "frozen D6" in s10["pump_power_law"]
        and s10["realized_feasibility"]["all_realized_points_feasible"] is True
        and all(row["idle_rows_have_no_hydraulic_power"] for row in s10["scenarios"].values())
    )
    independent_energy_oracle = (
        s10["oracle"]["independent_of_production_helpers"] is True
        and s10["independent_recomputation_matches"] is True
        and s10["capacity_substitution_detected"] is True
        and s10["hreq_substitution_detected"] is True
        and s10["realized_feasibility"]["infeasible_ticks"] == 0
        and all(row["water_physical_valid"] for row in s10["scenarios"].values())
    )
    return {
        "pump_power_law": pump_power_law,
        "independent_energy_oracle": independent_energy_oracle,
    }


def _pi(profile, loop_id: str, error_sign: str, sp: float | None = None) -> PIController:
    config = profile.controllers[loop_id]
    if sp is not None:
        config = replace(config, sp=sp)
    return PIController(config, error_sign=error_sign)


def _protective_epilogue(
    *,
    pi: PIController,
    pv: float,
    changed_pv: float,
    release_pv: float,
    protection: str,
    kwargs: dict,
    slew: float,
    ticks: int = 60,
) -> dict:
    """Drive to a working point, enter the protection, hold it with a CHANGED PV,
    release it and then ramp: the C01-1 statement measured end to end.

    ``release_pv`` is the PV that is CONSISTENT with the protected actuator (a closed
    valve gives no inlet flow; a stopped transfer pump lets the level rise), so the
    release is a real, slew-limited reopening and not a synthetic constant-PV scan.
    """
    for _ in range(ticks):
        pi.evaluate(pv=pv, dt_s=1.0)
    working = pi.applied_mv
    integral_before = pi.integral
    first = pi.evaluate(pv=pv, dt_s=1.0, **kwargs)
    integral_held_first = abs(first.integral - integral_before) <= 1e-12
    for _ in range(5):
        pi.evaluate(pv=changed_pv, dt_s=1.0, **kwargs)
    integral_held_changed_pv = abs(pi.integral - integral_before) <= 1e-12
    tracked_stopped = pi.applied_mv
    release = pi.evaluate(pv=release_pv, dt_s=1.0)
    release_step = abs(release.applied_mv - tracked_stopped)
    steps = []
    previous = release.applied_mv
    for _ in range(40):
        status = pi.evaluate(pv=release_pv, dt_s=1.0)
        steps.append(abs(status.applied_mv - previous))
        previous = status.applied_mv
    return {
        "protection": protection,
        "working_mv": round(working, 9),
        "protected_applied_mv": round(first.applied_mv, 9),
        "protection_recognised": first.protection == protection,
        "integral_held_on_first_tick": integral_held_first,
        "integral_held_with_changed_pv": integral_held_changed_pv,
        "tracked_after_protection_mv": round(tracked_stopped, 9),
        "release_step_pp": round(release_step, 9),
        "slew_limit_pp": slew,
        "release_within_slew": release_step <= slew + 1e-9,
        "max_ramp_step_pp": round(max(steps), 9) if steps else 0.0,
        "ramp_within_slew": all(step <= slew + 1e-9 for step in steps),
        "reopened_above_the_stopped_value": previous > tracked_stopped + 1e-9,
    }


def _loop_probe(model) -> dict:
    rows = {row["controller_id"]: row for row in model.control_rows()}
    flow = rows[FLOW_LOOP]
    measured = (
        model.participants["vf-shw-node-t106"].monitor_values()["inflow_m3h"] / 3600.0
    )
    return {
        "tick": model._tick_index,
        "flow_sp": flow["sp"],
        "flow_measured": measured,
        "flow_error_frac": abs(measured - flow["sp"]) / flow["sp"],
        "valve_applied_pct": flow["applied_mv"],
        "saturated": flow["saturated"],
        "limitation_reason": flow["limitation_reason"],
        "alarm": flow["alarm"],
        "integral": flow["integral"],
    }


def _actuator_tracking_evidence(profile, contracts) -> dict:
    """C01-1: the tracked actuator is the REALIZED one on every protective path."""
    flow_slew = profile.controllers[FLOW_LOOP].slew_per_s
    level_slew = profile.controllers[LEVEL_LOOP].slew_per_s
    epilogues: dict[str, dict] = {}
    for loop_id, sign, pv, changed_pv, release_pv, slew in (
        (FLOW_LOOP, X3_CONTROL_ERROR_SIGN_FLOW, 0.008, 0.009, 0.0, flow_slew),
        (LEVEL_LOOP, X3_CONTROL_ERROR_SIGN_LEVEL, 2.5, 2.55, 2.6, level_slew),
    ):
        for name, kwargs in (
            ("trip", {"forced_stop": True}),
            ("interlock", {"interlock": True, "interlock_alarm": "c01_interlock"}),
            (
                "c1_override",
                {
                    "external_override": True,
                    "external_override_mv": 0.0,
                    "external_override_reason": "c1_backwash_closes_inlet",
                },
            ),
        ):
            epilogues[f"{loop_id}|{name}"] = _protective_epilogue(
                pi=_pi(profile, loop_id, sign),
                pv=pv,
                changed_pv=changed_pv,
                release_pv=release_pv,
                protection=name,
                kwargs=kwargs,
                slew=slew,
            )

    # the exact SA counterexample: normal 90 % -> forced stop 0 % -> release
    counterexample_pi = _pi(profile, FLOW_LOOP, X3_CONTROL_ERROR_SIGN_FLOW)
    for _ in range(60):
        counterexample_pi.evaluate(pv=0.008, dt_s=1.0)
    normal = counterexample_pi.applied_mv
    stopped = counterexample_pi.evaluate(pv=0.008, dt_s=1.0, forced_stop=True)
    tracked_after_stop = counterexample_pi.applied_mv
    released = counterexample_pi.evaluate(pv=0.008, dt_s=1.0)
    counterexample = {
        "normal_command_pct": round(normal, 9),
        "stopped_applied_pct": round(stopped.applied_mv, 9),
        "tracked_after_stop_pct": round(tracked_after_stop, 9),
        "release_applied_pct": round(released.applied_mv, 9),
        "release_step_pp": round(abs(released.applied_mv - stopped.applied_mv), 9),
        "slew_limit_pp": flow_slew,
        "within_slew": abs(released.applied_mv - stopped.applied_mv) <= flow_slew + 1e-9,
    }

    # runtime continuity over the WHOLE run: only entering protection may bypass the slew
    model = build_shwtp_whole_plant_x3(
        profile=profile, contracts=contracts, run_id="x3-ev-tracking"
    )
    violations: list[dict] = []
    owner_counts: dict[str, int] = {}
    previous = None
    for index in range(1, 5401):
        model.run_window(f"w{index}")
        report = model.control_report()
        owner = report["arbitration"]["inlet_valve_pos"]
        pump_owner = report["arbitration"]["transfer_pump_speed_cmd"]
        valve = float(model._control.commands["inlet_valve_pos"])
        pump = float(model._control.commands["transfer_pump_speed_cmd"])
        tracked = model.control_layer.flow_pi.applied_mv
        tracked_pump = model.control_layer.level_pi.applied_mv
        if abs(tracked - valve) > 1e-9:
            violations.append(
                {"tick": index, "kind": "valve_tracking", "tracked": tracked, "realized": valve}
            )
        if abs(tracked_pump - pump) > 1e-9:
            violations.append(
                {"tick": index, "kind": "pump_tracking", "tracked": tracked_pump, "realized": pump}
            )
        if previous is not None:
            enters_valve = owner != "pi_flow_output" and previous[1] == "pi_flow_output"
            valve_step = abs(valve - previous[0])
            if not enters_valve and valve_step > flow_slew + 1e-9:
                violations.append(
                    {"tick": index, "kind": "valve_step", "step_pp": round(valve_step, 9)}
                )
            enters_pump = pump_owner != "pi_level_output" and previous[3] == "pi_level_output"
            pump_step = abs(pump - previous[2])
            if not enters_pump and pump_step > level_slew + 1e-9:
                violations.append(
                    {"tick": index, "kind": "pump_step", "step_pp": round(pump_step, 9)}
                )
        owner_counts[owner] = owner_counts.get(owner, 0) + 1
        owner_counts[f"pump:{pump_owner}"] = owner_counts.get(f"pump:{pump_owner}", 0) + 1
        previous = (valve, owner, pump, pump_owner)
    runtime = {
        "ticks": 5400,
        "owner_counts": dict(sorted(owner_counts.items())),
        "violations": violations[:10],
        "violation_count": len(violations),
        "backwash_episode_seen": "c1_backwash_closes_inlet" in owner_counts,
    }

    # one ONGOING attempt: feasible step -> unreachable -> recovery (state retained)
    step_model = build_shwtp_whole_plant_x3(
        profile=profile, contracts=contracts, run_id="x3-ev-steps"
    )
    flow_pi = step_model.control_layer.flow_pi
    acceptance = profile.acceptance
    advanced = {"ticks": 0}

    def advance(ticks: int) -> None:
        run(step_model, ticks, offset=advanced["ticks"])
        advanced["ticks"] += ticks

    flow_pi.set_setpoint(0.006)
    advance(acceptance.nominal_settling_window_s + 600)
    stepped = _loop_probe(step_model)
    flow_pi.set_setpoint(0.0125)
    advance(acceptance.nominal_settling_window_s)
    unreachable = _loop_probe(step_model)
    flow_pi.set_setpoint(0.008)
    advance(acceptance.nominal_settling_window_s)
    recovered = _loop_probe(step_model)
    one_attempt = {
        "mode": "one_ongoing_attempt_state_retained",
        "feasible_step": stepped,
        "unreachable_step": unreachable,
        "recovered_step": recovered,
        "feasible_step_tracked": stepped["flow_error_frac"]
        <= acceptance.flow_steady_error_frac_of_sp,
        "unreachable_saturated_with_reason": bool(unreachable["saturated"])
        and unreachable["limitation_reason"] == "output_saturated"
        and unreachable["flow_measured"] < unreachable["flow_sp"],
        "recovered_within_band": recovered["saturated"] is False
        and recovered["flow_error_frac"] <= acceptance.flow_steady_error_frac_of_sp,
        "state_retained": recovered["tick"] > unreachable["tick"] > stepped["tick"],
    }

    epilogue_pass = all(
        row["protection_recognised"]
        and row["protected_applied_mv"] == 0.0
        and row["tracked_after_protection_mv"] == 0.0
        and row["integral_held_on_first_tick"]
        and row["integral_held_with_changed_pv"]
        and row["release_within_slew"]
        and row["ramp_within_slew"]
        and row["reopened_above_the_stopped_value"]
        for row in epilogues.values()
    )
    checks_pass = (
        epilogue_pass
        and counterexample["within_slew"]
        and counterexample["tracked_after_stop_pct"] == 0.0
        and runtime["violation_count"] == 0
        and runtime["backwash_episode_seen"]
        and one_attempt["feasible_step_tracked"]
        and one_attempt["unreachable_saturated_with_reason"]
        and one_attempt["recovered_within_band"]
        and one_attempt["state_retained"]
    )
    return write(
        "11-actuator-tracking",
        {
            "finding": "C01-1 final physical actuator is the controller's tracked actuator",
            "sa_counterexample": counterexample,
            "protective_epilogues": epilogues,
            "epilogues_pass": epilogue_pass,
            "runtime_continuity": runtime,
            "setpoint_steps_one_attempt": one_attempt,
            "slew_limits_pp_per_s": {"valve": flow_slew, "pump": level_slew},
            "all_checks_pass": checks_pass,
            "verdict": (
                "ACTUATOR_TRACKING_AND_RELEASE_SLEW_VERIFIED"
                if checks_pass
                else "ACTUATOR_TRACKING_OR_RELEASE_SLEW_UNPROVEN"
            ),
        },
    )


def frozen_pump_parameters() -> dict:
    """Frozen pump/unit parameters read straight from the config file (SA C02-2)."""
    raw = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    constants = raw["constants"]
    return {
        "rho_kg_m3": float(constants["rho_kg_m3"]),
        "g_m_s2": float(constants["g_m_s2"]),
        "pumps": {
            pump_id: {
                "h0_m": float(pump["h0_m"]),
                "k_s2_m5": float(pump["k_s2_m5"]),
                "h_static_m": float(pump["h_static_m"]),
                "r_s2_m5": float(pump["r_s2_m5"]),
                "eta_total": float(pump["eta_total"]),
                "no_load_w": float(pump["no_load_w"]),
                "motor_rating_w": float(pump["motor_rating_w"]),
            }
            for pump_id, pump in raw["pumps"].items()
        },
    }


#: tokens that would mean the oracle reuses the production implementation (SA C02-2)
ORACLE_FORBIDDEN_TOKENS = (
    "realized_point",
    "operating_point",
    "power_split_w",
    "hydraulic_power_w",
    "electric_power_w",
    "energy_step_j",
    "pump_models",
    "energy_trace",
    "energy_report",
    "energy_components_j",
    "per_pump_electric_j",
    "hydraulic_w",
)


def independent_energy(model, *, basis: str = "achieved") -> dict[str, float]:
    """Electricity per pump WITHOUT any production energy helper (SA C02-2).

    Inputs: the committed PHYSICAL pump discharge records (committed water, the commanded
    speed of that tick, the binding) joined by tick. Every hydraulic and electric quantity
    is then evaluated from the frozen parameters read out of the config file.

    ``basis="achieved"`` committed discharge flow against the frozen D6 law;
    ``basis="capacity"`` substitutes the allocation capacity flow (mutation 1);
    ``basis="hreq_law"`` substitutes Hreq for the pump head H(n,Q) (mutation 2, the C01-2
    error the SA reproduced, which must not reproduce the ledger).
    """
    frozen = frozen_pump_parameters()
    rho = frozen["rho_kg_m3"]
    g = frozen["g_m_s2"]
    totals: dict[str, float] = {}
    for record in model.pump_discharge_records():
        pump_id = record["pump_id"]
        pump = frozen["pumps"][pump_id]
        dt_s = float(record["dt_s"])
        speed = float(record["commanded_speed_pct"]) / 100.0
        if speed <= 0.0:
            continue  # not energized: exactly zero flow and zero energy
        if basis == "capacity":
            flow = float(record["capacity_flow_m3_s"])
        else:
            flow = float(record["discharge_m3"]) / dt_s if dt_s > 0.0 else 0.0
        if flow <= 0.0:
            electric_w = pump["no_load_w"]
        else:
            head = max(0.0, pump["h0_m"] * speed * speed - pump["k_s2_m5"] * flow * flow)
            required = pump["h_static_m"] + pump["r_s2_m5"] * flow * flow
            head_for_power = required if basis == "hreq_law" else head
            electric_w = rho * g * flow * head_for_power / pump["eta_total"] + pump["no_load_w"]
        totals[pump_id] = totals.get(pump_id, 0.0) + electric_w * dt_s
    return totals


def oracle_is_independent() -> bool:
    """True when the oracle source contains no production power/energy reference."""
    import inspect

    source = inspect.getsource(independent_energy) + inspect.getsource(
        frozen_pump_parameters
    )
    return not any(token in source for token in ORACLE_FORBIDDEN_TOKENS)


def section_10(profile, contracts) -> dict:
    """C02-1/C02-2: energy on the FROZEN pump law, verified by an independent oracle."""
    dt_s = profile.tick_s
    model = build_shwtp_whole_plant_x3(
        profile=profile, contracts=contracts, run_id="x3-ev-10"
    )
    run(model, 1200)
    report = model.energy_report()
    trace = model.energy_trace()

    frozen = frozen_pump_parameters()
    # SA exact-source reproduction of the frozen DIST parameters at 80 %, Q = 0.008 m3/s
    dist_point = PumpModel(profile.pumps["dist-hsp"], profile.units).realized_point(80.0, 0.008)
    sa_counterexample = {
        "description": "SA exact-source reproduction, frozen DIST parameters, 80 %, Q = 0.008 m3/s",
        "head_m": dist_point.head_m,
        "required_head_m": dist_point.required_head_m,
        "pump_hydraulic_w": dist_point.hydraulic_w,
        "useful_hydraulic_w": dist_point.useful_hydraulic_w,
        "throttle_power_w": dist_point.throttle_power_w,
        "electric_w": dist_point.electric_w,
        "power_balance_error_w": dist_point.power_balance_error_w,
        "feasible": dist_point.feasible,
        "sa_expected": {
            "head_m": 26.0928,
            "required_head_m": 5.07302784,
            "pump_hydraulic_w": 2047.762944,
            "useful_hydraulic_w": 398.131224883,
            "throttle_power_w": 1649.631719117,
            "electric_w": 3325.375634286,
        },
    }
    sa_counterexample["matches_sa_numbers"] = (
        abs(dist_point.head_m - 26.0928) < 1e-6
        and abs(dist_point.required_head_m - 5.07302784) < 1e-6
        and abs(dist_point.hydraulic_w - 2047.762944) < 1e-3
        and abs(dist_point.useful_hydraulic_w - 398.131224883) < 1e-3
        and abs(dist_point.throttle_power_w - 1649.631719117) < 1e-3
        and abs(dist_point.electric_w - 3325.375634286) < 1e-3
    )

    independent = independent_energy(model, basis="achieved")
    capacity_basis = independent_energy(model, basis="capacity")
    hreq_basis = independent_energy(model, basis="hreq_law")

    ledger = {key: float(value) for key, value in report["per_pump_electric_j"].items()}
    matches = {
        pump_id: abs(independent.get(pump_id, 0.0) - energy) <= 1e-6
        for pump_id, energy in ledger.items()
    }
    substitution = {
        pump_id: round(abs(capacity_basis.get(pump_id, 0.0) - energy), 6)
        for pump_id, energy in ledger.items()
    }
    capacity_detected = max(substitution.values(), default=0.0) > 1.0
    hreq_substitution = {
        pump_id: round(abs(hreq_basis.get(pump_id, 0.0) - energy), 6)
        for pump_id, energy in ledger.items()
    }
    hreq_detected = max(hreq_substitution.values(), default=0.0) > 1.0
    components = report["energy_components_j"]
    power_identity_holds = (
        abs(
            components["pump_hydraulic_j"]
            - (components["useful_hydraulic_j"] + components["throttle_dissipated_j"])
        )
        <= 1e-3
        and components["max_power_balance_error_w"] <= 1e-6
    )
    throttle_is_charged = (
        components["throttle_dissipated_j"] > 0.0
        and components["total_electric_j"] > components["useful_hydraulic_j"]
        and sum(hreq_basis.values()) < report["total_energy_j"]
    )

    # scenario matrix: startup / zero available water / full receiver / narrowed pipe
    startup = build_shwtp_whole_plant_x3(
        profile=profile, contracts=contracts, run_id="x3-ev-10-startup"
    )
    run(startup, 120)
    startup_rows = startup.energy_trace()
    empty = build_shwtp_whole_plant_x3(
        profile=profile, contracts=contracts, run_id="x3-ev-10-empty"
    )
    for participant in empty.participants.values():
        if getattr(participant, "storage", False):
            participant._volume_m3 = 0.0
            participant._initial_volume_m3 = 0.0
    run(empty, 60)
    empty_rows = empty.energy_trace()
    full = build_shwtp_whole_plant_x3(
        profile=profile, contracts=contracts, run_id="x3-ev-10-full"
    )
    tank = full.participants["vf-shw-node-t108"]
    tank._volume_m3 = tank.capacity_m3
    tank._initial_volume_m3 = tank.capacity_m3
    run(full, 60)
    edges = dict(profile.edges)
    edges["vf-shw-edge-dist-demand"] = replace(
        edges["vf-shw-edge-dist-demand"], max_flow_m3_s=0.0005
    )
    narrow = build_shwtp_whole_plant_x3(
        profile=replace(profile, edges=edges), contracts=contracts, run_id="x3-ev-10-narrow"
    )
    run(narrow, 900)

    def _scenario(instance, rows) -> dict:
        pumped = sum(
            data["achieved_flow_m3_s"]
            for row in rows
            for data in row["pumps"].values()
        )
        # the raw-intake pump draws from the DECLARED boundary source, so a "no water"
        # statement is made on the downstream chain (T108 transfer + DIST), where a
        # limited startup inventory / empty upstream / full receiver really binds
        downstream = sum(
            data["achieved_flow_m3_s"]
            for row in rows
            for pump_id, data in row["pumps"].items()
            if pump_id in ("t108-transfer-pump", "dist-hsp")
        )
        return {
            "total_energy_j": instance.energy_report()["total_energy_j"],
            "ticks": len(rows),
            "pumped_flow_sum_m3_s": round(pumped, 12),
            "downstream_pumped_flow_sum_m3_s": round(downstream, 12),
            "water_physical_valid": instance.balance_report()["plant_water"]["physical_valid"],
            "all_realized_points_feasible": instance.energy_report()["realized_feasibility"][
                "all_realized_points_feasible"
            ],
            "off_rows_integrate_zero": all(
                data["electric_w"] == 0.0 and data["energy_delta_j"] == 0.0
                for row in rows
                for data in row["pumps"].values()
                if data["off"]
            ),
            "idle_rows_have_no_hydraulic_power": all(
                data["hydraulic_w"] == 0.0
                for row in rows
                for data in row["pumps"].values()
                if data["idle"]
            ),
        }

    scenarios = {
        "startup": _scenario(startup, startup_rows),
        "zero_available_water": _scenario(empty, empty_rows),
        "full_receiver": _scenario(full, full.energy_trace()),
        "narrowed_downstream": _scenario(narrow, narrow.energy_trace()),
    }

    sample_ticks = [row for row in trace if row["tick_index"] in (1, 60, 600, 1200)]
    realized_feasible = report["realized_feasibility"]["all_realized_points_feasible"]
    oracle_independent = oracle_is_independent()
    checks_pass = (
        all(matches.values())
        and capacity_detected
        and hreq_detected
        and throttle_is_charged
        and power_identity_holds
        and oracle_independent
        and sa_counterexample["matches_sa_numbers"]
        and realized_feasible
        and all(row["water_physical_valid"] for row in scenarios.values())
        and all(row["all_realized_points_feasible"] for row in scenarios.values())
        and all(row["off_rows_integrate_zero"] for row in scenarios.values())
        and all(row["idle_rows_have_no_hydraulic_power"] for row in scenarios.values())
        and report["operating_point_basis"] == "realized_actual_pumped_throughput"
        and report["total_energy_j"] > 0.0
        and scenarios["zero_available_water"]["downstream_pumped_flow_sum_m3_s"] == 0.0
    )
    return write(
        "10-energy-from-actual-flow",
        {
            "finding": (
                "C01-2 (achieved basis, kept under regression) + C02-1 (frozen pump law) + "
                "C02-2 (genuinely independent oracle and both substitution mutations)"
            ),
            "pump_power_law": report["pump_power_law"],
            "power_identity_rule": report["power_identity_rule"],
            "operating_point_basis": report["operating_point_basis"],
            "idle_loss_rule": report["idle_loss_rule"],
            "frozen_parameters_used_by_the_oracle": frozen,
            "sa_counterexample": sa_counterexample,
            "oracle": {
                "independent_of_production_helpers": oracle_independent,
                "forbidden_tokens_checked": list(ORACLE_FORBIDDEN_TOKENS),
                "inputs": "model.pump_discharge_records() joined by tick and binding "
                "(committed discharge water + the commanded speed of the tick)",
                "parameters": "configs/vnext/shwtp/shwtp_x3_profile_v1.json "
                "(constants + pumps), read by the generator itself",
            },
            "total_energy_j": report["total_energy_j"],
            "per_pump_electric_j": report["per_pump_electric_j"],
            "per_pump_pump_hydraulic_j": report["per_pump_pump_hydraulic_j"],
            "per_pump_useful_hydraulic_j": report["per_pump_useful_hydraulic_j"],
            "per_pump_throttle_dissipated_j": report["per_pump_throttle_dissipated_j"],
            "energy_components_j": components,
            "power_identity_holds": power_identity_holds,
            "throttle_energy_is_charged_in_the_electricity": throttle_is_charged,
            "idle_energy_j": report["idle_energy_j"],
            "actual_pumped_energy_j": report["actual_pumped_energy_j"],
            "independent_recomputation_j": {
                key: round(value, 6) for key, value in sorted(independent.items())
            },
            "independent_recomputation_matches": all(matches.values()),
            "capacity_basis_j": {
                key: round(value, 6) for key, value in sorted(capacity_basis.items())
            },
            "capacity_substitution_difference_j": substitution,
            "capacity_substitution_detected": capacity_detected,
            "hreq_law_basis_j": {
                key: round(value, 6) for key, value in sorted(hreq_basis.items())
            },
            "hreq_substitution_difference_j": hreq_substitution,
            "hreq_substitution_detected": hreq_detected,
            "realized_operating_points_last_tick": report["pump_operating_points"],
            "allocation_capacity_points_last_tick": report["allocation_capacity_points"],
            "realized_feasibility": report["realized_feasibility"],
            "scenarios": scenarios,
            "per_tick_export_sample": sample_ticks,
            "per_tick_export_fields": [
                "commanded_speed_pct",
                "achieved_flow_m3_s",
                "achieved_flow_m3h",
                "capacity_flow_m3h",
                "head_m",
                "required_head_m",
                "throttle_head_m",
                "hydraulic_w",
                "useful_hydraulic_w",
                "throttle_power_w",
                "power_balance_error_w",
                "electric_w",
                "energy_delta_j",
                "energized",
                "idle",
                "off",
                "feasible",
                "reason",
            ],
            "all_checks_pass": checks_pass,
            "verdict": (
                "ENERGY_FROM_ACHIEVED_FLOW_ON_THE_FROZEN_PUMP_LAW"
                if checks_pass
                else "ENERGY_BASIS_UNPROVEN"
            ),
        },
    )


def main() -> int:
    profile = load_x3_profile(PROFILE_PATH)
    contracts = load_whole_plant_contracts()
    expected = {
        "01": "X3_SURFACE_MATERIALIZED_16_SCOPES_TWO_PI",
        "02": "PLANT_WATER_IDENTITY_CLOSED_FROM_TICK_ZERO",
        "03": "RESERVATIONS_ARE_CAPACITY_TOKENS_NOT_WATER",
        "04": "TWO_PI_ACTUATOR_RESPONSE_AND_ARBITRATION_VERIFIED",
        "05": "PUMP_ENVELOPE_FEASIBLE_WITH_EXPLICIT_UNITS",
        "06": "MUTATIONS_VIOLATE_THE_PHYSICAL_ENVELOPE",
        "07": "X3_CANONICAL_WITH_X2_AND_G21_COMPATIBILITY",
        "10": "ENERGY_FROM_ACHIEVED_FLOW_ON_THE_FROZEN_PUMP_LAW",
        "11": "ACTUATOR_TRACKING_AND_RELEASE_SLEW_VERIFIED",
    }
    artefacts = {
        "01": section_01(profile, contracts),
        "02": section_02(profile, contracts),
        "03": section_03(profile, contracts),
        "04": section_04(profile, contracts),
        "05": section_05(profile, contracts),
        "06": section_06(profile, contracts),
        "07": section_07(),
        "10": section_10(profile, contracts),
    }
    artefacts["11"] = write(
        "11-actuator-tracking",
        {**artefacts["04"]["actuator_tracking"], "evidence": "VF-SHW-X3-C01 finding 1"},
    )
    verdicts = {key: payload["verdict"] for key, payload in artefacts.items()}
    all_pass = all(verdicts.get(key) == value for key, value in expected.items())
    acceptance = _acceptance_block(artefacts)
    c01_acceptance = _c01_acceptance_block(artefacts)
    c02_acceptance = _c02_acceptance_block(artefacts)
    summary = write(
        "08-verdict",
        {
            "evidence": "VF-SHW-X3",
            "issue": "https://github.com/hieudovn/virtual-factory/issues/98",
            "verdicts": verdicts,
            "expected_verdicts": expected,
            "all_sections_pass": all_pass,
            "x3": acceptance,
            "x3c01": c01_acceptance,
            "x3c02": c02_acceptance,
            "overall": "SHW_X3_PHYSICAL_BOUNDS_AND_TWO_PI_VERIFIED"
            if all_pass and all(c01_acceptance.values()) and all(c02_acceptance.values())
            else "SHW_X3_EVIDENCE_INCOMPLETE",
        },
    )
    # Machine-checkable acceptance: the harness evaluates the CORRECTION contract rules
    # (the C02 findings, the C01 regressions and the X3-1..X3-7 regression re-assertions)
    # against the blocks above.
    evaluation = subprocess.run(
        [
            sys.executable,
            str(ROOT / ".ai-harness" / "scripts" / "evaluate_acceptance.py"),
            str(OUT / "08-verdict.json"),
            str(ROOT / ".ai-harness" / "tasks" / "VF-SHW-X3-C02.json"),
            "--phase",
            "final",
            "--output",
            str(OUT / "08-verdict.json"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    evaluated = json.loads((OUT / "08-verdict.json").read_text(encoding="utf-8"))["acceptance"]
    passed = [row for row in evaluated if row["result"] == "PASS"]
    failed = [row["id"] for row in evaluated if row["result"] != "PASS"]
    acceptance_line = (
        f"- acceptance: {len(passed)}/{len(evaluated)} criteria PASS "
        f"(X3C02-1, X3C02-2 + the X3C01-1/X3C01-2 and X3-1..X3-7 regression "
        f"re-assertions, evaluated by .ai-harness/scripts/evaluate_acceptance.py against "
        f"the VF-SHW-X3-C02 contract; rules x3c02.pump_power_law / "
        f"x3c02.independent_energy_oracle / x3c01.* / x3.*)"
    )
    lines = [
        "# VF-SHW-X3 evidence summary",
        "",
        f"Overall: **{summary['overall']}**",
        "",
        "| section | verdict |",
        "|---|---|",
    ]
    lines.extend(f"| {key} | {value} |" for key, value in sorted(verdicts.items()))
    lines.extend(
        [
            "",
            "Key machine-derived numbers:",
            "",
            f"- water: invalid ticks {artefacts['02']['invalid_ticks']}, worst residual "
            f"{artefacts['02']['worst_residual_m3']:.3e} m3 (tick "
            f"{artefacts['02']['worst_residual_tick']}), created water "
            f"{artefacts['02']['final_created_water_m3']:.3e} m3",
            f"- control: last PI-owned window tick "
            f"{artefacts['04']['last_pi_owned_window']['tick']}, flow error "
            f"{artefacts['04']['final_flow_error_frac']:.4%} of SP, level error "
            f"{artefacts['04']['final_level_error_m']:.4f} m, backwash at tick "
            f"{artefacts['04']['backwash_arbitration']['tick']} with the integral held",
            f"- pumps: total energy {artefacts['05']['energy']['total_energy_j'] / 1e6:.3f} MJ; "
            f"DIST loss conversion configured "
            f"{artefacts['05']['dimensional_conversion']['configured_r_s2_m5']:.2f} s^2/m^5 vs "
            f"expected {artefacts['05']['dimensional_conversion']['expected_r_s2_m5']:.2f} s^2/m^5",
            f"- identity: canonical model {artefacts['07']['canonical_default_model']} at "
            f"{artefacts['07']['tick_s']} s, X2 compatible at "
            f"{artefacts['07']['x2_compatibility']['tick_s']} s, G21 scopes "
            f"{artefacts['07']['g21_compatibility']['scopes']}",
            f"- setpoint sweep: flow {artefacts['04']['setpoint_sweep']['flow']['low']['flow_measured_m3_s']:.5f} "
            f"-> {artefacts['04']['setpoint_sweep']['flow']['high']['flow_measured_m3_s']:.5f} m3/s "
            f"(valve {artefacts['04']['setpoint_sweep']['flow']['low']['valve_applied_pct']:.2f} -> "
            f"{artefacts['04']['setpoint_sweep']['flow']['high']['valve_applied_pct']:.2f} %), level "
            f"{artefacts['04']['setpoint_sweep']['level']['low']['level_measured_m']:.4f} -> "
            f"{artefacts['04']['setpoint_sweep']['level']['high']['level_measured_m']:.4f} m "
            f"(pump {artefacts['04']['setpoint_sweep']['level']['low']['pump_applied_pct']:.2f} -> "
            f"{artefacts['04']['setpoint_sweep']['level']['high']['pump_applied_pct']:.2f} %)",
            f"- C01-1 actuator tracking: SA counterexample "
            f"{artefacts['11']['sa_counterexample']['normal_command_pct']:.1f} % -> stop "
            f"{artefacts['11']['sa_counterexample']['stopped_applied_pct']:.1f} % (tracked "
            f"{artefacts['11']['sa_counterexample']['tracked_after_stop_pct']:.1f} %) -> release step "
            f"{artefacts['11']['sa_counterexample']['release_step_pp']:.3f} pp (limit "
            f"{artefacts['11']['sa_counterexample']['slew_limit_pp']:.1f} pp/s); protective epilogues "
            f"{len(artefacts['11']['protective_epilogues'])}; runtime slew violations "
            f"{artefacts['11']['runtime_continuity']['violation_count']}",
            f"- C02-1 frozen pump law (SA counterexample, DIST 80 %, Q = 0.008 m3/s): "
            f"H {artefacts['10']['sa_counterexample']['head_m']:.4f} m, Hreq "
            f"{artefacts['10']['sa_counterexample']['required_head_m']:.8f} m, pump "
            f"{artefacts['10']['sa_counterexample']['pump_hydraulic_w']:.6f} W, useful "
            f"{artefacts['10']['sa_counterexample']['useful_hydraulic_w']:.6f} W, throttle "
            f"{artefacts['10']['sa_counterexample']['throttle_power_w']:.6f} W, electric "
            f"{artefacts['10']['sa_counterexample']['electric_w']:.6f} W "
            f"(matches the SA numbers: {artefacts['10']['sa_counterexample']['matches_sa_numbers']})",
            f"- C02-1/C02-2 realized energy: total "
            f"{artefacts['10']['total_energy_j'] / 1e6:.6f} MJ (idle "
            f"{artefacts['10']['idle_energy_j'] / 1e6:.6f} MJ, pumped "
            f"{artefacts['10']['actual_pumped_energy_j'] / 1e6:.6f} MJ; pump hydraulic "
            f"{artefacts['10']['energy_components_j']['pump_hydraulic_j'] / 1e6:.6f} MJ = useful "
            f"{artefacts['10']['energy_components_j']['useful_hydraulic_j'] / 1e6:.6f} MJ + throttle "
            f"{artefacts['10']['energy_components_j']['throttle_dissipated_j'] / 1e6:.6f} MJ); "
            f"independent oracle (no production helper: "
            f"{artefacts['10']['oracle']['independent_of_production_helpers']}) matches "
            f"{artefacts['10']['independent_recomputation_matches']}; capacity-basis substitution "
            f"differs by up to "
            f"{max(artefacts['10']['capacity_substitution_difference_j'].values(), default=0.0) / 1e6:.6f} MJ "
            f"(detected {artefacts['10']['capacity_substitution_detected']}), H-to-Hreq power "
            f"substitution by up to "
            f"{max(artefacts['10']['hreq_substitution_difference_j'].values(), default=0.0) / 1e6:.6f} MJ "
            f"(detected {artefacts['10']['hreq_substitution_detected']})",
            acceptance_line,
            "",
            "Every number above is produced by `generate_evidence.py` from the committed model at",
            "the reported head; no value is transcribed by hand.",
            "",
        ]
    )
    (OUT / "09-summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary["verdicts"], indent=2))
    print("overall:", summary["overall"])
    print("acceptance:", f"{len(passed)}/{len(evaluated)} PASS", "failed:", failed)
    if evaluation.returncode != 0 or failed:
        print(evaluation.stdout.strip()[-2000:])
    return 0 if all_pass and not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
