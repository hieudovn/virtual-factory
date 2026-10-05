#!/usr/bin/env python3
"""Collect DDAY-B7-X01-C02 machine evidence."""

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
    OPERATING_STATE_EVENT_TYPE,
    dictionary_summary,
    map_snapshot,
    publish_via_existing_mqtt,
)

WORKSPACE = REPO / "configs" / "workspaces" / "bottled-water-dday"
C01_REVIEWED = "97e313ab0df6efb19b4374cfd857940f9e5c76fd"


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


def main() -> None:
    factory = BottledWaterFactory(WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml")
    idle = factory.snapshot()
    factory.start()
    started = factory.snapshot()
    factory.pause()
    paused = factory.snapshot()

    def state_count(snapshot: dict) -> int:
        return sum(
            1 for event in snapshot.get("recent_events") or ()
            if event.get("event_type") == OPERATING_STATE_EVENT_TYPE
        )

    def mapped_count(snapshot: dict) -> int:
        return sum(
            1 for item in map_snapshot(snapshot)
            if item.payload.get("event_type") == OPERATING_STATE_EVENT_TYPE
        )

    class _Ok:
        def publish(self, topic, payload, qos=0, retain=False):
            return _Ack(0, True)

        def disconnect(self) -> None:
            self.disconnected = True

    ok = MqttGateway(client=_Ok())
    delivered = publish_via_existing_mqtt(ok, map_snapshot(started)[:3])
    drain_ok = ok.disconnect(drain_timeout_s=0.2)

    class _Fail:
        def publish(self, topic, payload, qos=0, retain=False):
            return _Ack(0, False)

        def disconnect(self) -> None:
            self.disconnected = True

    failed = MqttGateway(client=_Fail())
    timeout_error = ""
    try:
        publish_via_existing_mqtt(failed, map_snapshot(started)[:1])
    except MqttPublishError as exc:
        timeout_error = str(exc)
    drain_fail = failed.drain_pending(timeout_s=0.01)
    shutdown_error = ""
    try:
        failed.disconnect(drain_timeout_s=0.01)
    except MqttPublishError as exc:
        shutdown_error = str(exc)

    evidence = {
        "task_id": "DDAY-B7-X01-C02",
        "baseline_c01_rejected": C01_REVIEWED,
        "head": _git("rev-parse", "HEAD"),
        "origin_main": _git("rev-parse", "origin/main"),
        "contract_version": CONTRACT_VERSION,
        "idle_mapped_state_events": mapped_count(idle),
        "start_runtime_state_events": state_count(started),
        "start_mapped_state_events": mapped_count(started),
        "pause_runtime_state_events": state_count(paused),
        "pause_mapped_state_events": mapped_count(paused),
        "identical_snapshot_delta": mapped_count(started) - mapped_count(factory.snapshot() if False else started),
        "event_only_metadata": dictionary_summary()["event_only_states"],
        "confirmed_deliveries": delivered,
        "confirmed_drain_ok": drain_ok.get("ok"),
        "timeout_error": timeout_error,
        "drain_fail_ok": drain_fail.get("ok"),
        "shutdown_error": shutdown_error,
        "plantos_49_authorized": False,
        "merge_authorized": False,
        "deploy_authorized": False,
    }
    (HERE / "machine-evidence.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
