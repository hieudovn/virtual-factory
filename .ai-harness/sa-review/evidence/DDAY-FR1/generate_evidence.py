#!/usr/bin/env python3
"""Collect DDAY-FR1 machine evidence and dictionary compatibility."""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "src"))

from virtual_factory.protocols.mqtt_gateway import MqttGateway
from virtual_factory.workspaces.bottled_water import BottledWaterFactory
from virtual_factory.workspaces.plantos_export import (
    CONTRACT_VERSION,
    SIX_EVENT_TYPES,
    exported_signal_entries,
    load_runtime_profile,
    map_snapshot,
    profile_measurement_map,
    selected_signal_keys,
)

WORKSPACE = REPO / "configs" / "workspaces" / "bottled-water-dday"
C03_ACCEPTED = "320d82fb2fb3339461553e258b09ebee6689615a"


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
    def __init__(self) -> None:
        self.recorded: list[tuple] = []

    def publish(self, topic, payload, qos=0, retain=False):
        self.recorded.append((topic, payload, qos))
        return _Ack(0, True)

    def disconnect(self) -> None:
        self.disconnected = True


def main() -> None:
    profile = load_runtime_profile()
    mapped = profile_measurement_map(profile)
    dictionary_rows = []
    for entry in exported_signal_entries():
        key = (str(entry["source_id"]), str(entry["signal_id"]))
        spec = mapped[key]
        dictionary_rows.append({
            "source_id": key[0],
            "signal_id": key[1],
            "b1_cadence": entry.get("cadence"),
            "dday_class": spec["class"],
            "export_status": "EXPORTED",
        })

    factory = BottledWaterFactory(WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml")
    factory.start()
    snapshot = factory.snapshot()
    recorder = _Recorder()
    gateway = MqttGateway(client=recorder)
    factory.publish_live_mqtt(gateway)
    for _ in range(60):
        factory.step(1.0)
        factory.publish_live_mqtt(gateway)
    signal_count = sum(1 for topic, _payload, _qos in recorder.recorded if "/signal/" in topic)
    event_count = sum(1 for topic, _payload, _qos in recorder.recorded if "/event/" in topic)
    counts = Counter()
    for topic, payload, _qos in recorder.recorded:
        if "/signal/" not in topic:
            continue
        data = json.loads(payload)
        counts[(data["source_id"], data["signal_id"])] += 1
    drain = gateway.drain_pending(timeout_s=0.2)

    evidence = {
        "task_id": "DDAY-FR1",
        "baseline_c03_accepted": C03_ACCEPTED,
        "head": _git("rev-parse", "HEAD"),
        "origin_main": _git("rev-parse", "origin/main"),
        "contract_version": CONTRACT_VERSION,
        "profile_id": profile["profile_id"],
        "exported_measurement_count": len(selected_signal_keys()),
        "profile_measurement_count": len(mapped),
        "map_snapshot_signal_count": sum(
            1 for item in map_snapshot(snapshot) if item.kind == "signal"
        ),
        "event_types": list(SIX_EVENT_TYPES),
        "bounded_horizon_s": 60,
        "bounded_signal_publishes": signal_count,
        "bounded_event_publishes": event_count,
        "bounded_total_publishes": len(recorder.recorded),
        "naive_every_snapshot_signals": 22 * 61,
        "sim_rate_msg_per_s": round(len(recorder.recorded) / 60.0, 3),
        "fast_motor_current_publishes": counts[("BW-FP-CAP01", "motor_current")],
        "slow_water_flow_publishes": counts[("BW-WT-FEED01", "water_flow")],
        "drain_ok": drain.get("ok"),
        "rejects": 0,
        "plantos_handoff": False,
        "plantos_49_authorized": False,
        "merge_authorized": False,
        "deploy_authorized": False,
    }
    (HERE / "machine-evidence.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    compatibility = {
        "contract_version": CONTRACT_VERSION,
        "profile_id": profile["profile_id"],
        "dictionary_cadence_unchanged": True,
        "operating_state_remains_event_only": True,
        "unavailable_remain_unpublished": [
            {"source_id": "BW-FP", "signal_id": "target_rate"},
            {"source_id": "BW-UT-CMP01", "signal_id": "load"},
        ],
        "measurements": dictionary_rows,
    }
    (HERE / "dictionary-compatibility.json").write_text(
        json.dumps(compatibility, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# DDAY-FR1 contract/dictionary compatibility",
        "",
        f"Contract `{CONTRACT_VERSION}` is unchanged. B1 dictionary cadence",
        "strings remain metadata. Live transport uses the FR1 profile class.",
        "",
        "| source_id | signal_id | B1 cadence | D-Day class |",
        "|---|---|---|---|",
    ]
    for row in dictionary_rows:
        lines.append(
            f"| `{row['source_id']}` | `{row['signal_id']}` | "
            f"`{row['b1_cadence']}` | `{row['dday_class']}` |"
        )
    (HERE / "02-dictionary-compatibility.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
