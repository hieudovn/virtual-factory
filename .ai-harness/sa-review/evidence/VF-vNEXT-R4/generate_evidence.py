"""VF-vNEXT-R4 — deterministic evidence generator (Issue #83).

Sections (Issue #83 "Mandatory parity evidence"):
A. same-session authority;
B. jam / recovery;
C. run-to-terminal (+ parity with manual stepping);
D. OEE / final summary;
E. scenario / new-run semantics;
F. existing parity oracle.

Browser sanity (G) lives in ``07-browser-sanity.md``.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from virtual_factory.federation import SUB_LINE_IDS
from virtual_factory.ui.api import create_app
from virtual_factory.ui.assy_experience import CanonicalAssyExperience
from virtual_factory.ui.assy_output import CanonicalAssyOutput
from virtual_factory.ui.workspace_monitor import WorkspaceMonitor

OUT = Path(__file__).resolve().parent


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "configs" / "plants" / "tipa_assy_demo.yaml").exists():
            return parent
    raise RuntimeError("repository root not found from R4 evidence generator")


TIPA_CONFIG = str(_repo_root() / "configs" / "plants" / "tipa_assy_demo.yaml")


def _write(name: str, payload: dict) -> None:
    (OUT / name).write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    print("wrote", name)


def _client() -> TestClient:
    return TestClient(create_app())


def _output() -> CanonicalAssyOutput:
    return CanonicalAssyOutput(
        CanonicalAssyExperience(WorkspaceMonitor(tipa_config_path=TIPA_CONFIG))
    )


def _frame_a(client: TestClient) -> dict[str, dict]:
    overview = client.get("/assy-demo/overview").json()
    return {row["sub_line_id"]: row for row in overview["sub_lines"]}


def _state(out: CanonicalAssyOutput, sub_line_id: str) -> dict:
    detail = out.experience.detail(sub_line_id)
    return {
        "simulation_time_s": detail["simulation_time_s"],
        "positions": detail["positions"],
        "genealogy": detail["genealogy"],
        "production": detail["production"],
        "quality_records": detail["quality_records"],
    }


class _Counter:
    """Count runtime/session/federation/controller constructions."""

    def __init__(self) -> None:
        self.federations: list[str] = []
        self.sessions: list[str] = []
        self.legacy: list[str] = []

    def __enter__(self):
        import virtual_factory.assembly.demo_controller as demo_controller
        import virtual_factory.federation.assy_host as host
        import virtual_factory.runcontrol.session as session_module

        def fed_init(inner, config_path):  # noqa: ANN001
            self.federations.append(str(config_path))
            original_fed(inner, config_path)

        def sess_init(inner, *args, **kwargs):  # noqa: ANN001
            self.sessions.append("RuntimeSession")
            original_sess(inner, *args, **kwargs)

        def legacy_init(inner, *args, **kwargs):  # noqa: ANN001
            self.legacy.append("DemoController")
            raise AssertionError("legacy DemoController must not be instantiated")

        original_fed = host.TipaAssyFederation.__init__
        original_sess = session_module.RuntimeSession.__init__
        original_legacy = demo_controller.DemoController.__init__
        host.TipaAssyFederation.__init__ = fed_init
        session_module.RuntimeSession.__init__ = sess_init
        demo_controller.DemoController.__init__ = legacy_init
        self._restore = [
            (host.TipaAssyFederation, original_fed),
            (session_module.RuntimeSession, original_sess),
            (demo_controller.DemoController, original_legacy),
        ]
        return self

    def __exit__(self, *exc):  # noqa: ANN002
        for target, original in self._restore:
            target.__init__ = original
        return False


# ─────────────── A. same-session authority ───────────────
def evidence_a() -> dict:
    counter = _Counter()
    with counter:
        c = _client()
        c.post("/assy-demo/reset")
        for _ in range(3):
            c.post("/assy-demo/step")
        rich = c.get("/assy-demo/identity").json()["canonical"]
        shell = c.get("/vnext/workspaces/TIPA/view").json()
        jam = c.post("/assy-demo/jam", json={"sub_line_id": "ASSY-SL03"}).json()
        for _ in range(2):
            c.post("/assy-demo/step")
        recover = c.post("/assy-demo/recover", json={"sub_line_id": "ASSY-SL03"}).json()
        terminal = c.post("/assy-demo/run-to-terminal", json={"max_windows": 40}).json()
        oee = c.get("/assy-demo/oee").json()
        observations = c.get("/assy-demo/observations").json()
        messages = c.get("/assy-demo/mes-messages").json()
    run_ids = {
        "shell": shell["identity"]["run_id"],
        "rich": rich["run_id"],
        "jam": jam["canonical"]["run_id"],
        "recover": recover["canonical"]["run_id"],
        "run_to_terminal": terminal["canonical"]["run_id"],
        "oee": oee["canonical"]["run_id"],
        "observations": observations["canonical"]["run_id"],
        "mes_messages": messages["canonical"]["run_id"],
    }
    payload = {
        "run_ids": run_ids,
        "one_run_id_everywhere": len(set(run_ids.values())) == 1,
        "sub_line_ids": list(SUB_LINE_IDS),
        "sub_line_count": len(SUB_LINE_IDS),
        "federations_constructed": counter.federations,
        "sessions_constructed": counter.sessions,
        "legacy_controllers_constructed": counter.legacy,
        "exactly_one_federation": len(counter.federations) == 1,
        "exactly_one_session": len(counter.sessions) == 1,
        "no_legacy_controller": counter.legacy == [],
        "oee_summaries": oee["count"],
        "observation_count": observations["count"],
        "mes_message_count": messages["count"],
    }
    payload["PASS"] = (
        payload["one_run_id_everywhere"]
        and payload["exactly_one_federation"]
        and payload["exactly_one_session"]
        and payload["no_legacy_controller"]
        and payload["sub_line_count"] == 6
    )
    _write("01-same-session-authority.json", payload)
    return payload


# ─────────────── B. jam / recovery ───────────────
def evidence_b() -> dict:
    c = _client()
    c.post("/assy-demo/reset")
    for _ in range(3):
        c.post("/assy-demo/step")
    before = _frame_a(c)
    jam = c.post("/assy-demo/jam", json={"sub_line_id": "ASSY-SL03"}).json()
    for _ in range(3):
        c.post("/assy-demo/step")
    after = _frame_a(c)
    sl03_detail = c.get("/assy-demo/sub-line/ASSY-SL03").json()
    mes = c.get("/assy-demo/mes-messages").json()
    issues = [
        m["payload"] for m in mes["mes_messages"] if m["message_type"] == "mes.issue"
    ]
    execution = [
        m["payload"]
        for m in mes["mes_messages"]
        if m["message_type"] == "mes.execution_event"
    ]
    downtime = [e for e in execution if e.get("event_type") == "DOWNTIME_START"]
    recover = c.post("/assy-demo/recover", json={"sub_line_id": "ASSY-SL03"}).json()
    c.post("/assy-demo/step")
    resumed = _frame_a(c)

    exp = _experience_output()
    exp.experience.jam("ASSY-SL03")
    exp.poll()
    bridge = exp.experience.bridge()
    projection_owns_fault = bool(exp._mes._fault) or bool(exp._mes._jam_pending)

    payload = {
        "target_sub_line": "ASSY-SL03",
        "before_fault": {
            sid: {
                "simulation_time_s": before[sid]["simulation_time_s"],
                "motors_created": before[sid]["motors_created"],
            }
            for sid in sorted(before)
        },
        "jam": jam["fault"],
        "jammed_sub_line_ids": jam["jammed_sub_line_ids"],
        "after_fault": {
            sid: {
                "simulation_time_s": after[sid]["simulation_time_s"],
                "motors_created": after[sid]["motors_created"],
            }
            for sid in sorted(after)
        },
        "target_frozen": (
            after["ASSY-SL03"]["simulation_time_s"]
            == before["ASSY-SL03"]["simulation_time_s"]
            and after["ASSY-SL03"]["motors_created"]
            == before["ASSY-SL03"]["motors_created"]
        ),
        "five_lines_continue": all(
            after[sid]["simulation_time_s"] > before[sid]["simulation_time_s"]
            for sid in SUB_LINE_IDS
            if sid != "ASSY-SL03"
        ),
        "frame_b_matches_fault_truth": (
            sl03_detail["simulation_time_s"]
            == after["ASSY-SL03"]["simulation_time_s"]
        ),
        "issue_facts": [
            {
                "event_type": i.get("event_type"),
                "station_id": i.get("station_id"),
                "run_id": i.get("run_id"),
                "simulation_time_s": i.get("simulation_time_s"),
                "reason_code": i.get("reason_code"),
            }
            for i in issues
        ],
        "downtime_facts": [
            {
                "event_type": d.get("event_type"),
                "downtime_s": d.get("downtime_s"),
                "run_id": d.get("run_id"),
            }
            for d in downtime
        ],
        "canonical_fault_owner": {
            "jammed_sub_line_ids": list(bridge.jammed_sub_line_ids),
            "fault": bridge.fault_for("ASSY-SL03"),
        },
        "projection_owns_fault_state": projection_owns_fault,
        "recover": recover["fault"],
        "jammed_after_recover": recover["jammed_sub_line_ids"],
        "resumed_times": {
            sid: resumed[sid]["simulation_time_s"] for sid in sorted(resumed)
        },
        "resumed_line_caught_up": (
            resumed["ASSY-SL03"]["simulation_time_s"]
            == resumed["ASSY-SL01"]["simulation_time_s"]
        ),
    }
    payload["PASS"] = (
        payload["target_frozen"]
        and payload["five_lines_continue"]
        and payload["frame_b_matches_fault_truth"]
        and bool(payload["issue_facts"])
        and bool(payload["downtime_facts"])
        and payload["downtime_facts"][0]["downtime_s"] == 120.0
        and payload["projection_owns_fault_state"] is False
        and payload["jammed_after_recover"] == []
        and payload["resumed_line_caught_up"]
    )
    _write("02-jam-recovery.json", payload)
    return payload


def _experience_output() -> CanonicalAssyOutput:
    out = _output()
    out.experience.reset()
    for _ in range(3):
        out.experience.step()
    return out


# ─────────────── C. run-to-terminal ───────────────
def evidence_c() -> dict:
    automated = _output()
    automated.experience.reset()
    result = automated.experience.run_to_terminal(40)
    windows = int(result["windows"])

    manual = _output()
    manual.experience.reset()
    for _ in range(windows):
        manual.experience.step()

    per_line = {
        sid: {
            "automated_equals_manual": _state(automated, sid) == _state(manual, sid),
            "simulation_time_s": _state(automated, sid)["simulation_time_s"],
        }
        for sid in SUB_LINE_IDS
    }
    bounded = _client()
    bounded.post("/assy-demo/reset")
    over = bounded.post("/assy-demo/run-to-terminal", json={"max_windows": 500})
    under = bounded.post("/assy-demo/run-to-terminal", json={"max_windows": 0})
    payload = {
        "status": result["status"],
        "windows": windows,
        "max_windows": result["max_windows"],
        "terminal_reached": result["terminal_reached"],
        "canonical_run_id": result["canonical"]["run_id"],
        "per_line_parity": per_line,
        "all_lines_parity": all(
            row["automated_equals_manual"] for row in per_line.values()
        ),
        "manual_reached_terminal": manual.experience.terminal_reached(),
        "bounded_guard": {
            "max_windows_500": over.status_code,
            "max_windows_0": under.status_code,
        },
    }
    payload["PASS"] = (
        payload["windows"] > 0
        and payload["terminal_reached"] is True
        and payload["all_lines_parity"]
        and payload["manual_reached_terminal"] is True
        and payload["bounded_guard"]["max_windows_500"] in (404, 409)
        and payload["bounded_guard"]["max_windows_0"] in (404, 409)
    )
    _write("03-run-to-terminal.json", payload)
    return payload


# ─────────────── D. OEE / final summary ───────────────
def evidence_d() -> dict:
    c = _client()
    c.post("/assy-demo/reset")
    for _ in range(3):
        c.post("/assy-demo/step")
    c.post("/assy-demo/jam", json={"sub_line_id": "ASSY-SL03"})
    for _ in range(2):
        c.post("/assy-demo/step")
    c.post("/assy-demo/recover", json={"sub_line_id": "ASSY-SL03"})
    c.post("/assy-demo/run-to-terminal", json={"max_windows": 40})
    identity = c.get("/assy-demo/identity").json()["canonical"]
    before = c.post("/assy-demo/snapshot").json()
    first = c.get("/assy-demo/oee")
    body = first.json()
    second = c.get("/assy-demo/oee").json()
    after = c.post("/assy-demo/snapshot").json()
    summaries = {s["payload"]["subline_id"]: s["payload"] for s in body["oee_summaries"]}
    payload = {
        "status_code": first.status_code,
        "authority": body["authority"],
        "legacy_runtime_authority": body["legacy_runtime_authority"],
        "canonical_run_id": body["canonical"]["run_id"],
        "identity_run_id": identity["run_id"],
        "count": body["count"],
        "sub_lines_covered": sorted(summaries),
        "all_payload_run_ids_canonical": all(
            s["payload"]["run_id"] == identity["run_id"] for s in body["oee_summaries"]
        ),
        "downtime_by_line": {
            sid: summaries[sid]["downtime_s"] for sid in sorted(summaries)
        },
        "oee_by_line": {sid: summaries[sid]["oee"] for sid in sorted(summaries)},
        "faulted_line_downtime_120": summaries.get("ASSY-SL03", {}).get("downtime_s")
        == 120.0,
        "other_lines_no_downtime": all(
            summaries[sid]["downtime_s"] == 0.0
            for sid in summaries
            if sid != "ASSY-SL03"
        ),
        "idempotent_keys": [s["message_key"] for s in body["oee_summaries"]]
        == [s["message_key"] for s in second["oee_summaries"]],
        "idempotent_count": second["count"] == body["count"],
        "simulation_time_unchanged": (
            before["simulation_time_s"] == after["simulation_time_s"]
        ),
        "production_unchanged": before["production"] == after["production"],
        "positions_unchanged": before["positions"] == after["positions"],
    }
    payload["PASS"] = (
        payload["status_code"] == 200
        and payload["legacy_runtime_authority"] is False
        and payload["canonical_run_id"] == identity["run_id"]
        and payload["count"] == 6
        and len(payload["sub_lines_covered"]) == 6
        and payload["all_payload_run_ids_canonical"]
        and payload["faulted_line_downtime_120"]
        and payload["other_lines_no_downtime"]
        and payload["idempotent_keys"]
        and payload["idempotent_count"]
        and payload["simulation_time_unchanged"]
        and payload["production_unchanged"]
        and payload["positions_unchanged"]
    )
    _write("04-oee-summary.json", payload)
    return payload


# ─────────────── E. scenario / new-run ───────────────
def evidence_e() -> dict:
    c = _client()
    c.post("/assy-demo/reset")
    for _ in range(2):
        c.post("/assy-demo/step")
    previous = c.get("/assy-demo/identity").json()["canonical"]
    previous_snapshot = c.post("/assy-demo/snapshot").json()
    resp = c.post("/assy-demo/scenario", json={"scenario_id": "FAILED_FINAL"})
    body = resp.json()
    fresh = body["canonical"]
    shell = c.get("/vnext/workspaces/TIPA/view").json()
    output = c.get("/assy-demo/observations").json()["canonical"]
    unknown = c.post("/assy-demo/scenario", json={"scenario_id": "NOT_A_SCENARIO"})

    exp = _output()
    exp.experience.reset()
    exp.experience.select_scenario("FAILED_FINAL")
    exp.experience.run_to_terminal(60)
    rejects = [
        m["payload"]
        for m in exp.mes_messages()["mes_messages"]
        if m["payload"].get("disposition") == "reject"
    ]
    target = exp.experience.detail("ASSY-SL03")["production"]
    payload = {
        "status_code": resp.status_code,
        "status": body["status"],
        "legacy_runtime_authority": body["legacy_runtime_authority"],
        "previous_run_id": body["previous"]["run_id"],
        "previous_scenario_id": body["previous"]["scenario_id"],
        "fresh_run_id": fresh["run_id"],
        "fresh_scenario_id": fresh["scenario_id"],
        "fresh_profile_id": fresh["profile_id"],
        "fresh_run_id_differs": fresh["run_id"] != previous["run_id"],
        "identity_consistent": (
            shell["identity"]["run_id"] == fresh["run_id"] == output["run_id"]
            and shell["identity"]["scenario_id"]
            == fresh["scenario_id"]
            == output["scenario_id"]
        ),
        "shell_step_count_after_fresh_run": shell["session"]["step_count"],
        "previous_run_history": shell.get("run_history"),
        "previous_run_snapshot_time_s": previous_snapshot["simulation_time_s"],
        "unknown_scenario": {
            "status_code": unknown.status_code,
            "identity_unchanged": c.get("/assy-demo/identity").json()["canonical"][
                "run_id"
            ]
            == fresh["run_id"],
        },
        "scenario_effect": {
            "rejects": len(rejects),
            "reason_codes": sorted({r.get("reason_code") for r in rejects}),
            "target_motors_released": target["motors_released"],
            "target_quality_holds": target["active_quality_holds"],
        },
    }
    payload["PASS"] = (
        payload["status_code"] == 200
        and payload["status"] == "fresh_run"
        and payload["legacy_runtime_authority"] is False
        and payload["fresh_run_id_differs"]
        and payload["fresh_scenario_id"] == "FAILED_FINAL"
        and payload["fresh_profile_id"] == "tipa-assy-failed_final"
        and payload["identity_consistent"]
        and payload["shell_step_count_after_fresh_run"] == 0
        and bool(payload["previous_run_history"])
        and payload["previous_run_history"][-1]["run_id"] == previous["run_id"]
        and payload["unknown_scenario"]["status_code"] in (400, 404, 409)
        and payload["unknown_scenario"]["identity_unchanged"]
        and payload["scenario_effect"]["rejects"] > 0
        and payload["scenario_effect"]["reason_codes"] == ["failed_final"]
    )
    _write("05-scenario-fresh-run.json", payload)
    return payload


# ─────────────── F. existing parity oracle ───────────────
def evidence_f() -> dict:
    exp = _output()
    exp.experience.reset()
    exp.experience.run_to_terminal(40)
    happy = exp.mes_messages()
    families: dict[str, int] = {}
    for msg in happy["mes_messages"]:
        families[msg["message_type"]] = families.get(msg["message_type"], 0) + 1
    detail = {sid: exp.experience.detail(sid) for sid in SUB_LINE_IDS}
    genealogy = sum(len(d["genealogy"]) for d in detail.values())
    releases = sum(1 for m in happy["mes_messages"] if m["message_type"] == "mes.release")
    quality = sum(
        1 for m in happy["mes_messages"] if m["message_type"] == "mes.quality_result"
    )
    positions_ok = all(
        [p["position_id"] for p in d["positions"]]
        == [
            "PRE-ASSY",
            "AP01",
            "AP02",
            "AP03",
            "AP04",
            "AP05",
            "AP06",
            "AP07",
            "AP08",
            "AP09",
            "AP10",
            "AP11",
        ]
        for d in detail.values()
    )
    feeds = {
        sid: {
            "sso2_buffer": detail[sid]["production"]["sso2_buffer"],
            "rso2_buffer": detail[sid]["production"]["rso2_buffer"],
        }
        for sid in SUB_LINE_IDS
    }

    # scenario oracles: AP06 retest / AP08 reinspect / failed-final
    scenario_facts: dict[str, dict] = {}
    for scenario in (
        "AP06_FAIL_RETEST_PASS",
        "AP08_NG_REINSPECT_PASS",
        "FAILED_FINAL",
    ):
        sc = _output()
        sc.experience.reset()
        sc.experience.select_scenario(scenario)
        sc.experience.run_to_terminal(60)
        records = []
        for sid in SUB_LINE_IDS:
            records.extend(sc.experience.detail(sid)["quality_records"])
        rejects = [
            m["payload"]
            for m in sc.mes_messages()["mes_messages"]
            if m["payload"].get("disposition") == "reject"
        ]
        scenario_facts[scenario] = {
            "quality_records": len(records),
            "attempts_gt_1": sum(1 for r in records if (r.get("attempt_number") or 1) > 1),
            "dispositions": sorted({str(r.get("disposition")) for r in records}),
            "released": sum(
                int(sc.experience.detail(sid)["production"]["motors_released"])
                for sid in SUB_LINE_IDS
            ),
            "reject_facts": len(rejects),
            "reject_reason_codes": sorted({str(r.get("reason_code")) for r in rejects}),
        }

    # deterministic replay (same scenario, same windows, fresh run ids)
    first = _output()
    first.experience.reset()
    for _ in range(8):
        first.experience.step()
    reference = {sid: _state(first, sid) for sid in SUB_LINE_IDS}
    first.experience.session.replay()
    for _ in range(8):
        first.experience.step()
    replayed = {sid: _state(first, sid) for sid in SUB_LINE_IDS}
    replay_identical = reference == replayed

    # six-line independence under a hold
    held = _output()
    held.experience.reset()
    for _ in range(3):
        held.experience.step()
    held.experience.bridge().hold_sub_line("ASSY-SL03")
    for _ in range(3):
        held.experience.step()
    rows = {
        row["sub_line_id"]: row
        for row in held.experience.overview()["sub_lines"]
    }
    hold_independent = (
        rows["ASSY-SL03"]["simulation_time_s"]
        < rows["ASSY-SL01"]["simulation_time_s"]
        and all(
            rows[sid]["simulation_time_s"] == rows["ASSY-SL01"]["simulation_time_s"]
            for sid in SUB_LINE_IDS
            if sid != "ASSY-SL03"
        )
    )
    held.experience.bridge().release_sub_line("ASSY-SL03")

    # R3 output identity / epochs on the canonical path
    obs = exp.observations()
    mes = exp.mes_messages()
    oee = exp.oee_summary()
    output_identity = (
        obs["canonical"]["run_id"]
        == mes["canonical"]["run_id"]
        == oee["canonical"]["run_id"]
        == exp.experience.session_identity()["run_id"]
    )
    epochs = mes["canonical"]["output_namespace"]

    payload = {
        "happy_path": {
            "families": families,
            "genealogy_records": genealogy,
            "releases": releases,
            "quality_results": quality,
            "positions_match_canonical_12": positions_ok,
            "feeds": feeds,
        },
        "scenario_oracles": scenario_facts,
        "replay_deterministic": replay_identical,
        "six_line_independence": hold_independent,
        "r3_output_identity": {
            "same_run_id_across_surfaces": output_identity,
            "projection_epoch": epochs["projection_epoch"],
            "session_reset_generation": epochs["session_reset_generation"],
            "epoch_source": epochs["epoch_source"],
        },
    }
    payload["PASS"] = (
        payload["happy_path"]["genealogy_records"] > 0
        and payload["happy_path"]["releases"] > 0
        and payload["happy_path"]["quality_results"] > 0
        and payload["happy_path"]["positions_match_canonical_12"]
        and payload["scenario_oracles"]["AP06_FAIL_RETEST_PASS"]["attempts_gt_1"] > 0
        and payload["scenario_oracles"]["AP08_NG_REINSPECT_PASS"]["attempts_gt_1"] > 0
        and payload["scenario_oracles"]["FAILED_FINAL"]["reject_facts"] > 0
        and payload["scenario_oracles"]["FAILED_FINAL"]["reject_reason_codes"]
        == ["failed_final"]
        and payload["replay_deterministic"]
        and payload["six_line_independence"]
        and output_identity
        and epochs["epoch_source"] == "canonical_session_reset_generation"
    )
    _write("06-parity-oracle.json", payload)
    return payload


def main() -> int:
    results = {
        "A_same_session_authority": evidence_a(),
        "B_jam_recovery": evidence_b(),
        "C_run_to_terminal": evidence_c(),
        "D_oee_summary": evidence_d(),
        "E_scenario_fresh_run": evidence_e(),
        "F_parity_oracle": evidence_f(),
    }
    print()
    for name, payload in results.items():
        print(f"{name}: PASS={payload['PASS']}")
    if not all(payload["PASS"] for payload in results.values()):
        print("EVIDENCE FAILED")
        return 1
    print("R4 evidence complete: all sections PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
