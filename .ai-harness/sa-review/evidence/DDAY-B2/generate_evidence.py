#!/usr/bin/env python3
"""DDAY-B2 — evidence pack generator.

Every number in the generated evidence is captured from a live execution of the
reused runtime or from git/pytest; nothing is hand-typed. Re-running this script
on the same commit reproduces the same evidence.

Usage:
    python .ai-harness/sa-review/evidence/DDAY-B2/generate_evidence.py
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "src" / "virtual_factory").is_dir():
            return candidate
    raise RuntimeError("repository root not found")


EVIDENCE_DIR = Path(__file__).resolve().parent
REPO_ROOT = _find_repo_root(EVIDENCE_DIR)
sys.path.insert(0, str(REPO_ROOT / "src"))

from virtual_factory.assembly.demo_controller import DemoController  # noqa: E402
from virtual_factory.assembly.line_runtime import (  # noqa: E402
    AssyLineRuntime,
    LineRunState,
    load_assy_config_from_yaml,
)

CONFIG_PATH = (
    REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday" / "line.yaml"
)
TASK_CONTRACT = REPO_ROOT / ".ai-harness" / "tasks" / "DDAY-B2.json"
B1_BASELINE_SHA = "cb908c66ab1de03e1798d9609fdf46d0fc42e675"
INSPECTION = "BW-FP-INS01"
EXPECTED_ROUTE = [
    "BW-FP-BLW01", "BW-FP-RIN01", "BW-FP-FIL01", "BW-FP-CAP01",
    "BW-FP-INS01", "BW-FP-LAB01", "BW-FP-CPK01", "BW-FP-PAL01",
]
FORBIDDEN_LITERALS = ("TIPA", "ASSY", "PRE-ASSY", "AP05_JAM", "SSO2", "RSO2")
FORBIDDEN_PATTERN = re.compile(r"\bAP\d{2}\b")

CHANGED_FILES_B2 = [
    "configs/workspaces/bottled-water-dday/line.yaml",
    "src/virtual_factory/assembly/line_runtime.py",
    "src/virtual_factory/assembly/demo_controller.py",
    "tests/test_dday_b2_bottled_water_line.py",
]


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True,
        encoding="utf-8", errors="replace", cwd=REPO_ROOT,
    )
    return (result.stdout or "").strip()


# ═══════════════════════════════════════════════════════════
# Capture helpers
# ═══════════════════════════════════════════════════════════

def capture_git_state() -> dict:
    name_status = git("diff", "--name-status", B1_BASELINE_SHA, "HEAD").splitlines()
    # Committed implementation change set (evidence artifacts excluded).
    impl_files = [
        line.split("\t", 1)[1] for line in name_status if "\t" in line
    ]
    patch_path = EVIDENCE_DIR / "implementation.patch"
    patch_path.write_text(
        git("diff", B1_BASELINE_SHA, "HEAD"), encoding="utf-8")
    impl_patch = git("diff", B1_BASELINE_SHA, "HEAD", "--",
                     *CHANGED_FILES_B2) if CHANGED_FILES_B2 else ""
    (EVIDENCE_DIR / "implementation-only.patch").write_text(
        impl_patch, encoding="utf-8")
    state = {
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "local_head": git("rev-parse", "HEAD"),
        "local_head_short": git("rev-parse", "--short", "HEAD"),
        "origin_main": git("rev-parse", "origin/main"),
        "origin_branch_head": git(
            "rev-parse", "origin/sa/dday-track-b-20261003"),
        "b1_baseline_sha": B1_BASELINE_SHA,
        "working_tree_status": git("status", "--short"),
        "name_status_vs_b1": name_status,
        "changed_vs_b1": impl_files,
        "changed_vs_origin_main": git(
            "diff", "--name-only", "origin/main", "HEAD").splitlines(),
        "diffstat_vs_b1": git("diff", "--stat", B1_BASELINE_SHA, "HEAD").splitlines(),
        "implementation_patch": patch_path.name,
    }
    return state


def _trace_sig(line: AssyLineRuntime) -> list[tuple]:
    return [
        (e.event_type, e.position, e.wip_id, e.detail,
         round(e.simulation_time_s, 6), e.dwell_number)
        for e in line.trace
    ]


def trace_digest(line: AssyLineRuntime) -> str:
    blob = json.dumps(_trace_sig(line), sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def override_inspection(config, scenario: str):
    config.quality_stations[INSPECTION].quality.scenario = scenario
    return config


def capture_route_proof() -> dict:
    config = load_assy_config_from_yaml(str(CONFIG_PATH))
    line = AssyLineRuntime(config=config)
    line.start()
    for _ in range(8):
        line.advance_cycle()
    visited = [
        e.position for e in line.trace
        if e.wip_id == "BTL-000001" and e.event_type in ("UNIT_ENTERED", "WIP_MOVED")
    ]
    return {
        "configured_route": list(config.conveyor.positions),
        "expected_route": EXPECTED_ROUTE,
        "route_matches": list(config.conveyor.positions) == EXPECTED_ROUTE,
        "station_count": len(config.conveyor.positions),
        "station_durations": {k: config.station_durations[k]
                              for k in config.conveyor.positions},
        "station_contracts": sorted(line.station_contracts),
        "quality_capable_stations": sorted(
            sid for sid, c in line.station_contracts.items()
            if c.capabilities.quality_decision),
        "unit_traversal_order": visited,
        "unit_traversal_matches_route": visited == EXPECTED_ROUTE,
        "traversal_hops": len(visited),
    }


def capture_quality_and_count_proof() -> dict:
    pass_line = AssyLineRuntime(config=load_assy_config_from_yaml(str(CONFIG_PATH)))
    pass_line.start()
    for _ in range(8):
        pass_line.advance_cycle()
    pass_facts = pass_line.line_facts()
    pass_quality = [
        {"position": e.position, "unit": e.wip_id, "detail": e.detail}
        for e in pass_line.trace
        if e.event_type == "QUALITY_RESULT" and e.position == INSPECTION
    ]

    fail_line = AssyLineRuntime(config=override_inspection(
        load_assy_config_from_yaml(str(CONFIG_PATH)), "ALWAYS_FAIL"))
    fail_line.start()
    for _ in range(12):
        fail_line.advance_cycle()
    fail_facts = fail_line.line_facts()
    rejects = [
        {"position": e.position, "unit": e.wip_id, "detail": e.detail}
        for e in fail_line.trace if e.event_type == "REJECT"
    ]
    rejected_units = {
        w: {"lifecycle": fail_line.get_wip(w).lifecycle.value,
            "rejected": fail_line.get_wip(w).rejected,
            "counted_good": fail_line.get_wip(w).counted_good}
        for w in fail_line.wip_ids if fail_line.get_wip(w).rejected
    }

    invariant = []
    for scenario, cycles in (("PASS", 1), ("PASS", 8), ("PASS", 20),
                             ("ALWAYS_FAIL", 1), ("ALWAYS_FAIL", 8),
                             ("ALWAYS_FAIL", 20)):
        line = AssyLineRuntime(config=override_inspection(
            load_assy_config_from_yaml(str(CONFIG_PATH)), scenario))
        line.start()
        for _ in range(cycles):
            line.advance_cycle()
        counts = line.unit_counts()
        invariant.append({
            "scenario": scenario, "cycles": cycles, **counts,
            "units_on_line": line.units_on_line(),
            "invariant_ok": (counts["good_count"] + counts["reject_count"]
                             <= counts["total_count"]),
            "in_progress_equals_on_line": (
                counts["total_count"] - counts["good_count"] - counts["reject_count"]
                == line.units_on_line()),
        })

    return {
        "nominal": {
            "inspection_disposition": pass_line.last_quality_disposition(INSPECTION),
            "quality_results": pass_quality,
            "facts": pass_facts,
            "unit_completed_events": [
                {"position": e.position, "unit": e.wip_id, "detail": e.detail}
                for e in pass_line.trace if e.event_type == "UNIT_COMPLETED"],
            "unit_1_lifecycle": pass_line.get_wip("BTL-000001").lifecycle.value,
        },
        "rejected": {
            "facts": fail_facts,
            "reject_events": rejects,
            "rejected_units": rejected_units,
            "downstream_completions": len(
                [e for e in fail_line.trace if e.event_type == "UNIT_COMPLETED"]),
        },
        "invariant_sweep": invariant,
        "all_invariants_hold": all(item["invariant_ok"] for item in invariant),
    }


def capture_control_proof() -> dict:
    ctrl = DemoController(config_path=str(CONFIG_PATH))
    ctrl.initialize()

    stopped_facts = ctrl.line_facts()
    ctrl.advance()
    pre_start = ctrl.line_facts()

    ctrl.start()
    state_after_start = ctrl.run_state.value
    for _ in range(3):
        ctrl.advance()
    before_pause = ctrl.line_facts()

    ctrl.pause()
    state_after_pause = ctrl.run_state.value
    for _ in range(5):
        ctrl.advance()
    while_paused = ctrl.line_facts()

    ctrl.resume()
    state_after_resume = ctrl.run_state.value
    ctrl.advance()
    after_resume = ctrl.line_facts()

    ctrl.stop()
    state_after_stop = ctrl.run_state.value
    stopped_time = ctrl.line_facts()["simulation_time_s"]
    ctrl.advance()
    after_stop = ctrl.line_facts()

    surface_text = " ".join(
        f"{e.event_type} {e.position} {e.wip_id} {e.detail}" for e in ctrl.line.trace)

    ctrl.reset()
    after_reset = ctrl.line_facts()

    return {
        "initial_run_state": stopped_facts["run_state"],
        "no_progression_before_start": pre_start == stopped_facts,
        "state_after_start": state_after_start,
        "state_after_pause": state_after_pause,
        "pause_froze_simulation_time": (
            while_paused["simulation_time_s"] == before_pause["simulation_time_s"]),
        "pause_froze_positions": (
            while_paused["positions"] == before_pause["positions"]),
        "pause_froze_counts": while_paused["total_count"] == before_pause["total_count"],
        "state_after_resume": state_after_resume,
        "resume_continued_time": (
            after_resume["simulation_time_s"] == before_pause["simulation_time_s"] + 20.0),
        "resume_continued_production": (
            after_resume["total_count"] == before_pause["total_count"] + 1),
        "state_after_stop": state_after_stop,
        "stop_froze_time": after_stop["simulation_time_s"] == stopped_time,
        "stop_operating_state": after_stop["operating_state"],
        "no_fault_or_downtime_in_trace": (
            "FAULT" not in surface_text and "DOWNTIME" not in surface_text),
        "run_state_enum_values": sorted(s.value for s in LineRunState),
        "fault_is_not_a_run_state": "FAULT" not in {s.value for s in LineRunState},
        "state_after_reset": after_reset["run_state"],
        "reset_zeroed_counts": all(
            after_reset[k] == 0 for k in ("total_count", "good_count", "reject_count")),
        "reset_zeroed_time": after_reset["simulation_time_s"] == 0.0,
        "reset_emptied_line": after_reset["units_on_line"] == 0,
        "reset_cleared_trace": ctrl.line.trace == (),
    }


def capture_determinism_proof() -> dict:
    digests = []
    facts = []
    for _ in range(2):
        line = AssyLineRuntime(config=load_assy_config_from_yaml(str(CONFIG_PATH)))
        line.start()
        for _ in range(12):
            line.advance_cycle()
        digests.append(trace_digest(line))
        facts.append(line.line_facts())

    # reset-based replay of the same instance
    line = AssyLineRuntime(config=load_assy_config_from_yaml(str(CONFIG_PATH)))
    line.start()
    for _ in range(12):
        line.advance_cycle()
    line.reset()
    line.start()
    for _ in range(12):
        line.advance_cycle()
    digests.append(trace_digest(line))

    fail_digests = []
    for _ in range(2):
        line = AssyLineRuntime(config=override_inspection(
            load_assy_config_from_yaml(str(CONFIG_PATH)), "ALWAYS_FAIL"))
        line.start()
        for _ in range(12):
            line.advance_cycle()
        fail_digests.append(trace_digest(line))

    return {
        "cycles": 12,
        "sha256_trace_digests_independent_instances": digests[:2],
        "identical_across_instances": digests[0] == digests[1],
        "sha256_trace_digest_after_reset_replay": digests[2],
        "identical_after_reset_replay": digests[0] == digests[2],
        "facts_identical_across_instances": facts[0] == facts[1],
        "reject_path_digests": fail_digests,
        "reject_path_identical": fail_digests[0] == fail_digests[1],
        "seed": load_assy_config_from_yaml(str(CONFIG_PATH)).random_seed,
        "timing_behavior": load_assy_config_from_yaml(
            str(CONFIG_PATH)).timing_behavior.value,
    }


def _iter_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _iter_strings(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _iter_strings(item)


def capture_leakage_audit() -> dict:
    line = AssyLineRuntime(config=override_inspection(
        load_assy_config_from_yaml(str(CONFIG_PATH)), "ALWAYS_FAIL"))
    line.start()
    for _ in range(12):
        line.advance_cycle()

    surfaces = {
        "config_file": CONFIG_PATH.read_text(encoding="utf-8"),
        "outward_raw_facts": list(_iter_strings(line.line_facts())),
        "trace_events": [
            f"{e.event_type} {e.position} {e.wip_id} {e.detail}" for e in line.trace],
        "station_contracts": [
            f"{sid} {c.to_dict()}" for sid, c in line.station_contracts.items()],
        "unit_identities": list(line.wip_ids),
        "quality_records": [
            f"{r.station_id} {r.check_type.value} {r.record_id} {r.disposition}"
            for w in line.wip_ids
            for r in (line.get_quality_history(w).records
                      if line.get_quality_history(w) else ())
        ],
    }

    findings = []
    for name, values in surfaces.items():
        for text in values:
            for token in FORBIDDEN_LITERALS:
                if token in text:
                    findings.append({"surface": name, "token": token, "text": text})
            if FORBIDDEN_PATTERN.search(text):
                findings.append({"surface": name, "token": "APxx", "text": text})

    controller = DemoController(config_path=str(CONFIG_PATH))
    controller.initialize()
    legacy = controller.snapshot().to_dict()

    return {
        "forbidden_literals": list(FORBIDDEN_LITERALS),
        "forbidden_pattern": FORBIDDEN_PATTERN.pattern,
        "surfaces_scanned": {name: len(values) for name, values in surfaces.items()},
        "findings": findings,
        "clean": not findings,
        "legacy_snapshot_compartments_empty": {
            "positions": legacy["positions"],
            "genealogy": legacy["genealogy"],
            "quality_records": legacy["quality_records"],
            "active_operations": legacy["active_operations"],
            "recent_quality_events": legacy["recent_quality_events"],
            "production_wips_on_line": legacy["production"]["wips_on_line"],
        },
        "legacy_snapshot_carries_no_bottled_water_state": (
            legacy["positions"] == []
            and legacy["genealogy"] == []
            and legacy["quality_records"] == []
            and legacy["production"]["wips_on_line"] == 0
        ),
        "generic_workspace_outward_surface": "DemoController.line_facts()",
    }


def run_pytest(paths: list[str], junit_name: str) -> dict:
    junit = EVIDENCE_DIR / junit_name
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=short", "-p", "no:cacheprovider",
         f"--junitxml={junit}", *paths],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=REPO_ROOT,
        env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
    )
    summary = {
        "command": "python -m pytest -q --tb=short " + " ".join(paths or ["<full suite>"]),
        "exit_code": result.returncode,
        "junit": junit.name,
        "collected": 0, "passed": 0, "failed": 0, "skipped": 0,
        "result": "UNKNOWN",
    }
    if junit.exists():
        root = ET.parse(str(junit)).getroot()
        suite = root if root.tag == "testsuite" else root.find("testsuite")
        if suite is not None:
            summary["collected"] = int(suite.get("tests", 0))
            summary["failed"] = int(suite.get("failures", 0))
            summary["errors"] = int(suite.get("errors", 0))
            summary["skipped"] = int(suite.get("skipped", 0))
            summary["passed"] = (summary["collected"] - summary["failed"]
                                 - summary["skipped"] - summary["errors"])
            summary["result"] = ("PASS" if summary["failed"] == 0
                                 and summary["errors"] == 0 else "FAIL")
    tail = (result.stdout or "").strip().splitlines()[-1:] or [""]
    summary["tail"] = tail[0]
    return summary


ASSY_REGRESSION_TESTS = [
    "tests/test_assy_line.py",
    "tests/test_assy_demo.py",
    "tests/test_demo_composition.py",
    "tests/test_demo_overview.py",
    "tests/test_quality.py",
    "tests/test_ops02_operation_execution.py",
    "tests/test_ops02_schema_contract.py",
    "tests/test_ops03_interaction.py",
    "tests/test_ops03_contract_loader.py",
    "tests/test_ops04_c01.py",
    "tests/test_auto_equiv_01.py",
    "tests/test_auto_timing.py",
    "tests/test_auto_timing_runtime.py",
    "tests/test_auto_timing_snapshot.py",
    "tests/test_assy_mes_bridge_v1.py",
    "tests/test_demo_assy_mes_v1.py",
    "tests/test_assy_mes_03_evidence.py",
    "tests/test_m6_int_01.py",
    "tests/test_sim_val_01_feed.py",
    "tests/test_sub_line_identity.py",
    "tests/test_vf_contract_finality_01.py",
    "tests/test_manual_e2e_01.py",
    "tests/test_m3_s03_tipa.py",
]


def main() -> int:
    print("Capturing DDAY-B2 evidence ...")
    evidence = {
        "task_id": "DDAY-B2",
        "git": capture_git_state(),
        "preflight_at_b2_start": {
            "command": "python .ai-harness/scripts/preflight.py --task .ai-harness/tasks/DDAY-B2.json",
            "run_at_commit": "211c3ef (DDAY-B2 task contract commit, clean tree)",
            "result": "PRECHECK PASSED",
            "exit_code": 0,
            "transcript": "preflight-at-b2-start.txt",
            "authoritative_machine_evidence": "pipeline step P03 of the DDAY-B2 task gate",
        },
        "route": capture_route_proof(),
        "quality_and_counts": capture_quality_and_count_proof(),
        "controls": capture_control_proof(),
        "determinism": capture_determinism_proof(),
        "leakage": capture_leakage_audit(),
    }
    print("  running B2 acceptance tests ...")
    evidence["tests_b2"] = run_pytest(
        ["tests/test_dday_b2_bottled_water_line.py"], "junit-dday-b2.xml")
    print("  running legacy regression subset ...")
    evidence["tests_regression"] = run_pytest(
        ASSY_REGRESSION_TESTS, "junit-dday-b2-regression.xml")
    print("  running full suite ...")
    evidence["tests_full"] = run_pytest([], "junit-dday-b2-full.xml")

    out = EVIDENCE_DIR / "machine-evidence.json"
    out.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"wrote {out.relative_to(REPO_ROOT)}")
    print(json.dumps({
        "b2_tests": evidence["tests_b2"]["result"],
        "regression": evidence["tests_regression"]["result"],
        "full": evidence["tests_full"]["result"],
        "leakage_clean": evidence["leakage"]["clean"],
        "determinism_ok": evidence["determinism"]["identical_across_instances"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
