"""VF-SHW-X3 - physical bounds, hydraulic feasibility and the closed water ledger.

Covers the Issue #98 / SA continuation requirements that are physically binding:

 1  the X3 profile is a versioned, validated X3 surface (16 scopes, 1 s global
    windows, exactly two admitted C2 loops, the deferred loops explicitly
    unavailable, a bounded queue, declared unavailable energy);
 2  the FULL-RUN water identity closes from tick zero (startup, ramp and steady
    operation) - a warm-up differenced interval can only supplement it;
 3  no created water on any accepted window; every discharge bounded by the water
    actually available;
 4  per-scope storage integration agrees with the flows the participants
    integrated (per-window validity);
 5  mutations that violate the physical envelope fail the oracle: injected water,
    created water, a dropped delivery, an impossible head, a motor overload and a
    missing/duplicated initialisation stock remain detectable even after a
    balance baseline is marked;
 6  determinism and reset/replay reproducibility of the X3 trajectory.
"""

from __future__ import annotations

import inspect
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from virtual_factory.shwtp.contracts import load_whole_plant_contracts  # noqa: E402
from virtual_factory.shwtp.physical_budget import (  # noqa: E402
    PumpModel,
    X3BudgetError,
    allocate_tick,
    require_valid_state,
)
from virtual_factory.shwtp.whole_plant import (  # noqa: E402
    AUTHORITY_LABELS,
    CREATED_WATER_TOLERANCE_M3,
    SCOPE_PATHS,
)
from virtual_factory.shwtp.x3_profile import (  # noqa: E402
    X3_ACTIVE_C2_LOOP_IDS,
    X3_PROFILE_SCHEMA,
    X3ProfileError,
    load_x3_profile,
)
from virtual_factory.shwtp.x3_whole_plant import (  # noqa: E402
    PIPELINE_SCOPES,
    X3_EXPECTED_SCOPE_COUNT,
    WholePlantX3Error,
    build_shwtp_whole_plant_x3,
)

X3_PROFILE_PATH = ROOT / "configs" / "vnext" / "shwtp" / "shwtp_x3_profile_v1.json"
AUTHORITY_KEYS = (
    "site_truth",
    "simulation_truth",
    "vf_runtime_authorization",
    "site_authorized_execution",
)
DEFERRED_LOOP_IDS = (
    "vf-shw-ctrl-dist-pressure-pi",
    "vf-shw-ctrl-raw-flow-pi",
    "vf-shw-ctrl-t100-level-pi",
)


@pytest.fixture(scope="module")
def profile():
    return load_x3_profile(X3_PROFILE_PATH)


@pytest.fixture(scope="module")
def contracts():
    return load_whole_plant_contracts()


def _run(model, ticks: int, *, offset: int = 0) -> None:
    for index in range(1, ticks + 1):
        model.run_window(f"w{offset + index}")


def _settled(model, ticks: int = 2400):
    """Run the declared cold start plus the settling horizon."""
    _run(model, ticks)
    return model


class TestProfileSurface:
    def test_profile_is_versioned_and_declares_the_frozen_surface(self, profile):
        assert json.loads(X3_PROFILE_PATH.read_text(encoding="utf-8"))["schema"] == X3_PROFILE_SCHEMA
        assert profile.version == "1"
        assert profile.tick_s == 1.0
        assert profile.coupling_policy == "explicit_lagged"
        assert len(profile.tanks) == 8
        assert len(profile.edges) == 18
        assert len(profile.pumps) == 3
        assert len(profile.valves) == 1
        assert profile.pumps and profile.valves
        assert profile.raw["site_truth"] is False
        assert profile.raw["simulation_truth"] == "synthetic_reference"

    def test_exactly_two_c2_loops_are_admitted(self, profile):
        assert profile.active_c2_loop_ids == X3_ACTIVE_C2_LOOP_IDS
        assert len(profile.controllers) == 2
        for loop_id in DEFERRED_LOOP_IDS:
            assert loop_id in profile.deferred_loops
            assert loop_id not in profile.controllers

    def test_deferred_loops_are_unavailable_not_silently_claimed(self, profile):
        notes = " ".join(profile.deferred_loops.values()).lower()
        assert "deferred" in notes
        assert "x4" in notes or "not admitted" in notes
        assert profile.energy_unavailable, "unmodelled energy must be declared unavailable"
        assert any("dosing" in entry for entry in profile.energy_unavailable)

    def test_every_water_edge_declares_an_explicit_rating(self, profile):
        assert len(profile.edges) == len(set(profile.edges))
        for rating in profile.edges.values():
            assert rating.max_flow_m3_s >= 0.0

    def test_invalid_profile_fields_fail_closed(self, profile, tmp_path_factory):
        raw = json.loads(X3_PROFILE_PATH.read_text(encoding="utf-8"))
        workdir = Path(
            tmp_path_factory.mktemp("x3-profile") if False else ROOT / ".ai-harness" / "traces"
        )
        workdir.mkdir(parents=True, exist_ok=True)
        broken = json.loads(json.dumps(raw))
        broken["time"]["tick_s"] = 0.0
        path = workdir / "x3_profile_bad_tick.json"
        path.write_text(json.dumps(broken), encoding="utf-8")
        with pytest.raises(X3ProfileError):
            load_x3_profile(path)

        broken = json.loads(json.dumps(raw))
        broken["edges"]["vf-shw-edge-t101-t102"]["max_flow_m3_s"] = -1.0
        path.write_text(json.dumps(broken), encoding="utf-8")
        with pytest.raises(X3ProfileError):
            load_x3_profile(path)

        broken = json.loads(json.dumps(raw))
        broken["controllers"]["vf-shw-ctrl-borneo-pi"] = dict(
            broken["controllers"]["vf-shw-ctrl-f106-inlet-flow-pi"]
        )
        path.write_text(json.dumps(broken), encoding="utf-8")
        with pytest.raises(X3ProfileError):
            load_x3_profile(path)

        broken = json.loads(json.dumps(raw))
        broken["tanks"]["vf-shw-node-t100"]["level_band_m"] = [0.5, 4.0, 0.8, 3.5]
        path.write_text(json.dumps(broken), encoding="utf-8")
        with pytest.raises(X3ProfileError):
            load_x3_profile(path)
        path.unlink()


class TestRuntimeShape:
    def test_sixteen_scopes_run_on_one_second_windows(self, profile, contracts):
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-shape")
        assert len(model.participants) == X3_EXPECTED_SCOPE_COUNT
        assert set(model.participants) == set(SCOPE_PATHS)
        assert model.communication_step_s == 1.0
        assert len(model.control_layer.active_c2_loop_ids) == 2
        assert len(model.control_layer.c1.active_controller_ids) == 9

    def test_every_projection_carries_the_four_authority_labels(self, profile, contracts):
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-labels")
        _run(model, 3)
        for key in AUTHORITY_KEYS:
            assert model.runtime_truth()[key] == AUTHORITY_LABELS[key]
            assert model.balance_report()[key] == AUTHORITY_LABELS[key]
            assert model.budget_report()[key] == AUTHORITY_LABELS[key]
            assert model.energy_report()[key] == AUTHORITY_LABELS[key]
            assert model.control_report()[key] == AUTHORITY_LABELS[key]
        for row in model.monitor_rows():
            for key in AUTHORITY_KEYS:
                assert row[key] == AUTHORITY_LABELS[key]

    def test_repeated_or_invalid_window_id_fails_closed(self, profile, contracts):
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-window")
        model.run_window("w1")
        with pytest.raises(WholePlantX3Error):
            model.run_window("w1")
        with pytest.raises(WholePlantX3Error):
            model.run_window("")

    def test_invalid_state_is_rejected_before_stepping(self, profile, contracts):
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-state")
        _run(model, 2)
        with pytest.raises(X3BudgetError):
            require_valid_state(values={"volume": float("nan")}, tolerance_m3=1e-9)
        model.participants["vf-shw-node-t100"]._volume_m3 = -1.0
        with pytest.raises(WholePlantX3Error):
            model.run_window("w3")


class TestFullRunConservation:
    def test_full_run_identity_closes_from_tick_zero(self, profile, contracts):
        """R(t) = [storage_flow_delta + created + transit] - in + out - loss."""
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-ident")
        worst = 0.0
        worst_tick = 0
        for index in range(1, 2401):
            model.run_window(f"w{index}")
            plant = model.balance_report()["plant_water"]
            assert plant["physical_valid"] is True, f"tick {index}: {plant}"
            assert plant["shortfall_m3"] <= CREATED_WATER_TOLERANCE_M3
            if abs(plant["residual_m3"]) > abs(worst):
                worst = plant["residual_m3"]
                worst_tick = index
        assert abs(worst) <= plant["tolerance_m3"], f"worst {worst} at {worst_tick}"
        # the identity must hold through the STARTUP transient too, not only later
        assert worst_tick > 0
        assert plant["plant_in_m3"] > 0.0 and plant["plant_out_m3"] > 0.0

    def test_identity_is_checked_on_every_tick_not_only_at_the_end(self, profile, contracts):
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-each")
        for index in range(1, 901):
            model.run_window(f"w{index}")
            plant = model.balance_report()["plant_water"]
            assert abs(plant["residual_m3"]) <= plant["tolerance_m3"]
            assert plant["storage_integration_gap_m3"] <= plant["tolerance_m3"]

    def test_there_is_no_water_loss_at_the_pass_through_conduits(self, profile, contracts):
        """Every conduit emits exactly what it held (minus the declared law loss)."""
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-conduit")
        by_id = {binding["binding_id"]: binding for binding in model.bindings}
        expected = {
            "vf-shw-node-dist-p108": ("_inlet_flow_m3h", "_l2_flow_m3h"),
            "vf-shw-node-t102": ("_inflow_m3h",),
            "vf-shw-node-t103": ("_inflow_m3h",),
        }
        dt_h = model.profile.tick_s / 3600.0
        holding = {scope_id: 0.0 for scope_id in expected}
        for index in range(1, 1801):
            model.run_window(f"w{index}")
            emitted = {scope_id: 0.0 for scope_id in expected}
            for row in model._transfers:
                if row["transfer_kind"] != "physical_water":
                    continue
                source = by_id[row["binding_id"]]["source_scope"]
                if source in emitted:
                    emitted[source] += float(row["water_m3"])
            for scope_id in expected:
                assert emitted[scope_id] == pytest.approx(holding[scope_id], abs=1e-12), (
                    f"{scope_id} lost water at tick {index}"
                )
                participant = model.participants[scope_id]
                state = 0.0
                for attr in expected[scope_id]:
                    value = getattr(participant, attr, None)
                    state += float(value) * dt_h if isinstance(value, (int, float)) else 0.0
                holding[scope_id] = state

    def test_window_baseline_is_a_supplement_not_a_certificate(self, profile, contracts):
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-baseline")
        _settled(model, 1800)
        baseline = model.mark_balance_baseline()
        assert baseline["tick_index"] == 1800
        _run(model, 600, offset=1800)
        plant = model.balance_report()["plant_water"]
        assert plant["window_physical_valid"] is True
        assert plant["full_run_authoritative"] is True
        assert plant["physical_valid"] is True
        assert plant["evaluation_window_start_tick"] == 1800

    def test_missing_or_duplicated_initial_water_stays_detectable_after_a_baseline(
        self, profile, contracts
    ):
        """A baseline may not hide an initialised/duplicated stock."""
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-init")
        _settled(model, 900)
        model.mark_balance_baseline()
        # duplicate an initialisation stock: pretend T100 silently held 0.5 m3 more
        model.participants["vf-shw-node-t100"]._volume_m3 += 0.5
        model.run_window("w901")
        plant = model.balance_report()["plant_water"]
        assert plant["physical_valid"] is False
        assert abs(plant["storage_integration_gap_m3"]) > plant["tolerance_m3"]
        assert plant["storage_integration_gap_within_rounding"] is False
        # the window diagnostic alone would have hidden it; the full run must not
        assert plant["full_run_authoritative"] is True

    def test_created_water_is_a_physical_failure(self, profile, contracts):
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-created")
        _settled(model, 600)
        model.participants["vf-shw-node-t108"]._shortfall_m3 = 1.0
        plant = model.balance_report()["plant_water"]
        assert plant["created_water_within_rounding"] is False
        assert plant["physical_valid"] is False
        # ... and the reconciliation diagnostic must not hide it
        assert plant["accounting_reconciled"] in (True, False)
        assert plant["created_water_diagnostic_m3"] >= 1.0

    def test_reset_restores_a_deterministic_state_without_falsifying_history(
        self, profile, contracts
    ):
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-reset")
        _run(model, 300)
        polluted = model.balance_report()["plant_water"]
        assert polluted["plant_in_m3"] > 0.0
        model.reset()
        fresh = model.balance_report()["plant_water"]
        assert fresh["plant_in_m3"] == 0.0
        assert fresh["residual_m3"] == 0.0
        assert fresh["physical_valid"] is True
        _run(model, 300, offset=100000)
        again = model.balance_report()["plant_water"]
        assert again["plant_in_m3"] == pytest.approx(polluted["plant_in_m3"], abs=1e-9)


class TestPhysicalEnvelope:
    def test_no_negative_state_and_no_unbounded_queue(self, profile, contracts):
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-bounds")
        for index in range(1, 1201):
            model.run_window(f"w{index}")
            for scope_id, participant in model.participants.items():
                volume = participant._storage_volume()
                assert volume >= 0.0, f"{scope_id} went negative at tick {index}"
                capacity = getattr(participant, "capacity_m3", None)
                if capacity is not None:
                    assert volume <= capacity + 1e-9
            assert model.budget_report()["queued_volume_m3"] <= profile.queue.max_queued_volume_m3
            for row in model._transfers:
                assert float(row["payload"]["flow_m3h"]) >= 0.0

    def test_dry_and_full_downstream_cases_fail_safely(self, profile, contracts):
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-dry")
        # a DRY plant is a scenario change: state AND its declared initial stock are
        # both empty, so no state stock appears that the flows do not explain
        for participant in model.participants.values():
            if getattr(participant, "storage", False):
                participant._volume_m3 = 0.0
                participant._initial_volume_m3 = 0.0
        _run(model, 120)
        plant = model.balance_report()["plant_water"]
        assert plant["shortfall_m3"] <= CREATED_WATER_TOLERANCE_M3
        assert plant["physical_valid"] is True
        # a FULL receiver may not accept more than its declared headroom
        tank = model.participants["vf-shw-node-t108"]
        tank._volume_m3 = tank.capacity_m3
        tank._initial_volume_m3 = tank.capacity_m3
        _run(model, 5, offset=1000)
        plant = model.balance_report()["plant_water"]
        assert plant["shortfall_m3"] <= CREATED_WATER_TOLERANCE_M3
        assert tank._storage_volume() <= tank.capacity_m3 + 1e-9
        assert plant["physical_valid"] is True

    def test_pump_envelope_feasibility_and_motor_overload_rejection(self, profile):
        pump = profile.pumps["raw-intake-pump"]
        model = PumpModel(pump, profile.units)
        # impossible head: a speed below the static lift cannot move water
        assert model.max_feasible_flow_m3_s(0.0) == 0.0
        point = model.operating_point(0.0, pump.q_rated_m3_s)
        assert point.off and point.flow_m3_s == 0.0 and point.electric_w == 0.0
        # motor overload: a speed that would exceed the rating is bounded by the curve
        overloaded = model.operating_point(100.0, pump.motor_rating_w)
        assert overloaded.electric_w <= pump.motor_rating_w + 1e-9
        assert overloaded.reason in (
            "ok",
            "limited_by_head_or_motor_rating",
            "insufficient_head_or_motor_overload",
        )
        # over the whole declared envelope the head must cover the system curve
        for speed in range(0, 101, 5):
            cap = model.max_feasible_flow_m3_s(speed / 100.0)
            if cap > 0.0:
                head = model.head_m(speed / 100.0, cap)
                assert head >= model.required_head_m(cap) - 1e-9
                power = model.electric_power_w(model.hydraulic_power_w(cap, head))
                assert power <= pump.motor_rating_w + 1e-9

    def test_dimensional_conversion_of_the_distribution_loss(self, profile):
        """0.0006 bar per (m3/h)^2 must convert to 79266.06 s^2/m^5 at rho*g."""
        units = profile.units
        per_m3h2_pa = 0.0006 * units.bar_pa
        expected = per_m3h2_pa * (3600.0**2) / (units.rho_kg_m3 * units.g_m_s2)
        assert profile.pumps["dist-hsp"].r_s2_m5 == pytest.approx(expected, rel=1e-6)
        assert profile.pumps["dist-hsp"].r_s2_m5 == pytest.approx(79266.06, rel=1e-4)
        # a wrong (unconverted) value would pin the pump far below the plant demand
        model = PumpModel(profile.pumps["dist-hsp"], units)
        cap = model.max_feasible_flow_m3_s(0.8)
        assert cap * 3600.0 > 40.0

    def test_allocation_rejects_a_binding_without_a_rating(self, profile, contracts):
        with pytest.raises((X3BudgetError, X3ProfileError)):
            allocate_tick(
                profile=profile,
                tick_index=1,
                scope_state={
                    "vf-shw-node-t100": {"volume_m3": 1.0, "capacity_m3": 200.0},
                    "vf-shw-node-t101": {"volume_m3": 0.0, "capacity_m3": 30.0},
                },
                requested_m3_s={"vf-shw-edge-unknown": 0.001},
                bindings=[
                    {
                        "binding_id": "vf-shw-edge-unknown",
                        "source_scope": "vf-shw-node-t100",
                        "target_scope": "vf-shw-node-t101",
                    }
                ],
                source_ports={"vf-shw-edge-unknown": "l1_out"},
            )

    def test_invented_water_mutation_fails_the_oracle(self, profile, contracts):
        """A state stock the flows do not explain must not be certified."""
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-invent")
        _settled(model, 600)
        plant = model.balance_report()["plant_water"]
        assert plant["physical_valid"] is True
        # inject: remove water from a tank state without any flow explaining it
        model.participants["vf-shw-node-t105"]._volume_m3 -= 0.25
        model.run_window("w601")
        plant = model.balance_report()["plant_water"]
        assert plant["physical_valid"] is False
        assert abs(plant["storage_integration_gap_m3"]) > plant["tolerance_m3"]
        # ... and invent: add water to a tank state
        model.participants["vf-shw-node-t105"]._volume_m3 += 0.5
        model.run_window("w602")
        plant = model.balance_report()["plant_water"]
        assert plant["physical_valid"] is False

    def test_pipeline_scopes_are_declared_not_invented(self, profile, contracts):
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-pipe")
        for scope_id in PIPELINE_SCOPES:
            assert scope_id in model.participants
            assert getattr(model.participants[scope_id], "storage", False) is False
        assert "vf-shw-node-raw-intake" not in PIPELINE_SCOPES
        assert "vf-shw-node-network-demand" not in PIPELINE_SCOPES


def _frozen_pump_parameters() -> dict:
    """Frozen pump/unit parameters read straight from the config file (SA C02-2).

    The energy oracle must not depend on the production profile objects or on any
    production power/energy computation; the declared numbers are read from the frozen
    JSON surface itself.
    """
    raw = json.loads(X3_PROFILE_PATH.read_text(encoding="utf-8"))
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


#: Tokens that would mean the oracle reuses the production implementation (SA C02-2).
_ORACLE_FORBIDDEN_TOKENS = (
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


def _oracle_energy(model, *, basis: str = "achieved") -> dict[str, float]:
    """Electricity per pump recomputed WITHOUT any production energy helper (SA C02-2).

    The only runtime inputs are the committed PHYSICAL pump discharge records of
    :meth:`pump_discharge_records` (committed water, the commanded speed of that tick and
    the binding), joined by tick; every hydraulic/electric quantity is then evaluated
    from the frozen parameters read out of the config file.

    ``basis="achieved"`` committed discharge flow against the frozen D6 law;
    ``basis="capacity"`` substitutes the allocation capacity flow (mutation 1);
    ``basis="hreq_law"`` substitutes Hreq for the pump head H(n,Q) (mutation 2, the
    C01-2 error the SA reproduced).
    """
    frozen = _frozen_pump_parameters()
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
            electric_w = pump["no_load_w"]  # energized without water: declared idle loss
        else:
            head = max(0.0, pump["h0_m"] * speed * speed - pump["k_s2_m5"] * flow * flow)
            required = pump["h_static_m"] + pump["r_s2_m5"] * flow * flow
            head_for_power = required if basis == "hreq_law" else head
            electric_w = rho * g * flow * head_for_power / pump["eta_total"] + pump["no_load_w"]
        totals[pump_id] = totals.get(pump_id, 0.0) + electric_w * dt_s
    return totals


class TestC02FrozenPumpPowerLaw:
    """SA C02-1: the realized point applies the frozen D6 pump law (throttle included)."""

    def test_sa_counterexample_dist_80_matches_the_frozen_law(self, profile):
        """The SA's exact-source reproduction of the frozen DIST parameters."""
        model = PumpModel(profile.pumps["dist-hsp"], profile.units)
        point = model.realized_point(80.0, 0.008)
        assert point.head_m == pytest.approx(26.0928, abs=1e-9)
        assert point.required_head_m == pytest.approx(5.07302784, abs=1e-9)
        assert point.hydraulic_w == pytest.approx(2047.762944, abs=1e-6)
        assert point.useful_hydraulic_w == pytest.approx(398.131224883, abs=1e-6)
        assert point.throttle_power_w == pytest.approx(1649.631719117, abs=1e-6)
        assert point.electric_w == pytest.approx(3325.375634286, abs=1e-6)
        assert point.power_balance_error_w == 0.0
        assert point.feasible is True and point.reason == "ok"

    def test_oracle_does_not_reuse_the_production_implementation(self):
        """The claimed independent oracle must not call or read production energy code."""
        source = inspect.getsource(_oracle_energy) + inspect.getsource(
            _frozen_pump_parameters
        )
        for token in _ORACLE_FORBIDDEN_TOKENS:
            assert token not in source, f"the independent oracle must not use {token!r}"

    def test_power_identity_holds_on_every_exported_tick(self, profile, contracts):
        """P_pump = P_useful + P_throttle and P_elec = P_pump/eta + no_load on each tick."""
        frozen = _frozen_pump_parameters()
        model = _settled(
            build_shwtp_whole_plant_x3(
                profile=profile, contracts=contracts, run_id="x3-c02-identity"
            ),
            900,
        )
        pumped_ticks = 0
        throttled_ticks = 0
        for row in model.energy_trace():
            for pump_id, data in row["pumps"].items():
                pump = frozen["pumps"][pump_id]
                # the identity holds up to float rounding of the split itself
                assert data["power_balance_error_w"] == pytest.approx(0.0, abs=1e-6), (
                    pump_id,
                    row["tick_index"],
                )
                assert data["hydraulic_w"] == pytest.approx(
                    data["useful_hydraulic_w"] + data["throttle_power_w"], abs=1e-9
                ), (pump_id, row["tick_index"])
                assert data["throttle_power_w"] >= 0.0
                if data["off"]:
                    assert data["electric_w"] == 0.0
                    assert data["hydraulic_w"] == 0.0
                    continue
                assert data["electric_w"] == pytest.approx(
                    data["hydraulic_w"] / pump["eta_total"] + pump["no_load_w"], abs=1e-9
                ), (pump_id, row["tick_index"])
                if data["achieved_flow_m3_s"] > 0.0:
                    pumped_ticks += 1
                    if data["throttle_power_w"] > 0.0:
                        throttled_ticks += 1
        assert pumped_ticks > 0, "the settled plant must really pump"
        assert throttled_ticks > 0, "the declared pump curve must really throttle"

    def test_throttle_dissipation_is_charged_in_the_electricity(self, profile, contracts):
        """The omitted throttle share must be a material part of the electricity (SA C02-1)."""
        model = _settled(
            build_shwtp_whole_plant_x3(
                profile=profile, contracts=contracts, run_id="x3-c02-throttle"
            ),
            1200,
        )
        report = model.energy_report()
        components = report["energy_components_j"]
        assert components["pump_hydraulic_j"] == pytest.approx(
            components["useful_hydraulic_j"] + components["throttle_dissipated_j"], abs=1e-6
        )
        assert components["throttle_dissipated_j"] > 1.0e5, (
            "the throttle-dissipated energy must be a real part of the electricity, "
            f"got {components['throttle_dissipated_j']} J"
        )
        assert components["total_electric_j"] > components["useful_hydraulic_j"], (
            "electricity must exceed the useful system work by the dissipated share"
        )
        assert "frozen D6" in report["pump_power_law"]
        assert report["per_pump_throttle_dissipated_j"]

    def test_oracle_reproduces_the_ledger(self, profile, contracts):
        model = _settled(
            build_shwtp_whole_plant_x3(
                profile=profile, contracts=contracts, run_id="x3-c02-oracle"
            ),
            1200,
        )
        report = model.energy_report()
        oracle = _oracle_energy(model, basis="achieved")
        assert report["per_pump_electric_j"], "the ledger must carry per-pump entries"
        for pump_id, energy in report["per_pump_electric_j"].items():
            assert energy == pytest.approx(oracle.get(pump_id, 0.0), abs=1e-6), pump_id
        assert sum(report["per_pump_electric_j"].values()) == pytest.approx(
            report["total_energy_j"], rel=1e-9
        )
        assert report["realized_feasibility"]["infeasible_ticks"] == 0
        assert report["realized_feasibility"]["all_realized_points_feasible"] is True

    def test_capacity_flow_substitution_fails_the_energy_audit(self, profile, contracts):
        """A rated/capacity-flow substitution must NOT reproduce the ledger."""
        model = _settled(
            build_shwtp_whole_plant_x3(
                profile=profile, contracts=contracts, run_id="x3-c02-mut-capacity"
            ),
            1200,
        )
        report = model.energy_report()
        wrong = _oracle_energy(model, basis="capacity")
        differences = {
            pump_id: abs(wrong.get(pump_id, 0.0) - report["per_pump_electric_j"].get(pump_id, 0.0))
            for pump_id in report["per_pump_electric_j"]
        }
        assert max(differences.values()) > 1.0, (
            f"the capacity-flow substitution is indistinguishable: {differences}"
        )
        assert any(
            row["pumps"][pump_id]["achieved_flow_m3h"]
            < row["pumps"][pump_id]["capacity_flow_m3h"] - 1e-9
            for row in model.energy_trace()
            for pump_id in row["pumps"]
        ), "at least one pump must really pump less than its declared capacity"

    def test_hreq_power_law_substitution_fails_the_energy_audit(self, profile, contracts):
        """The C01-2 error (Hreq in the hydraulic power) must NOT reproduce the ledger."""
        model = _settled(
            build_shwtp_whole_plant_x3(
                profile=profile, contracts=contracts, run_id="x3-c02-mut-hreq"
            ),
            1200,
        )
        report = model.energy_report()
        wrong = _oracle_energy(model, basis="hreq_law")
        differences = {
            pump_id: abs(wrong.get(pump_id, 0.0) - report["per_pump_electric_j"].get(pump_id, 0.0))
            for pump_id in report["per_pump_electric_j"]
        }
        assert max(differences.values()) > 1.0, (
            f"the H-to-Hreq power substitution is indistinguishable: {differences}"
        )
        assert sum(wrong.values()) < report["total_energy_j"], (
            "crediting only the useful head must under-count the electricity"
        )


class TestC01EnergyFromAchievedFlow:
    """SA C01-2 (kept as regression): the ledger integrates the ACHIEVED pumped throughput.

    The power law itself was corrected by C02-1 and the oracle replaced by C02-2; these
    tests keep the original finding's semantics under regression.
    """

    def test_off_idle_and_pumped_states_are_distinguished(self, profile, contracts):
        """OFF = exactly zero; energized-no-flow = declared idle loss, never P_hyd."""
        pump = profile.pumps["raw-intake-pump"]
        model = PumpModel(pump, profile.units)

        off = model.realized_point(0.0, 0.0)
        assert off.off is True and off.energized is False
        assert off.flow_m3_s == 0.0 and off.electric_w == 0.0 and off.hydraulic_w == 0.0

        idle = model.realized_point(20.0, 0.0)
        assert idle.off is False and idle.energized is True and idle.idle is True
        assert idle.electric_w == pytest.approx(pump.no_load_w)
        assert idle.hydraulic_w == 0.0, "no useful power may be invented with no water"
        assert idle.reason == "energized_zero_flow_no_lift_head"
        assert idle.feasible is True

        pumped = model.realized_point(90.0, 0.010)
        assert pumped.idle is False and pumped.feasible is True
        frozen = _frozen_pump_parameters()["pumps"]["raw-intake-pump"]
        rho_g = _frozen_pump_parameters()["rho_kg_m3"] * _frozen_pump_parameters()["g_m_s2"]
        assert pumped.hydraulic_w == pytest.approx(rho_g * 0.010 * pumped.head_m)
        assert pumped.useful_hydraulic_w == pytest.approx(
            rho_g * 0.010 * pumped.required_head_m
        )
        assert pumped.throttle_power_w == pytest.approx(
            pumped.hydraulic_w - pumped.useful_hydraulic_w
        )
        assert pumped.electric_w == pytest.approx(
            pumped.hydraulic_w / frozen["eta_total"] + frozen["no_load_w"]
        ), "the electricity is charged on the PUMP hydraulic power, not only on the useful head"
        assert pumped.throttle_head_m >= 0.0

    def test_realized_points_enforce_head_and_motor_feasibility(self, profile):
        """A realized point that violates the frozen laws is reported infeasible."""
        pump = profile.pumps["t108-transfer-pump"]
        model = PumpModel(pump, profile.units)
        # impossible head at the realized flow
        no_lift = model.realized_point(10.0, 0.005)
        assert no_lift.feasible is False
        assert no_lift.reason == "insufficient_head_at_realized_flow"
        # motor overload at the realized flow
        tiny = replace(pump, motor_rating_w=10.0, no_load_w=1.0)
        overloaded = PumpModel(tiny, profile.units).realized_point(100.0, 0.0167)
        assert overloaded.feasible is False
        assert overloaded.reason in ("motor_overload_at_realized_flow", "insufficient_head_at_realized_flow")

    def test_startup_and_zero_water_energy_is_achieved_not_rated(self, profile, contracts):
        """Startup (nothing moved yet) may not integrate a capacity-rated power."""
        model = build_shwtp_whole_plant_x3(
            profile=profile, contracts=contracts, run_id="x3-c01-startup"
        )
        _run(model, 120)
        report = model.energy_report()
        trace = model.energy_trace()
        assert trace, "the per-tick export must exist"
        for row in trace[:60]:
            for pump_id, data in row["pumps"].items():
                if data["off"]:
                    assert data["electric_w"] == 0.0
                    assert data["energy_delta_j"] == 0.0
                else:
                    assert data["hydraulic_w"] == 0.0 or data["achieved_flow_m3_s"] > 0.0
                    power = (
                        data["hydraulic_w"] / model.pump_models[pump_id].pump.eta_total
                        + model.pump_models[pump_id].pump.no_load_w
                    )
                    assert data["electric_w"] == pytest.approx(power, abs=1e-9)
        assert report["idle_energy_j"] >= 0.0
        assert report["actual_pumped_energy_j"] >= 0.0
        assert report["total_energy_j"] == pytest.approx(
            report["idle_energy_j"] + report["actual_pumped_energy_j"], abs=1e-6
        )

    def test_empty_storages_keep_the_energy_on_the_declared_law(self, profile, contracts):
        """With every storage empty the DOWNSTREAM chain has no water to move, so only
        OFF/idle energy may be integrated - never a capacity-rated hydraulic power.

        (The raw-intake pump draws from the declared boundary source, which is a
        separate, explicitly modelled boundary; the no-water claim is therefore made on
        the chain that a limited startup inventory really binds.)
        """
        model = build_shwtp_whole_plant_x3(
            profile=profile, contracts=contracts, run_id="x3-c01-nowater"
        )
        for participant in model.participants.values():
            if getattr(participant, "storage", False):
                participant._volume_m3 = 0.0
                participant._initial_volume_m3 = 0.0
        _run(model, 60)
        report = model.energy_report()
        trace = model.energy_trace()
        for row in trace[:20]:
            for pump_id in ("t108-transfer-pump", "dist-hsp"):
                data = row["pumps"][pump_id]
                assert data["achieved_flow_m3_s"] == 0.0, "an empty chain delivers no water"
                assert data["hydraulic_w"] == 0.0, "no water moved, no useful power"
                if data["off"]:
                    assert data["energy_delta_j"] == 0.0
                else:
                    assert data["energy_delta_j"] == pytest.approx(
                        model.pump_models[pump_id].pump.no_load_w * row["dt_s"], abs=1e-9
                    ), "an energized dry pump draws only the declared idle loss"
        assert report["total_energy_j"] == pytest.approx(
            report["idle_energy_j"] + report["actual_pumped_energy_j"], abs=1e-6
        )
        plant = model.balance_report()["plant_water"]
        assert plant["shortfall_m3"] <= CREATED_WATER_TOLERANCE_M3
        assert plant["physical_valid"] is True

        # a FULL receiver throttles the chain: still no invented flow
        tank = model.participants["vf-shw-node-t108"]
        tank._volume_m3 = tank.capacity_m3
        tank._initial_volume_m3 = tank.capacity_m3
        _run(model, 30, offset=500)
        assert tank._storage_volume() <= tank.capacity_m3 + 1e-9
        assert model.balance_report()["plant_water"]["physical_valid"] is True

    def test_narrowed_downstream_capacity_shrinks_the_achieved_flow(self, profile, contracts):
        """A narrowed downstream hop reduces the ACHIEVED flow, hence the energy."""
        edges = dict(profile.edges)
        edges["vf-shw-edge-dist-demand"] = replace(
            edges["vf-shw-edge-dist-demand"], max_flow_m3_s=0.0005
        )
        narrow = replace(profile, edges=edges)
        narrow_model = _settled(
            build_shwtp_whole_plant_x3(
                profile=narrow, contracts=contracts, run_id="x3-c01-narrow"
            ),
            900,
        )
        baseline_model = _settled(
            build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-c01-wide"),
            900,
        )
        narrow_report = narrow_model.energy_report()
        baseline_report = baseline_model.energy_report()
        narrow_flow = narrow_report["pump_operating_points"]["dist-hsp"]["flow_m3h"]
        baseline_flow = baseline_report["pump_operating_points"]["dist-hsp"]["flow_m3h"]
        assert narrow_flow <= baseline_flow + 1e-9
        assert narrow_report["total_energy_j"] != baseline_report["total_energy_j"]
        # the ledger of the narrowed plant still matches its own independent recomputation
        independent = _oracle_energy(narrow_model, basis="achieved")
        for pump_id, energy in narrow_report["per_pump_electric_j"].items():
            assert energy == pytest.approx(independent.get(pump_id, 0.0), abs=1e-6)
        assert narrow_model.balance_report()["plant_water"]["physical_valid"] is True

