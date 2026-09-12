"""VF-SHW-X3 - canonical session wiring, attempt identity and compatibility.

Pins the SA-required integration surface:

 1  the canonical SH-WTP default is the X3 whole-plant profile (1-second global
    windows, two C2 PI loops) reached through ONE attempt-bound RuntimeSession /
    RunLifecycleService / bridge (no second session, clock or lifecycle authority);
 2  the model identity comes from the active attempt context and survives a reset,
    while new attempt / replay receive fresh lifecycle identities;
 3  identical sessions produce identical deterministic trajectories;
 4  the accepted X2 60-second zero-C2 model and the G21 slice stay explicitly
    constructible (compatibility, not the default);
 5  the read-only workspace monitor projects the X3 model with the four authority
    labels and no site truth.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from virtual_factory.runcontrol import RuntimeSession  # noqa: E402
from virtual_factory.shwtp import (  # noqa: E402
    SHWTP_DEFAULT_MODEL,
    SHWTP_MODEL_G21_SLICE,
    SHWTP_MODEL_WHOLE_PLANT_X2,
    SHWTP_MODEL_WHOLE_PLANT_X3,
    build_shwtp_g21_slice_session,
    build_shwtp_session,
    build_shwtp_whole_plant_session,
    build_shwtp_whole_plant_x3_session,
)
from virtual_factory.shwtp.bridge import ShwtpExecutionBridge  # noqa: E402
from virtual_factory.shwtp.whole_plant import SCOPE_PATHS  # noqa: E402
from virtual_factory.shwtp.x3_whole_plant import WholePlantX3Runtime  # noqa: E402

EXPECTED_SCOPES = 16
AUTHORITY_KEYS = (
    "site_truth",
    "simulation_truth",
    "vf_runtime_authorization",
    "site_authorized_execution",
)


def _fingerprint(model) -> tuple:
    return tuple(
        (
            row["scope_id"],
            row["values"].get("time_s"),
            row["values"].get("volume_m3"),
            row["values"].get("level_m"),
            row["values"].get("inflow_m3h"),
        )
        for row in model.monitor_rows()
    )


class TestCanonicalX3Session:
    def test_default_is_the_x3_profile_on_one_second_windows(self):
        assert SHWTP_DEFAULT_MODEL == SHWTP_MODEL_WHOLE_PLANT_X3 == "whole_plant_x3"
        session = build_shwtp_session()
        assert isinstance(session, RuntimeSession)
        assert session.workspace_id == "shwtp"
        assert session.scenario_id == "shwtp-x3-whole-plant"
        session.advance()
        model = session.record.bridge.model
        assert isinstance(model, WholePlantX3Runtime)
        assert isinstance(session.record.bridge, ShwtpExecutionBridge)
        assert len(model.participants) == EXPECTED_SCOPES
        assert set(model.participants) == set(SCOPE_PATHS)
        assert model.communication_step_s == 1.0
        assert model.tick_index == 1
        assert len(model.control_layer.active_c2_loop_ids) == 2

    def test_bridge_natural_boundary_is_one_second(self):
        session = build_shwtp_session()
        session.advance()
        bridge = session.record.bridge
        # after one window the next natural boundary is the second one
        assert bridge.natural_next_boundary(("shwtp",)) == 2.0
        assert session.record.bridge.model.tick_index == 1

    def test_x3_compatibility_factory_builds_the_same_model(self):
        session = build_shwtp_whole_plant_x3_session()
        assert session.scenario_id == "shwtp-x3-whole-plant"
        session.advance()
        assert isinstance(session.record.bridge.model, WholePlantX3Runtime)

    def test_attempt_identity_is_carried_by_the_x3_model(self):
        session = build_shwtp_session()
        session.advance()
        run_id = session.record.context.run_id
        model = session.record.bridge.model
        assert model.run_id == run_id
        assert model.runtime_truth()["run_id_source"] == "attempt_context"
        assert {participant.run_id for participant in model.participants.values()} == {run_id}
        rows = model.transfer_records()
        assert rows
        assert {row["run_id"] for row in rows} == {run_id}
        assert all(row["window_id"].startswith(run_id) for row in rows)

    def test_reset_keeps_the_identity_and_the_trajectory(self):
        session = build_shwtp_session()
        for _ in range(30):
            session.advance()
        run_id = session.record.context.run_id
        first = _fingerprint(session.record.bridge.model)
        session.reset()
        assert session.record.context.run_id == run_id
        session.advance()
        assert session.record.bridge.model.tick_index == 1
        assert session.record.bridge.model.run_id == run_id
        for _ in range(29):
            session.advance()
        assert _fingerprint(session.record.bridge.model) == first

    def test_new_attempt_and_replay_issue_fresh_identities(self):
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
            assert {row["run_id"] for row in model.transfer_records()} == {issued}

    def test_two_sessions_are_independent_and_deterministic(self):
        first = build_shwtp_session()
        second = build_shwtp_session()
        for _ in range(20):
            first.advance()
            second.advance()
        assert _fingerprint(first.record.bridge.model) == _fingerprint(second.record.bridge.model)
        assert first.record.bridge.model is not second.record.bridge.model


class TestExplicitCompatibility:
    def test_x2_model_stays_available_with_zero_c2(self):
        session = build_shwtp_session(model=SHWTP_MODEL_WHOLE_PLANT_X2)
        assert session.scenario_id == "shwtp-x2-whole-plant"
        session.advance()
        model = session.record.bridge.model
        assert type(model).__name__ == "WholePlantX2Runtime"
        assert model.communication_step_s == 60.0
        assert not hasattr(model, "control_layer")
        compatibility = build_shwtp_whole_plant_session()
        compatibility.advance()
        assert type(compatibility.record.bridge.model).__name__ == "WholePlantX2Runtime"

    def test_g21_slice_stays_available_only_explicitly(self):
        session = build_shwtp_session(model=SHWTP_MODEL_G21_SLICE)
        assert session.scenario_id == "shwtp-g21-slice"
        session.advance()
        assert len(session.record.bridge.model.scopes) == 5
        compatibility = build_shwtp_g21_slice_session()
        compatibility.advance()
        assert len(compatibility.record.bridge.model.scopes) == 5

    def test_unknown_model_and_ambient_run_id_fail_closed(self):
        with pytest.raises(Exception):
            build_shwtp_session(model="not-a-model")
        with pytest.raises(Exception):
            build_shwtp_session(model=SHWTP_MODEL_WHOLE_PLANT_X3, run_id="run-fixed")


class TestReadOnlyMonitorProjection:
    def test_monitor_renders_the_x3_model_with_authority_labels(self):
        from virtual_factory.ui.workspace_monitor import WorkspaceMonitor

        monitor = WorkspaceMonitor()
        monitor.select("shwtp")
        view = monitor.view("shwtp")
        assert view["workspace_id"] == "shwtp"
        assert view["runtime"] in (
            "SH-WTP X3 whole plant (1 s windows, two PI loops)",
            "SH-WTP whole plant (canonical X3 profile; X2/G21 compatible)",
        )
        assert len(view["structure"]) == EXPECTED_SCOPES
        assert len(view["values"]) == EXPECTED_SCOPES
        expected_authority = {
            "site_truth": False,
            "simulation_truth": "synthetic_reference",
            "vf_runtime_authorization": "NOT_AUTHORIZED",
            "site_authorized_execution": "NOT_AUTHORIZED",
        }
        for key in AUTHORITY_KEYS:
            assert view[key] == expected_authority[key]
        assert view["ui_page"] is None

    def test_monitor_projection_is_read_only(self):
        """Selecting the workspace must not advance the canonical model."""
        from virtual_factory.ui.workspace_monitor import WorkspaceMonitor

        session = build_shwtp_session()
        monitor = WorkspaceMonitor()
        monitor._sessions["shwtp"] = session
        view = monitor.view("shwtp")
        assert view["workspace_id"] == "shwtp"
        bridge = session.record.bridge
        if bridge is not None and getattr(bridge, "model", None) is not None:
            assert bridge.model.tick_index == 0
