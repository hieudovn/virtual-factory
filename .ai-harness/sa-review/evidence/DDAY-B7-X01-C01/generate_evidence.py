#!/usr/bin/env python3
"""Collect DDAY-B7-X01-C01 machine evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "src"))

from virtual_factory.protocols.mqtt_gateway import DEFAULT_QOS, MqttGateway
from virtual_factory.workspaces.bottled_water import BottledWaterFactory
from virtual_factory.workspaces.plantos_export import (
    CONTRACT_VERSION,
    MQTT_QOS,
    SIX_EVENT_TYPES,
    TRANSPORT_KIND_EVENT_ONLY,
    dictionary_summary,
    map_snapshot,
    publish_via_existing_mqtt,
)

WORKSPACE = REPO / "configs" / "workspaces" / "bottled-water-dday"
C02_REVIEWED = "f0f5428e21d3f63f22c3e1419600dd63a30b1f75"
FROZEN = {
    "src/virtual_factory/workspaces/capper_degradation.py":
        "c5b2883a9a5ca50878a9cc7bab850ad0a296df19e73c0a6fc62c56a499e0891b",
    "src/virtual_factory/workspaces/compressor_pressure.py":
        "f35a639aced026e497edb53174034b207b86a6d0fa12db63fe7c80f18ca1ac08",
    "src/virtual_factory/ui/static/bottled_water_overview.html":
        "46ab475e5594014f0e2bd4384b0bb46e0623c6a8f2f4a453565346d1e961b8ae",
    "src/virtual_factory/ui/static/bottled_water_overview.js":
        "aba11b2b9c434da2c5aaec794904bd7e4278c9b2030188fccc53fe2cba093425",
    "src/virtual_factory/ui/static/bottled_water_overview.css":
        "8d4424b81772e591b8c5ce9ccb81fd5d03c4a9dd07517b942e877f94f4b21dc5",
}


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def main() -> None:
    factory = BottledWaterFactory(WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml")
    factory.start()
    for _ in range(12):
        factory.step(1.0)
    snapshot = factory.snapshot()
    messages = map_snapshot(snapshot)
    bundle = factory.plantos_export()
    recorded = []

    class _Fake:
        def publish(self, topic, payload, qos=0, retain=False):
            recorded.append({"topic": topic, "qos": qos})
            handle = type("Result", (), {})()
            handle.rc = 0
            handle.is_published = lambda: True
            handle.wait_for_publish = lambda timeout=1.0: None
            return handle

        def disconnect(self) -> None:
            self.disconnected = True

    gateway = MqttGateway(enabled=True, client=_Fake())
    published = publish_via_existing_mqtt(gateway, messages)
    drain = gateway.disconnect(drain_timeout_s=0.2)
    hashes = {
        rel: hashlib.sha256((REPO / rel).read_bytes()).hexdigest()
        for rel in FROZEN
    }
    evidence = {
        "task_id": "DDAY-B7-X01-C01",
        "baseline_c02_reviewed": C02_REVIEWED,
        "head": _git("rev-parse", "HEAD"),
        "origin_main": _git("rev-parse", "origin/main"),
        "contract_version": CONTRACT_VERSION,
        "mqtt_qos": MQTT_QOS,
        "default_qos": DEFAULT_QOS,
        "six_event_types": list(SIX_EVENT_TYPES),
        "export_dictionary": dictionary_summary(),
        "event_only_messages": [
            item.as_dict() for item in messages
            if item.payload.get("transport_kind") == TRANSPORT_KIND_EVENT_ONLY
        ],
        "measurement_operating_state_topics": [
            item.topic for item in messages
            if item.kind == "signal" and item.signal_or_event == "operating_state"
        ],
        "mqtt_publish_count": published,
        "mqtt_qos_values": sorted({item["qos"] for item in recorded}),
        "mqtt_drain": drain,
        "frozen_hashes_match": hashes == FROZEN,
        "frozen_hashes": hashes,
        "sample_envelope": bundle["current_values"][0]["payload"] if bundle["current_values"] else {},
        "plantos_49_authorized": False,
        "merge_authorized": False,
        "deploy_authorized": False,
    }
    (HERE / "machine-evidence.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    (HERE / "export-sample.json").write_text(
        json.dumps({
            "contract_version": bundle["contract_version"],
            "transport_semantics": bundle.get("transport_semantics"),
            "event_only_states": bundle.get("event_only_states"),
            "events": bundle.get("events"),
            "current_value_keys": [
                f"{item['asset_id']}.{item['signal_or_event']}"
                for item in bundle["current_values"]
            ],
        }, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
