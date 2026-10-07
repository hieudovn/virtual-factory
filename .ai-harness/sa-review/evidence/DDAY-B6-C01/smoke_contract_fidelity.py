#!/usr/bin/env python3
"""DDAY-B6-C01 — live envelope, dictionary, durable-example, and gap smoke."""

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
sys.path.insert(0, str(REPO_ROOT / "tests"))

from test_dday_b6_c01_contract_fidelity import collect_durable_examples
from virtual_factory.workspaces.plantos_compat import compatibility_status
from virtual_factory.workspaces.plantos_export import (
    CONTRACT_VERSION,
    PLANT_SOURCE_ID,
    UnmappedExportError,
    lookup_signal_entry,
    selected_signal_keys,
)

APP_CONFIG = REPO_ROOT / "configs" / "plants" / "continuous_mvp_01.yaml"
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
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
    print("DDAY-B6-C01 — VF→PlantOS contract fidelity smoke")
    print("=" * 72)

    print("\n[1] Durable B5 examples and fail-closed dictionary")
    examples = collect_durable_examples()
    claim(examples["capper_warning"]["capper_phase"] == "WARNING",
          "Capper warning envelope captured")
    claim(examples["capper_downtime"]["capper_phase"] == "INTERMITTENT_STOP",
          "Capper downtime envelope captured")
    claim(examples["capper_recovery"]["capper_phase"] == "RECOVERY",
          "Capper recovery envelope captured")
    claim(examples["compressor_warning"]["compressor_phase"] == "LOW_PRESSURE_WARNING",
          "Compressor warning envelope captured")
    claim(examples["compressor_undersupply"]["compressor_phase"] == "UNDERSUPPLY",
          "Compressor undersupply envelope captured")
    types = {item["payload"]["event_type"] for item in examples["final"]["events"]}
    claim("ALARM_RAISED" in types, "ALARM_RAISED present")
    claim("DOWNTIME_START" in types, "DOWNTIME_START present")
    classified = any(
        item["payload"].get("downtime_code") == "DT-AIR"
        for item in examples["final"]["events"]
        if item["asset_id"] == "BW-UT-CMP01"
    )
    claim(classified, "Compressor classification stamps exported events")
    claim(len(examples["process_history"]) >= 8, "process history samples exist")
    claim(len(examples["condition_history"]) >= 8, "condition history samples exist")
    closed = False
    try:
        lookup_signal_entry("BW-FP-RIN01", "operating_state")
    except UnmappedExportError:
        closed = True
    claim(closed, "unmapped signal fails closed")

    print("\n[2] HTTP export envelope")
    port = _free_port()
    server, _thread = _serve(port)
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=20.0) as client:
            client.post("/bottled-water-demo/reset")
            overview = client.get("/bottled-water-demo/overview")
            claim(overview.status_code == 200, "accepted overview still served")
            claim('data-area="BW-FP"' in overview.text, "overview still shows BW-FP")
            client.post("/bottled-water-demo/start")
            deadline = time.time() + 12
            factory = client.get("/bottled-water-demo/factory").json()
            while time.time() < deadline and factory["factory"]["simulation_time_s"] < 6:
                time.sleep(0.2)
                factory = client.get("/bottled-water-demo/factory").json()
            export = client.get("/bottled-water-demo/plantos-export").json()
            claim(export["contract_version"] == CONTRACT_VERSION,
                  "export discloses B1 contract_version")
            claim(export["plant_source_id"] == PLANT_SOURCE_ID,
                  "export discloses plant_source_id")
            claim(export["adapter_role"] == "vf_unit_test_aid_not_plantos_historian",
                  "in-memory sink is disclosed as adapter-only")
            claim(export["plantos_ingestion_proven"] is False,
                  "does not claim PlantOS ingestion")
            claim(export["plantos_historian_proven"] is False,
                  "does not claim PlantOS historian")
            payload = export["current_values"][0]["payload"]
            claim(payload["contract_version"] == CONTRACT_VERSION, "payload contract_version")
            claim(payload["source_id"] == payload["asset_id"], "source_id aliases asset_id")
            claim(bool(UTC_RE.match(payload["timestamp"])), "UTC timestamp shape")
            claim("simulation_time_s" in payload, "separate simulation_time_s")
            claim("timestamp_s" not in payload, "timestamp_s is not the boundary field")
            exported = {
                (item["asset_id"], item["signal_or_event"])
                for item in export["current_values"]
            }
            claim(exported <= set(selected_signal_keys()),
                  "HTTP export stays inside the selected dictionary")
    finally:
        server.should_exit = True

    print("\n[3] PlantOS repo gap")
    status = compatibility_status(live_probe=True)
    claim(status["plantos_ingestion_proven"] is False, "ingest not claimed")
    claim(status["plantos_historian_proven"] is False, "historian not claimed")
    claim(status["plantos_repo_present_locally"] is False, "PlantOS repo absent locally")
    claim(status["wtp_ingest_used"] is False, "WTP ingest not used as substitute")
    print(json.dumps(status["gap"]["minimal_sa_authorization_required"], indent=2))

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
