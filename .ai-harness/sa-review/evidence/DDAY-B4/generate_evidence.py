#!/usr/bin/env python3
"""DDAY-B4 — evidence generator.

Task: DDAY-B4 (SA Issue #105 / PR #101).
Contract: .ai-harness/tasks/DDAY-B4.json

Run:
    python .ai-harness/sa-review/evidence/DDAY-B4/generate_evidence.py

Captures, from the real code paths and the real configs:

  git / scope state (vs the B4 baseline and vs origin/main)
  headless autonomy proof (server-side clock, browser never involved)
  whole-factory raw projection sample
  hierarchy + taxonomy integrity
  conservation / process-consistency invariants
  deterministic replay digests
  B3 observer-only proof
  test results (B4 module, B3/B2/legacy regression, full suite)
  the machine task-gate record, when it exists
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from xml.etree import ElementTree as ET


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "src" / "virtual_factory").is_dir():
            return candidate
    raise RuntimeError("repository root not found")


EVIDENCE_DIR = Path(__file__).resolve().parent
REPO_ROOT = _find_repo_root(EVIDENCE_DIR)
sys.path.insert(0, str(REPO_ROOT / "src"))

import yaml  # noqa: E402  (after sys.path setup)

B4_BASELINE_SHA = "23b6208266751a8c508b0d96fd7a736dffc5676c"
B4_CONTRACT_SHA = "18e8cad1ef52f6eed549e753acfc464a4ef7e7dd"
B4_IMPLEMENTATION_SHA = "ae560c02e259ed91a9609b36b5dff060dc9d4fd4"
WORKSPACE = REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday"
LINE_YAML = WORKSPACE / "line.yaml"
FACTORY_YAML = WORKSPACE / "factory.yaml"
TOPOLOGY_YAML = WORKSPACE / "topology.yaml"
APP_CONFIG = REPO_ROOT / "configs" / "plants" / "continuous_mvp_01.yaml"
STATIC = REPO_ROOT / "src" / "virtual_factory" / "ui" / "static"

CONFIG = yaml.safe_load(FACTORY_YAML.read_text(encoding="utf-8"))
TOPOLOGY = yaml.safe_load(TOPOLOGY_YAML.read_text(encoding="utf-8"))

RECOVERY = CONFIG["water_treatment"]["recovery_factor"]
TANK_CAPACITY_M3 = CONFIG["water_treatment"]["tank_capacity_m3"]
TANK_HIGH_M3 = (TANK_CAPACITY_M3
                * CONFIG["water_treatment"]["tank_high_level_pct"] / 100.0)
BOTTLE_VOLUME_M3 = CONFIG["line"]["bottle_volume_m3"]
PROCESS_EFFICIENCY = CONFIG["line"]["process_efficiency"]
BASE_LOAD_KW = CONFIG["plant"]["base_load_kw"]
NOMINAL_DWELL_S = 20.0
STATIONS = CONFIG["line"]["stations"]
FEED = "BW-WT-FEED01"
COMPRESSOR = "BW-UT-CMP01"
METER = "BW-UT-PWR01"
LINE_AREA = "BW-FP"

FORBIDDEN_SEMANTICS = (
    re.compile(r"assy", re.IGNORECASE),
    re.compile(r"tipa", re.IGNORECASE),
    re.compile(r"pre-assy", re.IGNORECASE),
    re.compile(r"sso2", re.IGNORECASE),
    re.compile(r"rso2", re.IGNORECASE),
    re.compile(r"ap05_jam", re.IGNORECASE),
    re.compile(r"\bAP\d{2}\b"),
)
FORBIDDEN_KPI_FIELDS = (
    "oee", "availability", "performance_pct", "quality_pct", "energy_per",
    "utilization", "health_score", "predictive",
)
FORBIDDEN_INVENTED_IDS = (
    "vendor", "model_number", "serial", "canonical_id", "platform_id",
    "device_id",
)


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True,
        encoding="utf-8", errors="replace", cwd=REPO_ROOT,
    )
    return (result.stdout or "").strip()


def _digest(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ═══════════════════════════════════════════════════════════════
# 1. Git / scope state
# ═══════════════════════════════════════════════════════════════


def capture_git_state() -> dict:
    # The slice change set is pinned to the B4 implementation commit, so it stays
    # a faithful record of what B4 changed even after the evidence and
    # gate-status commits advance the branch head.
    name_status = git(
        "diff", "--name-status", B4_BASELINE_SHA, B4_IMPLEMENTATION_SHA
    ).splitlines()
    (EVIDENCE_DIR / "implementation.patch").write_text(
        git("diff", B4_CONTRACT_SHA, B4_IMPLEMENTATION_SHA), encoding="utf-8")
    scope = {
        "task_id": "DDAY-B4",
        "b4_baseline_sha": B4_BASELINE_SHA,
        "sa_expected_baseline_sha": "23b6208266751a8c508b0d96fd7a736dffc5676c",
        "b4_contract_sha": B4_CONTRACT_SHA,
        "b4_implementation_sha": B4_IMPLEMENTATION_SHA,
        "changed_vs_b4_baseline": [
            line.split("\t", 1)[1] for line in name_status if "\t" in line],
        "name_status_vs_b4_baseline": name_status,
        "diffstat_vs_b4_baseline": git(
            "diff", "--stat", B4_BASELINE_SHA, B4_IMPLEMENTATION_SHA).splitlines(),
        "diffstat_implementation_only": git(
            "diff", "--stat", B4_CONTRACT_SHA, B4_IMPLEMENTATION_SHA).splitlines(),
        "changed_vs_origin_main": git(
            "diff", "--name-only", "origin/main", "HEAD").splitlines(),
    }
    (EVIDENCE_DIR / "scope-contract-b4-baseline.json").write_text(
        json.dumps(scope, indent=2), encoding="utf-8")
    return {
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "local_head": git("rev-parse", "HEAD"),
        "origin_main": git("rev-parse", "origin/main"),
        "b4_baseline_sha": B4_BASELINE_SHA,
        "b4_implementation_sha": B4_IMPLEMENTATION_SHA,
        "working_tree_status": git("status", "--short"),
        "name_status_vs_b4_baseline": name_status,
        "changed_vs_b4_baseline": scope["changed_vs_b4_baseline"],
        "diffstat_vs_b4_baseline": scope["diffstat_vs_b4_baseline"],
        "diffstat_implementation_only": scope["diffstat_implementation_only"],
        "changed_vs_origin_main": scope["changed_vs_origin_main"],
    }


# ═══════════════════════════════════════════════════════════════
# 2. Headless autonomy proof
# ═══════════════════════════════════════════════════════════════


def capture_headless_autonomy() -> dict:
    """Prove the server owns the production clock with no browser involved.

    The only HTTP calls made here are control POSTs and GETs of the factory
    projection: no page, no skin asset and no POST /advance is ever issued.
    """
    from fastapi.testclient import TestClient

    from virtual_factory.ui.api import create_app

    os.environ.pop("BOTTLED_WATER_CONFIG", None)
    os.environ.pop("BOTTLED_WATER_FACTORY_CONFIG", None)
    app = create_app(
        config_path=APP_CONFIG, dt_s=1.0,
        factory_autorun=True, factory_tick_interval_s=0.05,
    )
    calls: list[str] = []
    samples: list[dict] = []
    before_start: dict = {}

    with TestClient(app) as client:
        calls.append("POST /bottled-water-demo/reset")
        client.post("/bottled-water-demo/reset")
        calls.append("GET /bottled-water-demo/factory")
        start_state = client.get("/bottled-water-demo/factory").json()
        before_start = {
            "run_state": start_state["factory"]["run_state"],
            "counts": start_state["target_line"]["counts"],
        }
        time.sleep(0.6)
        stopped = client.get("/bottled-water-demo/factory").json()

        calls.append("POST /bottled-water-demo/start")
        client.post("/bottled-water-demo/start")
        began = time.time()
        deadline = began + 20.0
        while time.time() < deadline and len(samples) < 40:
            payload = client.get("/bottled-water-demo/factory").json()
            samples.append({
                "wall_s": round(time.time() - began, 3),
                "simulation_time_s": payload["factory"]["simulation_time_s"],
                "dwell_number": payload["target_line"]["dwell_number"],
                "total_count": payload["target_line"]["counts"]["total"],
                "plant_energy_total_kwh":
                    payload["balances"]["energy"]["plant_energy_total_kwh"],
            })
            if samples[-1]["dwell_number"] >= 3:
                break
            time.sleep(0.05)

        final = client.get("/bottled-water-demo/factory").json()
        calls.append("GET /bottled-water-demo")

    page_requests = [c for c in calls if c == "GET /bottled-water-demo"]
    advance_requests = [c for c in calls if "advance" in c]
    return {
        "headless": True,
        "browser_opened": False,
        "page_requests_after_production": len(page_requests),
        "advance_requests": advance_requests,
        "http_calls_issued": calls,
        "stopped_state": {
            "run_state": before_start["run_state"],
            "counts": before_start["counts"],
            "simulation_time_s_after_0_6s": stopped["factory"][
                "simulation_time_s"],
            "counts_after_0_6s": stopped["target_line"]["counts"],
            "plant_energy_total_kwh_after_0_6s":
                stopped["balances"]["energy"]["plant_energy_total_kwh"],
        },
        "samples": samples,
        "final": {
            "run_state": final["factory"]["run_state"],
            "simulation_time_s": final["factory"]["simulation_time_s"],
            "dwell_number": final["target_line"]["dwell_number"],
            "counts": final["target_line"]["counts"],
            "units_on_line": final["target_line"]["units_on_line"],
            "plant_energy_total_kwh":
                final["balances"]["energy"]["plant_energy_total_kwh"],
        },
        "progression_without_advance": (
            final["target_line"]["dwell_number"] >= 1
            and final["target_line"]["counts"]["total"] >= 1
        ),
    }


# ═══════════════════════════════════════════════════════════════
# 3. Whole-factory projection sample
# ═══════════════════════════════════════════════════════════════


def capture_factory_projection() -> dict:
    from virtual_factory.workspaces.bottled_water import BottledWaterFactory

    factory = BottledWaterFactory(LINE_YAML, FACTORY_YAML)
    factory.start()
    for _ in range(500):
        factory.step(1.0)
    payload = factory.snapshot()

    (EVIDENCE_DIR / "factory-state-sample.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8")

    serialised = json.dumps(payload)
    facts: list[dict] = []
    for node_id, node in payload["nodes"].items():
        for signal_id, signal in (node.get("signals") or {}).items():
            facts.append({
                "source_id": node_id,
                "signal_id": signal_id,
                "value": signal["value"],
                "unit": signal["unit"],
                "quality": signal["quality"],
                "provenance": signal["provenance"],
                "simulation_time_s": signal["simulation_time_s"],
            })

    return {
        "sample_file": "factory-state-sample.json",
        "workspace_id": payload["workspace_id"],
        "plant_id": payload["plant_id"],
        "factory": payload["factory"],
        "top_level_keys": sorted(payload),
        "node_count": len(payload["nodes"]),
        "signal_count": len(facts),
        "signals": facts[:12],
        "balances": payload["balances"],
        "recent_events": payload["recent_events"],
        "kpi_hits": [k for k in FORBIDDEN_KPI_FIELDS if k in serialised.lower()],
        "foreign_semantics_hits": [
            p.pattern for p in FORBIDDEN_SEMANTICS if p.search(serialised)],
        "invented_identity_hits": [
            token for token in FORBIDDEN_INVENTED_IDS if token in serialised],
        "reuses_b3_target_line_facts": (
            payload["target_line"]["route"]
            == list(TOPOLOGY["areas"][2]["route"])
            and payload["target_line"]["line_id"] == LINE_AREA
        ),
    }


# ═══════════════════════════════════════════════════════════════
# 4. Hierarchy / taxonomy integrity
# ═══════════════════════════════════════════════════════════════


def capture_hierarchy() -> dict:
    from virtual_factory.workspaces.bottled_water import (
        BottledWaterFactory,
        load_hierarchy,
    )

    _topology, nodes = load_hierarchy(TOPOLOGY_YAML)
    ids = [node.source_id for node in nodes]
    factory = BottledWaterFactory(LINE_YAML, FACTORY_YAML)
    snapshot = factory.snapshot()

    expected_parent: dict[str, str | None] = {TOPOLOGY["plant"]["id"]: None}
    for area in TOPOLOGY["areas"]:
        expected_parent[area["id"]] = TOPOLOGY["plant"]["id"]
        for asset in area.get("assets", ()):
            expected_parent[asset["id"]] = area["id"]

    assets = {n.source_id: n for n in nodes if n.entity_type == "asset"}
    parents = [expected_parent[a] for a in assets]
    projection_ok = all(
        entry["parent_source_id"] == expected_parent[node_id]
        for node_id, entry in snapshot["nodes"].items()
    )
    return {
        "node_count": len(nodes),
        "plant_count": sum(1 for n in nodes if n.entity_type == "plant"),
        "area_count": sum(1 for n in nodes if n.entity_type == "area"),
        "asset_count": len(assets),
        "ids_unique": len(ids) == len(set(ids)),
        "every_asset_has_exactly_one_parent": (
            len(parents) == len(assets)
            and all(p is not None for p in parents)
        ),
        "every_asset_parent_is_an_area": all(
            expected_parent[asset_id] in {a["id"] for a in TOPOLOGY["areas"]}
            for asset_id in assets
        ),
        "projection_matches_frozen_topology": projection_ok,
        "blower_nodes": [
            {"source_id": n.source_id, "name": n.name,
             "parent_source_id": n.parent_source_id}
            for n in nodes if "blow" in n.name.lower()
        ],
        "bottle_preparation_assets": [
            n.source_id for n in nodes if n.parent_source_id == "BW-BP"
        ],
        "taxonomy_fields": sorted(
            {k for entry in snapshot["nodes"].values() for k in entry}),
        "equipment_classes": sorted(
            {n.equipment_class for n in nodes if n.equipment_class}),
        "all_nodes_carry_workspace_id": all(
            entry["workspace_id"] == snapshot["workspace_id"]
            for entry in snapshot["nodes"].values()
        ),
    }


# ═══════════════════════════════════════════════════════════════
# 5. Conservation / process consistency
# ═══════════════════════════════════════════════════════════════


def _trace_station_units(factory, station_id: str) -> int:
    return len({
        e.wip_id for e in factory.controller.line.trace
        if e.event_type == "STATION_COMPLETE" and e.position == station_id
    })


def capture_conservation() -> dict:
    from virtual_factory.workspaces.bottled_water import BottledWaterFactory

    factory = BottledWaterFactory(LINE_YAML, FACTORY_YAML)
    factory.start()

    violations: list[str] = []
    tank_min = None
    tank_max = None
    high_level_engaged = False
    previous_at_high = False
    previous_energy = 0.0
    previous_good = 0
    previous_materials = 0
    production_checks = 0

    for step in range(4000):
        factory.step(1.0)
        snapshot = factory.snapshot()
        water = snapshot["balances"]["water"]
        energy = snapshot["balances"]["energy"]
        materials = snapshot["balances"]["materials"]
        goods = snapshot["balances"]["finished_goods"]

        tank_min = water["tank_volume_m3"] if tank_min is None else min(
            tank_min, water["tank_volume_m3"])
        tank_max = water["tank_volume_m3"] if tank_max is None else max(
            tank_max, water["tank_volume_m3"])

        if not (0.0 <= water["tank_volume_m3"] <= water["tank_high_volume_m3"]):
            violations.append(f"step {step}: tank out of bounds")
        if abs(water["tank_volume_m3"]
               - (water["tank_initial_volume_m3"]
                  + water["treated_water_total_m3"]
                  - water["water_draw_total_m3"])) > 1e-9:
            violations.append(f"step {step}: tank balance does not close")
        if abs(water["treated_water_total_m3"]
               - water["raw_water_feed_total_m3"] * RECOVERY) > 1e-9:
            violations.append(f"step {step}: recovery balance broken")
        if abs(water["ro_reject_total_m3"]
               - (water["raw_water_feed_total_m3"]
                  - water["treated_water_total_m3"])) > 1e-9:
            violations.append(f"step {step}: RO reject balance broken")
        if energy["plant_energy_total_kwh"] < previous_energy:
            violations.append(f"step {step}: energy decreased")
        previous_energy = energy["plant_energy_total_kwh"]
        if goods["inventory_count"] < 0:
            violations.append(f"step {step}: negative FG inventory")
        if goods["inventory_count"] != (goods["receipt_count"]
                                        - goods["dispatch_count"]):
            violations.append(f"step {step}: FG balance does not close")
        if goods["receipt_count"] < previous_good:
            violations.append(f"step {step}: good count decreased")
        previous_good = goods["receipt_count"]
        total_materials = sum(
            materials[k] for k in
            ("preform_count", "cap_count", "label_count", "case_count",
             "pallet_count"))
        if total_materials < previous_materials:
            violations.append(f"step {step}: material counter decreased")
        previous_materials = total_materials
        if not (materials["label_count"] <= materials["cap_count"]
                <= materials["preform_count"]):
            violations.append(f"step {step}: material flow order broken")
        if water["tank_volume_m3"] >= water["tank_high_volume_m3"]:
            high_level_engaged = True
            feed_flow = snapshot["nodes"][FEED]["signals"].get(
                "water_flow", {}).get("value", 0.0)
            # A step whose inflow terminates exactly at the limit may still show
            # the flow that filled the last of the headroom; the invariant is
            # that a tank already at the limit must take no water.
            if previous_at_high and feed_flow != 0.0:
                violations.append(
                    f"step {step}: feed did not idle at the high level")
            previous_at_high = True
        else:
            previous_at_high = False
        if step % 250 == 0:
            production_checks += 1

    final = factory.snapshot()
    filled = _trace_station_units(factory, STATIONS["fill"])
    capped = _trace_station_units(factory, STATIONS["cap"])
    labeled = _trace_station_units(factory, STATIONS["label"])
    packed = _trace_station_units(factory, STATIONS["case_pack"])
    asset_energy = sum(
        node["signals"]["energy_total"]["value"]
        for node in final["nodes"].values()
        if "energy_total" in node["signals"]
    )
    clock_s = final["factory"]["simulation_time_s"]

    identity_errors = []
    if abs(final["balances"]["water"]["product_water_total_m3"]
           - filled * BOTTLE_VOLUME_M3) > 1e-12:
        identity_errors.append("product water != filled bottles x volume")
    if abs(final["balances"]["water"]["water_draw_total_m3"]
           - final["balances"]["water"]["product_water_total_m3"]
           / PROCESS_EFFICIENCY) > 1e-9:
        identity_errors.append("filler draw != product water / efficiency")
    if abs(final["balances"]["energy"]["plant_energy_total_kwh"]
           - (asset_energy + BASE_LOAD_KW * clock_s / 3600.0)) > 1e-9:
        identity_errors.append("plant energy != sum(asset energy) + base x time")
    if final["balances"]["materials"]["preform_count"] != (
            final["target_line"]["counts"]["total"]):
        identity_errors.append("preform count != units introduced")
    if final["balances"]["materials"]["cap_count"] != capped:
        identity_errors.append("cap count != capped units")
    if final["balances"]["materials"]["label_count"] != labeled:
        identity_errors.append("label count != labeled units")
    if final["balances"]["materials"]["case_count"] != (
            packed // CONFIG["packaging"]["bottles_per_case"]):
        identity_errors.append("case count != aggregate packing model")

    top_off = final["nodes"][METER]["signals"]["plant_active_power"]["value"]
    return {
        "steps": 4000,
        "sample_points": production_checks,
        "violations": violations,
        "identity_errors": identity_errors,
        "tank_volume_min_m3": round(tank_min, 6),
        "tank_volume_max_m3": round(tank_max, 6),
        "tank_high_volume_m3": TANK_HIGH_M3,
        "tank_capacity_m3": TANK_CAPACITY_M3,
        "high_level_rule_engaged": high_level_engaged,
        "flows": {
            "filled_units": filled,
            "capped_units": capped,
            "labeled_units": labeled,
            "packed_units": packed,
        },
        "final_balances": final["balances"],
        "final_factory": final["factory"],
        "plant_active_power_kw": top_off,
        "energy_identity_asset_energy_kwh": round(asset_energy, 6),
    }


def capture_utilities_causality() -> dict:
    from virtual_factory.workspaces.bottled_water import BottledWaterFactory

    factory = BottledWaterFactory(LINE_YAML, FACTORY_YAML)
    factory.start()
    for _ in range(300):
        factory.step(1.0)
    running = factory.snapshot()
    factory.stop()
    for _ in range(300):
        factory.step(1.0)
    stopped = factory.snapshot()

    def node(snapshot, node_id):
        return {k: v["value"] for k, v in snapshot["nodes"][node_id][
            "signals"].items()}

    return {
        "running": {
            "compressor": node(running, COMPRESSOR),
            "line_area": node(running, LINE_AREA),
            "plant_active_power_kw":
                running["balances"]["energy"]["plant_active_power_kw"],
        },
        "stopped": {
            "compressor": node(stopped, COMPRESSOR),
            "line_area": node(stopped, LINE_AREA),
            "plant_active_power_kw":
                stopped["balances"]["energy"]["plant_active_power_kw"],
        },
        "pressure_sags_under_load": (
            node(running, COMPRESSOR)["air_pressure"]
            < node(stopped, COMPRESSOR)["air_pressure"]
        ),
        "compressor_unloads_when_stopped": (
            node(stopped, COMPRESSOR)["operating_state"] == "IDLE"
            and node(stopped, COMPRESSOR)["active_power"]
            < node(running, COMPRESSOR)["active_power"]
        ),
        "feed_idles_when_stopped": (
            node(stopped, FEED)["water_flow"] == 0.0
        ),
        "plant_load_drops_when_stopped": (
            stopped["balances"]["energy"]["plant_active_power_kw"]
            < running["balances"]["energy"]["plant_active_power_kw"]
        ),
    }


# ═══════════════════════════════════════════════════════════════
# 6. Deterministic replay + control semantics
# ═══════════════════════════════════════════════════════════════


def _run_sequence() -> list[str]:
    from virtual_factory.workspaces.bottled_water import BottledWaterFactory

    factory = BottledWaterFactory(LINE_YAML, FACTORY_YAML)
    digests = [_digest(factory.snapshot())]
    factory.start()
    for _ in range(250):
        factory.step(1.0)
    digests.append(_digest(factory.snapshot()))
    factory.pause()
    for _ in range(40):
        factory.step(1.0)
    digests.append(_digest(factory.snapshot()))
    factory.resume()
    for _ in range(250):
        factory.step(1.0)
    digests.append(_digest(factory.snapshot()))
    factory.stop()
    for _ in range(120):
        factory.step(1.0)
    digests.append(_digest(factory.snapshot()))
    factory.reset()
    digests.append(_digest(factory.snapshot()))
    return digests


def capture_determinism() -> dict:
    from virtual_factory.workspaces.bottled_water import BottledWaterFactory

    first = _run_sequence()
    second = _run_sequence()

    fresh = _digest(BottledWaterFactory(LINE_YAML, FACTORY_YAML).snapshot())

    coarse = BottledWaterFactory(LINE_YAML, FACTORY_YAML)
    fine = BottledWaterFactory(LINE_YAML, FACTORY_YAML)
    coarse.start()
    fine.start()
    for _ in range(20):
        coarse.step(20.0)
        for _ in range(20):
            fine.step(1.0)

    payload = {
        "identical_control_sequences": first == second,
        "reset_returns_initial_state": first[-1] == fresh,
        "step_size_irrelevant": (
            _digest(coarse.snapshot()) == _digest(fine.snapshot())),
        "digests": first,
        "fresh_instance_initial_digest": fresh,
        "control_semantics": {},
    }

    factory = BottledWaterFactory(LINE_YAML, FACTORY_YAML)
    factory.start()
    for _ in range(100):
        factory.step(1.0)
    running = factory.snapshot()
    factory.pause()
    for _ in range(200):
        factory.step(1.0)
    paused = factory.snapshot()
    factory.resume()
    for _ in range(100):
        factory.step(1.0)
    resumed = factory.snapshot()
    factory.stop()
    for _ in range(200):
        factory.step(1.0)
    stopped = factory.snapshot()

    payload["control_semantics"] = {
        "running": {
            "run_state": running["factory"]["run_state"],
            "simulation_time_s": running["factory"]["simulation_time_s"],
            "counts": running["target_line"]["counts"],
        },
        "paused": {
            "run_state": paused["factory"]["run_state"],
            "simulation_time_s": paused["factory"]["simulation_time_s"],
            "counts": paused["target_line"]["counts"],
            "conserved_quantities_frozen": _conserved(paused) == _conserved(
                running),
        },
        "resumed": {
            "run_state": resumed["factory"]["run_state"],
            "simulation_time_s": resumed["factory"]["simulation_time_s"],
            "counts": resumed["target_line"]["counts"],
        },
        "stopped": {
            "run_state": stopped["factory"]["run_state"],
            "simulation_time_s": stopped["factory"]["simulation_time_s"],
            "counts": stopped["target_line"]["counts"],
            "counts_frozen_vs_resumed":
                stopped["target_line"]["counts"] == resumed["target_line"]["counts"],
            "fault_present": "FAULT" in json.dumps(stopped),
        },
    }
    payload["pause_freezes_conserved_quantities"] = (
        _conserved(paused) == _conserved(running))
    payload["stop_halts_production_only"] = (
        stopped["target_line"]["counts"] == resumed["target_line"]["counts"]
        and not payload["control_semantics"]["stopped"]["fault_present"]
    )
    return payload


def _conserved(snapshot: dict) -> dict:
    """Conserved quantities of a snapshot (excludes instantaneous load reads)."""
    balances = snapshot["balances"]
    return {
        "water": balances["water"],
        "materials": balances["materials"],
        "finished_goods": balances["finished_goods"],
        "plant_energy_total_kwh": balances["energy"]["plant_energy_total_kwh"],
    }


# ═══════════════════════════════════════════════════════════════
# 7. B3 observer-only proof
# ═══════════════════════════════════════════════════════════════


def capture_b3_observer_only() -> dict:
    js = (STATIC / "bottled_water_demo.js").read_text(encoding="utf-8")
    html = (STATIC / "bottled_water_demo.html").read_text(encoding="utf-8")
    posts = re.findall(r"bw(?:Post|Action)\('([^']+)'\)", js)

    from fastapi.testclient import TestClient

    from virtual_factory.ui.api import create_app

    app = create_app(config_path=APP_CONFIG, dt_s=1.0, factory_autorun=False)
    with TestClient(app) as client:
        client.post("/bottled-water-demo/reset")
        served = client.get("/bottled-water-demo")
        routes = sorted(
            route.path for route in client.app.routes
            if route.path.startswith("/bottled-water-demo")
        )
        client.post("/bottled-water-demo/start")
        client.post("/bottled-water-demo/advance")
        state = client.get("/bottled-water-demo/state").json()
        factory = client.get("/bottled-water-demo/factory").json()

    return {
        "skin_posts": sorted(posts),
        "skin_posts_advance": "/advance" in js,
        "skin_polls_state": "bwGet('/state')" in js,
        "operator_buttons": re.findall(r'id="(bw-btn-[a-z]+)"', html),
        "refresh_control_is_display_only": "display only" in html,
        "page_serves": served.status_code == 200,
        "bw_routes": routes,
        "skin_and_factory_share_one_runtime": (
            factory["target_line"] == state
            and factory["target_line"]["counts"]["total"] == 1
        ),
        "factory_clock_matches_line_clock_after_debug_advance": (
            factory["factory"]["simulation_time_s"]
            == state["simulation_time_s"] == NOMINAL_DWELL_S
        ),
    }


# ═══════════════════════════════════════════════════════════════
# 8. Tests
# ═══════════════════════════════════════════════════════════════


def run_pytest(paths: list[str], junit_name: str) -> dict:
    junit = EVIDENCE_DIR / junit_name
    env = {**os.environ}
    env.pop("PYTHONIOENCODING", None)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=short",
         "-p", "no:cacheprovider", f"--junitxml={junit}", *paths],
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


REGRESSION_TESTS = [
    "tests/test_api.py",
    "tests/test_assy_demo.py",
    "tests/test_demo_composition.py",
    "tests/test_demo_overview.py",
    "tests/test_dday_b2_bottled_water_line.py",
    "tests/test_dday_b3_bottled_water_ui.py",
    "tests/test_runtime_service.py",
]


def main() -> int:
    print("Capturing DDAY-B4 evidence ...")
    evidence: dict = {
        "task_id": "DDAY-B4",
        "parent_task": "DDAY-B3",
        "issue": 105,
        "pr": 101,
        "git": capture_git_state(),
    }

    print("  headless autonomy ...")
    evidence["autonomy"] = capture_headless_autonomy()
    print("  whole-factory projection ...")
    evidence["projection"] = capture_factory_projection()
    print("  hierarchy / taxonomy ...")
    evidence["hierarchy"] = capture_hierarchy()
    print("  conservation invariants ...")
    evidence["conservation"] = capture_conservation()
    print("  utilities causality ...")
    evidence["utilities"] = capture_utilities_causality()
    print("  deterministic replay ...")
    evidence["determinism"] = capture_determinism()
    print("  B3 observer-only ...")
    evidence["b3_observer"] = capture_b3_observer_only()

    print("  B4 tests ...")
    evidence["tests_b4"] = run_pytest(
        ["tests/test_dday_b4_bottled_water_factory.py"], "junit-b4.xml")
    print("  regression subset ...")
    evidence["tests_regression"] = run_pytest(
        REGRESSION_TESTS, "junit-b4-regression.xml")
    if evidence["tests_regression"]["result"] == "FAIL":
        print("  regression subset rerun (first run failed) ...")
        evidence["tests_regression_rerun"] = run_pytest(
            REGRESSION_TESTS, "junit-b4-regression-rerun.xml")
    print("  full suite ...")
    evidence["tests_full"] = run_pytest([], "junit-b4-full.xml")
    if evidence["tests_full"]["result"] == "FAIL":
        # Record the rerun: the only known failure mode in the full suite is the
        # pre-existing id()-reuse flake in tests/test_demo_composition.py.
        print("  full suite rerun (first run failed) ...")
        evidence["tests_full_rerun"] = run_pytest(
            [], "junit-b4-full-rerun.xml")

    gate_record = REPO_ROOT / ".ai-harness" / "traces" / "DDAY-B4" / "evidence.json"
    if gate_record.exists():
        gate = json.loads(gate_record.read_text(encoding="utf-8"))
        evidence["task_gate"] = {
            "record": ".ai-harness/traces/DDAY-B4/evidence.json",
            "report": ".ai-harness/traces/DDAY-B4/gate-report.md",
            "derived_status": gate.get("derived_status"),
            "exit_code": gate.get("exit_code"),
            "requested_gate_satisfied": gate.get("requested_gate_satisfied"),
            "implementation_sha": gate.get("implementation", {}).get("commit_sha"),
            "pipeline_steps": {s["id"]: s["result"]
                               for s in gate.get("pipeline_steps", [])},
            "acceptance": {a["id"]: a["result"]
                           for a in gate.get("acceptance", [])},
            "invariants": gate.get("invariants"),
            "ci": gate.get("ci"),
        }

    out = EVIDENCE_DIR / "machine-evidence.json"
    out.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"wrote {out.relative_to(REPO_ROOT)}")

    print(json.dumps({
        "autonomy_progression_without_advance":
            evidence["autonomy"]["progression_without_advance"],
        "autonomy_advance_requests": len(
            evidence["autonomy"]["advance_requests"]),
        "projection_signals": evidence["projection"]["signal_count"],
        "kpi_hits": evidence["projection"]["kpi_hits"],
        "foreign_semantics_hits":
            evidence["projection"]["foreign_semantics_hits"],
        "hierarchy_assets": evidence["hierarchy"]["asset_count"],
        "hierarchy_ok": (
            evidence["hierarchy"]["ids_unique"]
            and evidence["hierarchy"]["every_asset_has_exactly_one_parent"]
            and evidence["hierarchy"]["projection_matches_frozen_topology"]),
        "conservation_violations": len(
            evidence["conservation"]["violations"]),
        "conservation_identity_errors": evidence["conservation"][
            "identity_errors"],
        "determinism": evidence["determinism"]["identical_control_sequences"],
        "reset_initial": evidence["determinism"]["reset_returns_initial_state"],
        "b3_observer_only": (
            not evidence["b3_observer"]["skin_posts_advance"]
            and evidence["b3_observer"]["skin_and_factory_share_one_runtime"]),
        "tests_b4": evidence["tests_b4"]["result"],
        "tests_regression": evidence["tests_regression"]["result"],
        "tests_full": evidence["tests_full"]["result"],
        "tests_full_rerun": evidence.get(
            "tests_full_rerun", {}).get("result", "n/a"),
        "gate": evidence.get("task_gate", {}).get("derived_status"),
        "gate_exit": evidence.get("task_gate", {}).get("exit_code"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
