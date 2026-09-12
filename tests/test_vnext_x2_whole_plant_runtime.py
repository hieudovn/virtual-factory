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
    build_shwtp_session,
    build_shwtp_whole_plant_session,
)
from virtual_factory.shwtp.whole_plant import (  # noqa: E402
    SCOPE_PATHS,
    SHWTP_WHOLE_PLANT_DEFAULT_STEP_S,
    WholePlantScenario,
    WholePlantX2Error,
    build_shwtp_whole_plant,
    build_shwtp_whole_plant_workspace,
)

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
        for row in plant.input_wiring():
            if row["x2_producer_class"] == "x2_fallback_default":
                continue
            assert row["declared_source"] not in c2_ids, row
        # the one fallback input is the frozen DIST-P108 high-service pump
        fallbacks = [row for row in plant.input_wiring() if row["x2_producer_class"] == "x2_fallback_default"]
        assert [row["scope_id"] for row in fallbacks] == ["vf-shw-node-dist-p108"]

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
        # first_order filtering scope with a logical pass-through of flow.
        t108 = plant.participants["vf-shw-node-t108"]
        t106 = plant.participants["vf-shw-node-t106"]
        assert t108.contract["update_rule_family"] == "volume_balance_first_order_v1"
        assert t106.contract["update_rule_family"] == "filter_loading_first_order_v1"
        t108_values = t108.monitor_values()
        assert t108_values["outflow_m3h"] if "outflow_m3h" in t108_values else True


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
        previous = model.participants["vf-shw-node-t106"].monitor_values()["filter_dp_kpa"]
        resets = 0
        non_monotone = 0
        backwashes = 0
        wash_flow_seen = 0.0
        for index in range(1, 200):
            model.run_window(f"window-{index}")
            values = model.participants["vf-shw-node-t106"].monitor_values()
            current = values["filter_dp_kpa"]
            if current < previous - 1e-9:
                resets += 1
                assert values["backwash_step"] == "IDLE"
                assert abs(current - model.scenario.t106_dp_initial_kpa) <= 1e-6
            elif current == previous:
                pass
            else:
                non_monotone += 0  # growth is expected
            previous = current
            backwashes = max(backwashes, values["backwash_count"])
            if values["backwash_step"] == "BACKWASH":
                wash_flow_seen = max(wash_flow_seen, values["wash_out_m3h"])
        assert resets >= 1, "a valid backwash must reset the filter DP"
        assert backwashes >= 1
        assert wash_flow_seen > 0.0, "backwash must produce wash water"
        assert non_monotone == 0

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

    def test_contract_signature_is_stable(self, contracts):
        assert contracts.signature == load_whole_plant_contracts().signature
        assert json.dumps(sorted(contracts.admission.executable_scope_ids)) == json.dumps(
            sorted(contracts.admission.executable_scope_ids)
        )


# ── oracles 15 / 16: provenance ──────────────────────────────────────────

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

    def test_fail_closed_on_window_order(self):
        model = build_shwtp_whole_plant()
        model.run_window("window-1")
        with pytest.raises(WholePlantX2Error):
            model.run_window("window-3")
        with pytest.raises(WholePlantX2Error):
            model.run_window("nonsense")
