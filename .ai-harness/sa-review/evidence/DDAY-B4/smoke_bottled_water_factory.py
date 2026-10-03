#!/usr/bin/env python3
"""DDAY-B4 — live whole-factory autonomous-runtime smoke check.

Task: DDAY-B4 (SA Issue #105 / PR #101).
Contract: .ai-harness/tasks/DDAY-B4.json

Starts the real FastAPI app on a real socket and drives it over real HTTP. No
mocks, no TestClient shortcuts. Proves:

  the server owns the production clock (START progresses with zero /advance
    calls from any client, and with the B3 page never opened at all)
  PAUSE freezes target line and aggregate factory progression
  RESUME continues from preserved state
  STOP halts production without becoming FAULT
  RESET returns the deterministic initial state
  water balance is coherent and the tank stays bounded
  material/water consumption follows real production counts
  utilities respond causally, energy is monotonic power x time
  finished goods follow completed good production
  no calculated KPI and no foreign-line vocabulary in the projection
  the B3 target-line UI still works as an observer + control surface

Exit code 0 = every claim proven. Any failed claim exits non-zero.
"""

from __future__ import annotations

import json
import re
import socket
import sys
import threading
import time
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "src" / "virtual_factory").is_dir():
            return candidate
    raise RuntimeError("repository root not found")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
sys.path.insert(0, str(REPO_ROOT / "src"))

WORKSPACE = REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday"
LINE_YAML = WORKSPACE / "line.yaml"
FACTORY_YAML = WORKSPACE / "factory.yaml"
TOPOLOGY_YAML = WORKSPACE / "topology.yaml"
APP_CONFIG = REPO_ROOT / "configs" / "plants" / "continuous_mvp_01.yaml"

NOMINAL_DWELL_S = 20.0
FORBIDDEN_PATTERNS = (
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

_failures: list[str] = []


def claim(condition: bool, description: str) -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        _failures.append(description)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _serve(port: int, autorun: bool, tick_interval_s: float | None = None):
    """Start the real app with uvicorn on a background thread."""
    import uvicorn

    from virtual_factory.ui.api import create_app

    kwargs = {}
    if tick_interval_s is not None:
        kwargs["factory_tick_interval_s"] = tick_interval_s
    app = create_app(
        config_path=APP_CONFIG,
        dt_s=1.0,
        factory_autorun=autorun,
        **kwargs,
    )
    server = uvicorn.Server(uvicorn.Config(
        app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 30
    while time.time() < deadline:
        if server.started:
            return server, thread
        time.sleep(0.1)
    raise RuntimeError("server did not start")


def _client(port: int):
    import httpx
    return httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=20.0)


def _signal(snapshot: dict, node_id: str, signal_id: str):
    return snapshot["nodes"][node_id]["signals"][signal_id]["value"]


def _await(predicate, fetch, timeout_s: float = 20.0):
    deadline = time.time() + timeout_s
    payload = fetch()
    while time.time() < deadline and not predicate(payload):
        time.sleep(0.1)
        payload = fetch()
    return payload


def pytest_approx(value, rel: float = 1e-6):
    """Tiny tolerance helper so this script needs no pytest import."""
    class _Approx:
        def __eq__(self, other) -> bool:
            try:
                return abs(float(other) - float(value)) <= (
                    rel * max(1.0, abs(float(value))))
            except (TypeError, ValueError):
                return False

        def __repr__(self) -> str:  # pragma: no cover - debug helper
            return f"approx({value!r}, rel={rel})"

    return _Approx()


def main() -> int:
    import yaml

    config = yaml.safe_load(FACTORY_YAML.read_text(encoding="utf-8"))
    topology = yaml.safe_load(TOPOLOGY_YAML.read_text(encoding="utf-8"))
    recovery = config["water_treatment"]["recovery_factor"]
    tank_capacity = config["water_treatment"]["tank_capacity_m3"]
    tank_high_m3 = (
        tank_capacity * config["water_treatment"]["tank_high_level_pct"] / 100.0
    )
    bottle_volume = config["line"]["bottle_volume_m3"]
    efficiency = config["line"]["process_efficiency"]
    air_setpoint = config["utilities"]["compressed_air"]["setpoint_bar"]
    air_sag = config["utilities"]["compressed_air"]["production_sag_bar"]
    air_running_kw = config["utilities"]["compressed_air"]["running_kw"]
    air_standby_kw = config["utilities"]["compressed_air"]["standby_kw"]
    base_load_kw = config["plant"]["base_load_kw"]
    stations = config["line"]["stations"]
    feed, ro, tank = "BW-WT-FEED01", "BW-WT-RO01", "BW-WT-TK01"
    compressor = "BW-UT-CMP01"
    line_area = "BW-FP"
    prep_area = "BW-BP"

    print("=" * 72)
    print("DDAY-B4 — Bottled Water whole-factory autonomous runtime smoke")
    print(f"app config    : {APP_CONFIG}")
    print(f"line config   : {LINE_YAML}")
    print(f"factory config: {FACTORY_YAML}")
    print("=" * 72)

    # ── 1. Autonomous server-side runtime, browser never involved ───────────
    print("\n[1] server-side autonomy with no browser and no /advance calls")
    port = _free_port()
    _server, _thread = _serve(port, autorun=True, tick_interval_s=0.05)
    try:
        with _client(port) as client:
            client.post("/bottled-water-demo/reset")
            reset = client.get("/bottled-water-demo/factory").json()
            claim(reset["factory"]["simulation_time_s"] == 0.0,
                  "RESET puts the factory clock back to zero")

            initial = client.get("/bottled-water-demo/factory").json()
            claim(initial["factory"]["run_state"] == "STOPPED",
                  "factory starts STOPPED")
            time.sleep(0.5)
            idle = client.get("/bottled-water-demo/factory").json()
            claim(idle["target_line"]["counts"] == initial["target_line"]["counts"],
                  "a STOPPED factory does not produce")
            claim(idle["balances"]["materials"] == initial["balances"]["materials"],
                  "a STOPPED factory consumes no material")
            claim(idle["balances"]["energy"]["plant_energy_total_kwh"]
                  > initial["balances"]["energy"]["plant_energy_total_kwh"],
                  "a stopped plant stays energized: only standby load accrues")

            client.post("/bottled-water-demo/start")
            progressed = _await(
                lambda p: p["target_line"]["counts"]["total"] >= 1,
                lambda: client.get("/bottled-water-demo/factory").json(),
            )
            claim(progressed["factory"]["simulation_time_s"] >= NOMINAL_DWELL_S,
                  "START progresses simulated time with no client /advance")
            claim(progressed["target_line"]["dwell_number"] >= 1,
                  "the target line produced at least one cycle autonomously")
            claim(progressed["target_line"]["counts"]["total"] >= 1,
                  "target-line counts advanced autonomously")
            claim(progressed["balances"]["water"]["raw_water_feed_total_m3"] > 0,
                  "aggregate water treatment progressed autonomously")
            claim(progressed["balances"]["energy"]["plant_energy_total_kwh"] > 0,
                  "energy accrued autonomously")
            claim(client.get("/bottled-water-demo").status_code == 200,
                  "the B3 page was never needed but still serves")

            # ── 2. PAUSE / RESUME / STOP / RESET ───────────────────────────
            print("\n[2] operator control semantics")
            client.post("/bottled-water-demo/pause")
            paused_a = client.get("/bottled-water-demo/factory").json()
            time.sleep(1.0)
            paused_b = client.get("/bottled-water-demo/factory").json()
            claim(paused_a["factory"]["run_state"] == "PAUSED",
                  "PAUSE reports PAUSED")
            claim(paused_a["factory"]["simulation_time_s"]
                  == paused_b["factory"]["simulation_time_s"],
                  "PAUSE freezes the simulated clock")
            claim(paused_a["target_line"]["counts"]
                  == paused_b["target_line"]["counts"],
                  "PAUSE freezes target-line production")
            claim(paused_a["balances"] == paused_b["balances"],
                  "PAUSE freezes every aggregate factory quantity")

            client.post("/bottled-water-demo/resume")
            resumed = _await(
                lambda p: p["factory"]["simulation_time_s"]
                > paused_b["factory"]["simulation_time_s"] + 5.0,
                lambda: client.get("/bottled-water-demo/factory").json(),
            )
            claim(resumed["factory"]["run_state"] == "RUNNING",
                  "RESUME reports RUNNING")
            claim(resumed["factory"]["simulation_time_s"]
                  > paused_b["factory"]["simulation_time_s"],
                  "RESUME continues from the preserved state")
            claim(resumed["target_line"]["counts"]["total"]
                  >= paused_b["target_line"]["counts"]["total"],
                  "RESUME keeps the counters (no silent reset)")

            client.post("/bottled-water-demo/stop")
            stopped_a = client.get("/bottled-water-demo/factory").json()
            time.sleep(1.0)
            stopped_b = client.get("/bottled-water-demo/factory").json()
            claim(stopped_b["factory"]["run_state"] == "STOPPED",
                  "STOP reports STOPPED")
            claim("FAULT" not in json.dumps(stopped_b),
                  "STOP never becomes FAULT")
            claim(stopped_a["target_line"]["counts"]
                  == stopped_b["target_line"]["counts"],
                  "STOP halts production progression")
            claim(stopped_b["balances"]["energy"]["plant_energy_total_kwh"]
                  >= paused_b["balances"]["energy"]["plant_energy_total_kwh"],
                  "a stopped plant stays energized and energy stays monotonic")

            # ── 3. Whole-factory projection shape ─────────────────────────
            print("\n[3] whole-factory raw projection")
            client.post("/bottled-water-demo/start")
            payload = _await(
                lambda p: p["target_line"]["counts"]["total"] >= 3,
                lambda: client.get("/bottled-water-demo/factory").json(),
            )
            expected_nodes = {topology["plant"]["id"]}
            expected_assets = 0
            for area in topology["areas"]:
                expected_nodes.add(area["id"])
                for asset in area.get("assets", ()):
                    expected_nodes.add(asset["id"])
                    expected_assets += 1
            claim(set(payload["nodes"]) == expected_nodes,
                  "the frozen B1 hierarchy appears exactly")
            claim(len({n["source_id"] for n in payload["hierarchy"]})
                  == len(payload["hierarchy"]),
                  "every source id is unique")
            claim(sum(1 for n in payload["nodes"].values()
                      if n["entity_type"] == "asset") == expected_assets,
                  f"all {expected_assets} assets of the frozen topology "
                  "are present")
            claim(sum(1 for n in payload["nodes"].values()
                      if "Blower" in n["name"]) == 1,
                  "the Blower is not duplicated under Bottle Preparation")
            claim(not [n for n in payload["nodes"].values()
                       if n["parent_source_id"] == prep_area
                       and n["entity_type"] == "asset"],
                  "Bottle Preparation stays a logical area with no asset")

            fact_count = 0
            attributed = True
            for node_id, node in payload["nodes"].items():
                for signal_id, signal in (node.get("signals") or {}).items():
                    fact_count += 1
                    attributed = attributed and bool(signal_id) and bool(
                        signal["unit"]) and signal["quality"] == "GOOD" and (
                        signal["provenance"] in ("SIMULATED_RAW",
                                                 "CONFIGURED_TARGET")) and (
                        isinstance(signal["simulation_time_s"], (int, float)))
                    attributed = attributed and node["workspace_id"] == (
                        payload["workspace_id"])
            claim(fact_count > 40,
                  f"the projection carries {fact_count} attributed raw facts")
            claim(attributed,
                  "every fact is attributable (node, signal, unit, quality, "
                  "provenance, timestamp)")

            # ── 4. Conservation / process consistency ─────────────────────
            print("\n[4] conservation and process consistency")
            water = payload["balances"]["water"]
            claim(water["treated_water_total_m3"]
                  == pytest_approx(water["raw_water_feed_total_m3"] * recovery),
                  "treated water = raw water x recovery factor")
            claim(water["ro_reject_total_m3"] == pytest_approx(
                water["raw_water_feed_total_m3"]
                - water["treated_water_total_m3"]),
                  "RO reject = raw water - treated water")
            claim(0.0 <= water["tank_volume_m3"] <= tank_capacity,
                  "the treated-water tank stays within capacity")
            claim(water["tank_volume_m3"] == pytest_approx(
                water["tank_initial_volume_m3"]
                + water["treated_water_total_m3"]
                - water["water_draw_total_m3"]),
                  "tank balance closes: initial + treated - draw")
            claim(water["tank_volume_m3"] <= tank_high_m3,
                  "the tank high-level rule holds")
            claim(_signal(payload, feed, "water_flow") > 0.0,
                  "the treatment feed is running while the plant produces")

            materials = payload["balances"]["materials"]
            claim(materials["preform_count"]
                  == payload["target_line"]["counts"]["total"],
                  "preform consumption follows units introduced")
            claim(materials["label_count"] <= materials["cap_count"]
                  <= materials["preform_count"],
                  "material consumption flows downstream only")
            filled = round(water["product_water_total_m3"] / bottle_volume)
            claim(filled > 0 and water["product_water_total_m3"]
                  == pytest_approx(filled * bottle_volume),
                  "product water is a whole number of filled 500 mL bottles")
            claim(water["water_draw_total_m3"] == pytest_approx(
                water["product_water_total_m3"] / efficiency),
                  "filler draw = product water / process efficiency")

            energy = payload["balances"]["energy"]
            asset_energy = sum(
                node["signals"]["energy_total"]["value"]
                for node in payload["nodes"].values()
                if "energy_total" in node["signals"]
            )
            clock_s = payload["factory"]["simulation_time_s"]
            claim(energy["plant_energy_total_kwh"] == pytest_approx(
                asset_energy + base_load_kw * clock_s / 3600.0),
                  "plant energy = summed asset energy + base load x time")
            claim(_signal(payload, compressor, "air_pressure")
                  == pytest_approx(air_setpoint - air_sag),
                  "compressed air sags while the line is producing")
            claim(_signal(payload, compressor, "active_power") == air_running_kw,
                  "the compressor loads up under production demand")

            goods = payload["balances"]["finished_goods"]
            claim(goods["receipt_count"]
                  == payload["target_line"]["counts"]["good"],
                  "finished goods receipts follow completed good production")
            claim(goods["inventory_count"] == goods["receipt_count"]
                  - goods["dispatch_count"], "FG inventory balance closes")
            claim(goods["inventory_count"] >= 0,
                  "FG inventory is never negative")

            # ── 5. Causal utility response to a controlled stop ───────────
            print("\n[5] utilities respond causally to load")
            client.post("/bottled-water-demo/stop")
            recovered = _await(
                lambda p: _signal(p, compressor, "air_pressure")
                >= air_setpoint - 1e-9,
                lambda: client.get("/bottled-water-demo/factory").json(),
                timeout_s=15.0,
            )
            claim(_signal(recovered, compressor, "air_pressure")
                  == pytest_approx(air_setpoint),
                  "air pressure recovers after production stops")
            claim(_signal(recovered, compressor, "operating_state") == "IDLE",
                  "the compressor unloads after production stops")
            claim(_signal(recovered, compressor, "active_power")
                  == air_standby_kw, "compressor standby load applies")
            claim(_signal(recovered, feed, "water_flow") == 0.0,
                  "the treatment feed idles when the plant is stopped")
            claim(_signal(recovered, line_area, "operating_state") == "STOPPED",
                  "the production line reports STOPPED")

            # ── 6. Raw-fact boundary ──────────────────────────────────────
            print("\n[6] raw-fact boundary and domain isolation")
            serialised = json.dumps(payload)
            for kpi in FORBIDDEN_KPI_FIELDS:
                claim(kpi not in serialised.lower(),
                      f"no calculated KPI published: {kpi}")
            for pattern in FORBIDDEN_PATTERNS:
                claim(not pattern.search(serialised),
                      f"no foreign-line vocabulary: {pattern.pattern}")

            # ── 7. B3 target-line UI still works ─────────────────────────
            print("\n[7] B3 target-line UI regression")
            client.post("/bottled-water-demo/reset")
            page = client.get("/bottled-water-demo")
            claim(page.status_code == 200 and "Bottled Water" in page.text,
                  "the B3 skin page still serves")
            for name in ("bottled_water_demo.js", "bottled_water_demo.css"):
                asset = client.get(f"/bottled-water-demo/static/{name}")
                claim(asset.status_code == 200 and len(asset.text) > 500,
                      f"skin asset still serves: {name}")
            js = client.get("/bottled-water-demo/static/bottled_water_demo.js").text
            claim("/advance" not in js,
                  "the skin no longer requests a production step")
            client.post("/bottled-water-demo/start")
            state = _await(
                lambda p: p["counts"]["total"] >= 1,
                lambda: client.get("/bottled-water-demo/state").json(),
            )
            claim(state["counts"]["total"] >= 1,
                  "the target-line projection follows the autonomous runtime")
            claim(len(state["route"]) == 8,
                  "all 8 frozen stations remain on the route")
            claim(state["counts"]["good"] + state["counts"]["reject"]
                  <= state["counts"]["total"], "line counts remain coherent")

            # STOP the plant so the second server starts from a clean state.
            client.post("/bottled-water-demo/stop")
    finally:
        _server.should_exit = True

    # ── 8. Deterministic step seam (no autonomy) still works ─────────────
    print("\n[8] deterministic debug seam with autonomy disabled")
    port = _free_port()
    server, _thread = _serve(port, autorun=False)
    try:
        with _client(port) as client:
            client.post("/bottled-water-demo/reset")
            client.post("/bottled-water-demo/start")
            time.sleep(0.6)
            still = client.get("/bottled-water-demo/factory").json()
            claim(still["factory"]["simulation_time_s"] == 0.0,
                  "with autorun disabled nothing advances on its own")
            for _ in range(8):
                client.post("/bottled-water-demo/advance")
            stepped = client.get("/bottled-water-demo/factory").json()
            claim(stepped["target_line"]["counts"]["total"] == 8,
                  "the debug seam still advances exactly one cycle per call")
            claim(stepped["factory"]["simulation_time_s"] == 160.0,
                  "the debug seam keeps the factory clock with the line")
    finally:
        server.should_exit = True

    print("\n" + "=" * 72)
    if _failures:
        print(f"SMOKE-BW-FACTORY: FAIL ({len(_failures)} failed claims)")
        for failure in _failures:
            print(f"  - {failure}")
        return 1
    print("SMOKE-BW-FACTORY: PASS")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
