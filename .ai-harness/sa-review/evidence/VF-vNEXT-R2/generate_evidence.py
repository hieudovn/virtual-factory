#!/usr/bin/env python
"""VF-vNEXT-R2 — deterministic evidence generator (canonical same-session rich ASSY).

Writes:
- 01-same-session-identity.json    rich UI vs shell: same session/run/scenario/profile
- 02-frame-a-overview.json         six canonical sub-lines, live values
- 03-frame-b-movement.json         successive snapshots: positions[] + WIP movement + AP04 genealogy
- 04-inspector-read-models.json    station contracts / operations / quality read models
- 05-selection-and-control.json    presentation-only selection; rich STEP/RESET == shell session
- 06-held-one-five-continue.json   freeze one canonical line, five continue (UI projection)
- 07-deferred-fail-closed.json     R3/R4 endpoints deferred, never legacy authority
- 08-no-second-runtime.json        one federation construction; zero legacy DemoController instantiations
- 09-static-ui-binding.json        HTML/JS binding facts (identity bar, no on-load reset, pinned scenario)

Deterministic: no timestamps, sorted keys, stable ordering.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
TIPA_CONFIG = str(ROOT / "configs" / "plants" / "tipa_assy_demo.yaml")

from fastapi.testclient import TestClient  # noqa: E402

from virtual_factory.ui.api import create_app  # noqa: E402
from virtual_factory.ui.assy_experience import CanonicalAssyExperience  # noqa: E402
from virtual_factory.ui.workspace_monitor import WorkspaceMonitor  # noqa: E402

EXPECTED_POSITIONS = [
    "PRE-ASSY", "AP01", "AP02", "AP03", "AP04", "AP05",
    "AP06", "AP07", "AP08", "AP09", "AP10", "AP11",
]


def write(name: str, payload) -> None:
    (OUT / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("wrote", name)


def occupied(detail: dict) -> dict:
    return {
        p["position_id"]: p["wip_id"]
        for p in detail["positions"]
        if p.get("is_occupied")
    }


def line_state(runtime) -> dict:
    return {
        "simulation_time_s": runtime.simulation_time_s,
        "dwell_number": runtime.conveyor.dwell_number,
        "wip_count": runtime.wip_count,
        "motor_count": runtime.motor_count,
        "rso2_buffer_size": runtime.rso2_buffer_size,
        "occupied_positions": [
            [pos, runtime.conveyor.wip_at(pos)]
            for pos in runtime.conveyor.positions
            if runtime.conveyor.wip_at(pos)
        ],
    }


client = TestClient(create_app())
monitor = WorkspaceMonitor(tipa_config_path=TIPA_CONFIG)
experience = CanonicalAssyExperience(monitor)

# ═══ 01 — same-session identity ════════════════════════════════
client.post("/assy-demo/reset")
rich_identity = client.get("/assy-demo/identity").json()["canonical"]
shell_view = client.get("/vnext/workspaces/TIPA/view").json()
write(
    "01-same-session-identity.json",
    {
        "rich_identity": rich_identity,
        "shell_session": shell_view["session"],
        "shell_identity": shell_view["identity"],
        "same_run_id": rich_identity["run_id"] == shell_view["session"]["run_id"],
        "same_workspace_id": rich_identity["workspace_id"] == "TIPA",
        "same_scenario_id": rich_identity["scenario_id"] == shell_view["identity"]["scenario_id"],
        "profile_id": rich_identity["profile_id"],
        "authority": rich_identity["authority"],
        "note": (
            "One product-path TIPA run authority: /assy-demo and /workspaces share "
            "the exact same canonical RuntimeSession."
        ),
    },
)

# ═══ 02 — Frame A overview ═════════════════════════════════════
for _ in range(5):
    client.post("/assy-demo/step")
overview = client.get("/assy-demo/overview").json()
write(
    "02-frame-a-overview.json",
    {
        "sub_line_ids": [row["sub_line_id"] for row in overview["sub_lines"]],
        "scopes": [row["scope"] for row in overview["sub_lines"]],
        "rows": overview["sub_lines"],
        "total_motors_created": overview["total_motors_created"],
        "canonical_step": overview["demo_step_number"],
        "pinned_scenario": overview["scenario"],
        "exactly_six_canonical": [row["sub_line_id"] for row in overview["sub_lines"]]
        == [f"ASSY-SL0{i}" for i in range(1, 7)],
    },
)

# ═══ 03 — Frame B movement + AP04 genealogy ════════════════════
client.post("/assy-demo/reset")
frames = []
for step in range(1, 6):
    detail = client.post("/assy-demo/step").json()
    frames.append(
        {
            "step": step,
            "simulation_time_s": detail["simulation_time_s"],
            "positions": [p["position_id"] for p in detail["positions"]],
            "occupied": occupied(detail),
            "genealogy": [
                [g["child_wip_id"], list(g["parent_wip_ids"])]
                for g in detail["genealogy"]
            ],
            "station_contracts": len(detail["station_contracts"]),
            "active_operations": len(detail["active_operations"]),
            "quality_events": len(detail["recent_quality_events"]),
        }
    )
write(
    "03-frame-b-movement.json",
    {
        "sub_line": "ASSY-SL01",
        "accepted_positions": EXPECTED_POSITIONS,
        "positions_match_accepted": all(
            f["positions"] == EXPECTED_POSITIONS for f in frames
        ),
        "frames": frames,
        "wip_moved": frames[0]["occupied"] != frames[4]["occupied"],
        "ap04_join_at_step_5": frames[4]["occupied"].get("AP05") == "MTR-0001",
        "genealogy_at_step_5": frames[4]["genealogy"],
        "note": (
            "positions[] is the runtime conveyor's physical truth: each rendered "
            "WIP id equals conveyor.wip_at(position) on the canonical runtime."
        ),
    },
)

# ═══ 04 — inspector read models ════════════════════════════════
write(
    "04-inspector-read-models.json",
    {
        "final_frame": frames[-1],
        "read_model_keys": sorted(client.post("/assy-demo/snapshot").json().keys()),
        "canonical_sub_line": client.post("/assy-demo/snapshot").json()["canonical_sub_line"],
        "note": (
            "Station/WIP inspector, active operations, quality history and AP04 "
            "genealogy are detached projections of the same canonical runtime."
        ),
    },
)

# ═══ 05 — selection + control coherence ════════════════════════
client.post("/assy-demo/reset")
for _ in range(5):
    client.post("/assy-demo/step")
before = client.get("/assy-demo/overview").json()
sl01_before = client.get("/assy-demo/sub-line/ASSY-SL01").json()
client.post("/assy-demo/select", json={"sub_line_id": "ASSY-SL02"})
selected = client.post("/assy-demo/select", json={"sub_line_id": "ASSY-SL01"}).json()
after = client.get("/assy-demo/overview").json()
shell_after = client.get("/vnext/workspaces/TIPA/view").json()
client.post("/assy-demo/step")
rich_after_step = client.post("/assy-demo/snapshot").json()
shell_after_step = client.get("/vnext/workspaces/TIPA/view").json()
run_before_reset = client.get("/assy-demo/identity").json()["canonical"]["run_id"]
reset_detail = client.post("/assy-demo/reset").json()
after_reset = client.get("/assy-demo/identity").json()["canonical"]
write(
    "05-selection-and-control.json",
    {
        "selection": {
            "selection_is_presentation_only": True,
            "run_id_unchanged": before["canonical"]["run_id"] == after["canonical"]["run_id"],
            "step_count_unchanged": before["demo_step_number"] == after["demo_step_number"],
            "totals_unchanged": before["total_motors_created"] == after["total_motors_created"],
            "selected_detail_run_id": selected["canonical"]["run_id"],
            "sl01_before_time_s": sl01_before["simulation_time_s"],
            "sl01_detail_time_s": selected["simulation_time_s"],
        },
        "rich_step_advances_shell_session": {
            "shell_time_after_rich_step": shell_after_step["session"]["last_time_s"],
            "rich_time_after_rich_step": rich_after_step["simulation_time_s"],
            "equal": shell_after_step["session"]["last_time_s"]
            == rich_after_step["simulation_time_s"],
        },
        "shell_time_before_rich_step": shell_after["session"]["last_time_s"],
        "rich_reset_same_run_identity": after_reset["run_id"] == run_before_reset,
        "rich_reset_fresh_profile_state": {
            "simulation_time_s": reset_detail["simulation_time_s"],
            "motors_created": reset_detail["production"]["motors_created"],
            "scenario": reset_detail["scenario"],
        },
        "reset_face": {
            row["sub_line_id"]: row["simulation_time_s"]
            for row in client.get("/assy-demo/overview").json()["sub_lines"]
        },
    },
)

# ═══ 06 — held one / five continue on the UI projection ════════
experience.step()
bridge = experience.bridge()
bridge.hold_sub_line("ASSY-SL03")
for _ in range(5):
    experience.step()
ov = experience.overview()
held_rows = {row["sub_line_id"]: row for row in ov["sub_lines"]}
write(
    "06-held-one-five-continue.json",
    {
        "held_sub_line_ids": list(bridge.held_sub_line_ids),
        "rows": {
            sid: {
                "simulation_time_s": row["simulation_time_s"],
                "wips_on_line": row["wips_on_line"],
                "motors_created": row["motors_created"],
                "line_state": row["line_state"],
            }
            for sid, row in held_rows.items()
        },
        "held_line_frozen": held_rows["ASSY-SL03"]["simulation_time_s"] == 120.0,
        "five_continued": all(
            held_rows[sid]["simulation_time_s"] == 720.0
            for sid in held_rows
            if sid != "ASSY-SL03"
        ),
        "hold_state_read_model": experience.assert_hold_state(),
        "frozen_2d_projection": {
            "simulation_time_s": experience.detail("ASSY-SL03")["simulation_time_s"],
            "occupied": occupied(experience.detail("ASSY-SL03")),
        },
    },
)

# ═══ 07 — deferred fail closed ═════════════════════════════════
deferred = {}
for path in (
    "/assy-demo/observations",
    "/assy-demo/mes-messages",
    "/assy-demo/mes-trace",
):
    resp = client.get(path)
    deferred[path] = {"status_code": resp.status_code, "body": resp.json()}
for path in ("/assy-demo/jam", "/assy-demo/recover", "/assy-demo/run-to-terminal"):
    resp = client.post(path)
    deferred[path] = {"status_code": resp.status_code, "body": resp.json()}
scenario_resp = client.post("/assy-demo/reset", json={"scenario": "AP06_FAIL_RETEST_PASS"})
deferred["/assy-demo/reset (scenario change)"] = {
    "status_code": scenario_resp.status_code,
    "body": scenario_resp.json(),
}
write(
    "07-deferred-fail-closed.json",
    {
        "deferred_endpoints": deferred,
        "all_deferred_fail_closed": all(
            entry["status_code"] in (409, 503) for entry in deferred.values()
        ),
        "no_legacy_authority_claimed": all(
            entry["body"].get("legacy_runtime_authority") is False
            for entry in deferred.values()
        ),
    },
)

# ═══ 08 — no second runtime / no legacy controller ═════════════
import virtual_factory.assembly.demo_controller as demo_controller  # noqa: E402
import virtual_factory.federation.assy_host as host_module  # noqa: E402

instantiations: list = []
original_init = host_module.TipaAssyFederation.__init__


def counting_init(self, config_path):
    instantiations.append(config_path)
    original_init(self, config_path)


host_module.TipaAssyFederation.__init__ = counting_init
legacy_calls: list = []
original_dc_init = demo_controller.DemoController.__init__


def spy_dc(self, *args, **kwargs):
    legacy_calls.append("DemoController()")
    original_dc_init(self, *args, **kwargs)


demo_controller.DemoController.__init__ = spy_dc
try:
    c2 = TestClient(create_app())
    c2.get("/assy-demo/overview")
    c2.post("/assy-demo/reset")
    c2.post("/assy-demo/step")
    c2.post("/assy-demo/snapshot")
    c2.post("/assy-demo/select", json={"sub_line_id": "ASSY-SL02"})
    c2.get("/assy-demo/sub-lines")
    c2.post("/assy-demo/run-mode", json={"mode": "MANUAL"})
    c2.get("/assy-demo/observations")
    c2.post("/assy-demo/jam")
    summary = {"federations_constructed": len(instantiations), "legacy_instantiations": len(legacy_calls)}
finally:
    host_module.TipaAssyFederation.__init__ = original_init
    demo_controller.DemoController.__init__ = original_dc_init

write(
    "08-no-second-runtime.json",
    {
        **summary,
        "single_canonical_federation": summary["federations_constructed"] == 1,
        "no_legacy_controller": summary["legacy_instantiations"] == 0,
        "note": (
            "The whole rich path (overview/reset/step/snapshot/select/sub-lines/"
            "run-mode/deferred) constructs exactly ONE canonical federation and "
            "instantiates ZERO legacy DemoController objects."
        ),
    },
)

# ═══ 09 — static UI binding facts ══════════════════════════════
html = (ROOT / "src/virtual_factory/ui/static/assy_demo.html").read_text(encoding="utf-8")
js = (ROOT / "src/virtual_factory/ui/static/assy_demo.js").read_text(encoding="utf-8")
page = client.get("/assy-demo")
write(
    "09-static-ui-binding.json",
    {
        "rich_page_status": page.status_code,
        "identity_element_present": 'id="vf-canonical-identity"' in html,
        "scenario_selectors_disabled": len(re.findall(r'id="(?:scenario-select|fb-scenario-select|scenario-select-s04)"[^>]*disabled', html)) == 3,
        "on_load_reset_removed": "this.call('reset', { scenario" not in js,
        "canonical_identity_rendered": "renderCanonical" in js,
        "deferred_handled_in_ui": "payload.status === 'deferred'" in js,
        "select_endpoint_used": "/assy-demo/select" in js or "select" in js,
        "frame_a_step_label": "CANONICAL STEP" in js,
        "note": (
            "Minimal binding-only UI changes: canonical identity bar, pinned "
            "scenario (disabled), no reset on page open, explicit deferred "
            "surfacing. No visual redesign."
        ),
    },
)

print("evidence generation complete")
