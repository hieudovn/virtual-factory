"""VF-SHW-X2 — whole-plant shallow runnable model + C1 functional control.

Covers the Issue #94 required oracles:

 1  exactly one canonical SH-WTP RuntimeSession / run authority;
 2  all 16 admitted scopes participate as contracted;
 3  zero excluded scopes execute (T107, ELEC-MCC, AUTO-PLC, LINE2 internals);
 4  all 9 C1 controls active exactly as frozen;
 5  zero C2 loop evaluation;
 6  every X2 process input resolves at runtime without hidden fallback invention;
 7  storage volume balances within tolerance;
 8  plant-level water balance residual bounded and reported;
 9  no negative flow/volume and all states within declared bounds;
 10 T106/T108 accepted semantics preserved (G13/G13B/G21 reuse);
 11 filtered turbidity proxy <= settled turbidity under the normal scenario;
 12 filter DP non-decreasing between backwashes, resets after a valid backwash;
 13 no same-window feed-through (explicit_lagged);
 14 deterministic identical trajectory for identical inputs/reset;
 15 assumed-edge provenance visible in runtime records;
 16 site_truth=false / synthetic-reference provenance on outputs;
 17 T100/T108 low/high control direction behaves as frozen;
 18 raw/T106/T108/DIST X2 actuator commands behave exactly as X1-C01 froze.
"""

from __future__ import annotations

import inspect
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from virtual_factory.runcontrol import RuntimeSession  # noqa: E402
from virtual_factory.shwtp import x2_controls as x2_controls_module  # noqa: E402
from virtual_factory.shwtp.bridge import ShwtpExecutionBridge  # noqa: E402
from virtual_factory.shwtp.contracts import load_whole_plant_contracts  # noqa: E402
from virtual_factory.shwtp.session import (  # noqa: E402
    SHWTP_MODEL_G21_SLICE,
    SHWTP_MODEL_WHOLE_PLANT_X2,
    build_shwtp_g21_slice_session,
    build_shwtp_session,
    build_shwtp_whole_plant_session,
)
from virtual_factory.shwtp.whole_plant import (  # noqa: E402
    AUTHORITY_LABELS,
    SCOPE_PATHS,
    SHWTP_WHOLE_PLANT_DEFAULT_RUN_ID,
    SHWTP_WHOLE_PLANT_DEFAULT_STEP_S,
    WholePlantScenario,
    WholePlantX2Error,
    WholePlantX2Runtime,
    authority_labels,
    build_shwtp_whole_plant,
    build_shwtp_whole_plant_workspace,
    require_authority_labels,
)

AUTHORITY_KEYS = (
    "site_truth",
    "simulation_truth",
    "vf_runtime_authorization",
    "site_authorized_execution",
)
EXPECTED_AUTHORITY = {
    "site_truth": False,
    "simulation_truth": "synthetic_reference",
    "vf_runtime_authorization": "NOT_AUTHORIZED",
    "site_authorized_execution": "NOT_AUTHORIZED",
}


def _assert_monotone_between_resets(series: list[tuple[int, float]], resets: list[int]) -> None:
    """Filter DP must never decrease between two backwash resets."""
    previous_window = 0
    previous_value = None
    for reset_window in [*resets, series[-1][0] + 1]:
        for window, value in [row for row in series if previous_window < row[0] < reset_window]:
            if previous_value is not None and value < previous_value - 1e-9:
                raise AssertionError(
                    f"filter DP decreased between backwashes at window {window}: "
                    f"{previous_value!r} -> {value!r}"
                )
            previous_value = value
        previous_window = reset_window
        previous_value = None

WINDOWS = 120
EXCLUDED_SCOPE_IDS = ("vf-shw-node-t107", "vf-shw-node-elec-mcc", "vf-shw-node-auto-plc")
EXPECTED_SCOPE_COUNT = 16
EXPECTED_C1_COUNT = 9
PIM_KNOWN_EDGE_IDS = (
    "vf-shw-edge-intake-t100", "vf-shw-edge-t100-l1", "vf-shw-edge-t106-t108",
)
ASSUMED_EDGE_IDS = (
    "vf-shw-edge-chem-t102", "vf-shw-edge-chem-t103", "vf-shw-edge-dist-demand",
    "vf-shw-edge-line2-dist", "vf-shw-edge-raw-source-intake", "vf-shw-edge-t100-line2",
    "vf-shw-edge-t101-t102", "vf-shw-edge-t102-t103", "vf-shw-edge-t103-t104",
    "vf-shw-edge-t104-t105", "vf-shw-edge-t105-sludge", "vf-shw-edge-t105-t106",
    "vf-shw-edge-t106-wash", "vf-shw-edge-t108-dist", "vf-shw-edge-wash-t106",
)
EXCLUDED_EDGE_IDS = (
    "vf-shw-edge-chem-t107", "vf-shw-edge-t106-t107", "vf-shw-edge-t107-t108",
)


@pytest.fixture(scope="module")
def contracts():
    return load_whole_plant_contracts()


@pytest.fixture()
def workdir():
    """A writable scratch directory (the OS temp dir is not writable here)."""
    import shutil
    import tempfile

    base = ROOT / ".ai-harness" / "traces"
    base.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix="shwx2-", dir=str(base)))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="module")
def plant():
    model = build_shwtp_whole_plant()
    for index in range(1, WINDOWS + 1):
        model.run_window(f"window-{index}")
    return model


def _trajectory(model, windows: int) -> list[tuple]:
    rows: list[tuple] = []
    for index in range(1, windows + 1):
        model.run_window(f"window-{index}")
        for row in model.monitor_rows():
            for key, value in sorted(row["values"].items()):
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    rows.append((index, row["scope_id"], key, round(float(value), 6)))
                elif isinstance(value, dict):
                    for sub_key, sub_value in sorted(value.items()):
                        if isinstance(sub_value, (int, float)):
                            rows.append((index, row["scope_id"], f"{key}.{sub_key}", round(float(sub_value), 6)))
    return rows


# ── oracles 2 / 3: admitted scopes only ───────────────────────────────────

class TestAdmittedScopeExecution:
    def test_exactly_the_16_admitted_scopes_participate(self, plant, contracts):
        admitted = {scope.scope_id for scope in contracts.scopes if scope.x2_admitted}
        assert len(admitted) == EXPECTED_SCOPE_COUNT
        assert set(plant.participants) == admitted
        assert {info.scope_id for info in plant.scopes} == admitted
        assert len(plant.monitor_rows()) == EXPECTED_SCOPE_COUNT

    def test_excluded_scopes_never_execute(self, plant, contracts):
        excluded = set(contracts.admission.reference_only_scope_ids)
        assert set(EXCLUDED_SCOPE_IDS) <= excluded
        for scope_id in EXCLUDED_SCOPE_IDS:
            assert scope_id not in plant.participants
        registered = set(plant.coordinator.participants)
        for scope_id in EXCLUDED_SCOPE_IDS:
            assert not any(scope_id in key for key in registered)
        assert "vf-shw-node-line2-aggregate" in plant.participants
        for internal in ("l1_t107", "elec", "auto_plc", "l2_t101", "l2_t105", "l2_t106", "l2_t108"):
            assert not any(internal in key for key in registered), internal
        # no binding may reference an excluded edge
        assert not set(EXCLUDED_EDGE_IDS) & {binding.edge_id for binding in plant.graph.bindings}

    def test_every_participant_implements_its_contract_family(self, plant):
        for scope_id, participant in plant.participants.items():
            entry = participant.contract
            assert entry["scope_id"] == scope_id
            assert participant.scope_id == scope_id
            assert participant.workspace_id == "shwtp"
            assert participant.current_time_s == WINDOWS * SHWTP_WHOLE_PLANT_DEFAULT_STEP_S

    def test_line2_internals_are_reference_only_not_executable(self, plant, contracts):
        node = next(n for n in contracts.nodes if n.node_id == "vf-shw-node-line2-aggregate")
        assert node.canonical_id is None
        assert node.process_role == "parallel_line_aggregate"
        assert set(node.canonical_refs) == {
            "UNIT-SHW-L2-T101", "UNIT-SHW-L2-T105", "UNIT-SHW-L2-T106", "UNIT-SHW-L2-T108",
        }
        assert node.x2_eligible is True

    def test_registered_scope_paths_are_executable_capable(self, plant):
        for key in plant.coordinator.participants:
            scope = plant.workspace.resolve_scope(
                next(p.scope_path for p in plant.participants.values() if p.scope_path.as_string() == key)
            )
            assert not scope.is_container_only


# ── oracles 4 / 5: C1 active, zero C2 evaluation ──────────────────────────

class TestC1ControlsAndC2Prohibition:
    def test_exactly_the_nine_frozen_c1_controls_evaluate(self, plant, contracts):
        assert set(plant.controls.active_controller_ids) == set(contracts.admission.c1_active_ids)
        assert len(plant.controls.active_controller_ids) == EXPECTED_C1_COUNT

    def test_zero_c2_loop_evaluation(self, plant, contracts):
        c2_ids = {c.controller_id for c in contracts.controls if c.control_class == "C2"}
        assert not (c2_ids & set(plant.controls.active_controller_ids))
        for controller in plant.controls._controllers.values():
            assert controller.entry["control_class"] == "C1"
            assert controller.entry["active_in_x2"] is True
        for contract in contracts.controls:
            if contract.control_class == "C2":
                assert contract.active_in_x2 is False
                assert contract.raw["x2_status"].startswith("inactive in X2")

    def test_no_pid_equations_or_scan_loops_in_the_c1_layer(self):
        code = re.sub(r'""".*?"""', "", inspect.getsource(x2_controls_module), flags=re.DOTALL)
        lowered = code.lower()
        for token in ("integral", "derivative", "anti_windup", "proportional_gain", "ki =", "kp =", "kd ="):
            assert token not in lowered, token
        for forbidden in ("from virtual_factory.runcontrol", "SimulationEngine", "RuntimeSession"):
            assert forbidden not in code, forbidden

    def test_c1_outputs_are_only_declared_contract_signals(self, plant, contracts):
        rows = {row["controller_id"]: row for row in plant.control_rows()}
        assert set(rows) == set(contracts.admission.c1_active_ids)
        for controller_id, row in rows.items():
            contract = next(c for c in contracts.controls if c.controller_id == controller_id)
            declared = set(contract.raw["output_signals"])
            assert set(row["outputs"]) <= declared, controller_id
            assert row["control_class"] == "C1" and row["active_in_x2"] is True


# ── oracle 1: one canonical session / bridge authority ───────────────────

class TestCanonicalSessionAuthority:
    def test_whole_plant_session_is_one_canonical_session(self):
        session = build_shwtp_whole_plant_session()
        assert isinstance(session, RuntimeSession)
        assert session.workspace_id == "shwtp"
        assert session.run_id
        session.advance()
        bridge = session.record.bridge
        assert isinstance(bridge, ShwtpExecutionBridge)
        model = bridge.model
        assert len(model.participants) == EXPECTED_SCOPE_COUNT
        assert set(model.participants) == set(SCOPE_PATHS)
        assert model.window_index == 1

    def test_g21_slice_default_is_unchanged(self):
        session = build_shwtp_session()
        assert isinstance(session, RuntimeSession)
        assert session.workspace_id == "shwtp"
        # the accepted G21 slice remains the default model and is untouched
        from virtual_factory.shwtp.expansion import PLANT_SLICE_SCOPES, build_shwtp_plant_slice

        assert len(PLANT_SLICE_SCOPES) == 5
        assert len(build_shwtp_plant_slice().participants) == 5
        assert SHWTP_MODEL_G21_SLICE == "g21_slice"
        assert SHWTP_MODEL_WHOLE_PLANT_X2 == "whole_plant_x2"

    def test_unknown_model_fails_closed(self):
        with pytest.raises(Exception):
            build_shwtp_session(model="not-a-model")

    def test_bridge_drives_the_whole_plant_deterministically(self):
        bridge = ShwtpExecutionBridge(build_shwtp_whole_plant)
        assert bridge.natural_next_boundary(("shwtp",)) == SHWTP_WHOLE_PLANT_DEFAULT_STEP_S
        for index in range(1, 4):
            step = bridge.advance(SHWTp := SHWTP_WHOLE_PLANT_DEFAULT_STEP_S * index, ("shwtp",), f"window-{index}")
            assert step.status == "completed"
            assert step.target_time_s == SHWTp
        assert len(bridge.model.participants) == EXPECTED_SCOPE_COUNT
        bridge.reset(("shwtp",))
        assert bridge.model.window_index == 0

    def test_two_sessions_are_independent(self):
        first = build_shwtp_whole_plant_session()
        second = build_shwtp_whole_plant_session()
        assert first is not second
        first.advance()
        second.advance()
        assert first.record.bridge.model.window_index == 1
        assert second.record.bridge.model.window_index == 1
        assert first.record.bridge.model is not second.record.bridge.model
        first.record.bridge.model.run_window("window-2")
        assert second.record.bridge.model.window_index == 1


# ── oracle 6: runtime input resolution ───────────────────────────────────

class TestInputResolution:
    def test_every_contract_input_resolves_at_runtime(self, plant, contracts):
        rows = plant.input_wiring()
        expected = {
            (scope.scope_id, entry["signal"])
            for scope in contracts.scopes
            if scope.x2_admitted
            for entry in scope.raw["inputs"]
        }
        assert {(row["scope_id"], row["signal"]) for row in rows} == expected
        for row in rows:
            assert row["x2_producer_class"] in (
                "process_node", "x2_active_controller", "x2_fallback_default", "scenario", None,
            )
            assert row["runtime_resolution"]

    def test_no_contract_input_is_produced_by_a_c2_loop(self, plant, contracts):
        c2_ids = {c.controller_id for c in contracts.controls if c.control_class == "C2"}
        rows = plant.input_wiring()
        for row in rows:
            if row["x2_producer_class"] == "x2_fallback_default":
                continue
            assert row["declared_source"] not in c2_ids, row
        # the one fallback input is the frozen DIST-P108 high-service pump
        fallbacks = [row for row in rows if row["x2_producer_class"] == "x2_fallback_default"]
        assert [(row["scope_id"], row["signal"]) for row in fallbacks] == [
            ("vf-shw-node-dist-p108", "hsp_speed_cmd")
        ]

    def test_runtime_resolution_matches_the_declared_producer_class(self, plant):
        expected = {
            "process_node": "coordinated_transfer",
            "x2_active_controller": "c1_control_command",
            "x2_fallback_default": "declared_x2_fallback",
            "scenario": "scenario_parameter",
        }
        rows = plant.input_wiring()
        assert rows
        for row in rows:
            assert row["runtime_resolution"] == expected[row["x2_producer_class"]], row
        counts = {}
        for row in rows:
            counts[row["x2_producer_class"]] = counts.get(row["x2_producer_class"], 0) + 1
        assert counts.get("x2_fallback_default") == 1
        assert counts.get("scenario") == 1
        assert counts.get("x2_active_controller", 0) >= 8
        assert counts.get("process_node", 0) >= 15

    def test_controller_commands_reach_their_declared_scopes(self, plant, contracts):
        raw_intake = plant.participants["vf-shw-node-raw-intake"]
        assert raw_intake.monitor_values()["pump_speed_pct"] in (75.0, 0.0)
        t108_speed = plant.controls.evaluation_detail("vf-shw-ctrl-t108-permissive")
        assert t108_speed["upstream_inflow"] in ("permitted", "inhibited")


# ── oracles 7 / 8 / 9: balance, bounds, non-negativity ───────────────────

class TestBalanceAndBounds:
    def test_storage_volume_balances_exactly(self, plant):
        report = plant.balance_report()
        assert report["storage_balances"]
        for row in report["storage_balances"]:
            assert row["storage"] is True
            assert row["conservation_kind"] in ("volume_balance", "mass_flow_continuity")
            assert abs(row["residual_m3"]) <= 1e-6, row
        assert report["max_storage_residual_m3"] <= 1e-6

    def test_plant_water_residual_is_bounded_and_reported(self, plant):
        plant_water = plant.balance_report()["plant_water"]
        assert plant_water["plant_in_m3"] > 0
        assert plant_water["plant_out_m3"] > 0
        assert abs(plant_water["closure_m3"]) <= 0.05 * plant_water["plant_in_m3"] + 0.05
        assert plant_water["bounded"] is True

    def test_no_negative_or_non_finite_state_values(self, plant):
        for row in plant.monitor_rows():
            for key, value in row["values"].items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    assert value >= 0.0, (row["scope_id"], key, value)
                    assert value == value, (row["scope_id"], key)
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        assert isinstance(sub_value, (int, float))
                        assert sub_value >= 0.0, (row["scope_id"], key, sub_key)

    def test_states_stay_within_declared_bounds(self, plant):
        t100 = plant.participants["vf-shw-node-t100"].monitor_values()
        t108 = plant.participants["vf-shw-node-t108"].monitor_values()
        assert 0.0 <= t100["volume_m3"] <= plant.scenario.t100_capacity_m3
        assert 0.0 <= t108["volume_m3"] <= plant.scenario.t108_capacity_m3
        assert t100["level_m"] >= 0.0 and t108["level_m"] >= 0.0
        network = plant.participants["vf-shw-node-network-demand"].monitor_values()
        assert 0.0 <= network["demand_met_fraction"] <= 1.0
        intake = plant.participants["vf-shw-node-raw-intake"].monitor_values()
        assert 0.0 <= intake["pump_speed_pct"] <= 100.0
        assert intake["intake_flow_m3h"] <= plant.scenario.pump_rated_flow_m3h + 1e-9

    def test_t106_and_t108_accepted_semantics_preserved(self, plant):
        # T108 remains a first_order volume-balance tank; T106 remains a
        # first_order filtering scope.
        t108 = plant.participants["vf-shw-node-t108"]
        t106 = plant.participants["vf-shw-node-t106"]
        assert t108.contract["update_rule_family"] == "volume_balance_first_order_v1"
        assert t106.contract["update_rule_family"] == "filter_loading_first_order_v1"
        t108_values = t108.monitor_values()
        # the accepted T108 volume-balance state is present and consistent
        assert set(("volume_m3", "level_m", "inflow_m3h", "withdrawal_m3h")) <= set(t108_values)
        assert t108_values["volume_m3"] == pytest.approx(
            t108_values["level_m"] * plant.scenario.t108_area_m2, abs=1e-6
        )
        t106_values = t106.monitor_values()
        assert set(("filter_dp_kpa", "filtered_flow_m3h", "inlet_valve_pos_pct")) <= set(t106_values)
        assert t106_values["inlet_valve_pos_pct"] in (100.0, 0.0)


# ── oracles 11 / 12 / 17 / 18: process + control behaviour ───────────────

class TestProcessAndControlBehaviour:
    def test_filtered_turbidity_does_not_exceed_settled_turbidity(self):
        model = build_shwtp_whole_plant()
        previous_settled = None
        for index in range(1, 30):
            model.run_window(f"window-{index}")
            settled = model.participants["vf-shw-node-t105"].monitor_values()["turbidity_ntu"]
            filtered = model.participants["vf-shw-node-t106"].monitor_values()["turbidity_ntu"]
            if previous_settled is not None:
                assert filtered <= previous_settled + 1e-9, index
            previous_settled = settled
        assert previous_settled is not None
        assert previous_settled <= model.scenario.raw_turbidity_ntu
        assert model.participants["vf-shw-node-raw-intake"].monitor_values()["screen_dp_kpa"] >= 0.0

    def test_filter_dp_grows_between_backwashes_and_resets_after(self):
        model = build_shwtp_whole_plant()
        series: list[tuple[int, float]] = []
        resets: list[int] = []
        previous = model.scenario.t106_dp_initial_kpa
        backwashes = 0
        wash_flow_seen = 0.0
        for index in range(1, 200):
            model.run_window(f"window-{index}")
            values = model.participants["vf-shw-node-t106"].monitor_values()
            current = values["filter_dp_kpa"]
            series.append((index, current))
            if current < previous - 1e-9:
                # a decrease is ONLY legal as a completed backwash reset
                assert values["backwash_step"] == "IDLE"
                assert current == pytest.approx(model.scenario.t106_dp_initial_kpa, abs=1e-6)
                resets.append(index)
            elif current > previous + 1e-9:
                # growth is only legal while the filter is actually filtering
                assert values["inlet_valve_pos_pct"] == 100.0
                assert values["filtered_flow_m3h"] > 0.0
            previous = current
            backwashes = max(backwashes, values["backwash_count"])
            if values["backwash_step"] == "BACKWASH":
                wash_flow_seen = max(wash_flow_seen, values["wash_out_m3h"])
        assert resets, "a valid backwash must reset the filter DP"
        assert backwashes >= 1
        assert wash_flow_seen > 0.0, "backwash must produce wash water"
        _assert_monotone_between_resets(series, resets)

    def test_dp_monotonicity_check_bites_on_a_violation(self):
        series = [(1, 25.0), (2, 30.0), (3, 28.0), (4, 40.0)]
        with pytest.raises(AssertionError):
            _assert_monotone_between_resets(series, [])
        series_ok = [(1, 25.0), (2, 30.0), (3, 20.0), (4, 22.0)]
        _assert_monotone_between_resets(series_ok, [3])

    def test_wash_water_recovery_returns_to_t106(self, plant):
        wash = plant.participants["vf-shw-node-wash-t110"].monitor_values()
        assert wash["volume_m3"] >= 0.0
        assert wash["return_m3h"] >= 0.0

    def test_sludge_path_operates(self, plant):
        clarifier = plant.participants["vf-shw-node-t105"].monitor_values()
        sink = plant.participants["vf-shw-node-sludge-t201"].monitor_values()
        assert clarifier["sludge_out_m3h"] >= 0.0
        assert sink["processed_m3h"] >= 0.0
        assert sink["volume_m3"] <= plant.scenario.sludge_t201_capacity_m3

    def test_x2_actuator_commands_match_the_frozen_contract(self, plant, contracts):
        by_id = {control.controller_id: control.raw for control in contracts.controls}
        raw_intake = plant.participants["vf-shw-node-raw-intake"].monitor_values()
        raw_command = by_id["vf-shw-ctrl-raw-pump-duty"]["x2_actuator_command"]
        assert raw_intake["pump_speed_pct"] in (raw_command["value_when_running"], raw_command["value_when_stopped"])
        assert raw_command["value_when_running"] == 75.0
        assert raw_command["value_when_stopped"] == 0.0

        filter_values = plant.participants["vf-shw-node-t106"].monitor_values()
        valve_command = by_id["vf-shw-ctrl-backwash-sequence"]["x2_actuator_command"]
        assert valve_command["value_when_open"] == 100.0
        assert valve_command["value_when_closed"] == 0.0
        assert filter_values["inlet_valve_pos_pct"] in (100.0, 0.0)

        t108_command = by_id["vf-shw-ctrl-t108-permissive"]["x2_actuator_command"]
        assert t108_command["value_when_running"] == 70.0
        assert t108_command["value_when_stopped"] == 0.0
        snapshot = plant.controls.output_snapshot()["vf-shw-ctrl-t108-permissive"]["outputs"]
        assert snapshot["transfer_pump_speed_cmd"] in (70.0, 0.0)

        assert plant.participants["vf-shw-node-dist-p108"].monitor_values()["hsp_speed_pct"] == 80.0
        assert by_id["vf-shw-ctrl-dist-pressure-pi"]["x2_replacement"]["x2_producer"] == "x2_fallback_default"

    def test_c1_produced_actuator_commands_are_read_from_the_contract(self):
        code = inspect.getsource(x2_controls_module)
        assert "read_actuator_command" in code
        assert "value_when_running" in code
        assert "is_feedback_controlled_in_x2" in code

    def test_t100_low_level_protects_downstream_not_upstream(self):
        scenario = WholePlantScenario(t100_initial_volume_m3=4.0, t100_level_band_m=(0.5, 0.8, 3.5, 4.0))
        model = build_shwtp_whole_plant(scenario=scenario)
        model.run_window("window-1")
        outputs = model.control_rows()
        permissive = next(row for row in outputs if row["controller_id"] == "vf-shw-ctrl-t100-permissive")
        assert permissive["outputs"]["outlet_enable"] is False     # downstream inhibited
        assert permissive["outputs"]["intake_enable"] is True      # upstream refill permitted
        assert permissive["detail"]["low_action"] == "inhibit_downstream_withdrawal"

    def test_t100_high_level_inhibits_upstream_intake(self):
        scenario = WholePlantScenario(t100_initial_volume_m3=78.0, t100_level_band_m=(0.5, 0.8, 3.5, 4.0))
        model = build_shwtp_whole_plant(scenario=scenario)
        model.run_window("window-1")
        permissive = next(
            row for row in model.control_rows() if row["controller_id"] == "vf-shw-ctrl-t100-permissive"
        )
        assert permissive["outputs"]["intake_enable"] is False
        assert permissive["outputs"]["outlet_enable"] is True
        assert permissive["detail"]["high_action"] == "inhibit_upstream_intake"

    def test_t108_direction_is_correct(self):
        low = WholePlantScenario(t108_initial_volume_m3=18.0, t108_level_band_m=(1.0, 1.4, 4.0, 4.6))
        high = WholePlantScenario(t108_initial_volume_m3=92.0, t108_level_band_m=(1.0, 1.4, 4.0, 4.6))
        low_model = build_shwtp_whole_plant(scenario=low)
        high_model = build_shwtp_whole_plant(scenario=high)
        low_model.run_window("window-1")
        high_model.run_window("window-1")
        low_row = next(r for r in low_model.control_rows() if r["controller_id"] == "vf-shw-ctrl-t108-permissive")
        high_row = next(r for r in high_model.control_rows() if r["controller_id"] == "vf-shw-ctrl-t108-permissive")
        assert low_row["outputs"]["transfer_enable"] is False
        assert low_row["outputs"]["inflow_enable"] is True
        assert high_row["outputs"]["inflow_enable"] is False
        assert high_row["outputs"]["transfer_enable"] is True


# ── oracle 13: explicit_lagged (no same-window feed-through) ─────────────

class TestExplicitLagged:
    def test_no_same_window_feed_through(self):
        model = build_shwtp_whole_plant()
        previous_flows: dict[str, float] = {}
        for index in range(1, 12):
            model.run_window(f"window-{index}")
            t100 = model.participants["vf-shw-node-t100"].monitor_values()
            t101 = model.participants["vf-shw-node-t101"].monitor_values()
            delivered = t101["inflow_m3h"]
            if index > 1:
                assert delivered == previous_flows.get("t100_l1_feed", delivered), (
                    "T101 inbound must equal the PREVIOUS window T100 feed (explicit_lagged)"
                )
            previous_flows["t100_l1_feed"] = t100["outflows_m3h"]["vf-shw-node-t101"]

    def test_first_window_cannot_see_upstream_production(self):
        model = build_shwtp_whole_plant()
        model.run_window("window-1")
        # window-1 emission comes from the COMMITTED (initial) state only ...
        assert model.participants["vf-shw-node-t101"].monitor_values()["outflow_m3h"] == 0.0
        assert model.participants["vf-shw-node-t102"].monitor_values()["inflow_m3h"] == 0.0
        assert model.participants["vf-shw-node-raw-intake"].monitor_values()["intake_flow_m3h"] == 0.0
        # ... while window-1 production is only committed for window 2.
        assert model.participants["vf-shw-node-t101"].monitor_values()["inflow_m3h"] > 0.0
        assert model.participants["vf-shw-node-raw-intake"].monitor_values()["raw_flow_m3h"] > 0.0


# ── oracle 14: determinism ───────────────────────────────────────────────

class TestDeterminism:
    def test_identical_inputs_produce_identical_trajectories(self):
        first = build_shwtp_whole_plant()
        second = build_shwtp_whole_plant()
        assert _trajectory(first, 10) == _trajectory(second, 10)

    def test_reset_restores_the_identical_initial_trajectory(self):
        model = build_shwtp_whole_plant()
        before = _trajectory(model, 6)
        model.reset()
        assert model.window_index == 0
        after = _trajectory(model, 6)
        assert before == after

    def test_contract_signature_is_deterministic_and_mutation_sensitive(self, contracts, workdir):
        """The frozen contract layer must load to a stable ADMISSION signature.

        The signature deliberately covers the admission/identity surface (node
        role, scope fidelity/family, edge category, control class/gate/activity,
        admission manifest) - not every parameter value. The mutations below each
        target a covered field, so the signature must change.
        """
        from virtual_factory.shwtp.contracts import load_whole_plant_contracts

        # deterministic across loads
        assert load_whole_plant_contracts().signature == contracts.signature
        # graph node role is covered
        graph = json.loads((ROOT / "configs" / "vnext" / "shwtp" / "shwtp_whole_plant_graph_v1.json").read_text(encoding="utf-8"))
        graph["nodes"][0]["process_role"] = "tampered_role"
        path = workdir / "graph_tampered.json"
        path.write_text(json.dumps(graph), encoding="utf-8")
        assert load_whole_plant_contracts(graph_path=path).signature != contracts.signature
        # scope fidelity_class is covered
        process = json.loads((ROOT / "configs" / "vnext" / "shwtp" / "shwtp_process_contracts_v1.json").read_text(encoding="utf-8"))
        next(s for s in process["contracts"] if s["scope_id"] == "vf-shw-node-t100")["fidelity_class"] = "logical_only"
        process_path = workdir / "process_tampered.json"
        process_path.write_text(json.dumps(process), encoding="utf-8")
        assert load_whole_plant_contracts(process_contracts_path=process_path).signature != contracts.signature
        # control implementation_gate is cross-checked against the process
        # contract's deferred_modulator annotation -> a gate mutation is rejected
        from virtual_factory.shwtp.contracts import ShwtpContractError

        control = json.loads((ROOT / "configs" / "vnext" / "shwtp" / "shwtp_control_contracts_v1.json").read_text(encoding="utf-8"))
        next(c for c in control["controls"] if c["controller_id"] == "vf-shw-ctrl-f106-inlet-flow-pi")["implementation_gate"] = "X4"
        control_path = workdir / "control_tampered.json"
        control_path.write_text(json.dumps(control), encoding="utf-8")
        with pytest.raises(ShwtpContractError, match="deferred_modulator annotation"):
            load_whole_plant_contracts(control_contracts_path=control_path)
        # C2 activity is covered too: activating a C2 loop in X2 is rejected
        control2 = json.loads((ROOT / "configs" / "vnext" / "shwtp" / "shwtp_control_contracts_v1.json").read_text(encoding="utf-8"))
        next(c for c in control2["controls"] if c["controller_id"] == "vf-shw-ctrl-t108-level-pi")["active_in_x2"] = True
        control2_path = workdir / "control_active_c2.json"
        control2_path.write_text(json.dumps(control2), encoding="utf-8")
        with pytest.raises(ShwtpContractError):
            load_whole_plant_contracts(control_contracts_path=control2_path)


# ── oracles 15 / 16: provenance + mandatory authorization labels ────────

class TestAuthorityLabels:
    def test_authority_labels_constant_matches_the_frozen_vocabulary(self):
        assert authority_labels() == EXPECTED_AUTHORITY
        assert set(AUTHORITY_LABELS) == set(AUTHORITY_KEYS)

    def test_every_runtime_projection_carries_the_four_labels(self, plant):
        records: list[tuple[str, dict]] = []
        for row in plant.monitor_rows():
            records.append(("monitor_row", row))
            records.append(("monitor_values", row["values"]))
        for row in plant.control_rows():
            records.append(("control_row", row))
        for row in plant.input_wiring():
            records.append(("input_wiring", row))
        for row in plant.provenance_records():
            records.append(("provenance", row))
        for row in plant.transfer_records():
            records.append(("transfer_payload", dict(row["payload"])))
        balance = plant.balance_report()
        records.append(("balance_report", balance))
        for row in balance["storage_balances"]:
            records.append(("balance_row", row))
        records.append(("runtime_truth", plant.runtime_truth()))
        for row in plant.assumed_topology():
            records.append(("assumed_topology", row))
        assert len(records) > 100
        for where, record in records:
            for key, expected in EXPECTED_AUTHORITY.items():
                assert key in record, (where, key)
                assert record[key] == expected, (where, key, record[key])

    def test_label_guard_fails_closed(self):
        good = dict(EXPECTED_AUTHORITY)
        require_authority_labels(good, where="test")
        for key in AUTHORITY_KEYS:
            broken = dict(good)
            broken.pop(key)
            with pytest.raises(WholePlantX2Error):
                require_authority_labels(broken, where="test")
        mutated = dict(good, site_truth=True)
        with pytest.raises(WholePlantX2Error):
            require_authority_labels(mutated, where="test")
        mutated = dict(good, vf_runtime_authorization="AUTHORIZED")
        with pytest.raises(WholePlantX2Error):
            require_authority_labels(mutated, where="test")

    def test_implementation_state_is_separate_from_authorization_state(self, plant):
        truth = plant.runtime_truth()
        assert truth["whole_plant_runtime_implementation"] == "IMPLEMENTED_SYNTHETIC_REFERENCE"
        assert truth["whole_plant_runtime_authorization"] == "NOT_AUTHORIZED"
        assert truth["site_truth"] is False
        assert truth["simulation_truth"] == "synthetic_reference"


class TestCanonicalDefaultModel:
    def test_default_session_resolves_to_the_whole_plant_model(self):
        from virtual_factory.shwtp.session import SHWTP_DEFAULT_MODEL

        assert SHWTP_DEFAULT_MODEL == "whole_plant_x2"
        session = build_shwtp_session()
        assert isinstance(session, RuntimeSession)
        assert session.workspace_id == "shwtp"
        session.advance()
        model = session.record.bridge.model
        assert isinstance(model, WholePlantX2Runtime)
        assert len(model.participants) == EXPECTED_SCOPE_COUNT
        assert model.window_index == 1

    def test_g21_slice_is_available_only_through_the_explicit_selector(self):
        explicit = build_shwtp_session(model="g21_slice")
        explicit.advance()
        assert len(explicit.record.bridge.model.scopes) == 5
        compatibility = build_shwtp_g21_slice_session()
        compatibility.advance()
        assert len(compatibility.record.bridge.model.scopes) == 5
        # the canonical default is NOT the slice
        default = build_shwtp_session()
        default.advance()
        assert not hasattr(default.record.bridge.model, "scopes") or len(
            default.record.bridge.model.participants
        ) == EXPECTED_SCOPE_COUNT


# ── provenance ──────────────────────────────────────────────────────────

class TestProvenance:
    def test_runtime_transfers_carry_graph_provenance(self, plant, contracts):
        ledger = plant.transfer_records()
        assert ledger
        by_edge = {
            edge.edge_id: edge for edge in contracts.edges
            if edge.edge_id in set(PIM_KNOWN_EDGE_IDS) | set(ASSUMED_EDGE_IDS)
        }
        for row in ledger:
            provenance = row["provenance"]
            if row["binding_id"] in by_edge:
                edge = by_edge[row["binding_id"]]
                assert provenance["edge_category"] == edge.category
                if edge.category == "pim_known":
                    assert provenance["pim_relation_id"] == edge.pim_relation_id
                    assert provenance["assumption_id"] is None
                else:
                    assert provenance["assumption_id"] == edge.assumption_id
                    assert provenance["reversible"] is True
            else:
                assert provenance["edge_category"] == "contract_declared_input"

    def test_all_three_pim_known_and_fifteen_assumed_edges_are_used(self, plant):
        seen = {row["binding_id"] for row in plant.transfer_records()}
        recorded = {row["binding_id"] for row in plant.provenance_records()}
        for edge_id in PIM_KNOWN_EDGE_IDS:
            assert edge_id in seen, edge_id
            assert edge_id in recorded
        for edge_id in ASSUMED_EDGE_IDS:
            assert edge_id in seen, edge_id
        assert not (set(EXCLUDED_EDGE_IDS) & seen)

    def test_outputs_declare_synthetic_reference_and_no_site_truth(self, plant):
        for row in plant.monitor_rows():
            assert row["site_truth"] is False
            assert row["simulation_truth"] == "synthetic_reference"
        for row in plant.transfer_records():
            assert row["payload"]["site_truth"] is False
            assert row["payload"]["simulation_truth"] == "synthetic_reference"
            assert row["payload"]["fidelity_class"]

    def test_no_pim_id_is_invented_by_the_runtime(self, plant, contracts):
        allowed = {node.canonical_id for node in contracts.nodes if node.canonical_id}
        for row in plant.scopes:
            if row.canonical_id is not None:
                assert row.canonical_id in allowed

    def test_workspace_contains_no_reference_only_scope_as_executable(self):
        workspace = build_shwtp_whole_plant_workspace()
        for scope_id in EXCLUDED_SCOPE_IDS:
            path = SCOPE_PATHS.get(scope_id)
            assert path is None
        assert len(SCOPE_PATHS) == EXPECTED_SCOPE_COUNT
        assert workspace.workspace_id == "shwtp"

    def test_fail_closed_on_invalid_or_repeated_window_id(self):
        model = build_shwtp_whole_plant()
        model.run_window("window-1")
        with pytest.raises(WholePlantX2Error):
            model.run_window("window-1")
        with pytest.raises(WholePlantX2Error):
            model.run_window("")
        with pytest.raises(WholePlantX2Error):
            model.run_window(None)


# ── VF-SHW-X2-C02 ────────────────────────────────────────────────────────
#
# C02-1  runtime identity comes from the active lifecycle attempt context;
# C02-2  committed process input (WASH return) is consumed at the correct lag;
# C02-3  the plant conservation oracle counts water only (ledger-based);
# C02-4  a high-level permissive inhibits the declared UPSTREAM path instead of
#        deleting already-received water.

STEP_S = SHWTP_WHOLE_PLANT_DEFAULT_STEP_S
DT_H = STEP_S / 3600.0


def _t106(model):
    return model.participants["vf-shw-node-t106"]


def _t100(model):
    return model.participants["vf-shw-node-t100"]


def _t108(model):
    return model.participants["vf-shw-node-t108"]


def _t105(model):
    return model.participants["vf-shw-node-t105"]


def _controller(model, controller_id) -> dict:
    rows = {row["controller_id"]: row for row in model.control_rows()}
    assert controller_id in rows, f"controller {controller_id!r} not evaluated"
    return rows[controller_id]


def _flow_of(model, binding_id: str) -> float:
    rows = [row for row in model.transfer_records() if row["binding_id"] == binding_id]
    return sum(float(row["payload"]["flow_m3h"]) for row in rows)


class TestLifecycleRunIdentity:
    """C02-1: the model identity is the ACTIVE attempt's identity."""

    def test_transfers_carry_the_active_attempt_run_id(self):
        session = build_shwtp_session()
        session.advance()
        run_id = session.record.context.run_id
        model = session.record.bridge.model
        assert isinstance(model, WholePlantX2Runtime)
        assert model.run_id == run_id
        assert model.runtime_truth()["run_id"] == run_id
        assert model.runtime_truth()["run_id_source"] == "attempt_context"
        assert {participant.run_id for participant in model.participants.values()} == {run_id}
        rows = model.transfer_records()
        assert rows, "no transfer was recorded for the first window"
        assert {row["run_id"] for row in rows} == {run_id}
        assert all(row["window_id"].startswith(run_id) for row in rows)
        assert model.run_id != SHWTP_WHOLE_PLANT_DEFAULT_RUN_ID

    def test_reset_preserves_the_attempt_identity(self):
        session = build_shwtp_session()
        session.advance()
        run_id = session.record.context.run_id
        session.reset()
        assert session.record.context.run_id == run_id
        session.advance()
        model = session.record.bridge.model
        assert model.run_id == run_id
        assert model.window_index == 1
        assert {row["run_id"] for row in model.transfer_records()} == {run_id}

    def test_new_attempt_and_replay_issue_lifecycle_identities(self):
        session = build_shwtp_session()
        session.advance()
        first = session.record.context.run_id
        for transition in (session.new_attempt, session.replay):
            issued = transition()
            assert issued != first
            assert session.record.context.run_id == issued
            session.advance()
            model = session.record.bridge.model
            assert model.run_id == issued
            rows = model.transfer_records()
            assert rows
            assert {row["run_id"] for row in rows} == {issued}
            # no transfer of an older attempt identity leaks into this attempt
            assert first not in {row["run_id"] for row in rows}

    def test_attempt_bound_bridge_fails_closed_without_a_context(self):
        from virtual_factory import runcontrol
        from virtual_factory.shwtp import session as session_module

        with pytest.raises(runcontrol.SessionError):
            session_module._require_attempt_bound_bridge()
        # an explicit ambient run_id is rejected: identity is attempt-bound only
        with pytest.raises(runcontrol.SessionError):
            session_module._resolve_model(SHWTP_MODEL_WHOLE_PLANT_X2, {"run_id": "run-fixed"})


class TestCommittedProcessInputLag:
    """C02-2: the WASH return survives prepare_window and is consumed once."""

    def test_wash_return_is_consumed_exactly_once_at_the_correct_lag(self):
        # a low initial DP forces an early backwash -> wash water -> T110 -> T106
        model = build_shwtp_whole_plant(scenario=WholePlantScenario(t106_dp_initial_kpa=78.0))
        delivered_previous = 0.0
        saw_return = False
        for index in range(1, 25):
            model.run_window(f"window-{index}")
            values = _t106(model).monitor_values()
            # the COMMITTED wash return of the previous window is consumed now
            assert values["wash_return_m3h"] == pytest.approx(delivered_previous, abs=1e-9), index
            delivered_previous = _flow_of(model, "vf-shw-edge-wash-t106")
            if delivered_previous > 0.0:
                saw_return = True
        assert saw_return, "the WASH return never reached T106"
        # and it really enters the filter water accounting (mass, not "non-negative")
        model2 = build_shwtp_whole_plant(scenario=WholePlantScenario(t106_dp_initial_kpa=78.0))
        for index in range(1, 25):
            t106 = _t106(model2)
            delivered_previous = _flow_of(model2, "vf-shw-edge-wash-t106")
            sample = delivered_previous > 0.0
            inflow_previous = _flow_of(model2, "vf-shw-edge-t105-t106")
            volume_in_before = t106._volume_in_m3
            volume_before = t106._volume_m3
            model2.run_window(f"window-{index}")
            values = t106.monitor_values()
            if not sample:
                continue
            assert values["wash_return_m3h"] == pytest.approx(delivered_previous, abs=1e-9)
            assert t106._volume_in_m3 - volume_in_before == pytest.approx(
                (inflow_previous + delivered_previous) * DT_H, abs=1e-9
            )
            assert t106._volume_m3 - volume_before == pytest.approx(
                (inflow_previous + delivered_previous - values["filtered_flow_m3h"] - values["wash_out_m3h"])
                * DT_H,
                abs=1e-9,
            )

    def test_recovery_loop_never_returns_more_wash_water_than_it_received(self):
        model = build_shwtp_whole_plant(scenario=WholePlantScenario(t106_dp_initial_kpa=78.0))
        received = returned = 0.0
        for index in range(1, 40):
            model.run_window(f"window-{index}")
            received += _flow_of(model, "vf-shw-edge-t106-wash") * DT_H
            returned += _flow_of(model, "vf-shw-edge-wash-t106") * DT_H
            assert model.participants["vf-shw-node-wash-t110"]._volume_m3 >= 0.0
        assert returned > 0.0, "the WASH recovery loop never returned water"
        assert returned <= received + 1e-9

    def test_committed_input_survives_prepare_window(self):
        model = build_shwtp_whole_plant()
        filter_participant = _t106(model)
        model.run_window("window-1")
        # a committed process input MUST survive the next prepare_window, which
        # replaces the transient controller commands (the C02-2 defect)
        filter_participant._process_input["wash_return_flow_m3h"] = 3.0
        filter_participant.prepare_window(
            "window-2", {"backwash_step": "IDLE", "inlet_valve_pos": 100.0}, {}
        )
        assert filter_participant._process_input["wash_return_flow_m3h"] == 3.0
        # consumed exactly once
        assert filter_participant._consume_process_flow("wash_return_flow_m3h") == 3.0
        assert filter_participant._consume_process_flow("wash_return_flow_m3h") == 0.0


class TestPlantWaterLedger:
    """C02-3: conservation is a ledger-based water balance, not a tolerance."""

    def test_information_bindings_carry_no_water(self, plant):
        rows = plant.transfer_records()
        information = [row for row in rows if row["transfer_kind"] == "information"]
        assert information, "no information binding was recorded"
        # the SA reproduction: a 60 m3/h information signal is NOT 1 m3 of water - the
        # plant-flow information binding already carries a multi-m3/h signal value
        assert max(float(row["payload"]["flow_m3h"]) for row in information) > 40.0
        assert plant.information_inventory_m3 > 1.0
        assert all(row["water_m3"] == 0.0 for row in information)
        physical = [
            row
            for row in rows
            if row["transfer_kind"] == "physical_water" and row["boundary"] != "exit"
        ]
        assert plant.in_transit_m3 == pytest.approx(sum(row["water_m3"] for row in physical), abs=1e-12)
        # counting the information signals as water would inflate the inventory
        inflated = sum(row["water_m3"] for row in physical) + plant.information_inventory_m3
        assert inflated > plant.in_transit_m3

    def test_source_availability_outside_the_boundary_is_not_inventory(self, plant):
        rows = [row for row in plant.transfer_records() if row["binding_id"] == "vf-shw-edge-raw-source-intake"]
        assert rows
        assert all(row["transfer_kind"] == "source_availability_outside_boundary" for row in rows)
        assert all(row["water_m3"] == 0.0 for row in rows)
        assert plant.balance_report()["plant_water"]["source_availability_m3"] > 0.0
        # availability is a raw signal: the pump takes only part of it
        availability = float(rows[0]["payload"]["flow_m3h"])
        intake = _flow_of(plant, "vf-shw-edge-intake-t100")
        assert availability > intake

    def test_transfer_classification_is_load_bearing(self):
        kind = WholePlantX2Runtime._transfer_kind
        assert kind("vf-shw-info-t101-demand-t100") == "information"
        assert kind("vf-shw-info-line2-split-t100") == "information"
        assert kind("vf-shw-info-t100-plant-flow-chem") == "information"
        assert kind("vf-shw-edge-raw-source-intake") == "source_availability_outside_boundary"
        assert kind("vf-shw-edge-intake-t100") == "physical_water"
        assert kind("vf-shw-edge-t108-dist") == "physical_water"
        assert kind("vf-shw-edge-wash-t106") == "physical_water"

    def test_plant_water_ledger_is_conserved_over_the_run(self, plant):
        water = plant.balance_report()["plant_water"]
        assert water["plant_in_m3"] > 0.0
        assert water["plant_out_m3"] > 0.0
        assert water["process_loss_m3"] > 0.0
        assert water["tolerance_m3"] <= 1e-6
        assert abs(water["residual_m3"]) <= water["tolerance_m3"]
        assert water["conserved"] is True
        # the ledger closes to float rounding, NOT to a percentage allowance
        assert abs(water["residual_m3"]) <= 1e-9

    def test_a_percentage_allowance_would_hide_water(self, plant):
        water = plant.balance_report()["plant_water"]
        # the previous oracle accepted 5% of the input; the deficit that hid was
        # 0.55 m3 of water, i.e. materially larger than the float tolerance.
        hidden = 0.05 * water["plant_in_m3"] + 0.05
        assert hidden > 3.0
        assert abs(water["residual_m3"]) < 1e-6

    def test_information_inventory_would_break_the_ledger_if_counted(self, plant):
        water = plant.balance_report()["plant_water"]
        assert water["conserved"] is True
        # counting the information signals as water would leave a material residual
        assert abs(water["residual_m3"] + water["information_inventory_m3"]) > 1.0

    @pytest.mark.parametrize(
        "windows,scenario",
        [
            (1, WholePlantScenario()),  # startup
            (30, WholePlantScenario(raw_flow_sp_m3h=0.0)),  # stopped / zero inflow
            (30, WholePlantScenario(t106_dp_initial_kpa=78.0)),  # backwash + recovery
            (30, WholePlantScenario(line2_split_fraction=0.5)),  # LINE2 active
            (40, WholePlantScenario(t108_initial_volume_m3=91.0, t108_transfer_rated_flow_m3h=10.0)),
            (30, WholePlantScenario(t106_capacity_m3=10.0, t106_initial_volume_m3=9.0)),  # overflow
            (
                30,
                WholePlantScenario(
                    t100_initial_volume_m3=0.0,
                    t105_initial_volume_m3=0.0,
                    t106_initial_volume_m3=0.0,
                    t108_initial_volume_m3=0.0,
                    sludge_t201_initial_volume_m3=0.0,
                ),
            ),  # empty tanks
        ],
    )
    def test_plant_water_ledger_is_conserved_in_boundary_scenarios(self, windows, scenario):
        model = build_shwtp_whole_plant(scenario=scenario)
        worst = 0.0
        for index in range(1, windows + 1):
            model.run_window(f"window-{index}")
            water = model.balance_report()["plant_water"]
            worst = max(worst, abs(water["residual_m3"]))
            assert water["conserved"] is True, (index, scenario.name, water)
            assert abs(water["residual_m3"]) <= water["tolerance_m3"], (index, water)
        assert worst <= 1e-6, (scenario.name, worst)
        water = model.balance_report()["plant_water"]
        # every modelled loss is an EXPLICIT term, never a silent clamp
        assert water["overflow_m3"] >= 0.0
        assert water["shortfall_m3"] >= 0.0
        assert water["information_inventory_m3"] >= 0.0
        total = (
            water["water_inside_m3"]
            - water["plant_in_m3"]
            + water["plant_out_m3"]
            + water["process_loss_m3"]
            + water["overflow_m3"]
            - water["shortfall_m3"]
        )
        assert total == pytest.approx(water["residual_m3"], abs=1e-9)


class TestLevelInhibitRouting:
    """C02-4: a high-level permissive inhibits the UPSTREAM path (no deletion)."""

    def test_t108_high_level_inhibits_the_upstream_filter_path(self):
        # a low transfer capacity makes T108 rise into LAHH deterministically
        model = build_shwtp_whole_plant(
            scenario=WholePlantScenario(t108_initial_volume_m3=91.0, t108_transfer_rated_flow_m3h=10.0)
        )
        flip = None
        for index in range(1, 20):
            model.run_window(f"window-{index}")
            if _controller(model, "vf-shw-ctrl-t108-permissive")["outputs"]["inflow_enable"] is False:
                flip = index
                break
        assert flip is not None, "T108 never reached the high-level inhibit"
        t108 = _t108(model).monitor_values()
        t106 = _t106(model).monitor_values()
        t105 = _t105(model).monitor_values()
        assert t108["inflow_permitted"] is False
        # the declared upstream actuator PATH is closed instead of the water being deleted
        assert t106["filtered_path_inhibited"] is True
        assert t106["filtered_flow_m3h"] == 0.0
        assert t105["outflow_held_by_downstream_inhibit"] is True
        assert _flow_of(model, "vf-shw-edge-t106-t108") == 0.0
        assert "inhibit_upstream_intake" in _t108(model).open_alarms
        # the backwash sequence keeps exclusive ownership of the valve signal
        assert _controller(model, "vf-shw-ctrl-backwash-sequence")["outputs"]["inlet_valve_pos"] in (0.0, 100.0)

    def test_delivered_water_is_never_deleted_at_the_receiving_tank(self):
        """T108 keeps and balances every committed inflow across the transition."""
        model = build_shwtp_whole_plant(
            scenario=WholePlantScenario(t108_initial_volume_m3=91.0, t108_transfer_rated_flow_m3h=10.0)
        )
        t108 = _t108(model)
        delivered_previous = 0.0
        saw_inhibit = saw_delivery_while_inhibited = False
        for index in range(1, 20):
            volume_before = t108._volume_m3
            volume_in_before = t108._volume_in_m3
            model.run_window(f"window-{index}")
            values = t108.monitor_values()
            # the water T108 integrates THIS window is the inflow delivered last window
            assert t108._volume_in_m3 - volume_in_before == pytest.approx(delivered_previous * DT_H, abs=1e-9)
            assert t108._volume_m3 - volume_before == pytest.approx(
                (delivered_previous - values["withdrawal_m3h"]) * DT_H, abs=1e-9
            )
            if values["inflow_permitted"] is False:
                saw_inhibit = True
                if delivered_previous > 0.0:
                    saw_delivery_while_inhibited = True
            delivered_previous = _flow_of(model, "vf-shw-edge-t106-t108")
            assert t108._volume_m3 >= 0.0
        assert saw_inhibit, "the T108 high-level inhibit was never active"
        assert saw_delivery_while_inhibited, (
            "no window integrated a committed inflow while the inhibit was active "
            "(the pre-C02 defect deleted exactly this water)"
        )

    def test_t100_high_level_inhibits_the_upstream_intake_pump(self):
        model = build_shwtp_whole_plant(scenario=WholePlantScenario(t100_initial_volume_m3=90.0))
        model.run_window("window-1")
        assert _controller(model, "vf-shw-ctrl-t100-permissive")["outputs"]["intake_enable"] is False
        model.run_window("window-2")
        # inhibited at the SOURCE: the pump delivers nothing into the plant
        assert _t100(model).monitor_values()["inflow_permitted"] is False
        assert _flow_of(model, "vf-shw-edge-intake-t100") == 0.0
        assert model.participants["vf-shw-node-raw-intake"].monitor_values()["intake_flow_m3h"] == 0.0
        assert "inhibit_upstream_intake" in _t100(model).open_alarms

    def test_t100_never_deletes_a_received_intake(self):
        model = build_shwtp_whole_plant(
            scenario=WholePlantScenario(t100_initial_volume_m3=60.0, t100_capacity_m3=70.0, line1_demand_m3h=5.0)
        )
        t100 = _t100(model)
        delivered_previous = 0.0
        saw_inhibit = saw_integrated_after_inhibit = False
        for index in range(1, 40):
            volume_before = t100._volume_m3
            volume_in_before = t100._volume_in_m3
            overflow_before = t100._overflow_m3
            model.run_window(f"window-{index}")
            values = t100.monitor_values()
            assert t100._volume_in_m3 - volume_in_before == pytest.approx(delivered_previous * DT_H, abs=1e-9)
            # any capacity overflow is an EXPLICIT accounted term, never a silent loss
            assert (t100._volume_m3 - volume_before) + (t100._overflow_m3 - overflow_before) == pytest.approx(
                (delivered_previous - values["withdrawal_m3h"]) * DT_H, abs=1e-9
            )
            if values["inflow_permitted"] is False:
                saw_inhibit = True
                if delivered_previous > 0.0:
                    saw_integrated_after_inhibit = True
            delivered_previous = _flow_of(model, "vf-shw-edge-intake-t100")
        assert saw_inhibit, "T100 never reached its high-level inhibit"
        assert saw_integrated_after_inhibit, (
            "no window integrated a committed intake while the inhibit was active"
        )
        # and the upstream pump was actually stopped (not merely reported)
        assert _controller(model, "vf-shw-ctrl-t100-permissive")["outputs"]["intake_enable"] is False

    def test_the_audit_finds_no_other_deleting_tank(self, plant):
        """Every storage scope integrates exactly what the ledger delivered."""
        monitored = 0
        for scope_id, participant in plant.participants.items():
            values = participant.monitor_values()
            if "volume_m3" in values:
                assert participant._volume_in_m3 >= 0.0
                assert participant._overflow_m3 >= 0.0
                assert participant._shortfall_m3 < 1e-6, (scope_id, participant._shortfall_m3)
                monitored += 1
        assert monitored >= 5
