#!/usr/bin/env python3
"""Collect DDAY-B7-X01-C03 machine evidence."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "src"))

from virtual_factory.protocols.mqtt_gateway import MqttGateway, MqttPublishError
from virtual_factory.workspaces.bottled_water import BottledWaterFactory
from virtual_factory.workspaces.plantos_export import (
    CONTRACT_VERSION,
    SIX_EVENT_TYPES,
    map_snapshot,
    publish_snapshot_via_existing_mqtt,
)

WORKSPACE = REPO / "configs" / "workspaces" / "bottled-water-dday"
C02_REVIEWED = "39428b08ff5fbd19efe6dc0701bb64bafa73bf83"


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


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


def _event_count(recorder: _Recorder) -> int:
    return sum(1 for topic, _payload, _qos in recorder.recorded if "/event/" in topic)


def main() -> None:
    factory = BottledWaterFactory(WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml")
    factory.start()
    first_snap = factory.snapshot()
    first = _Recorder()
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=first), first_snap, factory.export_cursor
    )
    second = _Recorder()
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=second), factory.snapshot(), factory.export_cursor
    )
    factory.pause()
    third = _Recorder()
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=third), factory.snapshot(), factory.export_cursor
    )
    seen_before_reset = factory.export_cursor.seen_count
    factory.reset()
    cursor_after_reset = factory.export_cursor.seen_count
    factory.start()
    after_reset = _Recorder()
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=after_reset), factory.snapshot(), factory.export_cursor
    )

    long = BottledWaterFactory(WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml")
    long.start()
    for _ in range(220):
        long.step(1.0)
    long_snap = long.snapshot()
    all_six = _Recorder()
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=all_six), long_snap, long.export_cursor
    )
    replay = _Recorder()
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=replay), long.snapshot(), long.export_cursor
    )
    present = sorted({
        event["event_type"]
        for event in long_snap.get("recent_events") or ()
        if event.get("event_type") in SIX_EVENT_TYPES
    })

    class _FailEvents(_Recorder):
        def publish(self, topic, payload, qos=0, retain=False):
            self.recorded.append((topic, payload, qos))
            return _Ack(0, "/event/" not in topic)

    fail_factory = BottledWaterFactory(WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml")
    fail_factory.start()
    timeout_error = ""
    try:
        publish_snapshot_via_existing_mqtt(
            MqttGateway(client=_FailEvents()),
            fail_factory.snapshot(),
            fail_factory.export_cursor,
        )
    except MqttPublishError as exc:
        timeout_error = str(exc)

    evidence = {
        "task_id": "DDAY-B7-X01-C03",
        "baseline_c02_rejected": C02_REVIEWED,
        "head": _git("rev-parse", "HEAD"),
        "origin_main": _git("rev-parse", "origin/main"),
        "contract_version": CONTRACT_VERSION,
        "first_event_publishes": _event_count(first),
        "identical_snapshot_event_publishes": _event_count(second),
        "new_event_publishes": _event_count(third),
        "seen_before_reset": seen_before_reset,
        "cursor_after_reset": cursor_after_reset,
        "after_reset_event_publishes": _event_count(after_reset),
        "six_event_types_present": present,
        "six_type_first_publishes": _event_count(all_six),
        "six_type_replay_publishes": _event_count(replay),
        "map_snapshot_event_count": sum(
            1 for item in map_snapshot(first_snap) if item.kind == "event"
        ),
        "timeout_error": timeout_error,
        "failed_ack_cursor_seen": fail_factory.export_cursor.seen_count,
        "plantos_49_authorized": False,
        "merge_authorized": False,
        "deploy_authorized": False,
    }
    (HERE / "machine-evidence.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
