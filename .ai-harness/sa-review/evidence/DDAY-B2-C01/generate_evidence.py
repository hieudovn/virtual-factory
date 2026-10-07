#!/usr/bin/env python3
"""DDAY-B2-C01 — evidence generator.

Every captured value comes from a live run, git or the harness; nothing is
hand-typed. Re-running on the same commit reproduces the same evidence.

Usage:
    python .ai-harness/sa-review/evidence/DDAY-B2-C01/generate_evidence.py
"""

from __future__ import annotations

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
SCRIPTS = REPO_ROOT / ".ai-harness" / "scripts"
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(SCRIPTS))

from virtual_factory.assembly.line_runtime import (  # noqa: E402
    AssyLineRuntime,
    WipLifecycle,
    load_assy_config_from_yaml,
)
from virtual_factory.assembly.station_contracts import CompletionMode  # noqa: E402

CONFIG_PATH = REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday" / "line.yaml"
LEGACY_CONFIG_PATH = REPO_ROOT / "configs" / "plants" / "tipa_assy_demo.yaml"
C01_BASELINE_SHA = "0a1d18e42b5a28009ae05a6e916f9e942a857b38"
PR_NUMBER = "101"
INSPECTION = "BW-FP-INS01"

FORBIDDEN = (
    re.compile(r"assy", re.IGNORECASE),
    re.compile(r"tipa", re.IGNORECASE),
    re.compile(r"sso2", re.IGNORECASE),
    re.compile(r"rso2", re.IGNORECASE),
    re.compile(r"ap05_jam", re.IGNORECASE),
    re.compile(r"\bap\d{2}\b", re.IGNORECASE),
)


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True,
        encoding="utf-8", errors="replace", cwd=REPO_ROOT,
    )
    return (result.stdout or "").strip()


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from strings(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from strings(item)


def leaks(values) -> list[str]:
    hits = []
    for text in values:
        for pattern in FORBIDDEN:
            match = pattern.search(text)
            if match:
                hits.append(f"{match.group(0)!r} in {text!r}")
    return hits


def status_at(line: AssyLineRuntime, position: str) -> str:
    for entry in line.line_facts()["positions"]:
        if entry["position_id"] == position:
            return entry["manufacturing_status"]
    return ""


# ═══════════════════════════════════════════════════════════
# Captures
# ═══════════════════════════════════════════════════════════

def capture_git_state() -> dict:
    name_status_c01 = git("diff", "--name-status", C01_BASELINE_SHA, "HEAD").splitlines()
    patch = EVIDENCE_DIR / "implementation.patch"
    patch.write_text(
        git("diff", C01_BASELINE_SHA, "HEAD", "--",
            "src/", "tests/", ".ai-harness/scripts/", ".ai-harness/tests/"),
        encoding="utf-8")
    return {
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "local_head": git("rev-parse", "HEAD"),
        "origin_main": git("rev-parse", "origin/main"),
        "c01_baseline_sha": C01_BASELINE_SHA,
        "working_tree_status": git("status", "--short"),
        "name_status_vs_c01_baseline": name_status_c01,
        "changed_vs_c01_baseline": [
            line.split("\t", 1)[1] for line in name_status_c01 if "\t" in line],
        "changed_vs_origin_main": git(
            "diff", "--name-only", "origin/main", "HEAD").splitlines(),
        "diffstat_vs_c01_baseline": git(
            "diff", "--stat", C01_BASELINE_SHA, "HEAD").splitlines(),
        "implementation_patch": patch.name,
    }


def capture_semantic_isolation() -> dict:
    route = list(load_assy_config_from_yaml(str(CONFIG_PATH)).conveyor.positions)

    def fresh(scenario=None):
        cfg = load_assy_config_from_yaml(str(CONFIG_PATH))
        if scenario:
            cfg.quality_stations[INSPECTION].quality.scenario = scenario
        return AssyLineRuntime(config=cfg)

    entry = fresh()
    entry.start()
    unit = entry.produce_unit()
    entry.introduce_unit(unit, "CAR-0001")

    progress = fresh()
    progress.global_run_mode = CompletionMode.MANUAL
    progress.start()
    progress.advance_cycle()

    done = fresh()
    done.start()
    done.advance_cycle()
    station_status = status_at(done, route[1])
    for _ in range(7):
        done.advance_cycle()

    rejected = fresh("ALWAYS_FAIL")
    rejected.start()
    for _ in range(12):
        rejected.advance_cycle()

    states = {
        "entry": {
            "manufacturing_status": status_at(entry, route[0]),
            "lifecycle": entry.get_wip(unit).lifecycle.value,
        },
        "in_progress": {
            "manufacturing_status": status_at(progress, route[0]),
            "units_on_line": progress.units_on_line(),
        },
        "station_completion": {"manufacturing_status": station_status},
        "route_completion": {
            "lifecycle": done.get_wip("BTL-000001").lifecycle.value,
            "good_count": done.good_count,
        },
        "reject": {
            "lifecycle": rejected.get_wip("BTL-000001").lifecycle.value,
            "reject_count": rejected.reject_count,
            "good_count": rejected.good_count,
        },
    }

    sweep = {}
    for label, line in (("entry", entry), ("in_progress", progress),
                        ("station_completion", done), ("reject", rejected)):
        surface = list(strings(line.line_facts()))
        surface += [f"{e.event_type} {e.position} {e.wip_id} {e.detail}"
                    for e in line.trace]
        surface += [f"{sid} {c.to_dict()}" for sid, c in line.station_contracts.items()]
        surface += list(line.wip_ids)
        surface += [status_at(line, p) for p in route]
        sweep[label] = {"strings_scanned": len(surface), "findings": leaks(surface)}

    surface = list(strings(entry.line_facts())) + [status_at(entry, route[0])]
    legend = [f"{sid} {c.to_dict()}" for sid, c in entry.station_contracts.items()]
    legend += [f"{e.event_type} {e.position} {e.wip_id} {e.detail}" for e in entry.trace]
    legend += list(entry.wip_ids)

    legacy = AssyLineRuntime(config=load_assy_config_from_yaml(str(LEGACY_CONFIG_PATH)))
    legacy.start()
    legacy_wip = legacy.produce_sso2_wip()
    legacy.introduce_to_assy(legacy_wip, "PAL-001")

    return {
        "route": route,
        "states": states,
        "leak_sweep": sweep,
        "all_sweeps_clean": all(v["findings"] == [] for v in sweep.values()),
        "also_scanned": {
            "entry_facts": len(surface),
            "contracts_and_trace_and_units": len(legend),
            "findings": leaks(surface + legend),
        },
        "legacy_profile": {
            "is_generic": load_assy_config_from_yaml(
                str(LEGACY_CONFIG_PATH)).is_generic_profile,
            "introduce_to_assy_lifecycle": legacy.get_wip(legacy_wip).lifecycle.value,
            "IN_ASSY_value": WipLifecycle.IN_ASSY.value,
            "IN_LINE_value": WipLifecycle.IN_LINE.value,
            "distinct_values": WipLifecycle.IN_LINE is not WipLifecycle.IN_ASSY,
        },
    }


def capture_harness_repair() -> dict:
    import tempfile
    from run_task_gate import _write_gate_report, _normalize_pr_state
    from validate_report_consistency import validate

    sha = git("rev-parse", "HEAD")

    def evidence_for(pr_state: str) -> dict:
        return {
            "derived_status": "IMPLEMENTED — PR OPEN — READY FOR SA REVIEW",
            "ci": {"status": "completed", "conclusion": "success"},
            "acceptance": [{"id": "A01", "result": "PASS"}],
            "unknown_evidence": [], "tool_failures": [], "contradictions": [],
            "blocking_issues": [],
            "implementation": {"commit_sha": sha},
            "pipeline_steps": [], "requested_gate_satisfied": True,
            "pull_request": {"number": 101, "state": pr_state, "draft": False,
                             "base_branch": "main", "head_sha": sha,
                             "merged": False},
        }

    with tempfile.TemporaryDirectory(prefix="c01-evidence-") as tmp:
        generated = Path(tmp) / "gate-report.provisional.md"
        _write_gate_report(
            generated, "Gate Report (Provisional)", "DDAY-B2-C01",
            "IMPLEMENTED — PR OPEN — READY FOR SA REVIEW",
            "ready_for_sa_review", True, 0, [], sha)
        generated_report = generated.read_text()
        ok_generated, issues_generated = validate(evidence_for("OPEN"), generated_report)

    # A report without the head SHA still fails closed (validation untouched).
    ok_shapless, issues_shapless = validate(
        evidence_for("OPEN"), "# Gate Report (Provisional)\n\n**Status**: READY\n")

    # Representation-only proof on a *complete* evidence record: a closed PR
    # still fails closed after normalization, while the same record with an open
    # PR derives READY.
    from derive_status import derive_status

    def full_evidence(pr_state: str) -> dict:
        return {
            "preflight": {"baseline_match": True,
                          "expected_base_sha": "a" * 40,
                          "remote_main_head": "a" * 40},
            "tool_failures": [],
            "implementation": {"commit_exists_remotely": True,
                               "remote_branch_head": "b" * 40},
            "pull_request": {"number": 101, "state": pr_state, "draft": False,
                             "base_branch": "main", "head_sha": "b" * 40,
                             "merged": False},
            "ci": {"run_id": 1, "head_sha": "b" * 40, "conclusion": "success"},
            "tests": {"failed": 0},
            "acceptance": [],
            "unknown_evidence": [],
            "contradictions": [],
            "blocking_issues": [],
            "forbidden_actions": {"performed": False},
        }

    closed = _normalize_pr_state(full_evidence("closed"))
    opened = _normalize_pr_state(full_evidence("open"))
    twice = _normalize_pr_state(full_evidence("OPEN"))

    return {
        "implementation_sha_at_capture": sha,
        "p21_generated_report_contains_sha": sha in generated_report,
        "p21_generated_report_sha12": sha[:12] in generated_report,
        "validate_report_consistency_on_generated_report": {
            "passed": ok_generated, "issues": issues_generated},
        "report_without_sha_fails_closed": {
            "passed": ok_shapless, "issues": issues_shapless},
        "pr_state_normalization": {
            "raw_api_value": "open",
            "normalized_open": _normalize_pr_state(
                full_evidence("open"))["pull_request"]["state"],
            "normalized_closed": closed["pull_request"]["state"],
            "idempotent_for_uppercase": (
                twice["pull_request"]["state"] == "OPEN"),
            "derive_status_for_closed_pr": derive_status(closed),
            "derive_status_for_open_pr": derive_status(opened),
        },
    }


def run_pytest(paths: list[str], junit_name: str) -> dict:
    junit = EVIDENCE_DIR / junit_name
    env = {**__import__("os").environ}
    env.pop("PYTHONIOENCODING", None)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=short", "-p", "no:cacheprovider",
         f"--junitxml={junit}", *paths],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=REPO_ROOT, env=env,
    )
    summary = {
        "command": "python -m pytest -q " + " ".join(paths or ["<full suite>"]),
        "exit_code": result.returncode, "junit": junit.name,
        "collected": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0,
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
    return summary


LEGACY_REGRESSION_TESTS = [
    "tests/test_assy_line.py", "tests/test_assy_demo.py",
    "tests/test_demo_composition.py", "tests/test_demo_overview.py",
    "tests/test_quality.py", "tests/test_ops02_operation_execution.py",
    "tests/test_ops02_schema_contract.py", "tests/test_ops03_interaction.py",
    "tests/test_ops03_contract_loader.py", "tests/test_ops04_c01.py",
    "tests/test_auto_equiv_01.py", "tests/test_auto_timing.py",
    "tests/test_auto_timing_runtime.py", "tests/test_auto_timing_snapshot.py",
    "tests/test_assy_mes_bridge_v1.py", "tests/test_demo_assy_mes_v1.py",
    "tests/test_assy_mes_03_evidence.py", "tests/test_m6_int_01.py",
    "tests/test_sim_val_01_feed.py", "tests/test_sub_line_identity.py",
    "tests/test_vf_contract_finality_01.py", "tests/test_manual_e2e_01.py",
    "tests/test_m3_s03_tipa.py",
]


def main() -> int:
    print("Capturing DDAY-B2-C01 evidence ...")
    evidence = {
        "task_id": "DDAY-B2-C01",
        "parent_task": "DDAY-B2",
        "issue": 103, "parent_issue": 102, "pr": 101,
        "git": capture_git_state(),
        "semantic_isolation": capture_semantic_isolation(),
        "harness_repair": capture_harness_repair(),
    }
    print("  B2 + C01 tests ...")
    evidence["tests_b2"] = run_pytest(
        ["tests/test_dday_b2_bottled_water_line.py"], "junit-c01-b2.xml")
    print("  harness tests ...")
    evidence["tests_harness"] = run_pytest(
        [".ai-harness/tests/test_gate_report_provisional.py",
         ".ai-harness/tests/test_validate_report_consistency.py"],
        "junit-c01-harness.xml")
    print("  legacy regression ...")
    evidence["tests_regression"] = run_pytest(
        LEGACY_REGRESSION_TESTS, "junit-c01-regression.xml")
    print("  full suite ...")
    evidence["tests_full"] = run_pytest([], "junit-c01-full.xml")

    gate_record = REPO_ROOT / ".ai-harness" / "traces" / "DDAY-B2-C01" / "evidence.json"
    if gate_record.exists():
        gate = json.loads(gate_record.read_text(encoding="utf-8"))
        evidence["task_gate"] = {
            "record": ".ai-harness/traces/DDAY-B2-C01/evidence.json",
            "report": ".ai-harness/traces/DDAY-B2-C01/gate-report.md",
            "derived_status": gate.get("derived_status"),
            "exit_code": gate.get("exit_code"),
            "requested_gate_satisfied": gate.get("requested_gate_satisfied"),
            "implementation_sha": gate.get("implementation", {}).get("commit_sha"),
            "pipeline_steps": {s["id"]: s["result"] for s in gate.get("pipeline_steps", [])},
            "acceptance": {a["id"]: a["result"] for a in gate.get("acceptance", [])},
            "invariants": gate.get("invariants"),
            "ci": gate.get("ci"),
            "pull_request": gate.get("pull_request"),
        }

    out = EVIDENCE_DIR / "machine-evidence.json"
    out.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"wrote {out.relative_to(REPO_ROOT)}")
    print(json.dumps({
        "isolation_clean": evidence["semantic_isolation"]["all_sweeps_clean"],
        "p21_report_has_sha": evidence["harness_repair"]["p21_generated_report_contains_sha"],
        "p22_validation_passes": evidence["harness_repair"][
            "validate_report_consistency_on_generated_report"]["passed"],
        "b2_tests": evidence["tests_b2"]["result"],
        "harness_tests": evidence["tests_harness"]["result"],
        "regression": evidence["tests_regression"]["result"],
        "full": evidence["tests_full"]["result"],
        "gate": evidence.get("task_gate", {}).get("derived_status"),
        "gate_exit": evidence.get("task_gate", {}).get("exit_code"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
