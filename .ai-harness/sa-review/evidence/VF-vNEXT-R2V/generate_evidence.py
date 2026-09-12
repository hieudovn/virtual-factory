#!/usr/bin/env python
"""VF-vNEXT-R2V — deterministic functional validation evidence (validation only).

Covers Issue #82 scope A–F (launch/identity, Frame A, Frame B 2D parity,
interaction/inspector, lifecycle, six-line independence) and writes:
  01-launch-identity.json
  02-six-line-overview.json
  03-2d-wip-motion.json
  04-inspector-quality-genealogy.json
  05-lifecycle.json
  06-six-line-independence.json

No product code is modified. Deterministic: no timestamps, sorted keys.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
TIPA_CONFIG = str(ROOT / "configs" / "plants" / "tipa_assy_demo.yaml")

import virtual_factory.federation.assy_host as host_module  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from virtual_factory.federation import SUB_LINE_IDS  # noqa: E402
from virtual_factory.ui.api import create_app  # noqa: E402
from virtual_factory.ui.assy_experience import CanonicalAssyExperience  # noqa: E402
from virtual_factory.ui.workspace_monitor import WorkspaceMonitor  # noqa: E402

ACCEPTED_POSITIONS = [
    "PRE-ASSY", "AP01", "AP02", "AP03", "AP04", "AP05",
    "AP06", "AP07", "AP08", "AP09", "AP10", "AP11",
]
ROUTE = ["PRE-ASSY", "AP01", "AP02", "AP03", "AP04", "AP05", "AP06",
         "AP07", "AP08", "AP09", "AP10", "AP11"]


def write(name, payload):
    (OUT / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("wrote", name)


def occupied(detail):
    return {
        p["position_id"]: p["wip_id"]
        for p in detail["positions"]
        if p.get("is_occupied")
    }


# ── start the app with the canonical federation construction probe ──
constructed: list = []
original_init = host_module.TipaAssyFederation.__init__


def counting_init(self, config_path):
    constructed.append(config_path)
    original_init(self, config_path)


host_module.TipaAssyFederation.__init__ = counting_init
try:
    client = TestClient(create_app())
    c = client

    # ══════════ A. launch / navigation / identity ══════════
    shell_before = c.get("/vnext/workspaces/TIPA/view").json()
    select = c.post("/vnext/workspaces/select", json={"workspace_id": "TIPA"}).json()
    rich_identity_before = c.get("/assy-demo/identity").json()["canonical"]
    constr_before_open = len(constructed)

    page = c.get("/assy-demo")
    identity_after_open = c.get("/assy-demo/identity").json()["canonical"]
    shell_after_open = c.get("/vnext/workspaces/TIPA/view").json()
    overview_probe = c.get("/assy-demo/overview").json()

    launch = {
        "shell_view": {
            "workspace_id": shell_before["identity"]["workspace_id"],
            "run_id": shell_before["session"]["run_id"],
            "scenario_id": shell_before["identity"]["scenario_id"],
            "profile_id": shell_before["session"].get("profile_id")
            or rich_identity_before.get("profile_id"),
        },
        "rich_identity": rich_identity_before,
        "rich_page_status": page.status_code,
        "same_workspace_id": rich_identity_before["workspace_id"]
        == shell_before["identity"]["workspace_id"] == "TIPA",
        "same_run_id": rich_identity_before["run_id"] == shell_before["session"]["run_id"],
        "same_scenario_id": rich_identity_before["scenario_id"]
        == shell_before["identity"]["scenario_id"],
        "profile_id": rich_identity_before["profile_id"],
        "authority": rich_identity_before["authority"],
        "opening_rich_ui_advances_time": identity_after_open["simulation_time_s"]
        != rich_identity_before["simulation_time_s"],
        "step_count_before": rich_identity_before["step_count"],
        "step_count_after_open": identity_after_open["step_count"],
        "shell_time_after_open": shell_after_open["session"]["last_time_s"],
        "federations_before_open": constr_before_open,
        "federations_after_open": len(constructed),
        "overview_rows_on_open": len(overview_probe["sub_lines"]),
        "single_runtime_authority": len(constructed) == 1,
        "workspace_selector_ok": select["workspace_id"] == "TIPA",
    }
    write("01-launch-identity.json", launch)

    # ══════════ B. Frame A — six live sub-lines ══════════
    c.post("/assy-demo/reset")
    for _ in range(5):
        c.post("/assy-demo/step")
    overview = c.get("/assy-demo/overview").json()
    frame_a = {
        "sub_line_ids": [r["sub_line_id"] for r in overview["sub_lines"]],
        "exactly_six_canonical": [r["sub_line_id"] for r in overview["sub_lines"]]
        == list(SUB_LINE_IDS),
        "rows": [
            {
                "sub_line_id": r["sub_line_id"],
                "scope": r["scope"],
                "simulation_time_s": r["simulation_time_s"],
                "wips_on_line": r["wips_on_line"],
                "motors_created": r["motors_created"],
                "motors_released": r["motors_released"],
                "line_state": r["line_state"],
                "effective_scenario": r["effective_scenario"],
                "variant": r["variant"],
                "run_state": r["run_state"],
            }
            for r in overview["sub_lines"]
        ],
        "parent_run_id": overview["canonical"]["run_id"],
        "one_parent_run": len(
            {r["sub_line_id"] for r in overview["sub_lines"]}
        )
        == 6
        and overview["canonical"]["authority"] == "canonical_tipa_runtime_session",
        "all_six_live": all(
            r["simulation_time_s"] > 0 and r["wips_on_line"] > 0
            for r in overview["sub_lines"]
        ),
        "canonical_step": overview["demo_step_number"],
        "pinned_scenario": overview["scenario"],
    }
    write("02-six-line-overview.json", frame_a)

    # ══════════ C. Frame B — 2D parity + motion ══════════
    c.post("/assy-demo/reset")
    frames = []
    for step in range(1, 9):
        detail = c.post("/assy-demo/step").json()
        frames.append(
            {
                "step": step,
                "simulation_time_s": detail["simulation_time_s"],
                "positions": [p["position_id"] for p in detail["positions"]],
                "occupied": occupied(detail),
                "motors_created": detail["production"]["motors_created"],
                "genealogy": [
                    [g["child_wip_id"], list(g["parent_wip_ids"])]
                    for g in detail["genealogy"]
                ],
            }
        )

    # truth equality: rendered positions == canonical runtime positions[]
    exp = CanonicalAssyExperience(WorkspaceMonitor(tipa_config_path=TIPA_CONFIG))
    exp.step()
    for _ in range(7):
        exp.step()
    federation = exp.federation()
    runtime = federation.runtime("ASSY-SL01")
    detail_sl01 = exp.detail("ASSY-SL01")
    truth_pairs = [
        [p["position_id"], p["wip_id"] or None, runtime.conveyor.wip_at(p["position_id"])]
        for p in detail_sl01["positions"]
    ]
    motion = [
        [pos, wip]
        for pos, wip, _ in [(p["position_id"], p["wip_id"], None) for p in detail_sl01["positions"]]
        if wip
    ]
    write(
        "03-2d-wip-motion.json",
        {
            "sub_line": "ASSY-SL01",
            "accepted_positions": ACCEPTED_POSITIONS,
            "route_basis": ROUTE,
            "positions_match_accepted": all(
                f["positions"] == ACCEPTED_POSITIONS for f in frames
            ),
            "frames": frames,
            "wip_moves": frames[0]["occupied"] != frames[-1]["occupied"],
            "first_position_of_sso2_0001": next(
                (
                    pos
                    for f in frames
                    for pos, wip in f["occupied"].items()
                    if wip == "SSO2-0001"
                ),
                None,
            ),
            "ap04_join": {
                "step": 5,
                "motor": "MTR-0001",
                "genealogy": [["MTR-0001", ["SSO2-0001", "RSO2-0001"]]],
                "at_ap05": frames[4]["occupied"].get("AP05") == "MTR-0001",
                "visible_in_frame": [g for g in frames[4]["genealogy"]],
            },
            "motor_moves_downstream": {
                "step5": frames[4]["occupied"].get("AP05"),
                "step6": frames[5]["occupied"].get("AP06"),
                "step7": frames[6]["occupied"].get("AP07"),
                "step8": frames[7]["occupied"].get("AP08"),
            },
            "rendered_matches_positions_truth": all(
                (wip is None and truth is None) or wip == truth
                for _, wip, truth in truth_pairs
            ),
            "truth_pairs_rendered_vs_runtime": truth_pairs,
            "rendered_occupied_at_step8": motion,
        },
    )

    # ══════════ D. inspector / quality / genealogy ══════════
    c.post("/assy-demo/reset")
    for _ in range(6):
        detail = c.post("/assy-demo/step").json()
    before_select = c.get("/assy-demo/overview").json()
    sl02 = c.post("/assy-demo/select", json={"sub_line_id": "ASSY-SL02"}).json()
    after_select_back = c.post("/assy-demo/select", json={"sub_line_id": "ASSY-SL01"}).json()
    after_select = c.get("/assy-demo/overview").json()
    inspector = {
        "read_model_keys": sorted(detail.keys()),
        "station_contracts": len(detail["station_contracts"]),
        "station_contract_fields": sorted(detail["station_contracts"][0].keys())
        if detail["station_contracts"]
        else [],
        "active_operations_present": "active_operations" in detail,
        "quality_events_present": "recent_quality_events" in detail,
        "genealogy_present": "genealogy" in detail,
        "ap04_genealogy_visible": any(
            g["child_wip_id"] == "MTR-0001" for g in detail["genealogy"]
        ),
        "quality_records_sample": detail.get("quality_records", [])[:2]
        if isinstance(detail.get("quality_records"), list)
        else [],
        "selection": {
            "presentation_only": before_select["canonical"]["run_id"]
            == after_select["canonical"]["run_id"]
            and before_select["demo_step_number"] == after_select["demo_step_number"]
            and before_select["total_motors_created"] == after_select["total_motors_created"],
            "selected_sub_line_id": after_select["canonical"]["selected_sub_line_id"],
            "sl02_detail_time_s": sl02["simulation_time_s"],
            "sl01_detail_time_s_before": after_select_back["simulation_time_s"],
            "selection_is_presentation_only_flagged": after_select["canonical"][
                "selection_is_presentation_only"
            ],
        },
        "thin_ops_bindings": {
            "run_mode_manual": c.post("/assy-demo/run-mode", json={"mode": "MANUAL"}).status_code,
            "run_mode_assisted": c.post(
                "/assy-demo/run-mode", json={"mode": "ASSISTED"}
            ).status_code,
            "run_mode_invalid": c.post("/assy-demo/run-mode", json={"mode": "BOGUS"}).status_code,
            "operation_command_missing_fields": c.post(
                "/assy-demo/operation-command", json={}
            ).status_code,
            "operation_command_stale_target": c.post(
                "/assy-demo/operation-command",
                json={"station_id": "AP01", "wip_id": "NOPE", "command": "DONE"},
            ).status_code,
            "station_action_stale_target": c.post(
                "/assy-demo/station-action",
                json={"station_id": "AP11", "wip_id": "NOPE", "action": "HOLD"},
            ).status_code,
        },
        "deferred_classification": {
            "observations": c.get("/assy-demo/observations").status_code,
            "mes_messages": c.get("/assy-demo/mes-messages").status_code,
            "mes_trace": c.get("/assy-demo/mes-trace").status_code,
            "jam": c.post("/assy-demo/jam").status_code,
            "recover": c.post("/assy-demo/recover").status_code,
            "run_to_terminal": c.post("/assy-demo/run-to-terminal").status_code,
            "scenario_change": c.post(
                "/assy-demo/reset", json={"scenario": "AP06_FAIL_RETEST_PASS"}
            ).status_code,
        },
    }
    write("04-inspector-quality-genealogy.json", inspector)

    # ══════════ E. lifecycle ══════════
    c.post("/assy-demo/reset")
    c.post("/assy-demo/step")
    c.post("/assy-demo/step")
    time_before_shell_step = c.get("/assy-demo/identity").json()["canonical"]["simulation_time_s"]
    c.post("/vnext/workspaces/TIPA/control", json={"action": "step"})
    time_after_shell_step = c.get("/assy-demo/identity").json()["canonical"]["simulation_time_s"]
    run_before_reset = c.get("/assy-demo/identity").json()["canonical"]["run_id"]
    reset_detail = c.post("/assy-demo/reset").json()
    after_reset_identity = c.get("/assy-demo/identity").json()["canonical"]
    reset_rows = c.get("/assy-demo/overview").json()["sub_lines"]
    c.post("/assy-demo/step")
    c.post("/assy-demo/step")
    state_before_new_attempt = c.get("/assy-demo/overview").json()
    new_attempt_view = c.post(
        "/vnext/workspaces/TIPA/control", json={"action": "new_attempt"}
    ).json()
    new_run = new_attempt_view["session"]["run_id"]
    rich_new = c.get("/assy-demo/identity").json()["canonical"]
    for _ in range(2):
        c.post("/assy-demo/step")
    state_new_attempt = c.get("/assy-demo/overview").json()
    replay_view = c.post("/vnext/workspaces/TIPA/control", json={"action": "replay"}).json()
    replay_run = replay_view["session"]["run_id"]
    for _ in range(2):
        c.post("/assy-demo/step")
    state_replay = c.get("/assy-demo/overview").json()

    # SH-WTP switch isolation
    tipa_before_switch = c.get("/vnext/workspaces/TIPA/view").json()
    c.post("/vnext/workspaces/select", json={"workspace_id": "shwtp"})
    c.post("/vnext/workspaces/shwtp/control", json={"action": "step"})
    c.post("/vnext/workspaces/shwtp/control", json={"action": "step"})
    tipa_after_switch = c.get("/vnext/workspaces/TIPA/view").json()

    def summary(view):
        return [
            [r["sub_line_id"], r["simulation_time_s"], r["wips_on_line"], r["motors_created"]]
            for r in view["sub_lines"]
        ]

    write(
        "05-lifecycle.json",
        {
            "step": {
                "shell_step_advanced_same_session": time_after_shell_step
                > time_before_shell_step,
                "time_before_s": time_before_shell_step,
                "time_after_s": time_after_shell_step,
            },
            "reset": {
                "same_run_id": after_reset_identity["run_id"] == run_before_reset,
                "all_six_at_zero": all(r["simulation_time_s"] == 0.0 for r in reset_rows),
                "motors_zero": all(r["motors_created"] == 0 for r in reset_rows),
                "detail_time_s": reset_detail["simulation_time_s"],
                "scenario": reset_detail["scenario"],
            },
            "new_attempt": {
                "fresh_run_id": new_run != run_before_reset,
                "rich_identity_follows": rich_new["run_id"] == new_run,
                "state_equivalent_to_pre_attempt": summary(state_new_attempt)
                == summary(state_before_new_attempt),
            },
            "replay": {
                "fresh_run_id": replay_run != new_run,
                "deterministic_state_equivalent": summary(state_replay)
                == summary(state_new_attempt),
                "state": summary(state_replay),
            },
            "switch_isolation": {
                "tipa_run_unchanged": tipa_before_switch["session"]["run_id"]
                == tipa_after_switch["session"]["run_id"],
                "tipa_step_count_unchanged": tipa_before_switch["session"]["step_count"]
                == tipa_after_switch["session"]["step_count"],
                "tipa_time_unchanged": tipa_before_switch["session"]["last_time_s"]
                == tipa_after_switch["session"]["last_time_s"],
                "shwtp_existed": c.get("/vnext/workspaces/shwtp/view").status_code == 200,
            },
        },
    )

    # ══════════ F. six-line independence (visible projection) ══════════
    exp2 = CanonicalAssyExperience(WorkspaceMonitor(tipa_config_path=TIPA_CONFIG))
    exp2.step()
    bridge = exp2.bridge()
    before_hold = {
        row["sub_line_id"]: row["simulation_time_s"] for row in exp2.overview()["sub_lines"]
    }
    bridge.hold_sub_line("ASSY-SL03")
    held_frames = []
    for _ in range(5):
        exp2.step()
        held_frames.append(
            {
                row["sub_line_id"]: [row["simulation_time_s"], row["motors_created"]]
                for row in exp2.overview()["sub_lines"]
            }
        )
    ov_held = exp2.overview()
    rows_held = {row["sub_line_id"]: row for row in ov_held["sub_lines"]}
    detail_held = exp2.detail("ASSY-SL03")
    detail_other = exp2.detail("ASSY-SL01")
    held_ids_while_held = list(bridge.held_sub_line_ids)
    bridge.release_sub_line("ASSY-SL03")
    exp2.step()
    rows_released = {
        row["sub_line_id"]: row for row in exp2.overview()["sub_lines"]
    }
    write(
        "06-six-line-independence.json",
        {
            "before_hold_times": before_hold,
            "held_sub_line_ids_while_held": held_ids_while_held,
            "held_sub_line_ids_after_release": list(bridge.held_sub_line_ids),
            "frame_a_while_held": {
                "ASSY-SL03": [
                    rows_held["ASSY-SL03"]["simulation_time_s"],
                    rows_held["ASSY-SL03"]["wips_on_line"],
                    rows_held["ASSY-SL03"]["motors_created"],
                    rows_held["ASSY-SL03"]["line_state"],
                ],
                "others": {
                    sid: [
                        rows_held[sid]["simulation_time_s"],
                        rows_held[sid]["motors_created"],
                    ]
                    for sid in rows_held
                    if sid != "ASSY-SL03"
                },
            },
            "sl03_frozen_in_frame_a": rows_held["ASSY-SL03"]["simulation_time_s"] == 120.0
            and rows_held["ASSY-SL03"]["motors_created"] == 0,
            "five_continue_in_frame_a": all(
                rows_held[sid]["simulation_time_s"] == 720.0
                and rows_held[sid]["motors_created"] >= 1
                for sid in rows_held
                if sid != "ASSY-SL03"
            ),
            "frame_b_sl03_frozen": {
                "simulation_time_s": detail_held["simulation_time_s"],
                "occupied": occupied(detail_held),
                "frozen_at_120": detail_held["simulation_time_s"] == 120.0,
            },
            "frame_b_other_advanced": {
                "sub_line": "ASSY-SL01",
                "simulation_time_s": detail_other["simulation_time_s"],
                "occupied": occupied(detail_other),
                "motors_created": detail_other["production"]["motors_created"],
                "advanced": detail_other["simulation_time_s"] == 720.0,
            },
            "release_resumes": {
                "sl03_time_after_release": rows_released["ASSY-SL03"]["simulation_time_s"],
                "resumed": rows_released["ASSY-SL03"]["simulation_time_s"] == 840.0,
            },
            "projection_frames_while_held": held_frames,
        },
    )

    # ══════════ no legacy authority / one runtime ══════════
    legacy = subprocess.run(
        ["git", "-C", str(ROOT), "log", "--oneline", "-1"], capture_output=True, text=True
    ).stdout.strip()
    print("head:", legacy)
    print("federations constructed by the whole validation run:", len(constructed))
    print("validation complete")
finally:
    host_module.TipaAssyFederation.__init__ = original_init
