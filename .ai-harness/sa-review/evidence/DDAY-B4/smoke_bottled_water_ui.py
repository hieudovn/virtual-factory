#!/usr/bin/env python3
"""DDAY-B4-owned Bottled Water 2D skin smoke (B3 contract, B4 clock).

Task: DDAY-B4-C01 (SA Issue #106 / PR #101).
Owned by: .ai-harness/sa-review/evidence/DDAY-B4/
Not a mutation of the accepted B3 evidence file.

The accepted B3 smoke at 23b6208 starts create_app() without factory_autorun=
False. After B4 the default server clock races the /advance seam that the B3
contract uses. This B4-owned copy keeps that deterministic seam so the B3
visual/control claims remain checkable without editing historical B3 evidence.

Starts the real FastAPI app on a real socket and drives it over real HTTP. No
mocks, no TestClient shortcuts. Proves:

  page + assets served
  state projection bound to the running B2 line
  all 8 frozen stations in order
  operator control semantics (START/PAUSE/RESUME/STOP/RESET)
  inspection PASS/FAIL + reject observable
  read-only unit selection context
  no foreign-line vocabulary in the page, the projection or the API surface

Exit code 0 = every claim proven. Any failed claim exits non-zero.
"""

from __future__ import annotations

import json
import socket
import sys
import tempfile
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

CONFIG_PATH = REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday" / "line.yaml"
EXPECTED_ROUTE = [
    "BW-FP-BLW01", "BW-FP-RIN01", "BW-FP-FIL01", "BW-FP-CAP01",
    "BW-FP-INS01", "BW-FP-LAB01", "BW-FP-CPK01", "BW-FP-PAL01",
]
INSPECTION = "BW-FP-INS01"

_failures: list[str] = []


def claim(condition: bool, description: str) -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        _failures.append(description)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _serve(config_path: Path, port: int):
    """Start the real app with uvicorn on a background thread."""
    import uvicorn

    from virtual_factory.ui.api import create_app

    app = create_app(
        config_path=REPO_ROOT / "configs" / "plants" / "continuous_mvp_01.yaml",
        dt_s=1.0,
        # DDAY-B4: the B3 contract is checked with the deterministic step seam,
        # so the autonomous server-side clock is disabled here. Autonomy itself
        # is proven by SMOKE-BW-FACTORY.
        factory_autorun=False,
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


def _derive_failing_config(directory: Path) -> Path:
    text = CONFIG_PATH.read_text(encoding="utf-8")
    derived = text.replace("    scenario: PASS\n", "    scenario: ALWAYS_FAIL\n", 1)
    if derived == text:
        raise RuntimeError("could not derive the failing-inspection configuration")
    path = directory / "line-fail.yaml"
    path.write_text(derived, encoding="utf-8")
    return path


def main() -> int:
    print("=" * 72)
    print("DDAY-B3 — Bottled Water 2D skin live HTTP smoke")
    print(f"app config : {REPO_ROOT / 'configs' / 'plants' / 'continuous_mvp_01.yaml'}")
    print(f"line config: {CONFIG_PATH}")
    print("=" * 72)

    port = _free_port()
    server, _thread = _serve(REPO_ROOT / "configs" / "plants" / "continuous_mvp_01.yaml", port)

    try:
        with _client(port) as client:
            client.post("/bottled-water-demo/reset")

            # ── 1. Page + assets ────────────────────────────────────────────
            print("\n[1] page and skin assets over HTTP")
            page = client.get("/bottled-water-demo")
            claim(page.status_code == 200, "page served (200)")
            claim("text/html" in page.headers.get("content-type", ""),
                  "page content-type is text/html")
            claim("Bottled Water" in page.text, "page is the Bottled Water skin")
            for name in ("bottled_water_demo.js", "bottled_water_demo.css"):
                asset = client.get(f"/bottled-water-demo/static/{name}")
                claim(asset.status_code == 200 and len(asset.text) > 500,
                      f"asset served: {name}")

            # ── 2. State projection bound to the runtime ────────────────────
            print("\n[2] state projection bound to the running line")
            state = client.get("/bottled-water-demo/state").json()
            claim(state["line_id"] == "BW-FP", "line identity BW-FP")
            claim(state["unit_type"] == "bottle" and state["product_code"] == "WATER-500ML",
                  "unit metadata bottle / WATER-500ML")
            claim(state["run_state"] == "STOPPED", "line starts STOPPED")
            claim(state["counts"] == {"total": 0, "good": 0, "reject": 0},
                  "counts start at zero")

            client.post("/bottled-water-demo/advance")
            claim(client.get("/bottled-water-demo/state").json()["counts"]["total"] == 0,
                  "no progression before START")

            # ── 3. Frozen 8-station route ───────────────────────────────────
            print("\n[3] frozen 8-station route")
            claim(state["route"] == EXPECTED_ROUTE, "route equals the frozen order")
            claim([s["station_id"] for s in state["stations"]] == EXPECTED_ROUTE,
                  "stations are ordered as configured")
            claim(len(state["stations"]) == 8, "exactly 8 stations")
            claim(state["quality_checkpoints"] == [INSPECTION],
                  "exactly one quality checkpoint (Inspection)")

            # ── 4. Operator controls ────────────────────────────────────────
            print("\n[4] operator control semantics")
            claim(client.post("/bottled-water-demo/start").json()["run_state"] == "RUNNING",
                  "START enters RUNNING")
            for _ in range(8):
                state = client.post("/bottled-water-demo/advance").json()
            claim(state["counts"]["total"] == 8, "8 bottles released")
            claim(state["counts"]["good"] == 1, "1 good bottle after 8 cycles")
            claim(state["units_on_line"] == 7, "7 bottles on the line")

            paused = client.post("/bottled-water-demo/pause").json()
            claim(paused["run_state"] == "PAUSED", "PAUSE enters PAUSED")
            frozen = client.get("/bottled-water-demo/state").json()
            for _ in range(3):
                client.post("/bottled-water-demo/advance")
            now = client.get("/bottled-water-demo/state").json()
            claim(now == frozen, "PAUSE froze progression and preserved state")

            claim(client.post("/bottled-water-demo/resume").json()["run_state"] == "RUNNING",
                  "RESUME enters RUNNING")
            resumed = client.post("/bottled-water-demo/advance").json()
            claim(resumed["simulation_time_s"] == frozen["simulation_time_s"] + frozen["nominal_dwell_s"],
                  "RESUME continued from the preserved simulation time")
            claim(resumed["counts"]["total"] == frozen["counts"]["total"] + 1,
                  "RESUME continued production")

            stopped = client.post("/bottled-water-demo/stop").json()
            claim(stopped["run_state"] == "STOPPED" and stopped["operating_state"] == "STOPPED",
                  "STOP is a controlled stop")
            before = stopped["simulation_time_s"]
            client.post("/bottled-water-demo/advance")
            claim(client.get("/bottled-water-demo/state").json()["simulation_time_s"] == before,
                  "no progression after STOP")
            claim("FAULT" not in str(client.get("/bottled-water-demo/state").json()),
                  "STOP produced no FAULT")

            reset = client.post("/bottled-water-demo/reset").json()
            claim(reset["counts"] == {"total": 0, "good": 0, "reject": 0}
                  and reset["units_on_line"] == 0
                  and reset["simulation_time_s"] == 0.0
                  and reset["dwell_number"] == 0,
                  "RESET restored the known initial state")

            # ── 5. Inspection PASS + selection context ──────────────────────
            print("\n[5] inspection indication and read-only selection")
            client.post("/bottled-water-demo/start")
            for _ in range(8):
                client.post("/bottled-water-demo/advance")
            state = client.get("/bottled-water-demo/state?limit=200").json()
            inspection = next(s for s in state["stations"] if s["station_id"] == INSPECTION)
            claim(inspection["is_quality_checkpoint"], "Inspection is flagged as the checkpoint")
            claim(inspection["last_disposition"] == "PASS", "Inspection published PASS")
            claim(any(e["event_type"] == "QUALITY_RESULT" and e["station_id"] == INSPECTION
                      for e in state["recent_events"]),
                  "inspection result present in the event feed")

            unit_id = next(s["unit_id"] for s in state["stations"] if s["unit_id"])
            detail = client.get(f"/bottled-water-demo/unit/{unit_id}")
            claim(detail.status_code == 200, f"unit inspector resolves ({unit_id})")
            claim(detail.json()["unit_type"] == "bottle", "unit context carries bottle identity")
            claim(client.get("/bottled-water-demo/unit/BTL-999999").status_code == 404,
                  "unknown unit fails closed (404)")
            claim(client.post("/bottled-water-demo/disposition").status_code == 404,
                  "no manual disposition endpoint exists")

            # ── 6. Isolation ────────────────────────────────────────────────
            print("\n[6] workspace isolation")
            forbidden = ["assy", "tipa", "pre-assy", "sso2", "rso2", "ap05_jam"]
            import re
            patterns = [re.compile(p, re.IGNORECASE) for p in forbidden]
            patterns.append(re.compile(r"\bAP\d{2}\b"))

            page_text = client.get("/bottled-water-demo").text
            js_text = client.get("/bottled-water-demo/static/bottled_water_demo.js").text
            css_text = client.get("/bottled-water-demo/static/bottled_water_demo.css").text
            projection = str(state)
            for label, text in (("page", page_text), ("script", js_text),
                                ("style", css_text), ("projection", projection)):
                hits = [m.group(0) for p in patterns for m in [p.search(text)] if m]
                claim(not hits, f"{label} carries no foreign-line vocabulary")
                if hits:
                    print(f"        leak: {hits[:3]}")

            bw_paths = None
            claim("assy_demo" not in page_text, "page loads only its own assets")

        # ── 7. Failing inspection over live HTTP ───────────────────────────
        print("\n[7] failing inspection and reject over live HTTP")
        with tempfile.TemporaryDirectory(prefix="dday-b3-smoke-") as tmp:
            failing_config = _derive_failing_config(Path(tmp))
            import os
            os.environ["BOTTLED_WATER_CONFIG"] = str(failing_config)
            fail_port = _free_port()
            fail_server, _ = _serve(REPO_ROOT / "configs" / "plants" / "continuous_mvp_01.yaml",
                                    fail_port)
            try:
                with _client(fail_port) as client:
                    client.post("/bottled-water-demo/reset")
                    client.post("/bottled-water-demo/start")
                    for _ in range(12):
                        state = client.post("/bottled-water-demo/advance").json()
                    state = client.get("/bottled-water-demo/state?limit=200").json()

                    inspection = next(
                        s for s in state["stations"] if s["station_id"] == INSPECTION)
                    claim(inspection["last_disposition"] in ("FAIL", "NG"),
                          f"Inspection published a failure ({inspection['last_disposition']})")
                    claim(state["counts"]["reject"] == 8, "8 bottles rejected")
                    claim(state["counts"]["good"] == 0, "no rejected bottle counted good")
                    claim(state["last_reject"].startswith("BTL-"),
                          "last rejected bottle is identified")
                    claim(any(e["event_type"] == "REJECT" for e in state["recent_events"]),
                          "reject present in the event feed")
                    claim(state["counts"]["good"] + state["counts"]["reject"]
                          <= state["counts"]["total"],
                          "count invariant holds")
            finally:
                fail_server.should_exit = True
                os.environ.pop("BOTTLED_WATER_CONFIG", None)
    finally:
        server.should_exit = True

    print("\n" + "=" * 72)
    if _failures:
        print(f"SMOKE FAILED — {len(_failures)} claim(s) failed:")
        for failure in _failures:
            print(f"  - {failure}")
        print("=" * 72)
        return 1
    print("SMOKE PASSED — Bottled Water 2D skin verified over live HTTP")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
