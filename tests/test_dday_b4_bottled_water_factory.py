"""DDAY-B4 — Bottled Water whole-factory simulation + autonomous runtime tests.

Governed by .ai-harness/tasks/DDAY-B4.json (authored from SA Issue #105).

Every test exercises the real composition over the real B2 line runtime and the
real frozen B1 topology contract — no mocked factory data. Coverage maps 1:1 to
the 21 required verifications of Issue #105 §14.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import time
from pathlib import Path

import pytest
import yaml

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from virtual_factory.assembly.line_runtime import LineRunState
from virtual_factory.ui.api import create_app
from virtual_factory.workspaces.bottled_water import (
    BottledWaterFactory,
    load_hierarchy,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday"
LINE_YAML = WORKSPACE / "line.yaml"
FACTORY_YAML = WORKSPACE / "factory.yaml"
TOPOLOGY_YAML = WORKSPACE / "topology.yaml"
STATIC = REPO_ROOT / "src" / "virtual_factory" / "ui" / "static"

APP_CONFIG = REPO_ROOT / "configs" / "plants" / "continuous_mvp_01.yaml"

RAW_CONFIG = yaml.safe_load(FACTORY_YAML.read_text(encoding="utf-8"))
TOPOLOGY = yaml.safe_load(TOPOLOGY_YAML.read_text(encoding="utf-8"))

NOMINAL_DWELL_S = 20.0
BOTTLE_VOLUME_M3 = RAW_CONFIG["line"]["bottle_volume_m3"]
TANK_CAPACITY_M3 = RAW_CONFIG["water_treatment"]["tank_capacity_m3"]
TANK_HIGH_PCT = RAW_CONFIG["water_treatment"]["tank_high_level_pct"]
TANK_LOW_PCT = RAW_CONFIG["water_treatment"]["tank_low_level_pct"]
RECOVERY = RAW_CONFIG["water_treatment"]["recovery_factor"]
PROCESS_EFFICIENCY = RAW_CONFIG["line"]["process_efficiency"]
AIR_SETPOINT_BAR = RAW_CONFIG["utilities"]["compressed_air"]["setpoint_bar"]
AIR_SAG_BAR = RAW_CONFIG["utilities"]["compressed_air"]["production_sag_bar"]
AIR_RUNNING_KW = RAW_CONFIG["utilities"]["compressed_air"]["running_kw"]
AIR_STANDBY_KW = RAW_CONFIG["utilities"]["compressed_air"]["standby_kw"]
BASE_LOAD_KW = RAW_CONFIG["plant"]["base_load_kw"]

STATIONS = RAW_CONFIG["line"]["stations"]
FILL, CAP, LABEL = STATIONS["fill"], STATIONS["cap"], STATIONS["label"]
CASE_PACK, PALLETIZE = STATIONS["case_pack"], STATIONS["palletize"]
FEED, RO, TANK = "BW-WT-FEED01", "BW-WT-RO01", "BW-WT-TK01"
COMPRESSOR, CHILLER, PUMP, METER = (
    "BW-UT-CMP01", "BW-UT-CHL01", "BW-UT-PMP01", "BW-UT-PWR01",
)
FG = "BW-WH-FG01"
LINE_AREA, PREP_AREA = "BW-FP", "BW-BP"

# Workspace-domain isolation: no other line's vocabulary may leak out.
FORBIDDEN_PATTERNS = (
    re.compile(r"assy", re.IGNORECASE),
    re.compile(r"tipa", re.IGNORECASE),
    re.compile(r"pre-assy", re.IGNORECASE),
    re.compile(r"sso2", re.IGNORECASE),
    re.compile(r"rso2", re.IGNORECASE),
    re.compile(r"ap05_jam", re.IGNORECASE),
    re.compile(r"\bAP\d{2}\b"),
)

# Calculated KPIs belong to FactoriX IIoT / PlantOS, never to VF raw facts.
FORBIDDEN_KPI_FIELDS = (
    "oee", "availability", "performance_pct", "quality_pct", "energy_per",
    "utilization", "health_score", "predictive",
)


def _factory() -> BottledWaterFactory:
    return BottledWaterFactory(
        line_config_path=LINE_YAML,
        factory_config_path=FACTORY_YAML,
    )


def _run(factory: BottledWaterFactory, steps: int, dt: float = 1.0) -> None:
    for _ in range(steps):
        factory.step(dt)


def _signal(snapshot: dict, node_id: str, signal_id: str):
    return snapshot["nodes"][node_id]["signals"][signal_id]["value"]


def _digest(snapshot: dict) -> str:
    import hashlib

    canonical = json.dumps(snapshot, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _trace_station_units(factory: BottledWaterFactory, station_id: str) -> int:
    """Independent per-station completion count, straight from the line trace."""
    return len({
        event.wip_id
        for event in factory.controller.line.trace
        if event.event_type == "STATION_COMPLETE" and event.position == station_id
    })


@pytest.fixture()
def client(monkeypatch):
    """Fresh app with the server-side clock disabled for determinism."""
    monkeypatch.delenv("BOTTLED_WATER_CONFIG", raising=False)
    monkeypatch.delenv("BOTTLED_WATER_FACTORY_CONFIG", raising=False)
    app = create_app(config_path=APP_CONFIG, dt_s=1.0, factory_autorun=False)
    with TestClient(app) as test_client:
        test_client.post("/bottled-water-demo/reset")
        yield test_client


# ═══════════════════════════════════════════════════════════════
# B4-1 / B4-2 — server-side autonomous runtime, browser-independent
# ═══════════════════════════════════════════════════════════════

def test_b4_01_start_progresses_server_side_without_any_advance_call(
    monkeypatch,
):
    """START progresses production on the server with no /advance from a client."""
    monkeypatch.delenv("BOTTLED_WATER_CONFIG", raising=False)
    monkeypatch.delenv("BOTTLED_WATER_FACTORY_CONFIG", raising=False)
    app = create_app(
        config_path=APP_CONFIG,
        dt_s=1.0,
        factory_autorun=True,
        factory_tick_interval_s=0.05,
    )
    with TestClient(app) as autonomous:
        autonomous.post("/bottled-water-demo/start")
        deadline = time.time() + 10.0
        snapshot = autonomous.get("/bottled-water-demo/factory").json()
        while (time.time() < deadline
               and snapshot["factory"]["simulation_time_s"] < NOMINAL_DWELL_S):
            time.sleep(0.05)
            snapshot = autonomous.get("/bottled-water-demo/factory").json()

    assert snapshot["factory"]["run_state"] == "RUNNING"
    assert snapshot["factory"]["simulation_time_s"] >= NOMINAL_DWELL_S
    assert snapshot["target_line"]["dwell_number"] >= 1
    assert snapshot["target_line"]["counts"]["total"] >= 1
    # The tank/aggregate models progressed too, not just the line.
    assert snapshot["balances"]["water"]["raw_water_feed_total_m3"] > 0.0
    assert snapshot["balances"]["energy"]["plant_energy_total_kwh"] > 0.0


def test_b4_02_simulation_runs_with_the_b3_page_never_opened(monkeypatch):
    """Not opening the B3 page at all must not affect simulation progress."""
    monkeypatch.delenv("BOTTLED_WATER_CONFIG", raising=False)
    monkeypatch.delenv("BOTTLED_WATER_FACTORY_CONFIG", raising=False)
    app = create_app(
        config_path=APP_CONFIG,
        dt_s=1.0,
        factory_autorun=True,
        factory_tick_interval_s=0.05,
    )
    with TestClient(app, raise_server_exceptions=True) as autonomous:
        # Only the factory projection is ever requested — no skin, no assets.
        autonomous.post("/bottled-water-demo/start")
        deadline = time.time() + 10.0
        first = autonomous.get("/bottled-water-demo/factory").json()
        time.sleep(0.3)
        second = autonomous.get("/bottled-water-demo/factory").json()
        while (time.time() < deadline
               and second["factory"]["simulation_time_s"] < 20.0):
            time.sleep(0.05)
            second = autonomous.get("/bottled-water-demo/factory").json()

    assert first["factory"]["simulation_time_s"] >= 0.0
    assert second["factory"]["simulation_time_s"] > first["factory"][
        "simulation_time_s"]
    assert second["target_line"]["counts"]["total"] >= 1


def test_b4_02b_the_skin_never_posts_a_production_step():
    """The B3 skin is observer-only: it polls state and posts no step."""
    js = (STATIC / "bottled_water_demo.js").read_text(encoding="utf-8")

    assert "/advance" not in js
    posts = re.findall(r"bw(?:Post|Action)\('([^']+)'\)", js)
    assert sorted(posts) == ["/pause", "/reset", "/resume", "/start", "/stop"]
    # It reads state and it does not carry a client-side production clock.
    assert "bwGet('/state')" in js


# ═══════════════════════════════════════════════════════════════
# B4-3 … B4-6 — control semantics
# ═══════════════════════════════════════════════════════════════

def test_b4_03_pause_freezes_target_line_and_aggregate_progression():
    factory = _factory()
    factory.start()
    _run(factory, 100)
    running = factory.snapshot()
    assert running["factory"]["simulation_time_s"] == 100.0
    assert running["target_line"]["counts"]["total"] == 5

    factory.pause()
    _run(factory, 200)
    paused = factory.snapshot()

    assert paused["factory"]["run_state"] == LineRunState.PAUSED.value
    assert paused["factory"]["simulation_time_s"] == 100.0
    assert paused["factory"]["production_elapsed_s"] == 100.0
    assert paused["target_line"]["counts"] == running["target_line"]["counts"]
    assert paused["target_line"]["simulation_time_s"] == running["target_line"][
        "simulation_time_s"]
    # Every conserved quantity is frozen; only the instantaneous load reading
    # differs (a paused plant reports standby, and no simulated time passes, so
    # no energy accrues either).
    assert paused["balances"]["water"] == running["balances"]["water"]
    assert paused["balances"]["materials"] == running["balances"]["materials"]
    assert paused["balances"]["finished_goods"] == running["balances"][
        "finished_goods"]
    assert paused["balances"]["energy"]["plant_energy_total_kwh"] == running[
        "balances"]["energy"]["plant_energy_total_kwh"]


def test_b4_04_resume_continues_from_the_preserved_state():
    factory = _factory()
    factory.start()
    _run(factory, 100)
    factory.pause()
    _run(factory, 50)
    held = factory.snapshot()

    factory.resume()
    assert factory.controller.run_state is LineRunState.RUNNING
    _run(factory, 100)
    resumed = factory.snapshot()

    assert held["factory"]["simulation_time_s"] == 100.0
    assert resumed["factory"]["simulation_time_s"] == 200.0
    assert resumed["target_line"]["counts"]["total"] == 10
    # No state was rebuilt: the tank and counters carried over.
    assert resumed["balances"]["water"]["raw_water_feed_total_m3"] > held[
        "balances"]["water"]["raw_water_feed_total_m3"]


def test_b4_05_stop_halts_progression_without_becoming_fault():
    factory = _factory()
    factory.start()
    _run(factory, 100)
    before = factory.snapshot()

    factory.stop()
    assert factory.controller.run_state is LineRunState.STOPPED
    _run(factory, 200)
    after = factory.snapshot()

    assert after["factory"]["run_state"] == "STOPPED"
    assert after["target_line"]["counts"] == before["target_line"]["counts"]
    assert after["target_line"]["dwell_number"] == before["target_line"][
        "dwell_number"]
    assert after["balances"]["materials"] == before["balances"]["materials"]
    assert after["nodes"]["BW-DEMO-01"]["signals"]["operating_state"][
        "value"] == "STOPPED"
    # STOP is a controlled stop, never a fault.
    assert "FAULT" not in json.dumps(after)
    assert all(
        entry["signals"].get("operating_state", {}).get("value") != "FAULT"
        for entry in after["nodes"].values()
    )
    # The plant stays energized: only standby/base load accrues energy, so the
    # cumulative meter still only moves forward.
    assert after["balances"]["energy"]["plant_energy_total_kwh"] >= before[
        "balances"]["energy"]["plant_energy_total_kwh"]
    assert after["balances"]["energy"]["plant_active_power_kw"] < before[
        "balances"]["energy"]["plant_active_power_kw"]


def test_b4_06_reset_returns_the_deterministic_initial_state():
    fresh = _factory()
    factory = _factory()
    factory.start()
    _run(factory, 300)
    factory.pause()
    _run(factory, 40)

    factory.reset()
    initial = factory.snapshot()

    assert factory.controller.run_state is LineRunState.STOPPED
    assert initial["factory"]["simulation_time_s"] == 0.0
    assert initial["factory"]["production_elapsed_s"] == 0.0
    assert initial["target_line"]["counts"] == {"total": 0, "good": 0,
                                                "reject": 0}
    assert initial["target_line"]["units_on_line"] == 0
    assert initial["balances"]["materials"]["preform_count"] == 0
    assert initial["balances"]["finished_goods"]["dispatch_count"] == 0
    assert initial["balances"]["water"]["tank_volume_m3"] == pytest.approx(
        TANK_CAPACITY_M3 * RAW_CONFIG["water_treatment"][
            "tank_initial_fill_fraction"])
    assert _digest(initial) == _digest(fresh.snapshot())


# ═══════════════════════════════════════════════════════════════
# B4-7 — deterministic replay
# ═══════════════════════════════════════════════════════════════

def test_b4_07_identical_control_sequences_produce_identical_state_traces():
    traces = []
    for _ in range(2):
        factory = _factory()
        factory.start()
        _run(factory, 250)
        factory.pause()
        _run(factory, 30)
        factory.resume()
        _run(factory, 250)
        traces.append([
            _digest(factory.snapshot()) for _ in range(1)
        ] + [_digest(factory.snapshot())])

    assert traces[0] == traces[1]

    other = _factory()
    other.start()
    _run(other, 251)
    assert _digest(other.snapshot()) != traces[0][0]


def test_b4_07b_step_size_does_not_change_simulation_truth():
    """step(N) and N x step(1) must reach the same deterministic state."""
    coarse = _factory()
    fine = _factory()
    coarse.start()
    fine.start()

    for _ in range(20):
        coarse.step(20.0)
        _run(fine, 20)

    assert _digest(coarse.snapshot()) == _digest(fine.snapshot())


def test_b4_07c_no_wall_clock_leaks_into_simulation_facts():
    factory = _factory()
    factory.start()
    _run(factory, 20)
    first = factory.snapshot()
    time.sleep(0.25)
    second = factory.snapshot()

    assert _digest(first) == _digest(second)


# ═══════════════════════════════════════════════════════════════
# B4-8 / B4-9 / B4-10 — hierarchy, taxonomy and fact attribution
# ═══════════════════════════════════════════════════════════════

def test_b4_08_b1_hierarchy_appears_exactly_with_one_parent_per_asset():
    factory = _factory()
    factory.start()
    _run(factory, 60)
    snapshot = factory.snapshot()

    expected: dict[str, str] = {}
    for area in TOPOLOGY["areas"]:
        expected[area["id"]] = TOPOLOGY["plant"]["id"]
        for asset in area.get("assets", ()):
            expected[asset["id"]] = area["id"]

    nodes = snapshot["nodes"]
    assert snapshot["plant_id"] == TOPOLOGY["plant"]["id"]
    assert set(nodes) == set(expected) | {TOPOLOGY["plant"]["id"]}

    for node_id, entry in nodes.items():
        assert entry["source_id"] == node_id
        assert entry["entity_type"] in ("plant", "area", "asset")
        assert entry["parent_source_id"] == expected.get(node_id)
        assert entry["role"]
    assert nodes[TOPOLOGY["plant"]["id"]]["parent_source_id"] is None

    # Every asset has exactly one parent, and it is an area of the plant.
    area_ids = {area["id"] for area in TOPOLOGY["areas"]}
    for node_id, entry in nodes.items():
        if entry["entity_type"] == "asset":
            assert entry["parent_source_id"] in area_ids
    asset_counts = sum(
        1 for entry in nodes.values() if entry["entity_type"] == "asset"
    )
    assert asset_counts == sum(len(a.get("assets", ())) for a in TOPOLOGY["areas"])


def test_b4_09_source_ids_are_unique_and_the_blower_is_not_duplicated():
    _topology, nodes = load_hierarchy(TOPOLOGY_YAML)
    ids = [node.source_id for node in nodes]

    assert len(ids) == len(set(ids))
    blowers = [node for node in nodes if "blow" in node.name.lower()]
    assert len(blowers) == 1
    assert blowers[0].source_id == "BW-FP-BLW01"
    assert blowers[0].parent_source_id == "BW-FP"

    # Bottle Preparation stays a logical area owning no physical asset.
    assert not [
        node for node in nodes if node.parent_source_id == PREP_AREA
    ]
    assert any(node.source_id == PREP_AREA and node.entity_type == "area"
               for node in nodes)


def test_b4_10_every_exposed_fact_is_attributeable_to_a_hierarchy_node():
    factory = _factory()
    factory.start()
    _run(factory, 120)
    snapshot = factory.snapshot()

    valid_nodes = set(snapshot["nodes"])
    seen = 0
    for source_id, signal_id, signal in factory.iter_node_signals(snapshot):
        seen += 1
        assert source_id in valid_nodes
        assert signal_id
        assert set(signal) == {
            "value", "unit", "quality", "provenance", "simulation_time_s",
        }
        assert signal["unit"]
        assert signal["quality"] == "GOOD"
        assert signal["provenance"] in ("SIMULATED_RAW", "CONFIGURED_TARGET")
        assert isinstance(signal["simulation_time_s"], (int, float))
        assert "workspace_id" in snapshot["nodes"][source_id]
        assert snapshot["nodes"][source_id]["workspace_id"] == (
            snapshot["workspace_id"])

    assert seen > 40
    # No FactoriX platform canonical identity is invented by VF.
    combined = json.dumps(snapshot)
    for invented in ("vendor", "model_number", "serial", "canonical_id",
                     "platform_id", "device_id"):
        assert invented not in combined


# ═══════════════════════════════════════════════════════════════
# B4-11 / B4-12 — water and material conservation
# ═══════════════════════════════════════════════════════════════

def test_b4_11_water_balance_is_coherent_and_the_tank_stays_bounded():
    factory = _factory()
    factory.start()

    idle_seen = False
    previous_at_high = False
    for step in range(1500):
        factory.step(1.0)
        if step % 5:
            continue
        snapshot = factory.snapshot()
        water = snapshot["balances"]["water"]
        # Bounded tank: never below empty, never past the high-level limit.
        assert 0.0 <= water["tank_volume_m3"] <= water["tank_high_volume_m3"]
        assert water["tank_high_volume_m3"] <= TANK_CAPACITY_M3
        assert water["tank_volume_m3"] == pytest.approx(
            water["tank_initial_volume_m3"]
            + water["treated_water_total_m3"]
            - water["water_draw_total_m3"],
            abs=1e-12,
        )
        assert water["treated_water_total_m3"] == pytest.approx(
            water["raw_water_feed_total_m3"] * RECOVERY, rel=1e-12)
        assert water["ro_reject_total_m3"] == pytest.approx(
            water["raw_water_feed_total_m3"]
            - water["treated_water_total_m3"], rel=1e-12)
        assert water["product_water_total_m3"] <= water["water_draw_total_m3"]
        assert water["unmet_water_demand_m3"] == pytest.approx(0.0, abs=1e-12)
        assert water["water_request_total_m3"] == pytest.approx(
            water["water_draw_total_m3"] + water["unmet_water_demand_m3"],
            abs=1e-12,
        )
        assert water["water_request_total_m3"] == pytest.approx(
            water["product_water_total_m3"] / PROCESS_EFFICIENCY, rel=1e-12)

        feed_flow = _signal(snapshot, FEED, "water_flow")
        treated_flow = _signal(snapshot, RO, "production_flow")
        # The feed never delivers more than its nominal flow, and treated water
        # is always exactly the recovered fraction of the raw water taken.
        assert 0.0 <= feed_flow <= RAW_CONFIG["water_treatment"][
            "raw_water_flow_m3h"]
        assert treated_flow == pytest.approx(feed_flow * RECOVERY, rel=1e-6)
        at_high = water["tank_volume_m3"] >= water["tank_high_volume_m3"]
        if at_high:
            idle_seen = True
            if previous_at_high:
                # The tank entered this step already at the high limit, so the
                # feed must have delivered nothing.
                assert feed_flow == 0.0
        previous_at_high = at_high

    assert idle_seen, "the tank high-level rule never engaged"
    assert TANK_LOW_PCT < TANK_HIGH_PCT

    # Once the tank sits at the high limit the feed is fully shut off.
    assert _signal(factory.snapshot(), FEED, "water_flow") == 0.0


def test_b4_11b_the_tank_level_rule_has_hysteresis_and_drains():
    factory = _factory()
    factory.start()

    at_high = None
    for _ in range(1500):
        factory.step(1.0)
        snapshot = factory.snapshot()
        water = snapshot["balances"]["water"]
        if water["tank_volume_m3"] >= water["tank_high_volume_m3"]:
            at_high = snapshot
            break
    assert at_high is not None, "the tank never reached the high-level rule"

    factory.step(1.0)
    saturated = factory.snapshot()
    assert _signal(saturated, FEED, "water_flow") == 0.0
    assert _signal(saturated, RO, "production_flow") == 0.0
    assert _signal(saturated, FEED, "operating_state") == "IDLE"

    for _ in range(400):
        factory.step(1.0)
    after = factory.snapshot()

    high_water = at_high["balances"]["water"]
    later_water = after["balances"]["water"]
    assert later_water["tank_volume_m3"] < high_water["tank_volume_m3"]
    assert later_water["water_draw_total_m3"] > high_water["water_draw_total_m3"]
    assert later_water["water_draw_total_m3"] == pytest.approx(
        later_water["product_water_total_m3"]
        + later_water["other_loss_total_m3"],
        abs=1e-12,
    )
    # The feed stays latched off while the level is inside the hysteresis band.
    assert later_water["tank_volume_m3"] > later_water["tank_low_volume_m3"]
    assert _signal(after, FEED, "water_flow") == 0.0


def test_b4_12_consumption_follows_real_production_counts():
    factory = _factory()
    factory.start()
    for _ in range(20):
        factory.step(NOMINAL_DWELL_S)
    snapshot = factory.snapshot()

    line = factory.controller.line
    filled = _trace_station_units(factory, FILL)
    capped = _trace_station_units(factory, CAP)
    labeled = _trace_station_units(factory, LABEL)
    packed = _trace_station_units(factory, CASE_PACK)

    materials = snapshot["balances"]["materials"]
    water = snapshot["balances"]["water"]

    # Preforms follow units introduced; downstream material follows the units
    # that actually reached that station.
    assert materials["preform_count"] == line.total_count
    assert materials["cap_count"] == capped
    assert materials["label_count"] == labeled
    assert materials["case_count"] == packed // RAW_CONFIG["packaging"][
        "bottles_per_case"]
    assert materials["pallet_count"] == materials["case_count"] // (
        RAW_CONFIG["packaging"]["cases_per_pallet"])

    # Filled water is exactly the bottles that were actually filled.
    assert water["product_water_total_m3"] == pytest.approx(
        filled * BOTTLE_VOLUME_M3, rel=1e-9)
    assert water["water_draw_total_m3"] == pytest.approx(
        water["product_water_total_m3"] / PROCESS_EFFICIENCY, rel=1e-9)
    # Downstream material can never exceed upstream material.
    assert labeled <= capped <= filled <= materials["preform_count"]


def test_b4_12b_rejected_units_still_consume_already_used_material():
    """A FAIL at Inspection ejects the bottle after cap and fill were consumed."""
    text = LINE_YAML.read_text(encoding="utf-8")
    derived = text.replace("    scenario: PASS\n", "    scenario: ALWAYS_FAIL\n", 1)
    assert derived != text
    factory_text = FACTORY_YAML.read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="dday-b4-") as tmp:
        line_path = Path(tmp) / "line.yaml"
        line_path.write_text(derived, encoding="utf-8")
        factory_path = Path(tmp) / "factory.yaml"
        factory_path.write_text(factory_text, encoding="utf-8")

        factory = BottledWaterFactory(line_path, factory_path)
        factory.start()
        for _ in range(20):
            factory.step(NOMINAL_DWELL_S)
        snapshot = factory.snapshot()

        rejects = snapshot["target_line"]["counts"]["reject"]
        materials = snapshot["balances"]["materials"]
        filled = _trace_station_units(factory, FILL)
        capped = _trace_station_units(factory, CAP)
        labeled = _trace_station_units(factory, LABEL)

        assert rejects > 0
        assert capped >= rejects, "rejected bottles must still consume caps"
        assert materials["cap_count"] == capped
        assert materials["label_count"] == labeled <= capped
        # Water was consumed for every bottle that reached the filler.
        assert snapshot["balances"]["water"]["product_water_total_m3"] == (
            pytest.approx(filled * BOTTLE_VOLUME_M3, rel=1e-9))
        assert filled >= capped >= rejects


# ═══════════════════════════════════════════════════════════════
# DDAY-B4-C01 — unmet water demand + B3 evidence restore
# ═══════════════════════════════════════════════════════════════

B3_BASELINE = "23b6208266751a8c508b0d96fd7a736dffc5676c"
B3_EVIDENCE_FILES = (
    ".ai-harness/sa-review/evidence/DDAY-B3/generate_evidence.py",
    ".ai-harness/sa-review/evidence/DDAY-B3/smoke_bottled_water_ui.py",
)


def test_c01_unmet_water_demand_is_preserved_and_later_satisfied():
    """Empty-tank Filler demand must not disappear; later inventory pays it.

    Pre-fix ``_apply_draw()`` did ``pending = 0`` after taking ``min(pending,
    tank)``, so a starved request was silently destroyed. That is the SA
    blocker on Issue #106 / PR #101.
    """
    factory = _factory()
    request = 0.01
    factory._tank_volume_m3 = 0.0
    factory._pending_draw_m3 = request

    factory._apply_draw()
    starved = factory.snapshot()["balances"]["water"]
    assert starved["unmet_water_demand_m3"] == pytest.approx(request)
    assert starved["water_draw_total_m3"] == pytest.approx(0.0)
    assert starved["water_request_total_m3"] == pytest.approx(request)
    assert starved["tank_volume_m3"] == pytest.approx(0.0)

    factory._tank_volume_m3 = 0.004
    factory._apply_draw()
    partial = factory.snapshot()["balances"]["water"]
    assert partial["unmet_water_demand_m3"] == pytest.approx(0.006)
    assert partial["water_draw_total_m3"] == pytest.approx(0.004)
    assert partial["water_request_total_m3"] == pytest.approx(request)
    assert partial["tank_volume_m3"] == pytest.approx(0.0)

    factory._tank_volume_m3 = 0.02
    factory._apply_draw()
    paid = factory.snapshot()["balances"]["water"]
    assert paid["unmet_water_demand_m3"] == pytest.approx(0.0)
    assert paid["water_draw_total_m3"] == pytest.approx(request)
    assert paid["water_request_total_m3"] == pytest.approx(request)
    assert paid["tank_volume_m3"] == pytest.approx(0.014)


def test_c01_starved_fill_completions_keep_the_request_ledger():
    """A real fill completion against an empty tank leaves unmet demand."""
    factory = _factory()
    factory.start()
    factory._tank_volume_m3 = 0.0
    factory._feed_enabled = False
    # Freeze the hysteresis latch so treatment cannot refill during this
    # starvation probe. The production path still creates real Filler demand.
    factory._update_feed_state = lambda running: None

    _run(factory, 80)
    water = factory.snapshot()["balances"]["water"]
    assert water["product_water_total_m3"] > 0.0
    expected_request = water["product_water_total_m3"] / PROCESS_EFFICIENCY
    assert water["unmet_water_demand_m3"] == pytest.approx(expected_request)
    assert water["water_draw_total_m3"] == pytest.approx(0.0)
    assert water["water_request_total_m3"] == pytest.approx(expected_request)

    factory._feed_enabled = True
    factory._tank_volume_m3 = expected_request + 0.05
    factory._apply_draw()
    paid = factory.snapshot()["balances"]["water"]
    assert paid["unmet_water_demand_m3"] == pytest.approx(0.0)
    assert paid["water_draw_total_m3"] == pytest.approx(expected_request)
    assert paid["water_request_total_m3"] == pytest.approx(
        paid["water_draw_total_m3"] + paid["unmet_water_demand_m3"])


def test_c01_accepted_b3_evidence_files_match_b3_baseline():
    """The two SA-named B3 evidence files must equal the closed B3 head."""
    import subprocess

    result = subprocess.run(
        ["git", "diff", "--name-only", B3_BASELINE, "HEAD", "--", *B3_EVIDENCE_FILES],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    dirty = [line for line in result.stdout.splitlines() if line.strip()]
    assert dirty == [], f"B3 evidence files differ from {B3_BASELINE}: {dirty}"

    worktree = subprocess.run(
        ["git", "diff", "--name-only", B3_BASELINE, "--", *B3_EVIDENCE_FILES],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    dirty_wt = [line for line in worktree.stdout.splitlines() if line.strip()]
    assert dirty_wt == [], (
        f"B3 evidence files differ from {B3_BASELINE} in the worktree: {dirty_wt}"
    )


# ═══════════════════════════════════════════════════════════════
# B4-13 / B4-14 — utilities causality and energy conservation
# ═══════════════════════════════════════════════════════════════

def test_b4_13_utilities_respond_causally_to_production_load():
    factory = _factory()
    factory.start()
    _run(factory, 200)
    running = factory.snapshot()

    assert _signal(running, COMPRESSOR, "air_pressure") == pytest.approx(
        AIR_SETPOINT_BAR - AIR_SAG_BAR, abs=1e-6)
    assert _signal(running, COMPRESSOR, "operating_state") == "RUNNING"
    assert _signal(running, COMPRESSOR, "active_power") == AIR_RUNNING_KW
    assert _signal(running, PUMP, "operating_state") == "RUNNING"
    assert _signal(running, FEED, "water_flow") > 0.0

    factory.stop()
    _run(factory, 120)
    stopped = factory.snapshot()

    # Production stopped -> air demand drops -> pressure recovers -> the
    # compressor unloads; the chiller and treatment feed follow. Support
    # equipment reports its own load state rather than a blanket STOPPED...
    assert _signal(stopped, COMPRESSOR, "air_pressure") == pytest.approx(
        AIR_SETPOINT_BAR, abs=1e-6)
    assert _signal(stopped, COMPRESSOR, "operating_state") == "IDLE"
    assert _signal(stopped, COMPRESSOR, "active_power") == AIR_STANDBY_KW
    assert _signal(stopped, CHILLER, "operating_state") == "IDLE"
    assert _signal(stopped, FEED, "water_flow") == 0.0
    assert _signal(stopped, RO, "production_flow") == 0.0
    # ... while process equipment of the stopped plant reports STOPPED.
    assert _signal(stopped, FEED, "operating_state") == "STOPPED"
    assert _signal(stopped, LINE_AREA, "operating_state") == "STOPPED"
    assert (stopped["balances"]["energy"]["plant_active_power_kw"]
            < running["balances"]["energy"]["plant_active_power_kw"])


def test_b4_14_energy_is_monotonic_and_integrated_from_power():
    factory = _factory()
    factory.start()

    previous = 0.0
    for step in range(400):
        factory.step(1.0)
        if step % 10:
            continue
        snapshot = factory.snapshot()
        total = snapshot["balances"]["energy"]["plant_energy_total_kwh"]
        assert total >= previous
        previous = total

    snapshot = factory.snapshot()
    asset_energy = sum(
        entry["signals"]["energy_total"]["value"]
        for entry in snapshot["nodes"].values()
        if "energy_total" in entry["signals"]
    )
    clock_s = snapshot["factory"]["simulation_time_s"]
    expected = asset_energy + BASE_LOAD_KW * clock_s / 3600.0

    assert snapshot["balances"]["energy"]["plant_energy_total_kwh"] == (
        pytest.approx(expected, rel=1e-12))
    assert _signal(snapshot, METER, "plant_energy_total") == snapshot[
        "balances"]["energy"]["plant_energy_total_kwh"]


def test_b4_14b_energy_only_accrues_when_simulated_time_advances():
    factory = _factory()
    factory.start()
    _run(factory, 60)
    running_energy = factory.snapshot()["balances"]["energy"][
        "plant_energy_total_kwh"]

    factory.pause()
    _run(factory, 200)
    assert factory.snapshot()["balances"]["energy"][
        "plant_energy_total_kwh"] == running_energy

    # Let the utilities settle to their stopped standby load, then integrate.
    factory.stop()
    _run(factory, 120)
    settled = factory.snapshot()
    before = settled["balances"]["energy"]["plant_energy_total_kwh"]
    standby_kw = settled["balances"]["energy"]["plant_active_power_kw"]
    # A stopped plant draws only base + standby load, far below full production.
    assert standby_kw < 30.0

    _run(factory, 600)
    after = factory.snapshot()
    assert after["balances"]["energy"]["plant_energy_total_kwh"] > before
    # Pure power x time integration at the settled standby load.
    assert after["balances"]["energy"]["plant_energy_total_kwh"] == (
        pytest.approx(before + standby_kw * 600.0 / 3600.0, rel=1e-12))


# ═══════════════════════════════════════════════════════════════
# B4-15 — warehouse / finished goods follow-through
# ═══════════════════════════════════════════════════════════════

def test_b4_15_finished_goods_follow_completed_good_production():
    factory = _factory()
    factory.start()
    _run(factory, 40)
    early = factory.snapshot()
    assert early["balances"]["finished_goods"]["receipt_count"] == 0
    assert early["balances"]["finished_goods"]["inventory_count"] == 0
    assert early["balances"]["finished_goods"]["dispatch_count"] == 0

    for _ in range(20):
        factory.step(NOMINAL_DWELL_S)
    later = factory.snapshot()

    good = later["target_line"]["counts"]["good"]
    goods = later["balances"]["finished_goods"]
    assert good > 0
    assert goods["receipt_count"] == good == _signal(later, FG, "receipt_count")
    assert goods["dispatch_count"] > 0
    assert goods["inventory_count"] == goods["receipt_count"] - goods[
        "dispatch_count"]
    assert goods["inventory_count"] == _signal(later, FG, "inventory_count")
    assert goods["inventory_count"] >= 0

    before = goods["dispatch_count"]
    factory.stop()
    _run(factory, 120)
    drained = factory.snapshot()["balances"]["finished_goods"]
    assert drained["dispatch_count"] >= before
    assert drained["inventory_count"] == drained["receipt_count"] - drained[
        "dispatch_count"]
    assert drained["inventory_count"] >= 0


# ═══════════════════════════════════════════════════════════════
# B4-16 / B4-17 — raw-fact boundary and domain isolation
# ═══════════════════════════════════════════════════════════════

def test_b4_16_no_calculated_kpi_is_published(client):
    client.post("/bottled-water-demo/start")
    for _ in range(6):
        client.post("/bottled-water-demo/advance")

    payload = client.get("/bottled-water-demo/factory").json()
    serialised = json.dumps(payload).lower()

    for kpi in FORBIDDEN_KPI_FIELDS:
        assert kpi not in serialised, f"calculated KPI leaked: {kpi}"
    assert set(payload["balances"]) == {
        "water", "materials", "energy", "finished_goods",
    }
    assert set(payload["target_line"]["counts"]) == {"total", "good", "reject"}


def test_b4_17_no_foreign_line_semantics_leak_into_the_factory_state(client):
    client.post("/bottled-water-demo/start")
    for _ in range(8):
        client.post("/bottled-water-demo/advance")

    payload = client.get("/bottled-water-demo/factory").json()
    serialised = json.dumps(payload)
    for pattern in FORBIDDEN_PATTERNS:
        assert not pattern.search(serialised), (
            f"foreign-line vocabulary in the factory projection: {pattern.pattern}"
        )

    # Nor may it leak into the raw process event stream.
    for event in payload["target_line"]["recent_events"]:
        assert event["event_type"] != "LINE_ENTRY"


# ═══════════════════════════════════════════════════════════════
# B4-18 / B4-19 — B3 skin still works; regression intact
# ═══════════════════════════════════════════════════════════════

def test_b4_18_b3_target_line_ui_still_works_as_observer_and_control(client):
    page = client.get("/bottled-water-demo")
    assert page.status_code == 200 and "Bottled Water" in page.text
    for name in ("bottled_water_demo.js", "bottled_water_demo.css"):
        assert client.get(f"/bottled-water-demo/static/{name}").status_code == 200

    assert client.post("/bottled-water-demo/start").status_code == 200
    assert client.get("/bottled-water-demo/state").json()["run_state"] == "RUNNING"
    assert client.post("/bottled-water-demo/pause").json()["run_state"] == "PAUSED"
    assert client.post("/bottled-water-demo/resume").json()["run_state"] == "RUNNING"
    assert client.post("/bottled-water-demo/stop").json()["run_state"] == "STOPPED"
    assert client.post("/bottled-water-demo/reset").json()["run_state"] == "STOPPED"

    # The skin and the factory projection read the same runtime instance.
    factory = client.get("/bottled-water-demo/factory").json()
    state = client.get("/bottled-water-demo/state").json()
    assert factory["target_line"]["route"] == state["route"] == TOPOLOGY[
        "areas"][2]["route"]


def test_b4_19_legacy_and_other_endpoints_still_serve(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/").status_code == 200
    assert client.get("/assy-demo").status_code == 200
    assert client.get("/status").status_code == 200
    assert client.post(
        "/assy-demo/reset", json={"scenario": "HAPPY_PATH"}).status_code == 200

    # The Bottled Water factory must not be a second ASSY universe.
    routes = {route.path for route in client.app.routes}
    assert "/bottled-water-demo/factory" in routes
    assert not any(path.startswith("/bottled-water-demo/assy")
                   for path in routes)


def test_b4_19b_factory_owns_exactly_one_runtime_instance(client):
    factory = client.get("/bottled-water-demo/factory").json()
    client.post("/bottled-water-demo/start")
    for _ in range(4):
        client.post("/bottled-water-demo/advance")
    after = client.get("/bottled-water-demo/factory").json()
    state = client.get("/bottled-water-demo/state").json()

    assert after["target_line"]["counts"]["total"] == 4
    assert state["counts"]["total"] == 4
    assert after["factory"]["run_state"] == state["run_state"] == "RUNNING"
    assert after["target_line"] == state
    assert factory["factory"]["simulation_time_s"] == 0.0
    assert after["factory"]["simulation_time_s"] == 80.0


def test_b4_20_debug_advance_seam_stays_out_of_the_operator_surface(client):
    html = (STATIC / "bottled_water_demo.html").read_text(encoding="utf-8")
    buttons = re.findall(r'id="(bw-btn-[a-z]+)"', html)
    assert buttons == ["bw-btn-start", "bw-btn-pause", "bw-btn-resume",
                       "bw-btn-stop", "bw-btn-reset"]

    factory_js = (STATIC / "bottled_water_demo.js").read_text(encoding="utf-8")
    assert "/advance" not in factory_js
    assert client.post("/bottled-water-demo/advance").status_code == 200