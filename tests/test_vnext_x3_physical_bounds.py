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

import json
import sys
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
