#!/usr/bin/env python3
"""DDAY-FR1 — mixed-cadence runtime profile smoke."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "src" / "virtual_factory").is_dir():
            return candidate
    raise RuntimeError("repository root not found")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
sys.path.insert(0, str(REPO_ROOT / "src"))

from virtual_factory.protocols.mqtt_gateway import MqttGateway
from virtual_factory.workspaces.bottled_water import BottledWaterFactory
from virtual_factory.workspaces.plantos_export import (
    CONTRACT_VERSION,
    SIX_EVENT_TYPES,
    load_runtime_profile,
    map_snapshot,
    profile_measurement_map,
    selected_signal_keys,
)

WORKSPACE = REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday"
_failures: list[str] = []


def claim(condition: bool, description: str) -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        _failures.append(description)


class _Ack:
    def __init__(self, rc: int = 0, acked: bool = True) -> None:
        self.rc = rc
        self.acked = acked

    def is_published(self) -> bool:
        return self.acked

    def wait_for_publish(self, timeout: float = 1.0) -> None:
        if not self.acked:
            raise TimeoutError("publish acknowledgement timed out")


class _Recorder:
    def __init__(self) -> None:
        self.recorded: list[tuple] = []

    def publish(self, topic, payload, qos=0, retain=False):
        self.recorded.append((topic, payload, qos))
        return _Ack(0, True)

    def disconnect(self) -> None:
        self.disconnected = True


def main() -> int:
    print("=" * 72)
    print("DDAY-FR1 — freeze Bottled Water D-Day runtime profile")
    print("=" * 72)

    profile = load_runtime_profile()
    mapped = profile_measurement_map(profile)
    exported = set(selected_signal_keys())
    claim(len(exported) == 22, "dictionary still exports 22 measurements")
    claim(set(mapped) == exported, "profile maps exactly those 22 measurements")
    claim(profile["contract_version"] == CONTRACT_VERSION, "profile stays dday-bw-b1-v2")
    claim(profile["events"]["types"] == list(SIX_EVENT_TYPES), "six event types remain event-driven")

    factory = BottledWaterFactory(WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml")
    factory.start()
    mapped_signals = [item for item in map_snapshot(factory.snapshot()) if item.kind == "signal"]
    claim(len(mapped_signals) == 22, "map_snapshot remains a full 22-signal projection")
    operating = [
        item for item in mapped_signals if item.signal_or_event == "operating_state"
    ]
    claim(operating == [], "operating_state is not a live measurement signal")

    first = _Recorder()
    factory.publish_live_mqtt(MqttGateway(client=first))
    first_signals = [item for item in first.recorded if "/signal/" in item[0]]
    claim(len(first_signals) == 22, "first observation publishes all 22 measurements")
    second = _Recorder()
    factory.publish_live_mqtt(MqttGateway(client=second))
    second_signals = [item for item in second.recorded if "/signal/" in item[0]]
    claim(second_signals == [], "identical snapshot does not republish measurements")

    factory.step(1.0)
    after_one = _Recorder()
    factory.publish_live_mqtt(MqttGateway(client=after_one))
    after_one_ids = {
        json.loads(payload)["signal_id"]
        for topic, payload, _qos in after_one.recorded
        if "/signal/" in topic
    }
    claim("motor_current" in after_one_ids, "FAST republishes after 1 s")
    claim("water_flow" not in after_one_ids, "SLOW does not republish after 1 s")
    claim("fill_rate" not in after_one_ids, "MEDIUM does not republish after 1 s")

    recorder = _Recorder()
    gateway = MqttGateway(client=recorder)
    factory.publish_live_mqtt(gateway)
    for _ in range(20):
        factory.step(1.0)
        factory.publish_live_mqtt(gateway)
    naive = 22 * 21
    total = len([item for item in recorder.recorded if "/signal/" in item[0]])
    claim(total < naive, "bounded run publishes fewer signals than every-snapshot spam")
    claim(total / 20.0 < 250.0, "bounded run stays under the 250 msg/s burst ceiling")
    drain = gateway.drain_pending(timeout_s=0.2)
    claim(drain.get("ok") is True, "accepted ACK harness has no undelivered backlog")

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
