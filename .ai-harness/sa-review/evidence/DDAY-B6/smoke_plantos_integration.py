#!/usr/bin/env python3
"""DDAY-B6 — live PlantOS-local export + overview smoke over real HTTP."""

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

APP_CONFIG = REPO_ROOT / "configs" / "plants" / "continuous_mvp_01.yaml"
STATIC = REPO_ROOT / "src" / "virtual_factory" / "ui" / "static"
AREAS = ("BW-WT", "BW-BP", "BW-FP", "BW-UT", "BW-WH")
TOPIC_RE = re.compile(
    r"^virtual-factory/bottled-water-dday/(signal|event)/[A-Z0-9-]+/[A-Za-z0-9_]+$"
)
FORBIDDEN_KPI = (
    "oee", "availability", "performance_pct", "quality_pct",
    "energy_per", "utilization", "health_score",
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


def _serve(port: int):
    import uvicorn
    from virtual_factory.ui.api import create_app

    app = create_app(
        config_path=APP_CONFIG,
        dt_s=1.0,
        factory_autorun=True,
        factory_tick_interval_s=0.05,
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


def main() -> int:
    import httpx

    print("=" * 72)
    print("DDAY-B6 — PlantOS local integration + whole-factory overview smoke")
    print("=" * 72)

    port = _free_port()
    server, _thread = _serve(port)
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=20.0) as client:
            client.post("/bottled-water-demo/reset")
            overview_page = client.get("/bottled-water-demo/overview")
            claim(overview_page.status_code == 200, "overview page is served")
            body = overview_page.text
            for area in AREAS:
                claim(f'data-area="{area}"' in body, f"overview shows area {area}")
            claim('href="/bottled-water-demo"' in body,
                  "BW-FP drills down to the existing F&P page")
            claim("treated water → filler" in body, "process relationship WT→FP")
            claim("compressed air → line" in body, "utility relationship UT→FP")

            detail = client.get("/bottled-water-demo")
            claim(detail.status_code == 200, "existing F&P page still served")
            claim("bw-svg" in detail.text, "F&P page still has the line canvas")
            claim('href="/bottled-water-demo/overview"' in detail.text,
                  "F&P page links back to the overview")

            client.post("/bottled-water-demo/start")
            deadline = time.time() + 12
            factory = client.get("/bottled-water-demo/factory").json()
            while time.time() < deadline and factory["factory"]["simulation_time_s"] < 6:
                time.sleep(0.2)
                factory = client.get("/bottled-water-demo/factory").json()
            claim(factory["factory"]["simulation_time_s"] >= 6,
                  "autonomous factory advanced without a second simulator")

            export = client.get("/bottled-water-demo/plantos-export").json()
            claim(export["ingestion_path"] == "local_in_memory_plantos_compatible",
                  "local PlantOS-compatible ingestion path is used")
            claim(export["id_resolution"]["resolved"] is True,
                  "published IDs resolve against frozen plantos_mapping")
            claim(export["id_resolution"]["areas"] == list(AREAS),
                  "resolved areas are the five accepted factory areas")
            claim(export["current_values"], "export publishes current values")
            claim(export["historian"], "export retains historian samples")
            claim(export["message_count"] > 0, "historian has ingested messages")
            topics_ok = all(TOPIC_RE.match(item["topic"])
                            for item in export["current_values"][:20])
            claim(topics_ok, "current-value topics match the B1 MQTT pattern")

            fp_total = factory["nodes"]["BW-FP"]["signals"]["total_count"]["value"]
            current = {
                (item["asset_id"], item["signal_or_event"]): item["payload"]["value"]
                for item in export["current_values"]
            }
            claim(current[("BW-FP", "total_count")] == fp_total,
                  "export current value equals factory snapshot")
            claim(export["overview"]["areas"][2]["id"] == "BW-FP",
                  "overview view is derived from the same factory")
            claim(export["overview"]["drill_down"]["BW-FP"] == "/bottled-water-demo",
                  "overview drill-down target is the existing F&P UI")

            serialised = json.dumps(export).lower()
            kpi_hits = [key for key in FORBIDDEN_KPI if key in serialised]
            claim(kpi_hits == [], f"no PlantOS KPI fields in export ({kpi_hits})")
            claim("degradation_factor" not in serialised,
                  "hidden ground truth is not exported")
    finally:
        server.should_exit = True

    print()
    if _failures:
        print(f"SMOKE FAILED ({len(_failures)} claim(s))")
        for item in _failures:
            print(f"  - {item}")
        return 1
    print("SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
