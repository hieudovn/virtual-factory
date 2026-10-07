#!/usr/bin/env python3
"""DDAY-B7-X01-C02 — no synthesized state events; fail-closed QoS-1 ACK."""

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

from virtual_factory.protocols.mqtt_gateway import MqttGateway, MqttPublishError
from virtual_factory.workspaces.bottled_water import BottledWaterFactory
from virtual_factory.workspaces.plantos_export import (
    CONTRACT_VERSION,
    OPERATING_STATE_EVENT_TYPE,
    map_snapshot,
    publish_via_existing_mqtt,
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


def _state_events(snapshot) -> list:
    return [
        event for event in snapshot.get("recent_events") or ()
        if event.get("event_type") == OPERATING_STATE_EVENT_TYPE
    ]


def _mapped(snapshot) -> list:
    return [
        item for item in map_snapshot(snapshot)
        if item.payload.get("event_type") == OPERATING_STATE_EVENT_TYPE
    ]


def main() -> int:
    print("=" * 72)
    print("DDAY-B7-X01-C02 — no synthesized state events + fail-closed ACK")
    print("=" * 72)

    factory = BottledWaterFactory(WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml")
    idle = factory.snapshot()
    claim(len(_mapped(idle)) == 0, "idle snapshot has no synthesized state events")
    factory.start()
    started = factory.snapshot()
    claim(len(_state_events(started)) == 1, "start records one runtime MACHINE_STATE_CHANGED")
    claim(len(_mapped(started)) == 1, "start maps exactly that one state event")
    again = factory.snapshot()
    claim(len(_mapped(started)) == len(_mapped(again)),
          "identical snapshots add zero state events")
    factory.pause()
    paused = factory.snapshot()
    claim(len(_mapped(paused)) == len(_state_events(paused)),
          "pause maps only runtime state records")
    claim(CONTRACT_VERSION == "dday-bw-b1-v2", "contract remains dday-bw-b1-v2")

    class _Ok:
        def publish(self, topic, payload, qos=0, retain=False):
            return _Ack(rc=0, acked=True)

        def disconnect(self) -> None:
            self.disconnected = True

    ok = MqttGateway(client=_Ok())
    published = publish_via_existing_mqtt(ok, map_snapshot(paused)[:2])
    claim(published == 2, "confirmed ACK counts as delivered")
    claim(ok.disconnect(drain_timeout_s=0.2)["ok"] is True, "clean drain is successful shutdown")

    class _Timeout:
        def publish(self, topic, payload, qos=0, retain=False):
            return _Ack(rc=0, acked=False)

        def disconnect(self) -> None:
            self.disconnected = True

    timed = MqttGateway(client=_Timeout())
    timed_out = False
    try:
        publish_via_existing_mqtt(timed, map_snapshot(paused)[:1])
    except MqttPublishError as exc:
        timed_out = "ACK not confirmed" in str(exc)
    claim(timed_out, "ACK timeout is an explicit publish failure")
    drain = timed.drain_pending(timeout_s=0.01)
    claim(drain["ok"] is False, "drain timeout is not successful")
    shutdown_failed = False
    try:
        timed.disconnect(drain_timeout_s=0.01)
    except MqttPublishError as exc:
        shutdown_failed = "undelivered tail" in str(exc)
    claim(shutdown_failed, "undelivered tail cannot be a successful shutdown")

    class _Neg:
        def publish(self, topic, payload, qos=0, retain=False):
            return _Ack(rc=5, acked=True)

    neg = MqttGateway(client=_Neg())
    rc_failed = False
    try:
        neg.publish_raw("vf/neg", "x")
    except MqttPublishError as exc:
        rc_failed = "rc=5" in str(exc)
    claim(rc_failed, "negative rc is an explicit failure")

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
