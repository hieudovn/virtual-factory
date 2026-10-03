"""DDAY-B3 — Bottled Water 2D target-line skin (API + skin asset) tests.

Governed by .ai-harness/tasks/DDAY-B3.json (authored from SA Issue #104).

These tests exercise the real FastAPI app backed by the real B2 Bottled Water
runtime — no mocked line data. They cover the UI/API binding, the frozen station
order, operator control semantics, the inspection indication, the read-only
selection context and workspace isolation of the visual skin.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from virtual_factory.ui.api import create_app

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC = REPO_ROOT / "src" / "virtual_factory" / "ui" / "static"
BW_CONFIG = REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday" / "line.yaml"

EXPECTED_ROUTE = [
    "BW-FP-BLW01",   # Blower / Infeed
    "BW-FP-RIN01",   # Rinser
    "BW-FP-FIL01",   # Filler
    "BW-FP-CAP01",   # Capper
    "BW-FP-INS01",   # Inspection
    "BW-FP-LAB01",   # Labeler
    "BW-FP-CPK01",   # Case Packer
    "BW-FP-PAL01",   # Palletizer
]
INSPECTION = "BW-FP-INS01"

# Workspace-domain isolation: the Bottled Water skin must not carry the visual
# vocabulary of any other line.
FORBIDDEN_SKIN_PATTERNS = (
    re.compile(r"assy", re.IGNORECASE),
    re.compile(r"tipa", re.IGNORECASE),
    re.compile(r"pre-assy", re.IGNORECASE),
    re.compile(r"sso2", re.IGNORECASE),
    re.compile(r"rso2", re.IGNORECASE),
    re.compile(r"ap05_jam", re.IGNORECASE),
    re.compile(r"\bAP\d{2}\b"),
)

SKIN_ASSETS = (
    STATIC / "bottled_water_demo.html",
    STATIC / "bottled_water_demo.js",
    STATIC / "bottled_water_demo.css",
)


@pytest.fixture()
def client(monkeypatch):
    """Fresh app bound to a freshly reset Bottled Water runtime."""
    monkeypatch.delenv("BOTTLED_WATER_CONFIG", raising=False)
    app = create_app(config_path=REPO_ROOT / "configs" / "plants" / "continuous_mvp_01.yaml", dt_s=1.0)
    with TestClient(app) as test_client:
        test_client.post("/bottled-water-demo/reset")
        yield test_client


def _state(client) -> dict:
    response = client.get("/bottled-water-demo/state")
    assert response.status_code == 200
    return response.json()


def _start(client) -> None:
    """START the line (idempotent) — the runtime only advances while RUNNING."""
    client.post("/bottled-water-demo/start")


def _run_cycles(client, cycles: int) -> dict:
    """Run `cycles` production cycles the way the skin's clock does."""
    _start(client)
    state = _state(client)
    for _ in range(cycles):
        state = client.post("/bottled-water-demo/advance").json()
    return state


def _event_window(client, limit: int = 200) -> dict:
    """State projection with a wide event window (the skin accumulates too)."""
    response = client.get(f"/bottled-water-demo/state?limit={limit}")
    assert response.status_code == 200
    return response.json()


# ═══════════════════════════════════════════════════════════════
# B3-1 — dedicated UI route reachable and bound to the B2 runtime
# ═══════════════════════════════════════════════════════════════

def test_b3_01_ui_route_and_static_assets_are_served(client):
    page = client.get("/bottled-water-demo")
    assert page.status_code == 200
    assert "text/html" in page.headers["content-type"]
    assert "Bottled Water" in page.text

    for name in ("bottled_water_demo.js", "bottled_water_demo.css"):
        asset = client.get(f"/bottled-water-demo/static/{name}")
        assert asset.status_code == 200
        assert asset.text.strip()


def test_b3_01b_state_is_bound_to_the_b2_runtime_not_mocked(client):
    state = _state(client)

    assert state["workspace_id"] == "bottled-water-dday"
    assert state["line_id"] == "BW-FP"
    assert state["unit_type"] == "bottle"
    assert state["product_code"] == "WATER-500ML"
    assert state["run_state"] == "STOPPED"
    assert state["counts"] == {"total": 0, "good": 0, "reject": 0}
    assert state["units_on_line"] == 0

    # Advancing the real runtime must move the served facts.
    after = _run_cycles(client, 1)
    assert after["counts"]["total"] == 1
    assert after["dwell_number"] == 1
    assert after["simulation_time_s"] > 0
    assert after["units_on_line"] == 1


# ═══════════════════════════════════════════════════════════════
# B3-2 — all 8 frozen stations visible in correct order
# ═══════════════════════════════════════════════════════════════

def test_b3_02_all_eight_stations_in_frozen_order(client):
    state = _state(client)

    assert state["route"] == EXPECTED_ROUTE
    assert [s["station_id"] for s in state["stations"]] == EXPECTED_ROUTE
    assert [s["sequence"] for s in state["stations"]] == list(range(8))
    assert len(state["route"]) == 8
    assert state["quality_checkpoints"] == [INSPECTION]


def test_b3_02b_skin_defines_distinct_artwork_for_every_station():
    js = (STATIC / "bottled_water_demo.js").read_text(encoding="utf-8")

    # One named artwork builder per frozen station, plus a bottle token.
    artwork = re.findall(r"^  ([a-z]+)\(\) \{", js, re.MULTILINE)
    for kind in ("blower", "rinser", "filler", "capper", "inspection",
                 "labeler", "packer", "palletizer"):
        assert kind in artwork, f"missing station artwork: {kind}"

    for station_id in EXPECTED_ROUTE:
        assert f"'{station_id}'" in js, f"station {station_id} not mapped in the skin"

    # The station order is read from the runtime route, not hard-coded twice.
    assert "state.route" in js
    assert "bwComputeLayout" in js


# ═══════════════════════════════════════════════════════════════
# B3-3 — workspace-specific skin, no other line's vocabulary
# ═══════════════════════════════════════════════════════════════

def test_b3_03_skin_assets_carry_no_foreign_line_vocabulary():
    for path in SKIN_ASSETS:
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_SKIN_PATTERNS:
            match = pattern.search(text)
            assert match is None, (
                f"{path.name}: leaked {match.group(0)!r}"
            )


def test_b3_03b_skin_does_not_reuse_the_other_line_skin_assets(client):
    for path in SKIN_ASSETS:
        text = path.read_text(encoding="utf-8")
        assert "assy_demo" not in text, f"{path.name} references the other skin"

    # The Bottled Water page must load only its own assets.
    page = client.get("/bottled-water-demo").text
    assert "bottled_water_demo.css" in page
    assert "bottled_water_demo.js" in page
    assert "assy_demo" not in page


def test_b3_03c_api_projection_carries_no_foreign_line_vocabulary(client):
    _run_cycles(client, 9)

    serialised = str(client.get("/bottled-water-demo/state").json())
    for pattern in FORBIDDEN_SKIN_PATTERNS:
        match = pattern.search(serialised)
        assert match is None, f"API projection leaked {match.group(0)!r}"


# ═══════════════════════════════════════════════════════════════
# B3-4 — bottle movement corresponds to runtime positions
# ═══════════════════════════════════════════════════════════════

def test_b3_04_occupied_stations_match_advancing_runtime_positions(client):
    _run_cycles(client, 3)
    state = _state(client)

    occupied = [s["station_id"] for s in state["stations"] if s["is_occupied"]]
    indices = sorted(EXPECTED_ROUTE.index(sid) for sid in occupied)

    # Units index together, so occupancy is a contiguous stretch of the route.
    assert indices == list(range(indices[0], indices[0] + len(indices)))
    assert state["units_on_line"] == len(occupied)

    for station in state["stations"]:
        if station["is_occupied"]:
            assert station["unit_id"].startswith("BTL-")
            assert station["unit_type"] == "bottle"
            assert station["unit_status"]


def test_b3_04b_units_progress_downstream_between_ticks(client):
    _run_cycles(client, 2)
    first = {s["station_id"]: s["unit_id"] for s in _state(client)["stations"]}

    _run_cycles(client, 1)
    second = {s["station_id"]: s["unit_id"] for s in _state(client)["stations"]}

    # Every unit that stayed on the line moved to a strictly later station.
    for station_id, unit_id in first.items():
        if not unit_id:
            continue
        later = [sid for sid, uid in second.items() if uid == unit_id]
        if later:
            assert EXPECTED_ROUTE.index(later[0]) > EXPECTED_ROUTE.index(station_id)

    # The skin animates that movement rather than teleporting bottles.
    js = (STATIC / "bottled_water_demo.js").read_text(encoding="utf-8")
    assert "requestAnimationFrame" in js
    assert "prefers-reduced-motion" in js


# ═══════════════════════════════════════════════════════════════
# B3-5 — operator controls preserve B2 semantics
# ═══════════════════════════════════════════════════════════════

def test_b3_05_start_pause_resume_stop_reset_preserve_b2_semantics(client):
    assert _state(client)["run_state"] == "STOPPED"

    # STOP is refused before START: everything stays frozen.
    client.post("/bottled-water-demo/advance")
    assert _state(client)["counts"]["total"] == 0

    assert client.post("/bottled-water-demo/start").json()["run_state"] == "RUNNING"
    running = _run_cycles(client, 2)
    assert running["counts"]["total"] == 2

    # PAUSE freezes progression and preserves the state.
    paused = client.post("/bottled-water-demo/pause").json()
    assert paused["run_state"] == "PAUSED"
    frozen = _state(client)
    for _ in range(3):
        client.post("/bottled-water-demo/advance")
    assert _state(client) == frozen

    # RESUME continues from the preserved state.
    assert client.post("/bottled-water-demo/resume").json()["run_state"] == "RUNNING"
    resumed = _run_cycles(client, 1)
    assert resumed["simulation_time_s"] == frozen["simulation_time_s"] + frozen["nominal_dwell_s"]
    assert resumed["counts"]["total"] == frozen["counts"]["total"] + 1

    # STOP is a controlled stop, not a fault.
    stopped = client.post("/bottled-water-demo/stop").json()
    assert stopped["run_state"] == "STOPPED"
    assert stopped["operating_state"] == "STOPPED"
    before_stop = stopped["simulation_time_s"]
    client.post("/bottled-water-demo/advance")
    assert _state(client)["simulation_time_s"] == before_stop
    assert "FAULT" not in str(_state(client))

    # RESET returns the line to its known initial state.
    reset = client.post("/bottled-water-demo/reset").json()
    assert reset["run_state"] == "STOPPED"
    assert reset["counts"] == {"total": 0, "good": 0, "reject": 0}
    assert reset["units_on_line"] == 0
    assert reset["simulation_time_s"] == 0.0
    assert reset["dwell_number"] == 0
    assert reset["stations"] == [
        {"sequence": i, "station_id": sid, "unit_id": "", "unit_type": "",
         "product_code": "", "unit_status": "", "is_occupied": False,
         "is_quality_checkpoint": sid == INSPECTION, "last_disposition": ""}
        for i, sid in enumerate(EXPECTED_ROUTE)
    ]


def test_b3_05b_control_surface_exposes_only_the_allowed_operator_controls(client):
    """Exactly START/PAUSE/RESUME/STOP/RESET are exposed as operator controls."""
    page = (STATIC / "bottled_water_demo.html").read_text(encoding="utf-8")
    buttons = re.findall(r'id="(bw-btn-[a-z]+)"', page)
    assert buttons == ["bw-btn-start", "bw-btn-pause", "bw-btn-resume",
                       "bw-btn-stop", "bw-btn-reset"]

    # No manual operator-decision surface exists in the page.
    lowered = page.lower()
    for forbidden in ("checklist", "approve", "disposition", "rework",
                      "release", "retry", "manual"):
        assert forbidden not in lowered, f"skin page exposes {forbidden!r}"

    # The skin can only call the five operator controls plus the clock tick.
    js = (STATIC / "bottled_water_demo.js").read_text(encoding="utf-8")
    calls = re.findall(r"bw(?:Post|Action)\('([^']+)'\)", js)
    assert sorted(calls) == ["/advance", "/pause", "/reset", "/resume", "/start", "/stop"]

    # No quality-decision endpoint is reachable from the skin or the API.
    for path in ("/bottled-water-demo/disposition", "/bottled-water-demo/decision",
                 "/bottled-water-demo/release", "/bottled-water-demo/retry",
                 "/bottled-water-demo/rework", "/bottled-water-demo/checklist"):
        assert client.post(path).status_code == 404, f"{path} unexpectedly exists"


# ═══════════════════════════════════════════════════════════════
# B3-6 — counts and line state track runtime facts
# ═══════════════════════════════════════════════════════════════

def test_b3_06_counts_and_state_track_the_runtime(client):
    _run_cycles(client, 8)
    state = _state(client)

    assert state["counts"]["total"] == 8
    assert state["counts"]["good"] == 1
    assert state["counts"]["reject"] == 0
    assert state["counts"]["good"] + state["counts"]["reject"] <= state["counts"]["total"]
    assert state["run_state"] == "RUNNING"
    assert state["operating_state"] == "RUNNING"

    page = (STATIC / "bottled_water_demo.html").read_text(encoding="utf-8")
    for field in ("bw-total", "bw-good", "bw-reject", "bw-run-state",
                  "bw-operating-state", "bw-sim-time", "bw-dwell"):
        assert f'id="{field}"' in page, f"missing fact display: {field}"


def test_b3_06b_projection_publishes_no_calculated_kpi(client):
    """Raw facts only: no OEE/KPI vocabulary, no derived ratio fields."""
    _run_cycles(client, 6)
    state = _state(client)

    assert set(state["counts"]) == {"total", "good", "reject"}
    serialised = str(state).lower()
    for kpi in ("oee", "availability", "performance_pct", "quality_pct",
                "energy_per", "utilization", "health_score"):
        assert kpi not in serialised


# ═══════════════════════════════════════════════════════════════
# B3-7 — inspection PASS / FAIL / reject observable
# ═══════════════════════════════════════════════════════════════

def test_b3_07_inspection_pass_is_observable(client):
    _run_cycles(client, 8)
    state = _event_window(client)
    inspection = next(s for s in state["stations"] if s["station_id"] == INSPECTION)

    assert inspection["is_quality_checkpoint"] is True
    assert inspection["last_disposition"] == "PASS"

    results = [e for e in state["recent_events"]
               if e["event_type"] == "QUALITY_RESULT" and e["station_id"] == INSPECTION]
    assert results, "inspection result must appear in the event feed"


def test_b3_07c_event_window_covers_a_whole_production_cycle(client):
    """The default window must not drop a cycle's events between polls."""
    _run_cycles(client, 6)
    default_window = _state(client)["recent_events"]
    wide_window = _event_window(client)["recent_events"]

    assert len(default_window) == 60
    assert len(wide_window) > len(default_window)

    # A full cycle emits more than one event, so the window must span a cycle:
    # the default projection must contain at least one complete dwell marker.
    dwell_marks = [e for e in default_window if e["event_type"] == "DWELL_META"]
    assert dwell_marks, "default event window dropped the cycle markers"


def test_b3_07b_inspection_failure_and_reject_are_observable(client, monkeypatch):
    """A failing inspection must be visible without any manual disposition."""
    import tempfile

    text = BW_CONFIG.read_text(encoding="utf-8")
    derived = text.replace("    scenario: PASS\n", "    scenario: ALWAYS_FAIL\n", 1)
    assert derived != text

    with tempfile.TemporaryDirectory(prefix="dday-b3-") as tmp:
        failing = Path(tmp) / "line-fail.yaml"
        failing.write_text(derived, encoding="utf-8")
        monkeypatch.setenv("BOTTLED_WATER_CONFIG", str(failing))

        app = create_app(
            config_path=REPO_ROOT / "configs" / "plants" / "continuous_mvp_01.yaml",
            dt_s=1.0,
        )
        with TestClient(app) as failing_client:
            failing_client.post("/bottled-water-demo/reset")
            failing_client.post("/bottled-water-demo/start")
            for _ in range(12):
                state = failing_client.post("/bottled-water-demo/advance").json()
            state = failing_client.get(
                "/bottled-water-demo/state?limit=200").json()

            inspection = next(
                s for s in state["stations"] if s["station_id"] == INSPECTION)
            assert inspection["last_disposition"] in ("FAIL", "NG")
            assert state["counts"]["reject"] == 8
            assert state["counts"]["good"] == 0
            assert state["last_reject"].startswith("BTL-")

            events = state["recent_events"]
            assert any(e["event_type"] == "REJECT" for e in events)

            # The result came from the line, with no operator decision endpoint.
            assert failing_client.post(
                "/bottled-water-demo/disposition").status_code == 404

    js = (STATIC / "bottled_water_demo.js").read_text(encoding="utf-8")
    assert "no manual disposition exists" in js


# ═══════════════════════════════════════════════════════════════
# B3-8 — selection opens useful context, read-only
# ═══════════════════════════════════════════════════════════════

def test_b3_08_station_selection_context_is_available(client):
    _run_cycles(client, 3)
    js = (STATIC / "bottled_water_demo.js").read_text(encoding="utf-8")

    assert "bwSelectStation" in js
    assert "bwOpenPopup" in js
    data = _state(client)
    assert any(s["is_occupied"] for s in data["stations"])
    assert any("last_disposition" in s for s in data["stations"])


def test_b3_08b_unit_inspector_returns_runtime_context(client):
    _run_cycles(client, 8)
    state = _state(client)
    unit_id = next(s["unit_id"] for s in state["stations"] if s["unit_id"])

    response = client.get(f"/bottled-water-demo/unit/{unit_id}")
    assert response.status_code == 200
    detail = response.json()

    assert detail["unit_id"] == unit_id
    assert detail["unit_type"] == "bottle"
    assert detail["product_code"] == "WATER-500ML"
    assert detail["current_station_id"] in EXPECTED_ROUTE
    assert isinstance(detail["quality_records"], list)

    # Selection is read-only: no decision field is returned or accepted.
    assert "disposition_endpoint" not in detail
    assert client.post(f"/bottled-water-demo/unit/{unit_id}").status_code == 405
    assert client.get("/bottled-water-demo/unit/BTL-999999").status_code == 404


def test_b3_08c_skin_interaction_is_selection_only():
    js = (STATIC / "bottled_water_demo.js").read_text(encoding="utf-8")

    assert "This panel is read-only." in js
    # The only POSTs are the five operator controls plus the presentation tick.
    posts = re.findall(r"bw(?:Post|Action)\('([^']+)'\)", js)
    assert sorted(posts) == sorted(["/start", "/pause", "/resume", "/stop", "/reset", "/advance"])


# ═══════════════════════════════════════════════════════════════
# B3-9 — no B4/B5/B6/B7 implementation mixed in
# ═══════════════════════════════════════════════════════════════

def test_b3_09_no_later_slice_implementation_in_the_skin():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in SKIN_ASSETS).lower()

    for later_slice in ("degradation", "degrading", "warning_phase", "recovery_phase",
                        "water treatment", "utilities", "warehouse", "palletizing_runtime",
                        "mqtt", "opcua", "plantos", "docker", "dockerfile"):
        assert later_slice not in combined, f"skin contains later-slice concern: {later_slice}"


def test_b3_09b_api_exposes_no_later_slice_endpoint(client):
    paths = {route.path for route in client.app.routes}
    bw_paths = {p for p in paths if p.startswith("/bottled-water-demo")}

    assert bw_paths == {
        "/bottled-water-demo",
        "/bottled-water-demo/state",
        "/bottled-water-demo/static/{filename}",
        "/bottled-water-demo/unit/{unit_id}",
        "/bottled-water-demo/start",
        "/bottled-water-demo/pause",
        "/bottled-water-demo/resume",
        "/bottled-water-demo/stop",
        "/bottled-water-demo/reset",
        "/bottled-water-demo/advance",
    }


# ═══════════════════════════════════════════════════════════════
# B3-10 — existing UI/API behaviour is unaffected
# ═══════════════════════════════════════════════════════════════

def test_b3_10_other_endpoints_still_serve(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/").status_code == 200
    assert client.get("/assy-demo").status_code == 200
    assert client.get("/status").status_code == 200


def test_b3_10b_bottled_water_runtime_control_is_independent_of_the_other_line(client):
    """Driving the Bottled Water line must not disturb the other demo line."""
    other_before = client.post("/assy-demo/reset", json={"scenario": "HAPPY_PATH"}).json()
    client.post("/bottled-water-demo/start")
    _run_cycles(client, 4)
    other_after = client.post("/assy-demo/snapshot").json()

    assert other_before["sub_line_id"] == other_after["sub_line_id"]
    assert other_after["simulation_time_s"] == 0.0
    assert _state(client)["counts"]["total"] == 4
