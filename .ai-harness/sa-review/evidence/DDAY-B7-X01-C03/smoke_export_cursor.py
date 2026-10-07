#!/usr/bin/env python3
"""DDAY-B7-X01-C03 — export-session cursor publishes retained events once."""

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

from virtual_factory.protocols.mqtt_gateway import MqttGateway, MqttPublishError
from virtual_factory.workspaces.bottled_water import BottledWaterFactory
from virtual_factory.workspaces.plantos_export import (
    CONTRACT_VERSION,
    SIX_EVENT_TYPES,
    map_snapshot,
    publish_snapshot_via_existing_mqtt,
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
    def __init__(self, acked: bool = True) -> None:
        self.recorded: list[tuple] = []
        self.acked = acked

    def publish(self, topic, payload, qos=0, retain=False):
        self.recorded.append((topic, payload, qos))
        return _Ack(0, self.acked)

    def disconnect(self) -> None:
        self.disconnected = True


def _event_types(recorder: _Recorder) -> list[str]:
    types = []
    for topic, payload, _qos in recorder.recorded:
        if "/event/" in topic:
            types.append(json.loads(payload)["event_type"])
    return types


def main() -> int:
    print("=" * 72)
    print("DDAY-B7-X01-C03 — export-session event cursor / watermark")
    print("=" * 72)

    factory = BottledWaterFactory(WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml")
    factory.start()
    first_snap = factory.snapshot()
    first = _Recorder()
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=first), first_snap, factory.export_cursor
    )
    first_events = _event_types(first)
    claim(bool(first_events), "first observation publishes runtime events")
    claim(
        len([item for item in map_snapshot(first_snap) if item.kind == "event"])
        == len([
            event for event in first_snap.get("recent_events") or ()
            if event.get("event_type") in SIX_EVENT_TYPES
        ]),
        "map_snapshot remains a full projection of accepted recent_events",
    )

    second = _Recorder()
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=second), factory.snapshot(), factory.export_cursor
    )
    claim(_event_types(second) == [], "identical snapshot publishes zero additional events")

    factory.pause()
    third = _Recorder()
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=third), factory.snapshot(), factory.export_cursor
    )
    claim(len(_event_types(third)) == 1, "newly appended event publishes exactly once")

    factory.reset()
    claim(factory.export_cursor.seen_count == 0, "RESET clears the transport cursor")
    factory.start()
    after_reset = _Recorder()
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=after_reset), factory.snapshot(), factory.export_cursor
    )
    claim(bool(_event_types(after_reset)), "same transition after RESET publishes again")
    claim(CONTRACT_VERSION == "dday-bw-b1-v2", "contract remains dday-bw-b1-v2")

    fail = _Recorder(acked=False)

    class _FailEvents(_Recorder):
        def publish(self, topic, payload, qos=0, retain=False):
            self.recorded.append((topic, payload, qos))
            return _Ack(0, "/event/" not in topic)

    factory2 = BottledWaterFactory(WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml")
    factory2.start()
    failed = False
    try:
        publish_snapshot_via_existing_mqtt(
            MqttGateway(client=_FailEvents()), factory2.snapshot(), factory2.export_cursor
        )
    except MqttPublishError as exc:
        failed = "ACK not confirmed" in str(exc)
    claim(failed, "unacked event publish is an explicit failure")
    claim(factory2.export_cursor.seen_count == 0, "failed ACK does not mark the cursor")
    claim(fail.recorded == [], "fail-closed recorder was not used for success path")

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
