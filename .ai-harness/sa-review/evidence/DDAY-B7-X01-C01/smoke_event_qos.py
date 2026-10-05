#!/usr/bin/env python3
"""DDAY-B7-X01-C01 — event-only operating_state, v2 contract, QoS-1 drain smoke."""

from __future__ import annotations

import sys
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "src" / "virtual_factory").is_dir():
            return candidate
    raise RuntimeError("repository root not found")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
sys.path.insert(0, str(REPO_ROOT / "src"))

from virtual_factory.protocols.mqtt_gateway import DEFAULT_QOS, MqttGateway
from virtual_factory.workspaces.bottled_water import BottledWaterFactory
from virtual_factory.workspaces.plantos_export import (
    CONTRACT_VERSION,
    MQTT_QOS,
    OPERATING_STATE_EVENT_TYPE,
    SIX_EVENT_TYPES,
    TRANSPORT_KIND_EVENT_ONLY,
    UnmappedExportError,
    lookup_signal_entry,
    map_snapshot,
    publish_via_existing_mqtt,
    selected_event_entries,
    selected_signal_keys,
)

WORKSPACE = REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday"
_failures: list[str] = []


def claim(condition: bool, description: str) -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        _failures.append(description)


def main() -> int:
    print("=" * 72)
    print("DDAY-B7-X01-C01 — event-only operating_state + v2 + QoS-1 drain")
    print("=" * 72)

    factory = BottledWaterFactory(WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml")
    factory.start()
    for _ in range(8):
        factory.step(1.0)
    snapshot = factory.snapshot()
    messages = map_snapshot(snapshot)
    bundle = factory.plantos_export()

    signal_keys = {
        (item.asset_id, item.signal_or_event)
        for item in messages
        if item.kind == "signal"
    }
    claim(("BW-FP", "operating_state") not in signal_keys,
          "BW-FP.operating_state is not a measurement signal")
    claim(("BW-FP-CAP01", "operating_state") not in set(selected_signal_keys()),
          "Capper operating_state is not in the measurement dictionary")
    closed = False
    try:
        lookup_signal_entry("BW-UT-CMP01", "operating_state")
    except UnmappedExportError as exc:
        closed = "not a measurement" in str(exc)
    claim(closed, "compressor operating_state lookup fails as non-measurement")

    event_only = [
        item for item in messages
        if item.payload.get("transport_kind") == TRANSPORT_KIND_EVENT_ONLY
    ]
    claim(len(event_only) == 3, f"three event-only operating_state messages ({len(event_only)})")
    claim(all(item.payload["event_type"] == OPERATING_STATE_EVENT_TYPE for item in event_only),
          "event-only transport uses MACHINE_STATE_CHANGED")
    claim(all(item.payload.get("not_a_measurement") is True for item in event_only),
          "event-only payloads are marked not_a_measurement")
    types = [entry["event_type"] for entry in selected_event_entries()]
    claim(types == list(SIX_EVENT_TYPES), f"six event types remain {types}")
    claim(CONTRACT_VERSION == "dday-bw-b1-v2", "module contract_version is v2")
    claim(bundle["contract_version"] == CONTRACT_VERSION, "export bundle is v2")
    claim(all(item.payload["contract_version"] == CONTRACT_VERSION for item in messages),
          "every mapped payload is v2")

    recorded = []

    class _Fake:
        def publish(self, topic, payload, qos=0, retain=False):
            recorded.append((topic, payload, qos, retain))
            return type("Result", (), {"rc": 0})()

        def disconnect(self) -> None:
            self.disconnected = True

    gateway = MqttGateway(enabled=True, client=_Fake())
    published = publish_via_existing_mqtt(gateway, messages)
    claim(published == len(messages), "MQTT helper published every mapped message")
    claim(DEFAULT_QOS == MQTT_QOS == 1, "default MQTT QoS is 1")
    claim({item[2] for item in recorded} == {1}, "every publish_raw used QoS 1")
    summary = gateway.disconnect(drain_timeout_s=0.2)
    claim(summary["timed_out"] is False, "bounded drain completed before disconnect")
    claim(getattr(gateway.client, "disconnected", False) is True, "client disconnected after drain")

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
